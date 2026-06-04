"""
P1.4 — Billing & Invoice Audit: consultation fee, procedure fees, discount, GST, total, invoice HTML.

Tests verify the billing math and invoice HTML rendering without mocking.
Discount and GST are NOT implemented (documented TODO Phase 3C/4) — tests
assert they are NOT present in output to prevent silent regressions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.schemas.document import InvoiceDocumentData
from app.services.document_service import _build_invoice_html, _fmt_currency

_NOW = datetime.now(timezone.utc)
_TENANT_ID = uuid4()


def _make_data(
    *,
    consultation: str = "500.00",
    inventory_items: list[dict] | None = None,
    status: str = "paid",
    paid_via: str | None = "cash",
) -> InvoiceDocumentData:
    items = inventory_items or []
    inv_total = sum(
        Decimal(str(i.get("total", "0"))) for i in items
    )
    bill_total = Decimal(consultation) + inv_total
    return InvoiceDocumentData(
        bill_id=uuid4(),
        patient_id=uuid4(),
        patient_name="Test Patient",
        doctor_name="Dr. Test",
        appointment_id=uuid4(),
        appointment_time=_NOW,
        tenant_id=_TENANT_ID,
        tenant_name="Test Clinic",
        bill_amount=bill_total,
        consultation_amount=Decimal(consultation),
        inventory_amount=inv_total,
        inventory_items=items,
        status=status,
        paid_at=_NOW if status == "paid" else None,
        paid_via=paid_via,
        created_at=_NOW,
    )


class TestBillingMath:
    """Verify billing arithmetic: consultation + inventory = total."""

    def test_consultation_only(self) -> None:
        data = _make_data(consultation="500.00")
        assert data.bill_amount == Decimal("500.00")
        assert data.consultation_amount == Decimal("500.00")
        assert data.inventory_amount == Decimal("0.00")

    def test_consultation_with_single_procedure(self) -> None:
        data = _make_data(
            consultation="300.00",
            inventory_items=[{"item_name": "Scaling", "quantity": 1, "total": "1500.00"}],
        )
        assert data.bill_amount == Decimal("1800.00")
        assert data.consultation_amount == Decimal("300.00")
        assert data.inventory_amount == Decimal("1500.00")

    def test_consultation_with_multiple_procedures(self) -> None:
        data = _make_data(
            consultation="500.00",
            inventory_items=[
                {"item_name": "Scaling", "quantity": 1, "total": "1500.00"},
                {"item_name": "X-Ray", "quantity": 2, "total": "600.00"},
                {"item_name": "Filling", "quantity": 3, "total": "4500.00"},
            ],
        )
        assert data.bill_amount == Decimal("7100.00")
        assert data.consultation_amount == Decimal("500.00")
        assert data.inventory_amount == Decimal("6600.00")

    def test_discount_not_applied(self) -> None:
        """No discount field exists — total must equal sum of parts."""
        data = _make_data(
            consultation="1000.00",
            inventory_items=[{"item_name": "Scaling", "quantity": 1, "total": "2000.00"}],
        )
        expected = data.consultation_amount + data.inventory_amount
        assert data.bill_amount == expected

    def test_gst_not_applied(self) -> None:
        """No GST field exists — total must equal sum of parts with zero tax."""
        data = _make_data(consultation="500.00")
        assert data.bill_amount == Decimal("500.00")
        # Confirm no GST fields on the data object
        assert not hasattr(data, "gst_amount")
        assert not hasattr(data, "gst_registration")

    def test_currency_formatting(self) -> None:
        assert _fmt_currency(Decimal("500.00")) == "₹500.00"
        assert _fmt_currency(Decimal("0.00")) == "₹0.00"
        assert _fmt_currency(Decimal("1234.50")) == "₹1234.50"
        assert _fmt_currency(Decimal("1000000.00")) == "₹1000000.00"


class TestInvoiceHtmlRendering:
    """Invoice HTML builder with realistic billing scenarios."""

    def test_consultation_only_html(self) -> None:
        data = _make_data(
            consultation="300.00",
            status="unpaid",
            paid_via=None,
        )
        html = _build_invoice_html(data)
        assert "Consultation Fee" in html
        assert "₹300.00" in html
        assert "UNPAID" in html
        assert "Test Clinic" in html
        assert "Dr. Test" in html
        assert "Test Patient" in html

    def test_consultation_with_procedures_html(self) -> None:
        data = _make_data(
            consultation="500.00",
            inventory_items=[
                {"item_name": "Scaling", "quantity": 1, "total": "1500.00"},
                {"item_name": "X-Ray", "quantity": 2, "total": "600.00"},
            ],
        )
        html = _build_invoice_html(data)
        assert "Consultation Fee" in html
        assert "Scaling" in html
        assert "X-Ray" in html
        assert "₹2600.00" in html  # total
        assert "PAID" in html
        assert "cash" in html

    def test_unpaid_invoice(self) -> None:
        data = _make_data(
            consultation="750.00",
            status="unpaid",
            paid_via=None,
        )
        html = _build_invoice_html(data)
        assert "UNPAID" in html
        assert "Paid At" not in html
        assert "Payment Method" not in html

    def test_paid_invoice(self) -> None:
        data = _make_data(
            consultation="750.00",
            status="paid",
            paid_via="upi",
        )
        html = _build_invoice_html(data)
        assert "PAID" in html
        assert "Paid At" in html
        assert "UPI" in html or "upi" in html

    def test_bill_total_matches_sum_of_parts(self) -> None:
        """Verify HTML shows correct total = consultation + inventory."""
        data = _make_data(
            consultation="450.00",
            inventory_items=[
                {"item_name": "Filling", "quantity": 1, "total": "2500.00"},
                {"item_name": "Scaling", "quantity": 1, "total": "1200.00"},
            ],
        )
        html = _build_invoice_html(data)
        expected_total = data.consultation_amount + data.inventory_amount
        assert _fmt_currency(expected_total) in html

    def test_discount_not_in_html(self) -> None:
        """Discount is NOT implemented — must not appear in bill items."""
        data = _make_data(consultation="500.00")
        html = _build_invoice_html(data)
        assert "Discount" not in html
