"""
Document Generation Service — canonical document rendering layer.

Architecture:
  aggregate-driven rendering → reusable document builders → pluggable templates

Documents are DERIVED ARTIFACTS:
  canonical backend aggregate → document renderer → generated artifact

Source-of-truth remains:
  - encounter aggregate (appointment + SOAP + vitals + prescriptions)
  - billing records
  - inventory ledger
  - prescriptions

Separation of concerns:
  1. Data aggregation (fetch from existing services)
  2. Document rendering (build HTML → convert to PDF)
  3. Export delivery (stream bytes to client)

Branding Integration (Phase 3C):
  - All document builders consume tenant organization + branding profiles
  - Branding is derived from TenantOrganizationProfile + TenantBrandingProfile
  - NO hardcoded clinic names/colors — everything comes from tenant profiles
  - Headers, footers, colors, logos, contact info, prescription/invoice footers
  - Future-safe for white-labeling, multilingual rendering, custom templates

TODO: Phase 3C — Cached generation with S3/object storage
TODO: Phase 3C — Signed URLs for document downloads
TODO: Phase 3C — Email delivery pipeline
TODO: Phase 3C — Document versioning
TODO: Phase 4 — Custom document templates (per-tenant)
TODO: Phase 4 — Hospital chain / department branding
TODO: Phase 4 — Doctor digital signatures
TODO: Phase 4 — Digital stamps / seals
TODO: Phase 4 — QR verification codes on documents
TODO: Phase 4 — NABH/JCI accreditation metadata
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from dataclasses import dataclass, field

from app.core.request_context import get_request_id
from app.models.user import User
from app.schemas.document import (
    DocumentFormat,
    DocumentMeta,
    DocumentType,
    EncounterSummaryDocumentData,
    InvoiceDocumentData,
    PatientStatementDocumentData,
    PrescriptionDocumentData,
)
from app.services import encounter_service
from app.services.exceptions import NotFoundError
from app.services.reporting_service import (
    get_billing_report,
    get_patient_financial_ledger,
)
from app.services.security_audit import log_structured_audit_event

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# BRANDING CONTEXT (Phase 3C)
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class BrandingContext:
    """
    Tenant branding context for document rendering.

    Derived from TenantOrganizationProfile + TenantBrandingProfile.
    All fields optional — missing profiles produce empty defaults.
    Documents MUST consume this context, NOT hardcoded clinic data.

    TODO: Phase 4 — Custom document templates (per-tenant)
    TODO: Phase 4 — Hospital chain / department branding
    TODO: Phase 4 — Doctor digital signatures
    TODO: Phase 4 — Digital stamps / seals
    TODO: Phase 4 — QR verification codes on documents
    TODO: Phase 4 — NABH/JCI accreditation metadata
    """

    # Organization identity
    organization_name: str | None = None
    legal_name: str | None = None
    logo_url: str | None = None

    # Contact
    phone: str | None = None
    email: str | None = None
    website: str | None = None

    # Address
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    # Compliance / Taxation
    gst_number: str | None = None
    registration_number: str | None = None

    # Regional defaults
    timezone: str | None = None
    currency: str | None = None

    # Document footers
    prescription_footer: str | None = None
    invoice_footer: str | None = None

    # Branding colors
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None

    # Document styling
    document_header_style: str | None = None
    watermark_text: str | None = None

    # Template selection
    prescription_template: str | None = None
    invoice_template: str | None = None


def _load_branding_context(db: Session, tenant_id: UUID | None) -> BrandingContext:
    """
    Load branding context for a tenant.

    Returns empty BrandingContext if tenant_id is None or profiles don't exist.
    """
    if tenant_id is None:
        return BrandingContext()

    from app.services.tenant_branding_service import get_tenant_branding_context

    ctx = get_tenant_branding_context(db, tenant_id)
    org = ctx.get("organization", {}) or {}
    brand = ctx.get("branding", {}) or {}

    return BrandingContext(
        # Organization
        organization_name=org.get("organization_name"),
        legal_name=org.get("legal_name"),
        logo_url=org.get("logo_url"),
        phone=org.get("phone"),
        email=org.get("email"),
        website=org.get("website"),
        address_line_1=org.get("address_line_1"),
        address_line_2=org.get("address_line_2"),
        city=org.get("city"),
        state=org.get("state"),
        postal_code=org.get("postal_code"),
        country=org.get("country"),
        gst_number=org.get("gst_number"),
        registration_number=org.get("registration_number"),
        timezone=org.get("timezone"),
        currency=org.get("currency"),
        prescription_footer=org.get("prescription_footer"),
        invoice_footer=org.get("invoice_footer"),
        # Branding
        primary_color=brand.get("primary_color"),
        secondary_color=brand.get("secondary_color"),
        accent_color=brand.get("accent_color"),
        document_header_style=brand.get("document_header_style"),
        watermark_text=brand.get("watermark_text"),
        prescription_template=brand.get("prescription_template"),
        invoice_template=brand.get("invoice_template"),
    )


# ═════════════════════════════════════════════════════════════════════════════
# TEMPLATE HELPERS
# ═════════════════════════════════════════════════════════════════════════════


def _fmt_currency(amount: Decimal | None) -> str:
    """Format decimal as currency string."""
    if amount is None:
        return "₹0.00"
    return f"₹{amount:.2f}"


def _fmt_dt(dt: datetime | None) -> str:
    """Format datetime for document display."""
    if dt is None:
        return ""
    return dt.strftime("%d %b %Y, %I:%M %p")


def _fmt_date(dt: datetime | None) -> str:
    """Format date only for document display."""
    if dt is None:
        return ""
    return dt.strftime("%d %b %Y")


def _escape_html(text: str | None) -> str:
    """Escape HTML special characters for safe template rendering."""
    if text is None:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _build_css(branding: BrandingContext | None = None) -> str:
    """
    Return shared CSS for all document types.

    Applies tenant branding colors when available.
    Falls back to default blue (#2563eb) when no branding is set.
    """
    primary = _escape_html(branding.primary_color) if branding and branding.primary_color else "#2563eb"
    secondary = _escape_html(branding.secondary_color) if branding and branding.secondary_color else "#555"
    accent = _escape_html(branding.accent_color) if branding and branding.accent_color else "#f59e0b"

    # Build CSS template — use string.Template to avoid
    # Python .format() parsing issues with CSS values like "8px", "11px".
    _css_template = """
        @page {
            margin: $page_margin;
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 8px;
                color: #888;
            }
        }
        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 11px;
            line-height: 1.5;
            color: #222;
            margin: 0;
            padding: 0;
        }
        .header {
            border-bottom: 2px solid $primary;
            padding-bottom: 8px;
            margin-bottom: 12px;
        }
        .header h1 {
            font-size: 18px;
            color: $primary;
            margin: 0 0 4px 0;
        }
        .header .clinic-info {
            font-size: 10px;
            color: $secondary;
        }
        .section {
            margin-bottom: 12px;
        }
        .section-title {
            font-size: 12px;
            font-weight: bold;
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 3px;
            margin-bottom: 6px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 8px;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 5px 6px;
            text-align: left;
            font-size: 10px;
        }
        th {
            background-color: #f0f4ff;
            font-weight: bold;
            color: #333;
        }
        .info-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 8px;
        }
        .info-block {
            flex: 1;
            min-width: 180px;
        }
        .info-block label {
            font-size: 9px;
            color: #888;
            text-transform: uppercase;
            display: block;
        }
        .info-block .value {
            font-size: 11px;
            font-weight: 500;
        }
        .status-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
        }
        .status-paid {
            background-color: #d1fae5;
            color: #065f46;
        }
        .status-unpaid {
            background-color: #fee2e2;
            color: #991b1b;
        }
        .total-row {
            font-weight: bold;
            background-color: #f9fafb;
        }
        .footer {
            margin-top: 20px;
            padding-top: 8px;
            border-top: 1px solid #ddd;
            font-size: 9px;
            color: #888;
            text-align: center;
        }
        .todo-placeholder {
            border: 1px dashed $accent;
            background: #fffbeb;
            padding: 6px;
            margin: 6px 0;
            font-size: 9px;
            color: #92400e;
            border-radius: 3px;
        }
        .vitals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 4px;
        }
        .vital-item {
            padding: 3px 6px;
            background: #f9fafb;
            border-radius: 3px;
        }
        .vital-item label {
            font-size: 8px;
            color: #888;
            display: block;
        }
        .vital-item .value {
            font-size: 11px;
            font-weight: 500;
        }
        .soap-block {
            margin-bottom: 8px;
        }
        .soap-block .soap-label {
            font-weight: bold;
            color: $primary;
            font-size: 10px;
        }
        .soap-block .soap-content {
            margin-left: 8px;
            white-space: pre-wrap;
        }
        .prescription-item {
            padding: 4px 0;
            border-bottom: 1px dotted #eee;
        }
        .prescription-item:last-child {
            border-bottom: none;
        }
        .branding-logo {
            max-height: 60px;
            max-width: 200px;
            margin-bottom: 6px;
        }
        .branding-contact {
            font-size: 9px;
            color: $secondary;
            margin-top: 2px;
        }
        .branding-gst {
            font-size: 9px;
            color: $secondary;
            margin-top: 1px;
        }
        .branding-footer {
            margin-top: 16px;
            padding-top: 6px;
            border-top: 1px solid #ddd;
            font-size: 9px;
            color: #666;
            text-align: center;
            font-style: italic;
        }
        .watermark {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-30deg);
            font-size: 60px;
            opacity: 0.06;
            color: $primary;
            pointer-events: none;
            z-index: -1;
            white-space: nowrap;
        }
    """

    from string import Template
    return Template(_css_template).safe_substitute(
        page_margin="15mm 12mm",
        primary=primary,
        secondary=secondary,
        accent=accent,
    )


def _build_html_document(
    title: str,
    body_html: str,
    meta: DocumentMeta,
    branding: BrandingContext | None = None,
) -> str:
    """Wrap body HTML in a full HTML document with shared CSS and branding."""
    css = _build_css(branding)

    # Watermark
    watermark_html = ""
    if branding and branding.watermark_text:
        watermark_html = f'<div class="watermark">{_escape_html(branding.watermark_text)}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{_escape_html(title)}</title>
<style>{css}</style>
</head>
<body>
{watermark_html}
{body_html}
<div class="footer">
    <p>Generated on {_fmt_dt(meta.generated_at)} — Computer-generated document</p>
    <p>Document ID: {_escape_html(meta.resource_id or "")} | Type: {meta.document_type.value}</p>
    <!-- TODO: Phase 4 — Digital signature verification -->
    <!-- TODO: Phase 4 — Document hash for tamper detection -->
    <!-- TODO: Phase 4 — QR verification code -->
</div>
</body>
</html>"""


def _build_clinic_header(
    tenant_name: str | None,
    clinic_name: str | None = None,
    doctor_name: str | None = None,
    doctor_specialization: str | None = None,
    branding: BrandingContext | None = None,
) -> str:
    """
    Build clinic/doctor branding header.

    Consumes tenant branding context for logo, organization name, contact info, GST.
    Falls back to tenant_name / clinic_name when branding is not set.
    """
    # Use branding organization_name if available, otherwise fallback
    org_name = branding.organization_name if branding and branding.organization_name else None
    name = org_name or clinic_name or tenant_name or "Clinic"

    parts: list[str] = []

    # Logo
    if branding and branding.logo_url:
        parts.append(f'<img src="{_escape_html(branding.logo_url)}" alt="{_escape_html(name)}" class="branding-logo" />')

    parts.append(f"<h1>{_escape_html(name)}</h1>")

    # Doctor info
    if doctor_name:
        sub = _escape_html(doctor_name)
        if doctor_specialization:
            sub += f" — {_escape_html(doctor_specialization)}"
        parts.append(f'<div class="clinic-info">{sub}</div>')

    # Contact info from branding
    contact_parts: list[str] = []
    if branding and branding.address_line_1:
        addr = _escape_html(branding.address_line_1)
        if branding.address_line_2:
            addr += f", {_escape_html(branding.address_line_2)}"
        if branding.city:
            addr += f", {_escape_html(branding.city)}"
        if branding.state:
            addr += f", {_escape_html(branding.state)}"
        if branding.postal_code:
            addr += f" {_escape_html(branding.postal_code)}"
        if branding.country:
            addr += f", {_escape_html(branding.country)}"
        contact_parts.append(addr)

    if branding and branding.phone:
        contact_parts.append(f"Phone: {_escape_html(branding.phone)}")
    if branding and branding.email:
        contact_parts.append(f"Email: {_escape_html(branding.email)}")
    if branding and branding.website:
        contact_parts.append(f"Web: {_escape_html(branding.website)}")

    if contact_parts:
        parts.append(f'<div class="branding-contact">{" | ".join(contact_parts)}</div>')

    # GST / Registration
    gst_parts: list[str] = []
    if branding and branding.gst_number:
        gst_parts.append(f"GST: {_escape_html(branding.gst_number)}")
    if branding and branding.registration_number:
        gst_parts.append(f"Reg: {_escape_html(branding.registration_number)}")
    if gst_parts:
        parts.append(f'<div class="branding-gst">{" | ".join(gst_parts)}</div>')

    return f'<div class="header">{"".join(parts)}</div>'


def _build_info_block(label: str, value: str) -> str:
    """Build a single info block for the info grid."""
    return f'<div class="info-block"><label>{_escape_html(label)}</label><div class="value">{value}</div></div>'


def _build_info_grid(blocks: list[tuple[str, str]]) -> str:
    """Build an info grid from label/value pairs."""
    items = "\n".join(_build_info_block(label, value) for label, value in blocks)
    return f'<div class="info-grid">{items}</div>'


def _build_table(headers: list[str], rows: list[list[str]]) -> str:
    """Build an HTML table from headers and rows."""
    header_cells = "".join(f"<th>{_escape_html(h)}</th>" for h in headers)
    body_rows = ""
    for row in rows:
        cells = "".join(f"<td>{cell}</td>" for cell in row)
        body_rows += f"<tr>{cells}</tr>"
    return f"""<table>
<thead><tr>{header_cells}</tr></thead>
<tbody>{body_rows}</tbody>
</table>"""


def _build_todo_block(message: str) -> str:
    """Build a visible TODO placeholder in the document."""
    return f'<div class="todo-placeholder">🔧 TODO: {_escape_html(message)}</div>'


# ═════════════════════════════════════════════════════════════════════════════
# DOCUMENT BUILDERS
# ═════════════════════════════════════════════════════════════════════════════


def _build_invoice_html(
    data: InvoiceDocumentData,
    branding: BrandingContext | None = None,
) -> str:
    """Build invoice PDF HTML from aggregated data."""
    status_class = "status-paid" if data.status == "paid" else "status-unpaid"
    status_display = data.status.upper() if data.status else "UNPAID"

    # Header with branding
    header = _build_clinic_header(
        tenant_name=data.tenant_name,
        doctor_name=data.doctor_name,
        doctor_specialization=data.doctor_specialization,
        branding=branding,
    )

    # Info grid
    info_blocks = [
        ("Invoice Date", _fmt_dt(data.created_at)),
        ("Bill ID", str(data.bill_id)),
        ("Status", f'<span class="status-badge {status_class}">{status_display}</span>'),
        ("Patient", _escape_html(data.patient_name)),
        ("Doctor", _escape_html(data.doctor_name or "")),
    ]
    if data.paid_at:
        info_blocks.append(("Paid At", _fmt_dt(data.paid_at)))
    if data.paid_via:
        info_blocks.append(("Payment Method", _escape_html(data.paid_via)))
    if data.appointment_time:
        info_blocks.append(("Appointment", _fmt_dt(data.appointment_time)))

    info_grid = _build_info_grid(info_blocks)

    # Bill items table
    bill_rows = [
        ["Consultation Fee", "", _fmt_currency(data.consultation_amount)],
    ]
    for item in data.inventory_items:
        bill_rows.append([
            _escape_html(item.get("item_name", "Inventory Item")),
            f"× {item.get('quantity', 0)}",
            _fmt_currency(Decimal(str(item.get("total", "0.00")))),
        ])
    bill_rows.append(["", "Total", _fmt_currency(data.bill_amount)])

    bill_table = _build_table(
        ["Description", "Qty", "Amount"],
        bill_rows,
    )

    # Invoice footer from branding
    invoice_footer_html = ""
    if branding and branding.invoice_footer:
        invoice_footer_html = f'<div class="branding-footer">{_escape_html(branding.invoice_footer)}</div>'

    body = f"""
{header}
<div class="section">
    <div class="section-title">Invoice</div>
    {info_grid}
</div>
<div class="section">
    <div class="section-title">Bill Items</div>
    {bill_table}
</div>
{invoice_footer_html}
<!-- TODO: Phase 4 — GST/tax invoice support -->
<!-- TODO: Phase 4 — QR code for UPI payment links -->
<!-- TODO: Phase 4 — Digital signature -->
"""

    return _build_html_document(
        title=f"Invoice - {data.patient_name}",
        body_html=body,
        meta=DocumentMeta(
            document_type=DocumentType.invoice,
            tenant_id=data.tenant_id,
            resource_id=str(data.bill_id),
        ),
        branding=branding,
    )


def _build_patient_statement_html(
    data: PatientStatementDocumentData,
    branding: BrandingContext | None = None,
) -> str:
    """Build patient financial statement PDF HTML."""
    header = _build_clinic_header(
        tenant_name=data.tenant_name,
        branding=branding,
    )

    # Summary info
    info_blocks = [
        ("Patient Name", _escape_html(data.patient_name)),
        ("Patient ID", str(data.patient_id)),
        ("Total Billed", _fmt_currency(data.total_billed)),
        ("Total Paid", _fmt_currency(data.total_paid)),
        ("Total Unpaid", _fmt_currency(data.total_unpaid)),
        ("Balance", _fmt_currency(data.balance)),
    ]
    if data.last_payment_at:
        info_blocks.append(("Last Payment", _fmt_dt(data.last_payment_at)))
    if data.statement_date_from:
        info_blocks.append(("From", _fmt_date(data.statement_date_from)))
    if data.statement_date_to:
        info_blocks.append(("To", _fmt_date(data.statement_date_to)))

    info_grid = _build_info_grid(info_blocks)

    # Bills table
    bill_headers = ["Bill ID", "Amount", "Status", "Paid At", "Created At"]
    bill_rows = []
    for b in data.bills:
        b_status = b.get("status", "")
        status_class = "status-paid" if b_status == "paid" else "status-unpaid"
        bill_rows.append([
            str(b.get("bill_id", "")),
            _fmt_currency(Decimal(str(b.get("amount", "0.00")))),
            f'<span class="status-badge {status_class}">{_escape_html(b_status.upper())}</span>',
            _fmt_dt(b.get("paid_at")),
            _fmt_dt(b.get("created_at")),
        ])

    bill_table = _build_table(bill_headers, bill_rows)

    # Encounters table
    enc_headers = ["Appointment ID", "Date", "Doctor", "Has Bill"]
    enc_rows = []
    for e in data.encounters:
        enc_rows.append([
            str(e.get("appointment_id", "")),
            _fmt_dt(e.get("appointment_time")),
            _escape_html(e.get("doctor_name", "")),
            "Yes" if e.get("has_bill") else "No",
        ])

    enc_table = _build_table(enc_headers, enc_rows)

    body = f"""
{header}
<div class="section">
    <div class="section-title">Patient Financial Statement</div>
    {info_grid}
</div>
<div class="section">
    <div class="section-title">Bill Details</div>
    {bill_table}
</div>
<div class="section">
    <div class="section-title">Encounter References</div>
    {enc_table}
</div>
<!-- TODO: Phase 3C — Insurance claim references -->
<!-- TODO: Phase 3C — Payment plan details -->
<!-- TODO: Phase 3C — Refund tracking -->
"""

    return _build_html_document(
        title=f"Statement - {data.patient_name}",
        body_html=body,
        meta=DocumentMeta(
            document_type=DocumentType.patient_statement,
            tenant_id=data.tenant_id,
            resource_id=str(data.patient_id),
        ),
    )


def _build_prescription_html(
    data: PrescriptionDocumentData,
    branding: BrandingContext | None = None,
) -> str:
    """Build prescription PDF HTML.

    CRITICAL: Only prescription model data is used — NOT inventory usage.
    """
    header = _build_clinic_header(
        tenant_name=data.tenant_name,
        clinic_name=data.clinic_name,
        doctor_name=data.doctor_name,
        doctor_specialization=data.doctor_specialization,
        branding=branding,
    )

    # Doctor & Patient info
    info_blocks = [
        ("Doctor", _escape_html(data.doctor_name)),
        ("Specialization", _escape_html(data.doctor_specialization or "")),
        ("Patient", _escape_html(data.patient_name)),
        ("Date", _fmt_dt(data.created_at)),
    ]
    if data.doctor_registration:
        info_blocks.append(("Reg. No.", _escape_html(data.doctor_registration)))
    if data.patient_age is not None:
        info_blocks.append(("Age", str(data.patient_age)))
    if data.patient_gender:
        info_blocks.append(("Gender", _escape_html(data.patient_gender)))

    info_grid = _build_info_grid(info_blocks)

    # Diagnosis
    diagnosis_html = ""
    if data.diagnosis:
        diagnosis_html = f"""
<div class="section">
    <div class="section-title">Diagnosis</div>
    <p>{_escape_html(data.diagnosis)}</p>
</div>"""

    # Prescribed medicines table
    rx_headers = ["Medicine", "Dosage", "Frequency", "Duration", "Instructions"]
    rx_rows = []
    for rx in data.prescriptions:
        rx_rows.append([
            _escape_html(rx.get("medicine_name", "")),
            _escape_html(rx.get("dosage", "")),
            _escape_html(rx.get("frequency", "")),
            _escape_html(rx.get("duration", "")),
            _escape_html(rx.get("instructions", "")),
        ])

    rx_table = _build_table(rx_headers, rx_rows)

    # Vitals (optional)
    vitals_html = ""
    if data.vitals:
        vitals_items = ""
        for key, label in [
            ("temperature", "Temp (°F)"),
            ("bp_systolic", "BP Systolic"),
            ("bp_diastolic", "BP Diastolic"),
            ("pulse", "Pulse"),
            ("respiratory_rate", "RR"),
            ("spo2", "SpO₂"),
            ("weight", "Weight (kg)"),
            ("height", "Height (cm)"),
            ("bmi", "BMI"),
        ]:
            val = data.vitals.get(key)
            if val is not None:
                vitals_items += f'<div class="vital-item"><label>{label}</label><div class="value">{val}</div></div>'

        if vitals_items:
            vitals_html = f"""
<div class="section">
    <div class="section-title">Vitals</div>
    <div class="vitals-grid">{vitals_items}</div>
</div>"""

    # Notes
    notes_html = ""
    if data.notes:
        notes_html = f"""
<div class="section">
    <div class="section-title">Notes / Instructions</div>
    <p>{_escape_html(data.notes)}</p>
</div>"""

    body = f"""
{header}
<div class="section">
    <div class="section-title">Prescription</div>
    {info_grid}
</div>
{diagnosis_html}
<div class="section">
    <div class="section-title">Prescribed Medicines</div>
    {rx_table}
</div>
{vitals_html}
{notes_html}
<!-- TODO: Phase 3C — E-prescription digital signature -->
<!-- TODO: Phase 3C — QR code for prescription verification -->
<!-- TODO: Phase 3C — DEA/controlled substance fields -->
"""

    return _build_html_document(
        title=f"Prescription - {data.patient_name}",
        body_html=body,
        meta=DocumentMeta(
            document_type=DocumentType.prescription,
            tenant_id=data.tenant_id,
            resource_id=str(data.appointment_id),
        ),
    )


def _build_encounter_summary_html(
    data: EncounterSummaryDocumentData,
    branding: BrandingContext | None = None,
) -> str:
    """Build encounter summary PDF HTML.

    This becomes the future AI-summary delivery surface.
    """
    header = _build_clinic_header(
        tenant_name=data.tenant_name,
        doctor_name=data.doctor_name,
        doctor_specialization=data.doctor_specialization,
        branding=branding,
    )

    # Appointment info
    info_blocks = [
        ("Patient", _escape_html(data.patient_name)),
        ("Doctor", _escape_html(data.doctor_name)),
        ("Appointment", _fmt_dt(data.appointment_time)),
        ("Status", data.status.upper() if data.status else ""),
    ]
    if data.encounter_started_at:
        info_blocks.append(("Started", _fmt_dt(data.encounter_started_at)))
    if data.encounter_completed_at:
        info_blocks.append(("Completed", _fmt_dt(data.encounter_completed_at)))

    info_grid = _build_info_grid(info_blocks)

    # TODO: Phase 3C — AI-generated clinical summary
    # ai_summary_html = _build_todo_block("AI-generated clinical summary will appear here")

    # SOAP sections
    soap_sections = ""
    for label, key in [
        ("Subjective", data.subjective_notes),
        ("Objective", data.objective_notes),
        ("Assessment", data.assessment_notes),
        ("Plan", data.plan_notes),
    ]:
        if key:
            soap_sections += f"""
<div class="soap-block">
    <div class="soap-label">{label}</div>
    <div class="soap-content">{_escape_html(key)}</div>
</div>"""

    soap_html = ""
    if soap_sections:
        soap_html = f"""
<div class="section">
    <div class="section-title">SOAP Notes</div>
    {soap_sections}
</div>"""

    # Diagnosis
    diagnosis_html = ""
    if data.diagnosis:
        diagnosis_html = f"""
<div class="section">
    <div class="section-title">Diagnosis</div>
    <p>{_escape_html(data.diagnosis)}</p>
</div>"""

    # Treatment summary
    treatment_html = ""
    if data.treatment_summary:
        treatment_html = f"""
<div class="section">
    <div class="section-title">Treatment Summary</div>
    <p>{_escape_html(data.treatment_summary)}</p>
</div>"""

    # Clinical notes
    clinical_html = ""
    if data.clinical_notes:
        clinical_html = f"""
<div class="section">
    <div class="section-title">Clinical Notes</div>
    <p>{_escape_html(data.clinical_notes)}</p>
</div>"""

    # Vitals
    vitals_html = ""
    if data.vitals:
        vitals_items = ""
        for key, label in [
            ("temperature", "Temp (°F)"),
            ("bp_systolic", "BP Systolic"),
            ("bp_diastolic", "BP Diastolic"),
            ("pulse", "Pulse"),
            ("respiratory_rate", "RR"),
            ("spo2", "SpO₂"),
            ("weight", "Weight (kg)"),
            ("height", "Height (cm)"),
            ("bmi", "BMI"),
        ]:
            val = data.vitals.get(key)
            if val is not None:
                vitals_items += f'<div class="vital-item"><label>{label}</label><div class="value">{val}</div></div>'

        if vitals_items:
            vitals_html = f"""
<div class="section">
    <div class="section-title">Vitals</div>
    <div class="vitals-grid">{vitals_items}</div>
</div>"""

    # Prescriptions
    rx_html = ""
    if data.prescriptions:
        rx_headers = ["Medicine", "Dosage", "Frequency", "Duration", "Instructions"]
        rx_rows = []
        for rx in data.prescriptions:
            rx_rows.append([
                _escape_html(rx.get("medicine_name", "")),
                _escape_html(rx.get("dosage", "")),
                _escape_html(rx.get("frequency", "")),
                _escape_html(rx.get("duration", "")),
                _escape_html(rx.get("instructions", "")),
            ])
        rx_table = _build_table(rx_headers, rx_rows)
        rx_html = f"""
<div class="section">
    <div class="section-title">Prescriptions</div>
    {rx_table}
</div>"""

    # Follow-up
    followup_html = ""
    if data.follow_up_date or data.follow_up_notes:
        fu_blocks = []
        if data.follow_up_date:
            fu_blocks.append(("Follow-up Date", _fmt_date(data.follow_up_date)))
        if data.follow_up_notes:
            fu_blocks.append(("Notes", _escape_html(data.follow_up_notes)))
        followup_html = f"""
<div class="section">
    <div class="section-title">Follow-up Plan</div>
    {_build_info_grid(fu_blocks)}
</div>"""

    body = f"""
{header}
<div class="section">
    <div class="section-title">Encounter Summary</div>
    {info_grid}
</div>
<!-- TODO: Phase 3C — AI-generated clinical summary section -->
{soap_html}
{diagnosis_html}
{treatment_html}
{clinical_html}
{vitals_html}
{rx_html}
{followup_html}
"""

    return _build_html_document(
        title=f"Encounter Summary - {data.patient_name}",
        body_html=body,
        meta=DocumentMeta(
            document_type=DocumentType.encounter_summary,
            tenant_id=data.tenant_id,
            resource_id=str(data.appointment_id),
        ),
        branding=branding,
    )


def _aggregate_prescription_data(
    aggregate: EncounterDetailAggregate,
    *,
    tenant_id: UUID | None = None,
) -> PrescriptionDocumentData:
    """Aggregate prescription data from encounter aggregate for PDF generation.

    CRITICAL: Only prescription model data is used — NOT inventory usage.
    """
    appt = aggregate.appointment
    patient = aggregate.patient
    doctor = aggregate.doctor

    # Resolve tenant_id defensively
    resolved_tenant_id = tenant_id or appt.tenant_id
    if not resolved_tenant_id:
        logger.warning("[DOC_TRACE] No tenant_id available for prescription data; using placeholder")
        resolved_tenant_id = UUID("00000000-0000-0000-0000-000000000000")

    logger.info(
        "[DOC_TRACE] _aggregate_prescription_data: appointment_id=%s patient_id=%s tenant_id=%s prescription_count=%d",
        appt.id,
        patient.id,
        resolved_tenant_id,
        len(aggregate.prescriptions),
    )

    # Build prescription items from the aggregate
    rx_items = []
    for rx in aggregate.prescriptions:
        for item in rx.items:
            rx_items.append({
                "medicine_name": item.medicine_name,
                "dosage": item.dosage,
                "frequency": item.frequency,
                "duration": item.duration,
                "instructions": item.instructions,
            })

    return PrescriptionDocumentData(
        appointment_id=appt.id,
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        doctor_specialization=None,
        patient_id=patient.id,
        patient_name=patient.name,
        tenant_id=resolved_tenant_id,
        diagnosis=appt.diagnosis,
        prescriptions=rx_items,
        vitals=aggregate.vitals.model_dump() if aggregate.vitals else None,
        notes=appt.clinical_notes,
        created_at=appt.created_at,
    )


def _aggregate_encounter_summary_data(
    aggregate: EncounterDetailAggregate,
    *,
    tenant_id: UUID | None = None,
) -> EncounterSummaryDocumentData:
    """Aggregate encounter summary data from encounter aggregate for PDF generation."""
    appt = aggregate.appointment
    patient = aggregate.patient
    doctor = aggregate.doctor

    # Resolve tenant_id defensively
    resolved_tenant_id = tenant_id or appt.tenant_id
    if not resolved_tenant_id:
        logger.warning("[DOC_TRACE] No tenant_id available for encounter summary; using placeholder")
        resolved_tenant_id = UUID("00000000-0000-0000-0000-000000000000")

    logger.info(
        "[DOC_TRACE] _aggregate_encounter_summary_data: appointment_id=%s patient_id=%s tenant_id=%s prescription_count=%d",
        appt.id,
        patient.id,
        resolved_tenant_id,
        len(aggregate.prescriptions),
    )

    # Build prescription items
    rx_items = []
    for rx in aggregate.prescriptions:
        for item in rx.items:
            rx_items.append({
                "medicine_name": item.medicine_name,
                "dosage": item.dosage,
                "frequency": item.frequency,
                "duration": item.duration,
                "instructions": item.instructions,
            })

    return EncounterSummaryDocumentData(
        appointment_id=appt.id,
        patient_id=patient.id,
        patient_name=patient.name,
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        doctor_specialization=None,
        tenant_id=resolved_tenant_id,
        appointment_time=appt.appointment_time,
        status=appt.status,
        encounter_started_at=appt.encounter_started_at,
        encounter_completed_at=appt.encounter_completed_at,
        subjective_notes=appt.subjective_notes,
        objective_notes=appt.objective_notes,
        assessment_notes=appt.assessment_notes,
        plan_notes=appt.plan_notes,
        diagnosis=appt.diagnosis,
        treatment_summary=appt.treatment_summary,
        clinical_notes=appt.clinical_notes,
        vitals=aggregate.vitals.model_dump() if aggregate.vitals else None,
        prescriptions=rx_items,
        follow_up_date=appt.follow_up_date,
        follow_up_notes=appt.follow_up_notes,
        created_at=appt.created_at,
    )


# ═════════════════════════════════════════════════════════════════════════════
# PDF GENERATORS
# ═════════════════════════════════════════════════════════════════════════════


def generate_invoice_pdf(
    db: Session,
    bill_id: UUID,
    current_user: User,
    tenant_id: UUID | None = None,
    fmt: DocumentFormat = DocumentFormat.pdf,
) -> bytes:
    """Generate invoice PDF for the given bill."""
    from app.services.reporting_service import get_billing_aggregate

    # Load billing aggregate
    aggregate = get_billing_aggregate(db, bill_id, current_user, tenant_id)

    # Build document data
    data = InvoiceDocumentData(
        bill_id=aggregate.bill_id,
        patient_id=aggregate.patient_id,
        patient_name=aggregate.patient_name,
        doctor_id=aggregate.doctor_id,
        doctor_name=aggregate.doctor_name,
        doctor_specialization=aggregate.doctor_specialization,
        appointment_id=aggregate.appointment_id,
        appointment_time=aggregate.appointment_time,
        tenant_id=aggregate.tenant_id,
        tenant_name=aggregate.tenant_name,
        bill_amount=aggregate.bill_amount,
        consultation_amount=aggregate.consultation_amount,
        inventory_amount=aggregate.inventory_amount,
        inventory_items=aggregate.inventory_items,
        status=aggregate.status,
        paid_at=aggregate.paid_at,
        paid_via=aggregate.paid_via,
        created_at=aggregate.created_at,
    )

    html = _build_invoice_html(data)
    return _render_pdf(html, fmt)


def generate_patient_statement_pdf(
    db: Session,
    patient_id: UUID,
    current_user: User,
    tenant_id: UUID | None = None,
    fmt: DocumentFormat = DocumentFormat.pdf,
) -> bytes:
    """Generate patient financial statement PDF."""
    from app.services.reporting_service import get_patient_financial_ledger

    ledger = get_patient_financial_ledger(db, patient_id, current_user, tenant_id)

    data = PatientStatementDocumentData(
        patient_id=ledger.patient_id,
        patient_name=ledger.patient_name,
        tenant_id=ledger.tenant_id,
        tenant_name=ledger.tenant_name,
        total_billed=ledger.total_billed,
        total_paid=ledger.total_paid,
        total_unpaid=ledger.total_unpaid,
        balance=ledger.balance,
        last_payment_at=ledger.last_payment_at,
        bills=ledger.bills,
        encounters=ledger.encounters,
        statement_date_from=ledger.statement_date_from,
        statement_date_to=ledger.statement_date_to,
    )

    html = _build_patient_statement_html(data)
    return _render_pdf(html, fmt)


def generate_prescription_pdf(
    db: Session,
    appointment_id: UUID,
    current_user: User,
    tenant_id: UUID | None = None,
    fmt: DocumentFormat = DocumentFormat.pdf,
) -> bytes:
    """Generate prescription PDF for the given appointment.

    CRITICAL: Only prescription model data is used — NOT inventory usage.
    """
    from app.services.encounter_service import get_encounter_detail

    # Load encounter aggregate
    aggregate = get_encounter_detail(db, appointment_id, current_user, tenant_id)

    # Aggregate prescription data
    data = _aggregate_prescription_data(aggregate, tenant_id=tenant_id)

    html = _build_prescription_html(data)
    return _render_pdf(html, fmt)


def generate_encounter_summary_pdf(
    db: Session,
    appointment_id: UUID,
    current_user: User,
    tenant_id: UUID | None = None,
    fmt: DocumentFormat = DocumentFormat.pdf,
) -> bytes:
    """Generate encounter summary PDF for the given appointment."""
    from app.services.encounter_service import get_encounter_detail

    # Load encounter aggregate
    aggregate = get_encounter_detail(db, appointment_id, current_user, tenant_id)

    # Aggregate encounter summary data
    data = _aggregate_encounter_summary_data(aggregate, tenant_id=tenant_id)

    html = _build_encounter_summary_html(data)
    return _render_pdf(html, fmt)


# ═════════════════════════════════════════════════════════════════════════════
# PDF RENDERER
# ═════════════════════════════════════════════════════════════════════════════


def _render_pdf(html: str, fmt: DocumentFormat) -> bytes:
    """Render HTML to PDF (or return HTML bytes for preview)."""
    if fmt == DocumentFormat.html:
        return html.encode("utf-8")

    try:
        from weasyprint import HTML as WeasyprintHTML

        pdf_bytes = WeasyprintHTML(string=html).write_pdf()
        return pdf_bytes
    except Exception:
        logger.exception("PDF generation failed")
        raise
