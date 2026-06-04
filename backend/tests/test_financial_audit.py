"""
Sprint 2 — Financial Audit: document billing system gaps and verify current behavior.

The billing system has documented limitations (all marked TODO in code):
  - No partial payment support
  - No refund/reversal support
  - No invoice numbering
  - No duplicate invoice prevention (no unique constraint on bill+appointment)

This file documents each gap as a test that asserts the expected behavior
(preventing silent regressions when features are eventually implemented).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.appointment import AppointmentStatus, Appointment
from app.models.billing import Billing, BillingStatus
from app.models.user import UserRole
from app.schemas.billing import BillingCreate
from app.services import billing_service, reporting_service
from tests.factories import (
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)

_SLOT_TIME = datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc)
_SLOT_TIME_2 = datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc)


def _setup_minimal(db: Session) -> dict:
    tenant = create_tenant(db)
    doc_user = create_user(
        db, email="fin-doc@test.test", password="TestPass9!",
        role=UserRole.doctor, tenant_id=tenant.id,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)
    pat_user = create_user(
        db, email="fin-pat@test.test", password="TestPass9!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db, tenant_id=tenant.id, user_id=pat_user.id, created_by=doc_user.id,
    )
    db.commit()
    return {"tenant": tenant, "doc_user": doc_user, "doctor": doctor,
            "pat_user": pat_user, "patient": patient}


def _make_appt(db: Session, ctx: dict, time=_SLOT_TIME) -> Appointment:
    from app.crud import crud_appointment
    appt = crud_appointment.add_appointment(db, {
        "patient_id": ctx["patient"].id,
        "doctor_id": ctx["doctor"].id,
        "appointment_time": time.replace(tzinfo=None),
        "status": AppointmentStatus.completed,
        "created_by": ctx["doc_user"].id,
        "tenant_id": ctx["tenant"].id,
    })
    appt.encounter_completed_at = datetime.now(timezone.utc)
    db.commit()
    return appt


class TestPartialPaymentGap:
    """No partial payment support — a bill is either paid or unpaid."""

    def test_bill_is_either_paid_or_unpaid(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appt(db_session, ctx)

        bill = billing_service.create_bill(db_session, BillingCreate(
            patient_id=ctx["patient"].id,
            appointment_id=appt.id,
            amount=Decimal("500.00"),
            status=BillingStatus.unpaid,
        ), current_user=ctx["doc_user"], tenant_id=ctx["tenant"].id)
        assert bill.status == BillingStatus.unpaid

        paid = billing_service.mark_bill_paid(
            db_session, bill.id, ctx["doc_user"], ctx["tenant"].id, "cash",
        )
        assert paid.status == BillingStatus.paid

    def test_no_partial_payment_field(self) -> None:
        """Billing model has no partial_payment or paid_amount fields."""
        assert not hasattr(Billing, "partial_payment")
        assert not hasattr(Billing, "paid_amount")


class TestRefundReversalGap:
    """No refund or payment reversal support."""

    def test_no_refund_status(self) -> None:
        """BillingStatus enum does not include refunded."""
        statuses = [s.value for s in BillingStatus]
        assert "refunded" not in statuses
        assert "reversed" not in statuses

    def test_no_refund_amount_field(self) -> None:
        """Billing model has no refund_amount or refunded_at fields."""
        assert not hasattr(Billing, "refund_amount")
        assert not hasattr(Billing, "refunded_at")


class TestOutstandingBalance:
    """Verify outstanding balance calculation in patient financial ledger."""

    def test_outstanding_balance_correct(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt1 = _make_appt(db_session, ctx, time=_SLOT_TIME)
        appt2 = _make_appt(db_session, ctx, time=_SLOT_TIME_2)

        bill1 = billing_service.create_bill(db_session, BillingCreate(
            patient_id=ctx["patient"].id, appointment_id=appt1.id,
            amount=Decimal("300.00"), status=BillingStatus.unpaid,
        ), current_user=ctx["doc_user"], tenant_id=ctx["tenant"].id)

        billing_service.create_bill(db_session, BillingCreate(
            patient_id=ctx["patient"].id, appointment_id=appt2.id,
            amount=Decimal("200.00"), status=BillingStatus.unpaid,
        ), current_user=ctx["doc_user"], tenant_id=ctx["tenant"].id)

        billing_service.mark_bill_paid(
            db_session, bill1.id, ctx["doc_user"], ctx["tenant"].id, "cash",
        )

        ledger = reporting_service.get_patient_financial_ledger(
            db_session, ctx["doc_user"], ctx["patient"].id, ctx["tenant"].id,
        )
        assert ledger.total_billed == Decimal("500.00")
        assert ledger.total_paid == Decimal("300.00")
        assert ledger.total_unpaid == Decimal("200.00")
        assert ledger.balance == Decimal("200.00")


class TestDuplicateInvoice:
    """The system DOES prevent duplicate bills — only one bill per appointment."""

    def test_duplicate_bill_for_same_appointment_raises(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appt(db_session, ctx)

        billing_service.create_bill(db_session, BillingCreate(
            patient_id=ctx["patient"].id, appointment_id=appt.id,
            amount=Decimal("300.00"), status=BillingStatus.unpaid,
        ), current_user=ctx["doc_user"], tenant_id=ctx["tenant"].id)

        from app.services.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Bill already exists"):
            billing_service.create_bill(db_session, BillingCreate(
                patient_id=ctx["patient"].id, appointment_id=appt.id,
                amount=Decimal("500.00"), status=BillingStatus.unpaid,
            ), current_user=ctx["doc_user"], tenant_id=ctx["tenant"].id)

    def test_different_appointments_can_have_separate_bills(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt1 = _make_appt(db_session, ctx, time=_SLOT_TIME)
        appt2 = _make_appt(db_session, ctx, time=_SLOT_TIME_2)

        billing_service.create_bill(db_session, BillingCreate(
            patient_id=ctx["patient"].id, appointment_id=appt1.id,
            amount=Decimal("300.00"), status=BillingStatus.unpaid,
        ), current_user=ctx["doc_user"], tenant_id=ctx["tenant"].id)

        billing_service.create_bill(db_session, BillingCreate(
            patient_id=ctx["patient"].id, appointment_id=appt2.id,
            amount=Decimal("500.00"), status=BillingStatus.unpaid,
        ), current_user=ctx["doc_user"], tenant_id=ctx["tenant"].id)

        ledger = reporting_service.get_patient_financial_ledger(
            db_session, ctx["doc_user"], ctx["patient"].id, ctx["tenant"].id,
        )
        assert len(ledger.bills) == 2


class TestInvoiceNumberingGap:
    """No invoice numbering — bills are identified by UUID only."""

    def test_no_invoice_number_field(self) -> None:
        assert not hasattr(Billing, "invoice_number")
        assert not hasattr(Billing, "invoice_series")


class TestPaymentMethodTracking:
    """Payment method is tracked on the bill."""

    def test_payment_method_recorded(self, db_session: Session) -> None:
        ctx = _setup_minimal(db_session)
        appt = _make_appt(db_session, ctx)

        bill = billing_service.create_bill(db_session, BillingCreate(
            patient_id=ctx["patient"].id, appointment_id=appt.id,
            amount=Decimal("200.00"), status=BillingStatus.unpaid,
        ), current_user=ctx["doc_user"], tenant_id=ctx["tenant"].id)

        paid = billing_service.mark_bill_paid(
            db_session, bill.id, ctx["doc_user"], ctx["tenant"].id, "upi",
        )
        assert paid.payment_method == "upi"
