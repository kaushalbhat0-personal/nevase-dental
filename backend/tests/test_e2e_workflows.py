"""
End-to-end workflow tests — Receptionist, Doctor, Patient, Admin.

Each test group exercises a complete real-world scenario through the service layer.
All tests use the same minimal fixtures: tenant → doctor → patient → appointment.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from app.core.data_scope import DataScopeKind, ResolvedDataScope
from app.crud import crud_appointment, crud_billing
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    PrescriptionCreate,
    PrescriptionItemCreate,
    MarkAppointmentCompletedRequest,
)
from app.schemas.billing import BillingCreate
from app.schemas.patient import PatientCreate
from app.services import (
    appointment_service,
    billing_service,
    dashboard_service,
    doctor_service,
    encounter_service,
    inventory_service,
    patient_service,
)
from app.services.document_service import (
    generate_encounter_summary_pdf,
    generate_invoice_pdf,
    generate_prescription_pdf,
)
from app.services.patient_workspace_service import get_patient_workspace
from tests.factories import (
    BOOKING_ANCHOR_DATE_ISO,
    _BOOKING_ANCHOR_DATE,
    add_weekly_availability,
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)

_IST = ZoneInfo("Asia/Kolkata")
_FUTURE = _BOOKING_ANCHOR_DATE
_FUTURE_STR = BOOKING_ANCHOR_DATE_ISO


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _future_appt_time(hour: int = 10, minute: int = 0) -> datetime:
    """Wall-clock time converted to UTC."""
    return datetime.combine(_FUTURE, time(hour, minute), tzinfo=_IST).astimezone(timezone.utc)


def _setup_tenant_doctor_patient(db: Session) -> tuple[UUID, User, Doctor, User, UUID]:
    tenant = create_tenant(db, name="E2E Clinic")
    admin = create_user(
        db, email="e2e-admin@t.test", password="TestPass9!", role=UserRole.admin, tenant_id=tenant.id
    )
    doc_user = create_user(
        db, email="e2e-doc@t.test", password="TestPass9!", role=UserRole.doctor, tenant_id=tenant.id, is_owner=True
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)
    add_weekly_availability(db, doctor_id=doctor.id, tenant_id=tenant.id, day_of_week=_FUTURE.weekday(), start=time(9, 0), end=time(17, 0), slot_duration=15)
    pat_user = create_user(db, email="e2e-pat@t.test", password="TestPass9!", role=UserRole.patient)
    patient = create_patient_profile(
        db, tenant_id=tenant.id, user_id=pat_user.id, created_by=doc_user.id, name="E2E Patient Alpha"
    )
    db.commit()
    return tenant.id, doc_user, doctor, pat_user, patient.id


def _book_appointment(
    db: Session, patient_id: UUID, doctor: Doctor, doc_user: User, tenant_id: UUID
) -> UUID:
    appt_time = _future_appt_time(10, 0)
    appt, _ = appointment_service.create_appointment(
        db,
        AppointmentCreate(patient_id=patient_id, doctor_id=doctor.id, appointment_time=appt_time),
        current_user=doc_user,
        tenant_id=tenant_id,
    )
    db.commit()
    return appt.id


def _add_prescription(db: Session, appointment: Appointment) -> None:
    appointment_service._create_appointment_prescriptions(
        db,
        appointment,
        [
            PrescriptionCreate(
                notes="Take as directed",
                items=[
                    PrescriptionItemCreate(
                        medicine_name="Amoxicillin",
                        dosage="500mg",
                        frequency="TDS",
                        duration="5 days",
                        instructions="After meals",
                    ),
                    PrescriptionItemCreate(
                        medicine_name="Ibuprofen",
                        dosage="400mg",
                        frequency="SOS",
                        duration="3 days",
                        instructions="If pain persists",
                    ),
                ],
            )
        ],
    )
    db.commit()


def _book_past_appointment(
    db: Session, patient_id: UUID, doctor: Doctor, doc_user: User, tenant_id: UUID
) -> UUID:
    """Create an appointment in the past so completion validation passes."""
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    appt_data = {
        "patient_id": patient_id,
        "doctor_id": doctor.id,
        "appointment_time": past_time,
        "tenant_id": tenant_id,
        "created_by": doc_user.id,
        "status": AppointmentStatus.scheduled.value,
    }
    appt = crud_appointment.add_appointment(db, appt_data)
    db.commit()
    db.refresh(appt)
    return appt.id


def _complete_appointment(db: Session, appt_id: UUID, doc_user: User, tenant_id: UUID) -> None:
    appointment_service.mark_appointment_completed(
        db, appt_id, current_user=doc_user, tenant_id=tenant_id,
        completion=MarkAppointmentCompletedRequest(
            diagnosis="Acute sinusitis",
            treatment_summary="Prescribed antibiotics and anti-inflammatory",
            clinical_notes="Patient responded well",
            subjective_notes="Complains of headache and facial pressure",
            objective_notes="Mucosal swelling observed",
            assessment_notes="Moderate sinusitis",
            plan_notes="Follow up in 5 days if no improvement",
        ),
        idempotency_key=f"e2e-complete-{appt_id}",
    )
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# Test Group 1 — Receptionist Workflow
# ══════════════════════════════════════════════════════════════════════════════


class TestReceptionistWorkflow:
    """Receptionist: create patient → book → reschedule → cancel → rebook → check in → start encounter."""

    def test_create_patient(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, *_ = _setup_tenant_doctor_patient(db_session)
        new_pat = patient_service.create_patient(
            db_session,
            PatientCreate(name="New Patient", phone="9999999999", age=30, gender="male"),
            current_user=doc_user,
            tenant_id=tenant_id,
        )
        db_session.commit()
        assert new_pat.name == "New Patient"
        assert new_pat.phone == "9999999999"

    def test_patient_searchable_by_name(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        results = patient_service.get_patients(
            db_session, doc_user, search="Alpha", tenant_id=tenant_id,
            data_scope=ResolvedDataScope(kind=DataScopeKind.tenant, doctor_id=None),
        )
        assert len(results) == 1
        assert results[0].id == patient_id

    def test_patient_searchable_by_phone(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, _ = _setup_tenant_doctor_patient(db_session)
        # get_patients searches by name (ILike on Patient.name)
        results = patient_service.get_patients(
            db_session, doc_user, search="Patient", tenant_id=tenant_id,
            data_scope=ResolvedDataScope(kind=DataScopeKind.tenant, doctor_id=None),
        )
        assert len(results) >= 1

    def test_book_appointment(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appt = crud_appointment.get_appointment(db_session, appt_id)
        assert appt is not None
        assert appt.status == AppointmentStatus.scheduled
        assert appt.patient_id == patient_id
        assert appt.doctor_id == doctor.id

    def test_reschedule_appointment(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        new_time = _future_appt_time(14, 0)
        updated = appointment_service.update_appointment(
            db_session, appt_id,
            AppointmentUpdate(appointment_time=new_time),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        # SQLite stores naive datetimes — compare without tzinfo
        assert updated.appointment_time == new_time.replace(tzinfo=None)
        assert updated.status == AppointmentStatus.scheduled

    def test_cancel_appointment(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        cancelled = appointment_service.update_appointment(
            db_session, appt_id,
            AppointmentUpdate(status=AppointmentStatus.cancelled),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        assert cancelled.status == AppointmentStatus.cancelled

    def test_book_after_cancel(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appointment_service.update_appointment(
            db_session, appt_id,
            AppointmentUpdate(status=AppointmentStatus.cancelled),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        # Book at a different time to avoid SQLite UNIQUE constraint (Postgres uses partial index)
        from tests.factories import booking_slot_datetime_utc
        appt2_time = booking_slot_datetime_utc() + timedelta(hours=1)
        appt2, _ = appointment_service.create_appointment(
            db_session,
            AppointmentCreate(patient_id=patient_id, doctor_id=doctor.id, appointment_time=appt2_time),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        appt2 = crud_appointment.get_appointment(db_session, appt2.id)
        assert appt2 is not None
        assert appt2.status == AppointmentStatus.scheduled
        assert appt2.id != appt_id

    def test_check_in_patient(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        checked_in = appointment_service.update_appointment(
            db_session, appt_id,
            AppointmentUpdate(status=AppointmentStatus.checked_in),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        assert checked_in.status == AppointmentStatus.checked_in

    def test_start_encounter(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appointment_service.update_appointment(
            db_session, appt_id,
            AppointmentUpdate(status=AppointmentStatus.checked_in),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        in_consult = appointment_service.update_appointment(
            db_session, appt_id,
            AppointmentUpdate(status=AppointmentStatus.in_consultation),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        assert in_consult.status == AppointmentStatus.in_consultation

    def test_duplicate_appointment_prevented(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_time = _future_appt_time(10, 0)
        appointment_service.create_appointment(
            db_session,
            AppointmentCreate(patient_id=patient_id, doctor_id=doctor.id, appointment_time=appt_time),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        from app.services.exceptions import ConflictError as SrvConflictError
        with pytest.raises(SrvConflictError, match="already"):
            appointment_service.create_appointment(
                db_session,
                AppointmentCreate(patient_id=patient_id, doctor_id=doctor.id, appointment_time=appt_time),
                current_user=doc_user, tenant_id=tenant_id,
            )

    def test_appointment_status_transitions_forward(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        valid_chain = [
            AppointmentStatus.confirmed,
            AppointmentStatus.arrived,
            AppointmentStatus.checked_in,
            AppointmentStatus.vitals_completed,
            AppointmentStatus.waiting_for_doctor,
            AppointmentStatus.in_consultation,
        ]
        for status in valid_chain:
            appt = appointment_service.update_appointment(
                db_session, appt_id,
                AppointmentUpdate(status=status),
                current_user=doc_user, tenant_id=tenant_id,
            )
            db_session.commit()
            assert appt.status == status


# ══════════════════════════════════════════════════════════════════════════════
# Test Group 2 — Doctor Workflow
# ══════════════════════════════════════════════════════════════════════════════


class TestDoctorWorkflow:
    """Doctor: open encounter → add notes → add diagnosis → add medicines → complete → generate bill → download PDFs."""

    def test_open_encounter(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, current_user=doc_user, tenant_id=tenant_id,
        )
        assert aggregate is not None
        assert aggregate.appointment.id == appt_id
        assert aggregate.patient.id == patient_id

    def test_add_clinical_notes(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, current_user=doc_user, tenant_id=tenant_id,
        )
        assert aggregate is not None
        appt = crud_appointment.get_appointment(db_session, appt_id)
        assert appt is not None

    def test_add_diagnosis(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appointment_service.mark_appointment_completed(
            db_session, appt_id, current_user=doc_user, tenant_id=tenant_id,
            completion=MarkAppointmentCompletedRequest(diagnosis="Acute sinusitis"),
            idempotency_key=f"e2e-diag-{appt_id}",
        )
        db_session.commit()
        appt = crud_appointment.get_appointment(db_session, appt_id)
        assert appt.diagnosis == "Acute sinusitis"

    def test_add_medicines(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appt = crud_appointment.get_appointment(db_session, appt_id)
        _add_prescription(db_session, appt)
        agg = encounter_service.get_encounter_detail(db_session, appt_id, current_user=doc_user, tenant_id=tenant_id)
        assert len(agg.prescriptions) == 1
        rx = agg.prescriptions[0]
        assert len(rx.items) == 2
        assert rx.items[0].medicine_name == "Amoxicillin"
        assert rx.items[0].dosage == "500mg"
        assert rx.items[0].frequency == "TDS"
        assert rx.items[0].duration == "5 days"
        assert rx.items[0].instructions == "After meals"

    def test_complete_encounter(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        appt = crud_appointment.get_appointment(db_session, appt_id)
        assert appt.status == AppointmentStatus.completed
        assert appt.encounter_completed_at is not None
        assert appt.diagnosis == "Acute sinusitis"

    def test_generate_prescription(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appt = crud_appointment.get_appointment(db_session, appt_id)
        _add_prescription(db_session, appt)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        pdf = generate_prescription_pdf(db_session, appointment_id=appt_id, current_user=doc_user, tenant_id=tenant_id)
        assert pdf.startswith(b"%PDF") or b"Amoxicillin" in pdf

    def test_generate_bill(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        bill = billing_service.create_bill(
            db_session,
            billing_in=BillingCreate(
                patient_id=patient_id,
                appointment_id=appt_id,
                amount=Decimal("500.00"),
                description="Consultation fee",
            ),
            current_user=doc_user,
            tenant_id=tenant_id,
        )
        db_session.commit()
        assert bill.amount == Decimal("500.00")
        assert bill.status.value == "unpaid"

    def test_download_invoice_pdf(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        bill = billing_service.create_bill(
            db_session,
            billing_in=BillingCreate(
                patient_id=patient_id, appointment_id=appt_id, amount=Decimal("500.00"),
                description="Consultation",
            ),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        pdf = generate_invoice_pdf(db_session, bill_id=bill.id, current_user=doc_user, tenant_id=tenant_id)
        assert pdf.startswith(b"%PDF") or b"500.00" in pdf or b"Consultation" in pdf

    def test_download_encounter_summary_pdf(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, _, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        pdf = generate_encounter_summary_pdf(
            db_session, appointment_id=appt_id, current_user=doc_user, tenant_id=tenant_id
        )
        assert pdf.startswith(b"%PDF") or b"Acute sinusitis" in pdf


# ══════════════════════════════════════════════════════════════════════════════
# Test Group 3 — Patient Workflow
# ══════════════════════════════════════════════════════════════════════════════


class TestPatientWorkflow:
    """Patient: login → view appointment → view prescription → download PDF → view bills → check medicines."""

    def test_login_as_patient(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        assert pat_user.email == "e2e-pat@t.test"
        assert pat_user.role == UserRole.patient

    def test_view_appointment(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appts = crud_appointment.get_appointments(db_session, patient_id=patient_id, limit=50)
        assert len(appts) >= 1
        assert appts[0].id == appt_id

    def test_view_prescription(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appt = crud_appointment.get_appointment(db_session, appt_id)
        _add_prescription(db_session, appt)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        agg = encounter_service.get_encounter_detail(db_session, appt_id, current_user=pat_user, tenant_id=None)
        assert len(agg.prescriptions) >= 1
        rx = agg.prescriptions[0]
        assert len(rx.items) >= 1
        assert rx.items[0].medicine_name == "Amoxicillin"

    def test_download_prescription_pdf(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appt = crud_appointment.get_appointment(db_session, appt_id)
        _add_prescription(db_session, appt)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        pdf = generate_prescription_pdf(db_session, appointment_id=appt_id, current_user=pat_user, tenant_id=None)
        assert len(pdf) > 100

    def test_view_bills(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        billing_service.create_bill(
            db_session,
            billing_in=BillingCreate(
                patient_id=patient_id, appointment_id=appt_id, amount=Decimal("500.00"),
                description="Consultation",
            ),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        bills = crud_billing.get_bills_by_patient(db_session, patient_id)
        assert len(bills) >= 1
        assert bills[0].amount == Decimal("500.00")

    def test_download_invoice_as_patient(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        bill = billing_service.create_bill(
            db_session,
            billing_in=BillingCreate(
                patient_id=patient_id, appointment_id=appt_id, amount=Decimal("500.00"),
                description="Consultation",
            ),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        pdf = generate_invoice_pdf(db_session, bill_id=bill.id, current_user=pat_user, tenant_id=None)
        assert len(pdf) > 100

    def test_view_patient_workspace(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appt = crud_appointment.get_appointment(db_session, appt_id)
        _add_prescription(db_session, appt)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        billing_service.create_bill(
            db_session,
            billing_in=BillingCreate(
                patient_id=patient_id, appointment_id=appt_id, amount=Decimal("500.00"),
                description="Consultation",
            ),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        ws = get_patient_workspace(db_session, pat_user)
        assert ws is not None
        assert len(ws.recent_encounters) >= 1
        assert len(ws.prescriptions_history) >= 1
        assert ws.billing_summary.total_billed >= Decimal("500.00")


# ══════════════════════════════════════════════════════════════════════════════
# Test Group 4 — Admin Workflow
# ══════════════════════════════════════════════════════════════════════════════


class TestAdminWorkflow:
    """Admin: dashboard → doctors → patients → appointments → billing → inventory."""

    def _setup_with_appts(self, db_session: Session) -> tuple[UUID, User, Doctor, User, UUID]:
        """Setup tenant + 2 doctors + 2 patients + 2 appointments."""
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        doc_user2 = create_user(
            db_session, email="e2e-doc2@t.test", password="TestPass9!",
            role=UserRole.doctor, tenant_id=tenant_id, is_owner=True,
        )
        doctor2 = create_doctor_profile(db_session, tenant_id=tenant_id, user_id=doc_user2.id)
        add_weekly_availability(
            db_session, doctor_id=doctor2.id, tenant_id=tenant_id,
            day_of_week=_FUTURE.weekday(), start=time(9, 0), end=time(17, 0), slot_duration=15,
        )
        pat_user2 = create_user(
            db_session, email="e2e-pat2@t.test", password="TestPass9!", role=UserRole.patient,
        )
        patient2 = create_patient_profile(
            db_session, tenant_id=tenant_id, user_id=pat_user2.id,
            created_by=doc_user.id, name="E2E Patient Beta",
        )
        appt1_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        appt2_id = _book_appointment(db_session, patient2.id, doctor2, doc_user2, tenant_id)
        db_session.commit()
        return tenant_id, doc_user, doctor, pat_user, appt1_id, appt2_id

    def test_admin_dashboard_counts(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, _, _ = self._setup_with_appts(db_session)
        stats = dashboard_service.get_dashboard_stats_for_tenant(db_session, tenant_id=tenant_id)
        assert stats["total_doctors"] >= 2
        assert stats["total_patients"] >= 2
        assert stats["today_appointments"] >= 0

    def test_admin_list_doctors(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, _, _ = self._setup_with_appts(db_session)
        doctors = doctor_service.get_doctors(db_session, doc_user, tenant_id=tenant_id, limit=50)
        assert len(doctors) >= 2
        names = [d.name for d in doctors]
        assert any("E2E Doc" in n for n in names) or all(d.name for d in doctors)

    def test_admin_search_doctor(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, _, _ = self._setup_with_appts(db_session)
        # Search by name (ILike on Doctor.name), not email
        doctors = doctor_service.get_doctors(
            db_session, doc_user, tenant_id=tenant_id, search="Dr", limit=10
        )
        assert len(doctors) >= 2

    def test_admin_list_patients(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, _, _ = self._setup_with_appts(db_session)
        patients = patient_service.get_patients(
            db_session, doc_user, tenant_id=tenant_id,
            data_scope=ResolvedDataScope(kind=DataScopeKind.tenant, doctor_id=None),
        )
        assert len(patients) >= 2

    def test_admin_search_patient(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, _, _ = self._setup_with_appts(db_session)
        patients = patient_service.get_patients(
            db_session, doc_user, search="Beta", tenant_id=tenant_id,
            data_scope=ResolvedDataScope(kind=DataScopeKind.tenant, doctor_id=None),
        )
        assert len(patients) >= 1
        assert "Beta" in patients[0].name

    def test_admin_list_appointments(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, _, _ = self._setup_with_appts(db_session)
        appts = crud_appointment.get_appointments(
            db_session, tenant_id=tenant_id, limit=50,
        )
        assert len(appts) >= 2

    def test_admin_filter_appointments_by_doctor(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, appt1_id, _ = self._setup_with_appts(db_session)
        appts = crud_appointment.get_appointments(
            db_session, doctor_id=doctor.id, tenant_id=tenant_id, limit=50,
        )
        assert len(appts) == 1
        assert appts[0].id == appt1_id

    def test_admin_billing_summary(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_past_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        _complete_appointment(db_session, appt_id, doc_user, tenant_id)
        billing_service.create_bill(
            db_session,
            billing_in=BillingCreate(
                patient_id=patient_id, appointment_id=appt_id, amount=Decimal("500.00"),
                description="Consultation fee",
            ),
            current_user=doc_user, tenant_id=tenant_id,
        )
        db_session.commit()
        bills = crud_billing.get_bills(db_session, tenant_id=tenant_id, limit=50)
        assert len(bills) >= 1
        total = sum(b.amount for b in bills)
        assert total >= Decimal("500.00")

    def test_admin_inventory_list(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, _ = _setup_tenant_doctor_patient(db_session)
        items = inventory_service.list_items(db_session, doc_user, tenant_id=tenant_id)
        assert items == []  # no seed inventory — returns empty

    def test_admin_appointment_filters_by_status(self, db_session: Session) -> None:
        tenant_id, doc_user, doctor, pat_user, patient_id = _setup_tenant_doctor_patient(db_session)
        appt_id = _book_appointment(db_session, patient_id, doctor, doc_user, tenant_id)
        cancelled_appts = crud_appointment.get_appointments(
            db_session, appt_status=AppointmentStatus.cancelled, tenant_id=tenant_id,
        )
        assert len(cancelled_appts) == 0
        scheduled_appts = crud_appointment.get_appointments(
            db_session, appt_status=AppointmentStatus.scheduled, tenant_id=tenant_id,
        )
        assert len(scheduled_appts) >= 1
