"""
Document generation schemas — READ-ONLY derived models for PDF/export generation.

These are **read models** that compose existing domain data.
They do NOT create new tables or mutate transactional records.

Documents are DERIVED ARTIFACTS:
  canonical backend aggregate → document renderer → generated artifact

Source-of-truth remains:
  - encounter aggregate (appointment + SOAP + vitals + prescriptions)
  - billing records
  - inventory ledger
  - prescriptions
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, enum.Enum):
    """Types of documents that can be generated."""

    invoice = "invoice"
    patient_statement = "patient_statement"
    prescription = "prescription"
    encounter_summary = "encounter_summary"
    purchase_invoice = "purchase_invoice"
    inward_stock_summary = "inward_stock_summary"
    supplier_purchase_history = "supplier_purchase_history"


class DocumentFormat(str, enum.Enum):
    """Supported document output formats."""

    pdf = "pdf"
    html = "html"


class DocumentMeta(BaseModel):
    """Metadata for any generated document."""

    model_config = ConfigDict(from_attributes=True)

    document_type: DocumentType
    document_format: DocumentFormat = DocumentFormat.pdf
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: UUID | None = None
    actor_id: UUID | None = None
    request_id: str | None = None
    resource_id: str | None = None

    # TODO: Phase 3C — Document versioning
    # version: int = 1
    # TODO: Phase 3C — Document locale for multilingual rendering
    # locale: str = "en"


class InvoiceDocumentData(BaseModel):
    """
    Data payload for invoice PDF generation.

    Derived from BillingReportAggregate + additional billing details.
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
    bill_amount: Decimal
    consultation_amount: Decimal = Decimal("0.00")
    inventory_amount: Decimal = Decimal("0.00")
    inventory_items: list[dict] = Field(default_factory=list)
    status: str
    paid_at: datetime | None = None
    paid_via: str | None = None
    created_at: datetime

    # TODO: Phase 3C — GST/tax invoice support
    # gst_registration: str | None = None
    # taxable_amount: Decimal | None = None
    # gst_amount: Decimal | None = None
    # invoice_number: str | None = None
    # hsn_codes: list[dict] = Field(default_factory=list)

    # TODO: Phase 3C — QR payment links
    # upi_payment_link: str | None = None
    # qr_code_base64: str | None = None

    # TODO: Phase 3C — Digital signatures
    # digital_signature: str | None = None


class PatientStatementDocumentData(BaseModel):
    """
    Data payload for patient financial statement PDF.

    Derived from PatientFinancialLedger.
    """

    model_config = ConfigDict(from_attributes=True)

    patient_id: UUID
    patient_name: str
    tenant_id: UUID | None = None
    tenant_name: str | None = None
    total_billed: Decimal = Decimal("0.00")
    total_paid: Decimal = Decimal("0.00")
    total_unpaid: Decimal = Decimal("0.00")
    balance: Decimal = Decimal("0.00")
    last_payment_at: datetime | None = None
    bills: list[dict] = Field(default_factory=list)
    encounters: list[dict] = Field(default_factory=list)
    statement_date_from: datetime | None = None
    statement_date_to: datetime | None = None

    # TODO: Phase 3C — Insurance claims
    # insurance_claims: list[dict] = Field(default_factory=list)
    # TODO: Phase 3C — Refund tracking
    # refunds: list[dict] = Field(default_factory=list)
    # TODO: Phase 3C — Payment plan details
    # payment_plan: dict | None = None


class PrescriptionDocumentData(BaseModel):
    """
    Data payload for prescription PDF generation.

    Derived from EncounterDetailAggregate (prescriptions section).
    CRITICAL: Inventory usage must NOT appear as prescription medicines.
    """

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    prescription_id: UUID | None = None
    doctor_id: UUID
    doctor_name: str
    doctor_specialization: str | None = None
    doctor_registration: str | None = None
    patient_id: UUID
    patient_name: str
    patient_age: int | None = None
    patient_gender: str | None = None
    tenant_id: UUID
    tenant_name: str | None = None
    clinic_name: str | None = None
    clinic_address: str | None = None
    diagnosis: str | None = None
    prescriptions: list[dict] = Field(
        default_factory=list,
        description="Prescribed medicines from Prescription model — NOT inventory usage",
    )
    vitals: dict | None = None
    notes: str | None = None
    created_at: datetime

    # TODO: Phase 3C — E-prescription digital signature
    # digital_signature: str | None = None
    # prescription_qr: str | None = None
    # TODO: Phase 3C — DEA/controlled substance fields
    # dea_number: str | None = None
    # refills: int | None = None


class EncounterSummaryDocumentData(BaseModel):
    """
    Data payload for encounter summary PDF generation.

    Derived from EncounterDetailAggregate.
    This becomes the future AI-summary delivery surface.
    """

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    doctor_specialization: str | None = None
    tenant_id: UUID
    tenant_name: str | None = None
    appointment_time: datetime
    status: str
    encounter_started_at: datetime | None = None
    encounter_completed_at: datetime | None = None

    # SOAP sections
    subjective_notes: str | None = None
    objective_notes: str | None = None
    assessment_notes: str | None = None
    plan_notes: str | None = None

    # Clinical data
    diagnosis: str | None = None
    treatment_summary: str | None = None
    clinical_notes: str | None = None

    # Vitals
    vitals: dict | None = None

    # Prescriptions
    prescriptions: list[dict] = Field(default_factory=list)

    # Follow-up
    follow_up_date: datetime | None = None
    follow_up_notes: str | None = None

    created_at: datetime

    # TODO: Phase 3C — AI-generated clinical summary
    # ai_summary: str | None = None
    # TODO: Phase 3C — ICD codes
    # icd_codes: list[dict] = Field(default_factory=list)
    # TODO: Phase 3C — Referrals
    # referrals: list[dict] = Field(default_factory=list)
    # TODO: Phase 3C — Lab results
    # lab_results: list[dict] = Field(default_factory=list)
