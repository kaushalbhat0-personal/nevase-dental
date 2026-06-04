"""
Reporting aggregate schemas — READ-ONLY derived models for financial reporting.

These are **read models** that compose existing domain data.
They do NOT create new tables or mutate transactional records.

Billing remains the source-of-truth for patient charges.
Inventory movements remain the source-of-truth for stock history.
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.billing import BillingStatus
from app.models.inventory import InventoryItemType, InventoryMovementType


# ── Billing Report ───────────────────────────────────────────────────────────


class BillingReportAggregate(BaseModel):
    """
    Full billing snapshot for reporting dashboards and exports.

    Derived from Billing + Appointment + Doctor + InventoryUsage.
    """

    model_config = ConfigDict(from_attributes=True)

    bill_id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID | None = None
    doctor_name: str | None = None
    doctor_specialization: str | None = None
    appointment_id: UUID | None = None
    appointment_time: datetime | None = None
    tenant_id: UUID
    tenant_name: str | None = None
    bill_amount: Decimal = Field(..., description="Total bill amount")
    inventory_items: list[dict] = Field(default_factory=list)
    # TODO: Phase 3B — GST-ready tax line injection
    # gst_amount: Decimal | None = None
    # taxable_amount: Decimal | None = None
    # TODO: Phase 3B — Tax invoice reference
    # invoice_number: str | None = None
    consultation_amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Derived: bill_amount - inventory_selling_total",
    )
    inventory_amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Derived: sum(qty × item.selling_price) from visit inventory usage",
    )
    status: BillingStatus
    paid_at: datetime | None = None
    paid_via: str | None = Field(default=None, description="payment_method")
    created_by: UUID
    created_at: datetime


class BillingReportFilter(BaseModel):
    """Filter parameters for billing report queries."""

    date_from: datetime | None = None
    date_to: datetime | None = None
    status: BillingStatus | None = None
    doctor_id: UUID | None = None
    patient_id: UUID | None = None
    skip: int = 0
    limit: int = 50


class BillingReportResult(BaseModel):
    """Paginated billing report response."""

    items: list[BillingReportAggregate] = Field(default_factory=list)
    total: int = 0
    skip: int = 0
    limit: int = 50


# ── Inventory Ledger ─────────────────────────────────────────────────────────


class InventoryLedgerRow(BaseModel):
    """
    Immutable movement history with running stock snapshot.

    Running stock is computed via SQL window function:
        SUM(CASE type WHEN 'IN' THEN qty WHEN 'OUT' THEN -qty ELSE signed_qty END)
        OVER (PARTITION BY item_id ORDER BY created_at, id ROWS UNBOUNDED PRECEDING)
    """

    model_config = ConfigDict(from_attributes=True)

    movement_id: UUID
    item_id: UUID
    item_name: str
    item_type: InventoryItemType
    movement_type: InventoryMovementType
    quantity: int = Field(..., description="Signed delta (+ for IN, - for OUT, signed for ADJUST)")
    running_stock: int = Field(..., description="Snapshot after this movement")
    doctor_id: UUID | None = None
    billing_id: UUID | None = None
    encounter_id: UUID | None = Field(
        default=None,
        description="Appointment ID when reference_type=APPOINTMENT",
    )
    actor_id: UUID | None = None
    actor_role: str | None = None
    created_at: datetime


class InventoryLedgerFilter(BaseModel):
    """Filter parameters for inventory ledger queries."""

    date_from: datetime | None = None
    date_to: datetime | None = None
    item_id: UUID | None = None
    movement_type: InventoryMovementType | None = None
    skip: int = 0
    limit: int = 50


class InventoryLedgerResult(BaseModel):
    """Paginated inventory ledger response."""

    items: list[InventoryLedgerRow] = Field(default_factory=list)
    total: int = 0
    skip: int = 0
    limit: int = 50


# ── Patient Financial Ledger ─────────────────────────────────────────────────


class PatientBillSummary(BaseModel):
    """Single bill within a patient's financial ledger."""

    model_config = ConfigDict(from_attributes=True)

    bill_id: UUID
    appointment_id: UUID | None = None
    amount: Decimal
    status: BillingStatus
    paid_at: datetime | None = None
    created_at: datetime


class PatientEncounterRef(BaseModel):
    """Lightweight encounter reference for patient ledger context."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    appointment_time: datetime
    doctor_name: str
    has_bill: bool = False


class PatientFinancialLedger(BaseModel):
    """
    Patient statement — all bills, payments, balances, and encounter references.

    Purpose:
    * Patient statements
    * Clinic reconciliation
    * Taxation/export
    """

    model_config = ConfigDict(from_attributes=True)

    patient_id: UUID
    patient_name: str
    total_billed: Decimal = Decimal("0.00")
    total_paid: Decimal = Decimal("0.00")
    total_unpaid: Decimal = Decimal("0.00")
    balance: Decimal = Field(
        default=Decimal("0.00"),
        description="total_billed - total_paid",
    )
    last_payment_at: datetime | None = None
    bills: list[PatientBillSummary] = Field(default_factory=list)
    encounters: list[PatientEncounterRef] = Field(default_factory=list)

    # TODO: Phase 3B — Insurance claims
    # insurance_claims: list[InsuranceClaimSummary] = Field(default_factory=list)
    # TODO: Phase 3B — Refund tracking
    # refunds: list[RefundSummary] = Field(default_factory=list)
    # TODO: Phase 3B — Partial payments
    # partial_payments: list[PartialPaymentSummary] = Field(default_factory=list)


# ── Export ───────────────────────────────────────────────────────────────────


class ExportFormat(str, enum.Enum):
    """Supported export formats."""

    csv = "csv"
    xlsx = "xlsx"
    pdf = "pdf"


class ExportRequest(BaseModel):
    """Request body for report export."""

    format: ExportFormat = ExportFormat.csv
    date_from: datetime | None = None
    date_to: datetime | None = None
    status: BillingStatus | None = None
    doctor_id: UUID | None = None
    patient_id: UUID | None = None
    item_id: UUID | None = None
    movement_type: InventoryMovementType | None = None
