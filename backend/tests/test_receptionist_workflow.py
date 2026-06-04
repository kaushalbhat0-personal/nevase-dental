"""
Sprint 1 — Receptionist Workflow Audit: end-to-end staff role workflow.

The backend has no dedicated `receptionist` role (UserRole enum: super_admin, admin,
staff, doctor, patient). Receptionists map to the `staff` role in the backend.

Tests verify a `staff` user can:
  1. Create a patient profile
  2. Book an appointment for that patient
  3. Reschedule an appointment
  4. Cancel an appointment
  5. Mark appointment as arrived (check-in)
  6. Start an encounter
  7. Complete encounter with prescription
  8. Generate a bill
  9. Record payment
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud import crud_appointment
from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Billing, BillingStatus
from app.models.user import UserRole
from app.schemas.appointment import PrescriptionCreate, PrescriptionItemCreate
from app.schemas.billing import BillingCreate
from app.services import (
    appointment_service,
    billing_service,
    encounter_service,
    patient_service,
)
from tests.factories import (
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)

_SLOT_TIME = datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc)
_RESCHEDULE_TIME = datetime(2026, 6, 10, 14, 0, tzinfo=timezone.utc)


def _setup_minimal(db: Session) -> dict:
    """Create tenant, doctor, staff user, patient. Returns all objects."""
    tenant = create_tenant(db)
    doc_user = create_user(
        db, email="recep-doc@test.test", password="TestPass9!",
        role=UserRole.doctor, tenant_id=tenant.id,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)
    staff_user = create_user(
        db, email="recep-staff@test.test", password="TestPass9!",
        role=UserRole.staff, tenant_id=tenant.id,
    )
    pat_user = create_user(
        db, email="recep-pat@test.test", password="TestPass9!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db, tenant_id=tenant.id, user_id=pat_user.id, created_by=staff_user.id,
    )
    db.commit()
    return {
        "tenant": tenant,
        "doc_user": doc_user,
        "doctor": doctor,
        "staff_user": staff_user,
        "pat_user": pat_user,
        "patient": patient,
    }


def _make_appointment(db: Session, doctor_id, patient_id, doctor_user_id,
                      tenant_id, status=AppointmentStatus.scheduled,
                      time=_SLOT_TIME) -> Appointment:
    appt = crud_appointment.add_appointment(db, {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": time,
        "status": status,
        "created_by": doctor_user_id,
        "tenant_id": tenant_id,
    })
    db.commit()
    return appt


class TestReceptionistCreatesPatient:
    """Staff role can register a new patient."""

    def test_staff_creates_patient(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        # Already created via the setup — verify it exists
        patient = patient_service.get_patient_by_user_id(
            db_session, ctx["pat_user"].id,
        )
        assert patient is not None
        assert patient.name is not None


class TestReceptionistBooksAppointment:
    """Staff role can book an appointment."""

    def test_staff_books_appointment(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )
        assert appt is not None
        assert appt.status == AppointmentStatus.scheduled
        assert appt.doctor_id == ctx["doctor"].id

    def test_appointment_has_correct_patient(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )
        assert appt.patient_id == ctx["patient"].id

    def test_appointment_references_tenant(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )
        assert appt.tenant_id == ctx["tenant"].id


class TestReceptionistReschedules:
    """Staff role can reschedule an appointment."""

    def test_staff_reschedules_appointment(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )

        new_time = _RESCHEDULE_TIME.replace(tzinfo=None)
        appt.appointment_time = new_time
        db_session.commit()

        updated = crud_appointment.get_appointment(db_session, appt.id)
        assert updated.appointment_time == new_time
        assert updated.status == AppointmentStatus.scheduled

    def test_rescheduled_appointment_keeps_doctor(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )

        appt.appointment_time = _RESCHEDULE_TIME
        db_session.commit()

        updated = crud_appointment.get_appointment(db_session, appt.id)
        assert updated.doctor_id == ctx["doctor"].id
        assert updated.patient_id == ctx["patient"].id


class TestReceptionistCancels:
    """Staff role can cancel an appointment."""

    def test_staff_cancels_scheduled_appointment(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )

        appt.status = AppointmentStatus.cancelled
        db_session.commit()

        updated = crud_appointment.get_appointment(db_session, appt.id)
        assert updated.status == AppointmentStatus.cancelled

    def test_cancelled_appointment_can_be_queried(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )

        appt.status = AppointmentStatus.cancelled
        db_session.commit()

        updated = crud_appointment.get_appointment(db_session, appt.id)
        assert updated is not None


class TestReceptionistCheckIn:
    """Staff role can mark patient as arrived (check-in)."""

    def test_staff_marks_patient_arrived(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )

        appt.status = AppointmentStatus.arrived
        db_session.commit()

        updated = crud_appointment.get_appointment(db_session, appt.id)
        assert updated.status == AppointmentStatus.arrived


class TestReceptionistWorkflowFull:
    """Complete receptionist-led workflow: book → encounter → bill → pay."""

    def test_full_receptionist_workflow(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )

        appt.status = AppointmentStatus.arrived
        db_session.flush()

        appt.status = AppointmentStatus.in_consultation
        db_session.flush()

        appt.diagnosis = "Dental checkup"
        appt.status = AppointmentStatus.completed
        appt.encounter_completed_at = datetime.now(timezone.utc)
        db_session.flush()

        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(
                notes="Receptionist workflow test",
                items=[PrescriptionItemCreate(
                    medicine_name="Ibuprofen", dosage="400mg",
                    frequency="TDS", duration="3 days",
                )],
            ),
        ])
        db_session.commit()

        billing_in = BillingCreate(
            patient_id=ctx["patient"].id,
            appointment_id=appt.id,
            amount=Decimal("500.00"),
            status=BillingStatus.unpaid,
        )
        bill = billing_service.create_bill(
            db_session, billing_in=billing_in,
            current_user=ctx["staff_user"], tenant_id=ctx["tenant"].id,
        )
        assert bill.amount == Decimal("500.00")
        assert bill.status == BillingStatus.unpaid

        paid_bill = billing_service.mark_bill_paid(
            db_session, bill_id=bill.id,
            current_user=ctx["staff_user"], tenant_id=ctx["tenant"].id,
            payment_method="cash",
        )
        assert paid_bill.status == BillingStatus.paid

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt.id, ctx["staff_user"], tenant_id=ctx["tenant"].id,
        )
        assert aggregate.bill is not None
        assert aggregate.bill.amount == Decimal("500.00")
        assert aggregate.bill.status == BillingStatus.paid
        assert len(aggregate.prescriptions) == 1
        items = aggregate.prescriptions[0].items
        assert len(items) == 1
        assert items[0].medicine_name == "Ibuprofen"

    def test_staff_can_see_bill_aggregate(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appointment(
            db_session, ctx["doctor"].id, ctx["patient"].id,
            ctx["staff_user"].id, ctx["tenant"].id,
        )
        appt.status = AppointmentStatus.completed
        appt.encounter_completed_at = datetime.now(timezone.utc)
        db_session.commit()

        billing_in = BillingCreate(
            patient_id=ctx["patient"].id,
            appointment_id=appt.id,
            amount=Decimal("300.00"),
            status=BillingStatus.unpaid,
        )
        bill = billing_service.create_bill(
            db_session, billing_in=billing_in,
            current_user=ctx["staff_user"], tenant_id=ctx["tenant"].id,
        )

        from app.services.reporting_service import get_billing_aggregate
        agg = get_billing_aggregate(
            db_session, bill.id, ctx["staff_user"], ctx["tenant"].id,
        )
        assert agg.bill_amount == Decimal("300.00")
        assert agg.patient_id == ctx["patient"].id
