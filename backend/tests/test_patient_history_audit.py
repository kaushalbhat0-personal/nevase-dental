"""
P1.5 — Patient History Audit: verify prescription/encounter/bill history and historical PDF downloads.

Tests create multiple historical records across time and verify:
- Patient workspace aggregate returns all sections
- Patient can access encounter detail for old records
- Patient can download prescription PDF for historical encounters
- Patient can download encounter summary PDF for historical encounters
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

import pytest

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

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
    patient_service,
    patient_workspace_service,
)
from tests.factories import (
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)

# Two time anchors: "old" (1 year ago) and "recent" (1 week ago)
_OLD_TIME = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
_RECENT_TIME = datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc)


def _setup_patient_with_history(db: Session) -> dict:
    """Create a patient with 2 historical encounters (1 old, 1 recent),
    each with prescriptions and bills. Returns all IDs."""
    tenant = create_tenant(db)
    doc_user = create_user(
        db, email="history-doc@test.test", password="TestPass9!",
        role=UserRole.doctor, tenant_id=tenant.id,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)
    pat_user = create_user(
        db, email="history-pat@test.test", password="TestPass9!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db, tenant_id=tenant.id, user_id=pat_user.id, created_by=doc_user.id,
    )
    db.commit()

    def _make_completed_encounter(appt_time: datetime, rx_medicine: str,
                                   notes: str) -> UUID:
        appt = crud_appointment.add_appointment(db, {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": appt_time,
            "status": AppointmentStatus.completed,
            "created_by": doc_user.id,
            "tenant_id": tenant.id,
        })
        db.flush()
        appt.status = AppointmentStatus.completed
        appt.encounter_completed_at = appt_time + timedelta(minutes=30)
        appt.diagnosis = f"Test diagnosis: {rx_medicine}"
        db.flush()

        appointment_service._create_appointment_prescriptions(db, appt, [
            PrescriptionCreate(
                notes=notes,
                items=[PrescriptionItemCreate(
                    medicine_name=rx_medicine, dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ])

        billing_in = BillingCreate(
            patient_id=patient.id,
            appointment_id=appt.id,
            amount=Decimal("500.00"),
            status=BillingStatus.paid,
        )
        billing_service.create_bill(
            db, billing_in=billing_in, current_user=doc_user, tenant_id=tenant.id,
        )
        db.commit()
        return appt.id

    old_appt_id = _make_completed_encounter(
        _OLD_TIME, "Paracetamol", "Old encounter — 1 year ago",
    )
    recent_appt_id = _make_completed_encounter(
        _RECENT_TIME, "Amoxicillin", "Recent encounter — 1 week ago",
    )

    return {
        "tenant": tenant,
        "doc_user": doc_user,
        "doctor": doctor,
        "pat_user": pat_user,
        "patient": patient,
        "old_appt_id": old_appt_id,
        "recent_appt_id": recent_appt_id,
    }


class TestPatientHistoryPrescriptions:
    """Patient can see prescription history across multiple encounters."""

    def test_prescriptions_from_old_encounter(self, db_session: Session) -> None:
        ctx = _setup_patient_with_history(db_session)
        aggregate = encounter_service.get_encounter_detail(
            db_session, ctx["old_appt_id"], ctx["pat_user"],
            tenant_id=ctx["tenant"].id,
        )
        assert len(aggregate.prescriptions) == 1
        items = aggregate.prescriptions[0].items
        assert len(items) == 1
        assert items[0].medicine_name == "Paracetamol"

    def test_prescriptions_from_recent_encounter(self, db_session: Session) -> None:
        ctx = _setup_patient_with_history(db_session)
        aggregate = encounter_service.get_encounter_detail(
            db_session, ctx["recent_appt_id"], ctx["pat_user"],
            tenant_id=ctx["tenant"].id,
        )
        assert len(aggregate.prescriptions) == 1
        items = aggregate.prescriptions[0].items
        assert len(items) == 1
        assert items[0].medicine_name == "Amoxicillin"


class TestPatientHistoryBills:
    """Patient can see bill history across multiple encounters."""

    def test_bill_from_old_encounter(self, db_session: Session) -> None:
        ctx = _setup_patient_with_history(db_session)
        aggregate = encounter_service.get_encounter_detail(
            db_session, ctx["old_appt_id"], ctx["pat_user"],
            tenant_id=ctx["tenant"].id,
        )
        assert aggregate.bill is not None
        assert aggregate.bill.amount == Decimal("500.00")

    def test_bill_from_recent_encounter(self, db_session: Session) -> None:
        ctx = _setup_patient_with_history(db_session)
        aggregate = encounter_service.get_encounter_detail(
            db_session, ctx["recent_appt_id"], ctx["pat_user"],
            tenant_id=ctx["tenant"].id,
        )
        assert aggregate.bill is not None
        assert aggregate.bill.amount == Decimal("500.00")

    def test_both_bills_have_different_ids(self, db_session: Session) -> None:
        ctx = _setup_patient_with_history(db_session)
        old = encounter_service.get_encounter_detail(
            db_session, ctx["old_appt_id"], ctx["pat_user"],
            tenant_id=ctx["tenant"].id,
        )
        recent = encounter_service.get_encounter_detail(
            db_session, ctx["recent_appt_id"], ctx["pat_user"],
            tenant_id=ctx["tenant"].id,
        )
        assert old.bill is not None
        assert recent.bill is not None
        assert old.bill.id != recent.bill.id


class TestPatientWorkspaceHistory:
    """Patient workspace aggregate includes all history sections."""

    def test_workspace_contains_both_encounters(self, db_session: Session) -> None:
        ctx = _setup_patient_with_history(db_session)
        workspace = patient_workspace_service.get_patient_workspace(
            db_session, ctx["pat_user"],
        )
        assert len(workspace.recent_encounters) == 2
        encounter_ids = {e.appointment_id for e in workspace.recent_encounters}
        assert ctx["old_appt_id"] in encounter_ids
        assert ctx["recent_appt_id"] in encounter_ids

    def test_workspace_encounters_ordered_by_date_desc(self, db_session: Session) -> None:
        ctx = _setup_patient_with_history(db_session)
        workspace = patient_workspace_service.get_patient_workspace(
            db_session, ctx["pat_user"],
        )
        dates = [e.appointment_time for e in workspace.recent_encounters]
        assert dates == sorted(dates, reverse=True)

    def test_workspace_contains_prescriptions_history(self, db_session: Session) -> None:
        ctx = _setup_patient_with_history(db_session)
        workspace = patient_workspace_service.get_patient_workspace(
            db_session, ctx["pat_user"],
        )
        assert len(workspace.prescriptions_history) == 2
        med_names = set()
        for p in workspace.prescriptions_history:
            for item in p.items:
                med_names.add(item.medicine_name)
        assert med_names == {"Paracetamol", "Amoxicillin"}

    def test_workspace_contains_billing_summary(self, db_session: Session) -> None:
        ctx = _setup_patient_with_history(db_session)
        workspace = patient_workspace_service.get_patient_workspace(
            db_session, ctx["pat_user"],
        )
        assert len(workspace.billing_summary.recent_bills) == 2
        total = sum(b.amount for b in workspace.billing_summary.recent_bills)
        assert total == Decimal("1000.00")


class TestPatientHistoryPdfDownloads:
    """Patient can download PDFs for historical records."""

    @pytest.mark.asyncio
    @patch("app.services.document_service._render_pdf")
    async def test_download_old_prescription_pdf(self, mock_render,
                                                  db_session: Session,
                                                  client: AsyncClient) -> None:
        mock_render.return_value = b"%PDF-1.4 mock pdf"
        ctx = _setup_patient_with_history(db_session)
        pat_user = ctx["pat_user"]
        old_appt_id = ctx["old_appt_id"]

        patient_ctx = patient_service.get_patient_by_user_id(db_session, pat_user.id)
        token = _login_as(db_session, client, pat_user, patient_id=patient_ctx.id)

        response = await client.get(
            f"/api/v1/documents/prescription/{old_appt_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"

    @pytest.mark.asyncio
    @patch("app.services.document_service._render_pdf")
    async def test_download_recent_prescription_pdf(self, mock_render,
                                                     db_session: Session,
                                                     client: AsyncClient) -> None:
        mock_render.return_value = b"%PDF-1.4 mock pdf"
        ctx = _setup_patient_with_history(db_session)
        pat_user = ctx["pat_user"]
        recent_appt_id = ctx["recent_appt_id"]

        patient_ctx = patient_service.get_patient_by_user_id(db_session, pat_user.id)
        token = _login_as(db_session, client, pat_user, patient_id=patient_ctx.id)

        response = await client.get(
            f"/api/v1/documents/prescription/{recent_appt_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"

    @pytest.mark.asyncio
    @patch("app.services.document_service._render_pdf")
    async def test_download_old_encounter_summary_pdf(self, mock_render,
                                                       db_session: Session,
                                                       client: AsyncClient) -> None:
        mock_render.return_value = b"%PDF-1.4 mock pdf"
        ctx = _setup_patient_with_history(db_session)
        pat_user = ctx["pat_user"]
        old_appt_id = ctx["old_appt_id"]

        patient_ctx = patient_service.get_patient_by_user_id(db_session, pat_user.id)
        token = _login_as(db_session, client, pat_user, patient_id=patient_ctx.id)

        response = await client.get(
            f"/api/v1/documents/encounter-summary/{old_appt_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"


def _login_as(db: Session, client: AsyncClient, user: User,
              patient_id: UUID | None = None) -> str:
    """Helper: login user and return bearer token."""
    from app.core.security import create_access_token
    data = {"sub": str(user.id), "role": user.role.value}
    if patient_id:
        data["patient_id"] = str(patient_id)
    token = create_access_token(data)
    return token
