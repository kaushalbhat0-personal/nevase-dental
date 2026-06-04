"""End-to-end workflow tests: patient → appointment → encounter → prescription → bill.

Covers the full patient journey and the targeted data-quality improvements from
the P1 stabilization sprint (empty medicine_name rejection, negative amount rejection).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.crud import crud_appointment
from app.models.appointment import AppointmentStatus
from app.models.billing import Billing, BillingStatus
from app.models.user import UserRole
from app.schemas.appointment import PrescriptionCreate, PrescriptionItemCreate
from app.schemas.billing import BillingCreate, BillingUpdate
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

_PAST_TIME = datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _setup_minimal(db: Session):
    """Create tenant, doctor, patient. Returns (tenant, doc_user, doctor, pat_user, patient)."""
    tenant = create_tenant(db)
    doc_user = create_user(
        db, email="doc@workflow.test", password="TestPass9!",
        role=UserRole.doctor, tenant_id=tenant.id,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)
    pat_user = create_user(
        db, email="pat@workflow.test", password="TestPass9!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db, tenant_id=tenant.id, user_id=pat_user.id, created_by=doc_user.id,
    )
    db.commit()
    return tenant, doc_user, doctor, pat_user, patient


def _make_appointment(db: Session, doctor_id: UUID, patient_id: UUID,
                      doctor_user_id: UUID, tenant_id: UUID) -> UUID:
    appt = crud_appointment.add_appointment(db, {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": _PAST_TIME,
        "status": AppointmentStatus.scheduled,
        "created_by": doctor_user_id,
        "tenant_id": tenant_id,
    })
    db.commit()
    return appt.id


def _complete_appointment(db: Session, appt_id: UUID) -> None:
    appt = crud_appointment.get_appointment(db, appt_id)
    appt.status = AppointmentStatus.completed
    appt.encounter_completed_at = datetime.now(timezone.utc)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# P1.1 — Prescription Data Quality: empty medicine_name rejection
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmptyMedicineNameRejection:
    """Empty string medicine_name must be rejected by Pydantic validation."""

    def test_empty_medicine_name_raises(self) -> None:
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            PrescriptionItemCreate(
                medicine_name="",
                dosage="500mg",
                frequency="TDS",
                duration="5 days",
            )

    def test_valid_medicine_name_passes(self) -> None:
        item = PrescriptionItemCreate(
            medicine_name="Paracetamol",
            dosage="500mg",
            frequency="TDS",
            duration="5 days",
        )
        assert item.medicine_name == "Paracetamol"

    def test_whitespace_only_still_empty(self) -> None:
        """Whitespace-only strings pass min_length=1 but are semantically empty.
        This is informational — the schema uses plain str, not a constrained str
        with strip_whitespace. The test documents current behaviour."""
        item = PrescriptionItemCreate(
            medicine_name="   ",
            dosage="500mg",
            frequency="TDS",
            duration="5 days",
        )
        assert item.medicine_name == "   "

    def test_prescription_with_empty_item_rejected(self) -> None:
        """PrescriptionItemCreate with empty medicine_name raises at item level
        before being passed to PrescriptionCreate."""
        with pytest.raises(ValidationError):
            PrescriptionItemCreate(
                medicine_name="",
                dosage="500mg",
                frequency="OD",
                duration="3 days",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# P1.2 — Billing System: negative amount rejection
# ═══════════════════════════════════════════════════════════════════════════════


class TestNegativeBillingAmountRejection:
    """Negative billing amounts must be rejected by Pydantic validation."""

    def test_negative_amount_raises_on_create(self) -> None:
        with pytest.raises(ValidationError, match="Input should be greater than or equal to 0"):
            BillingCreate(
                patient_id=UUID("00000000-0000-0000-0000-000000000001"),
                amount=Decimal("-50.00"),
            )

    def test_zero_amount_allowed(self) -> None:
        bill = BillingCreate(
            patient_id=UUID("00000000-0000-0000-0000-000000000001"),
            amount=Decimal("0.00"),
        )
        assert bill.amount == Decimal("0.00")

    def test_positive_amount_allowed(self) -> None:
        bill = BillingCreate(
            patient_id=UUID("00000000-0000-0000-0000-000000000001"),
            amount=Decimal("150.00"),
        )
        assert bill.amount == Decimal("150.00")

    def test_negative_amount_raises_on_update(self) -> None:
        with pytest.raises(ValidationError, match="Input should be greater than or equal to 0"):
            BillingUpdate(amount=Decimal("-1.00"))


# ═══════════════════════════════════════════════════════════════════════════════
# P1.3 — Full patient workflow: appointment → encounter → prescription → bill
# ═══════════════════════════════════════════════════════════════════════════════


class TestPatientWorkflowE2E:
    """Full patient journey: create appointment, complete encounter,
    write prescription, create bill, verify via aggregate."""

    def test_patient_can_get_appointment(self, db_session: Session) -> None:
        tenant, doc_user, doctor, _, patient = _setup_minimal(db_session)
        appt_id = _make_appointment(
            db_session, doctor.id, patient.id, doc_user.id, tenant.id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        assert appt is not None
        assert appt.patient_id == patient.id

    def test_prescription_after_encounter(self, db_session: Session) -> None:
        tenant, doc_user, doctor, _, patient = _setup_minimal(db_session)
        appt_id = _make_appointment(
            db_session, doctor.id, patient.id, doc_user.id, tenant.id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)

        rx_data = [
            PrescriptionCreate(
                notes="E2E test prescription",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                    instructions="After meals",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        _complete_appointment(db_session, appt_id)

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=tenant.id,
        )
        assert len(aggregate.prescriptions) == 1
        items = aggregate.prescriptions[0].items
        assert len(items) == 1
        assert items[0].medicine_name == "Paracetamol"
        assert items[0].dosage == "500mg"

    def test_bill_after_appointment(self, db_session: Session) -> None:
        tenant, doc_user, doctor, _, patient = _setup_minimal(db_session)
        appt_id = _make_appointment(
            db_session, doctor.id, patient.id, doc_user.id, tenant.id,
        )
        _complete_appointment(db_session, appt_id)

        billing_in = BillingCreate(
            patient_id=patient.id,
            appointment_id=appt_id,
            amount=Decimal("200.00"),
            status=BillingStatus.unpaid,
        )
        bill = billing_service.create_bill(
            db_session, billing_in=billing_in, current_user=doc_user, tenant_id=tenant.id,
        )
        assert bill.amount == Decimal("200.00")
        assert bill.status == BillingStatus.unpaid

    def test_bill_payment(self, db_session: Session) -> None:
        tenant, doc_user, doctor, _, patient = _setup_minimal(db_session)
        appt_id = _make_appointment(
            db_session, doctor.id, patient.id, doc_user.id, tenant.id,
        )
        _complete_appointment(db_session, appt_id)

        billing_in = BillingCreate(
            patient_id=patient.id,
            appointment_id=appt_id,
            amount=Decimal("200.00"),
            status=BillingStatus.unpaid,
        )
        bill = billing_service.create_bill(
            db_session, billing_in=billing_in, current_user=doc_user, tenant_id=tenant.id,
        )
        paid_bill = billing_service.mark_bill_paid(
            db_session,
            bill_id=bill.id,
            current_user=doc_user,
            tenant_id=tenant.id,
            payment_method="cash",
        )
        assert paid_bill.status == BillingStatus.paid

    def test_bill_shows_in_encounter_aggregate(self, db_session: Session) -> None:
        tenant, doc_user, doctor, _, patient = _setup_minimal(db_session)
        appt_id = _make_appointment(
            db_session, doctor.id, patient.id, doc_user.id, tenant.id,
        )
        _complete_appointment(db_session, appt_id)

        billing_in = BillingCreate(
            patient_id=patient.id,
            appointment_id=appt_id,
            amount=Decimal("150.00"),
            status=BillingStatus.paid,
        )
        billing_service.create_bill(
            db_session, billing_in=billing_in, current_user=doc_user, tenant_id=tenant.id,
        )
        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=tenant.id,
        )
        assert aggregate.bill is not None
        assert aggregate.bill.amount == Decimal("150.00")

    def test_bill_with_zero_amount(self, db_session: Session) -> None:
        tenant, doc_user, doctor, _, patient = _setup_minimal(db_session)
        appt_id = _make_appointment(
            db_session, doctor.id, patient.id, doc_user.id, tenant.id,
        )
        _complete_appointment(db_session, appt_id)

        billing_in = BillingCreate(
            patient_id=patient.id,
            appointment_id=appt_id,
            amount=Decimal("0.00"),
            status=BillingStatus.unpaid,
        )
        bill = billing_service.create_bill(
            db_session, billing_in=billing_in, current_user=doc_user, tenant_id=tenant.id,
        )
        assert bill.amount == Decimal("0.00")

    def test_full_workflow_serialization(self, db_session: Session) -> None:
        """End-to-end: appointment -> encounter -> prescription -> bill -> JSON."""
        tenant, doc_user, doctor, _, patient = _setup_minimal(db_session)
        appt_id = _make_appointment(
            db_session, doctor.id, patient.id, doc_user.id, tenant.id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)

        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(
                notes="Full workflow",
                items=[PrescriptionItemCreate(
                    medicine_name="Amoxicillin", dosage="250mg",
                    frequency="TDS", duration="7 days",
                    instructions="With food",
                )],
            ),
        ])
        _complete_appointment(db_session, appt_id)

        billing_in = BillingCreate(
            patient_id=patient.id,
            appointment_id=appt_id,
            amount=Decimal("350.00"),
            status=BillingStatus.paid,
        )
        billing_service.create_bill(
            db_session, billing_in=billing_in, current_user=doc_user, tenant_id=tenant.id,
        )
        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=tenant.id,
        )
        data = aggregate.model_dump(mode="json")

        assert data["appointment"]["id"] == str(appt_id)
        assert data["patient"]["id"] == str(patient.id)
        assert len(data["prescriptions"]) == 1
        assert data["prescriptions"][0]["items"][0]["medicine_name"] == "Amoxicillin"
        assert str(data["bill"]["amount"]) == "350.00"
        assert data["bill"]["status"] == "paid"
