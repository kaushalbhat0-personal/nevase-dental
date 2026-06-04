"""
Sprint 3 — Security Audit: isolation boundaries, permissions, and IDOR proof.

Tests verify:
  1. Patient isolation — patient A's workspace contains no patient B data
  2. Tenant isolation — tenant A staff cannot access tenant B data
  3. Document download permissions — patient cannot download another's document
  4. Doctor isolation — doctor A cannot encounter-detail doctor B's appointment
  5. Staff permissions boundary — staff from wrong tenant is rejected
  6. Patient cannot access another patient's encounter detail
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.crud import crud_appointment
from app.models.appointment import AppointmentStatus
from app.models.billing import BillingStatus
from app.models.user import User, UserRole
from app.schemas.appointment import PrescriptionCreate, PrescriptionItemCreate
from app.schemas.billing import BillingCreate
from app.services import (
    appointment_service,
    billing_service,
    encounter_service,
    patient_workspace_service,
)
from tests.factories import (
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)

_SLOT_A = datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc)
_SLOT_B = datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc)


def _setup_two_patients_one_tenant(db: Session) -> dict:
    """Same doctor, same tenant, two patients each with encounter+rx+bill."""
    tenant = create_tenant(db)
    doc_user = create_user(
        db, email="sec-doc@test.test", password="TestPass9!",
        role=UserRole.doctor, tenant_id=tenant.id,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)

    pat_a_user = create_user(
        db, email="sec-pat-a@test.test", password="TestPass9!",
        role=UserRole.patient,
    )
    patient_a = create_patient_profile(
        db, tenant_id=tenant.id, user_id=pat_a_user.id, created_by=doc_user.id,
        name="Patient A",
    )

    pat_b_user = create_user(
        db, email="sec-pat-b@test.test", password="TestPass9!",
        role=UserRole.patient,
    )
    patient_b = create_patient_profile(
        db, tenant_id=tenant.id, user_id=pat_b_user.id, created_by=doc_user.id,
        name="Patient B",
    )
    db.commit()

    def _make_encounter(patient, appt_time, medicine):
        appt = crud_appointment.add_appointment(db, {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": appt_time.replace(tzinfo=None),
            "status": AppointmentStatus.completed,
            "created_by": doc_user.id,
            "tenant_id": tenant.id,
        })
        appt.encounter_completed_at = datetime.now(timezone.utc)
        db.flush()
        appointment_service._create_appointment_prescriptions(db, appt, [
            PrescriptionCreate(
                notes=f"Rx for {patient.name}",
                items=[PrescriptionItemCreate(
                    medicine_name=medicine, dosage="500mg",
                    frequency="OD", duration="5 days",
                )],
            ),
        ])
        billing_service.create_bill(db, BillingCreate(
            patient_id=patient.id, appointment_id=appt.id,
            amount=Decimal("100.00"), status=BillingStatus.paid,
        ), current_user=doc_user, tenant_id=tenant.id)
        db.flush()
        return appt.id

    appt_a_id = _make_encounter(patient_a, _SLOT_A, "MedicineA")
    appt_b_id = _make_encounter(patient_b, _SLOT_B, "MedicineB")
    db.commit()
    return {
        "tenant": tenant, "doc_user": doc_user, "doctor": doctor,
        "pat_a_user": pat_a_user, "patient_a": patient_a,
        "pat_b_user": pat_b_user, "patient_b": patient_b,
        "appt_a_id": appt_a_id, "appt_b_id": appt_b_id,
    }


def _token_for(user: User, patient_id: UUID | None = None) -> str:
    data = {"sub": str(user.id), "role": user.role.value}
    if patient_id:
        data["patient_id"] = str(patient_id)
    return create_access_token(data)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Patient Isolation
# ═══════════════════════════════════════════════════════════════════════════════


class TestPatientIsolation:
    """Patient A's workspace must NOT contain Patient B's data."""

    def test_patient_a_workspace_has_only_a_data(self, db_session: Session) -> None:
        ctx = _setup_two_patients_one_tenant(db_session)
        ws = patient_workspace_service.get_patient_workspace(
            db_session, ctx["pat_a_user"],
        )
        for rx in ws.prescriptions_history:
            for item in rx.items:
                assert item.medicine_name == "MedicineA"
        assert len(ws.billing_summary.recent_bills) == 1
        assert ws.billing_summary.total_billed == Decimal("100.00")

    def test_patient_b_workspace_has_only_b_data(self, db_session: Session) -> None:
        ctx = _setup_two_patients_one_tenant(db_session)
        ws = patient_workspace_service.get_patient_workspace(
            db_session, ctx["pat_b_user"],
        )
        for rx in ws.prescriptions_history:
            for item in rx.items:
                assert item.medicine_name == "MedicineB"

    def test_patient_a_cannot_access_b_encounter_detail(self, db_session: Session) -> None:
        ctx = _setup_two_patients_one_tenant(db_session)
        with pytest.raises(Exception):
            encounter_service.get_encounter_detail(
                db_session, ctx["appt_b_id"], ctx["pat_a_user"],
                tenant_id=ctx["tenant"].id,
            )

    def test_patient_b_cannot_access_a_encounter_detail(self, db_session: Session) -> None:
        ctx = _setup_two_patients_one_tenant(db_session)
        with pytest.raises(Exception):
            encounter_service.get_encounter_detail(
                db_session, ctx["appt_a_id"], ctx["pat_b_user"],
                tenant_id=ctx["tenant"].id,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Tenant Isolation
# ═══════════════════════════════════════════════════════════════════════════════


class TestTenantIsolation:
    """Staff from tenant B cannot access tenant A's patient data."""

    def test_cross_tenant_staff_access_rejected(self, db_session: Session) -> None:
        t1 = create_tenant(db_session, name="Tenant A")
        t2 = create_tenant(db_session, name="Tenant B")

        doc_user = create_user(
            db_session, email="t1-doc@test.test", password="TestPass9!",
            role=UserRole.doctor, tenant_id=t1.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=t1.id, user_id=doc_user.id,
        )

        staff_b = create_user(
            db_session, email="t2-staff@test.test", password="TestPass9!",
            role=UserRole.staff, tenant_id=t2.id,
        )

        pat_user = create_user(
            db_session, email="t1-pat@test.test", password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session, tenant_id=t1.id, user_id=pat_user.id,
            created_by=doc_user.id, name="T1 Patient",
        )

        appt = crud_appointment.add_appointment(db_session, {
            "patient_id": patient.id, "doctor_id": doctor.id,
            "appointment_time": datetime(2026, 6, 10, 10, 0),
            "status": AppointmentStatus.completed,
            "created_by": doc_user.id, "tenant_id": t1.id,
        })
        appt.encounter_completed_at = datetime.now(timezone.utc)
        db_session.commit()

        # Staff from tenant B should not access tenant A's encounter
        with pytest.raises(Exception):
            encounter_service.get_encounter_detail(
                db_session, appt.id, staff_b, tenant_id=t2.id,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Document Download Permissions
# ═══════════════════════════════════════════════════════════════════════════════


class TestDocumentDownloadPermissions:
    """Patient must only be able to download their own documents."""

    @pytest.mark.asyncio
    async def test_patient_cannot_download_other_patients_prescription(
        self, db_session: Session, client: AsyncClient,
    ) -> None:
        ctx = _setup_two_patients_one_tenant(db_session)
        token = _token_for(
            ctx["pat_b_user"], patient_id=ctx["patient_b"].id,
        )
        resp = await client.get(
            f"/api/v1/documents/prescription/{ctx['appt_a_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_patient_cannot_download_other_patients_encounter_summary(
        self, db_session: Session, client: AsyncClient,
    ) -> None:
        ctx = _setup_two_patients_one_tenant(db_session)
        token = _token_for(
            ctx["pat_b_user"], patient_id=ctx["patient_b"].id,
        )
        resp = await client.get(
            f"/api/v1/documents/encounter-summary/{ctx['appt_a_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (403, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Doctor Isolation
# ═══════════════════════════════════════════════════════════════════════════════


class TestDoctorIsolation:
    """Doctor A cannot encounter-detail appointments that belong to Doctor B."""

    def test_doctor_a_cannot_see_doctor_b_encounter(self, db_session: Session) -> None:
        tenant = create_tenant(db_session)

        doc_a_user = create_user(
            db_session, email="doc-a-iso@test.test", password="TestPass9!",
            role=UserRole.doctor, tenant_id=tenant.id,
        )
        create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_a_user.id)

        doc_b_user = create_user(
            db_session, email="doc-b-iso@test.test", password="TestPass9!",
            role=UserRole.doctor, tenant_id=tenant.id,
        )
        doctor_b = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_b_user.id,
        )

        pat_b_user = create_user(
            db_session, email="pat-b-iso@test.test", password="TestPass9!",
            role=UserRole.patient,
        )
        patient_b = create_patient_profile(
            db_session, tenant_id=tenant.id, user_id=pat_b_user.id,
            created_by=doc_b_user.id,
        )
        db_session.commit()

        appt_b = crud_appointment.add_appointment(db_session, {
            "patient_id": patient_b.id,
            "doctor_id": doctor_b.id,
            "appointment_time": datetime(2026, 6, 10, 10, 0),
            "status": AppointmentStatus.completed,
            "created_by": doc_b_user.id,
            "tenant_id": tenant.id,
        })
        appt_b.encounter_completed_at = datetime.now(timezone.utc)
        db_session.commit()

        with pytest.raises(Exception):
            encounter_service.get_encounter_detail(
                db_session, appt_b.id, doc_a_user,
                tenant_id=tenant.id,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Staff Permissions Boundary
# ═══════════════════════════════════════════════════════════════════════════════


class TestStaffPermissionsBoundary:
    """Staff from tenant B cannot see tenant A's patient bills."""

    def test_staff_outside_tenant_sees_no_bills(self, db_session: Session) -> None:
        t_a = create_tenant(db_session, name="T-A")
        t_b = create_tenant(db_session, name="T-B")

        doc_user = create_user(
            db_session, email="t-a-doc@test.test", password="TestPass9!",
            role=UserRole.doctor, tenant_id=t_a.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=t_a.id, user_id=doc_user.id,
        )

        staff_b = create_user(
            db_session, email="staff-t-b@test.test", password="TestPass9!",
            role=UserRole.staff, tenant_id=t_b.id,
        )

        pat_user = create_user(
            db_session, email="pat-t-a@test.test", password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session, tenant_id=t_a.id, user_id=pat_user.id,
            created_by=doc_user.id,
        )

        appt = crud_appointment.add_appointment(db_session, {
            "patient_id": patient.id, "doctor_id": doctor.id,
            "appointment_time": datetime(2026, 6, 10, 10, 0),
            "status": AppointmentStatus.completed,
            "created_by": doc_user.id, "tenant_id": t_a.id,
        })
        appt.encounter_completed_at = datetime.now(timezone.utc)
        db_session.commit()

        billing_service.create_bill(db_session, BillingCreate(
            patient_id=patient.id, appointment_id=appt.id,
            amount=Decimal("500.00"), status=BillingStatus.unpaid,
        ), current_user=doc_user, tenant_id=t_a.id)
        db_session.commit()

        from app.services.reporting_service import get_patient_financial_ledger

        # Staff from tenant B queries — should see 0 bills because bills are in tenant A
        ledger = get_patient_financial_ledger(
            db_session, staff_b, patient.id, tenant_id=t_b.id,
        )
        assert len(ledger.bills) == 0
        assert ledger.total_billed == Decimal("0.00")
