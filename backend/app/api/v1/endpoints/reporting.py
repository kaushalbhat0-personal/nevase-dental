"""
Reporting API endpoints — READ-ONLY derived aggregates for financial reporting.

Billing remains the source-of-truth for patient charges.
Inventory movements remain the source-of-truth for stock history.
Exports are derived artifacts — they NEVER mutate financial records.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    get_current_user,
    get_optional_scoped_tenant_id,
    get_resolved_data_scope,
    require_structured_profile_complete,
)
from app.core.data_scope import ResolvedDataScope
from app.core.database import get_db
from app.models.billing import BillingStatus
from app.models.inventory import InventoryMovementType
from app.models.user import User
from app.schemas.reporting import (
    BillingReportFilter,
    BillingReportResult,
    ExportFormat,
    ExportRequest,
    InventoryLedgerFilter,
    InventoryLedgerResult,
    PatientFinancialLedger,
)
from app.services.reporting_service import (
    get_billing_report,
    get_inventory_ledger,
    get_patient_financial_ledger,
)
from app.services.security_audit import log_structured_audit_event
from app.utils.export_service import (
    export_report,
    serialize_billing_report_for_export,
    serialize_inventory_ledger_for_export,
    serialize_patient_ledger_for_export,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(require_structured_profile_complete)],
)


# ── Billing Report ───────────────────────────────────────────────────────────


@router.get("/billing", response_model=BillingReportResult)
def billing_report(
    date_from: str | None = Query(default=None, description="ISO datetime filter start"),
    date_to: str | None = Query(default=None, description="ISO datetime filter end"),
    status: BillingStatus | None = Query(default=None),
    doctor_id: UUID | None = Query(default=None),
    patient_id: UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> BillingReportResult:
    """Get paginated billing report with filters."""
    import datetime

    def _parse_iso_dt(s: str) -> datetime.datetime:
        """Parse ISO datetime string, handling space-separated UTC offset."""
        try:
            return datetime.datetime.fromisoformat(s)
        except ValueError:
            # Handle '2026-05-06T01:49:35.970562 00:00' -> replace space with +
            if " " in s and ("+" not in s and "Z" not in s.upper()):
                # Try replacing last space with + for UTC offset
                parts = s.rsplit(" ", 1)
                if len(parts) == 2 and parts[1] in ("00:00", "+00:00", "-00:00"):
                    return datetime.datetime.fromisoformat(parts[0] + "+00:00")
            raise

    filters = BillingReportFilter(
        date_from=_parse_iso_dt(date_from) if date_from else None,
        date_to=_parse_iso_dt(date_to) if date_to else None,

        status=status,
        doctor_id=doctor_id,
        patient_id=patient_id,
        skip=skip,
        limit=limit,
    )
    return get_billing_report(
        db, current_user, tenant_id, filters, data_scope=data_scope
    )


# ── Inventory Ledger ─────────────────────────────────────────────────────────


@router.get("/inventory-ledger", response_model=InventoryLedgerResult)
def inventory_ledger(
    date_from: str | None = Query(default=None, description="ISO datetime filter start"),
    date_to: str | None = Query(default=None, description="ISO datetime filter end"),
    item_id: UUID | None = Query(default=None),
    movement_type: InventoryMovementType | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> InventoryLedgerResult:
    """Get paginated inventory movement ledger with running stock."""
    import datetime

    filters = InventoryLedgerFilter(
        date_from=datetime.datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.datetime.fromisoformat(date_to) if date_to else None,
        item_id=item_id,
        movement_type=movement_type,
        skip=skip,
        limit=limit,
    )
    return get_inventory_ledger(
        db, current_user, tenant_id, filters, data_scope=data_scope
    )


# ── Patient Financial Ledger ─────────────────────────────────────────────────


@router.get("/patient-financial/{patient_id}", response_model=PatientFinancialLedger)
def patient_financial_ledger(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> PatientFinancialLedger:
    """Get full financial ledger for a patient — all bills, payments, balances, encounters."""
    return get_patient_financial_ledger(
        db, current_user, patient_id, tenant_id, data_scope=data_scope
    )


# ── Exports ──────────────────────────────────────────────────────────────────


_CONTENT_TYPE_MAP = {
    ExportFormat.csv: "text/csv",
    ExportFormat.xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.pdf: "application/pdf",
}

_FILENAME_EXT_MAP = {
    ExportFormat.csv: ".csv",
    ExportFormat.xlsx: ".xlsx",
    ExportFormat.pdf: ".pdf",
}


@router.post("/billing/export")
def export_billing_report(
    body: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> Response:
    """Export billing report in requested format (CSV, XLSX, PDF)."""
    filters = BillingReportFilter(
        date_from=body.date_from,
        date_to=body.date_to,
        status=body.status,
        doctor_id=body.doctor_id,
        patient_id=body.patient_id,
        skip=0,
        limit=10000,  # Export up to 10k rows
    )
    result = get_billing_report(
        db, current_user, tenant_id, filters, data_scope=data_scope
    )

    headers, rows = serialize_billing_report_for_export(result.items)
    file_bytes = export_report(body.format, headers, rows, title="Billing Report")

    # Log audit event
    log_structured_audit_event(
        event="export_generated",
        tenant_id=tenant_id,
        resource_id=None,
        actor_id=str(current_user.id),
        export_type=body.format.value,
        report_type="billing",
        filters=body.model_dump(mode="json", exclude={"format"}),
    )

    content_type = _CONTENT_TYPE_MAP.get(body.format, "application/octet-stream")
    filename = f"billing_report{_FILENAME_EXT_MAP.get(body.format, '.csv')}"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/inventory-ledger/export")
def export_inventory_ledger(
    body: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> Response:
    """Export inventory ledger in requested format (CSV, XLSX, PDF)."""
    filters = InventoryLedgerFilter(
        date_from=body.date_from,
        date_to=body.date_to,
        item_id=body.item_id,
        movement_type=body.movement_type,
        skip=0,
        limit=10000,
    )
    result = get_inventory_ledger(
        db, current_user, tenant_id, filters, data_scope=data_scope
    )

    headers, rows = serialize_inventory_ledger_for_export(result.items)
    file_bytes = export_report(body.format, headers, rows, title="Inventory Ledger")

    # Log audit event
    log_structured_audit_event(
        event="export_generated",
        tenant_id=tenant_id,
        resource_id=None,
        actor_id=str(current_user.id),
        export_type=body.format.value,
        report_type="inventory_ledger",
        filters=body.model_dump(mode="json", exclude={"format"}),
    )

    content_type = _CONTENT_TYPE_MAP.get(body.format, "application/octet-stream")
    filename = f"inventory_ledger{_FILENAME_EXT_MAP.get(body.format, '.csv')}"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/patient-financial/{patient_id}/export")
def export_patient_financial(
    patient_id: UUID,
    body: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> Response:
    """Export patient financial ledger in requested format (CSV, XLSX, PDF)."""
    ledger = get_patient_financial_ledger(
        db, current_user, patient_id, tenant_id, data_scope=data_scope
    )

    # Build CSV rows from bills
    headers = [
        "Bill ID",
        "Amount",
        "Status",
        "Paid At",
        "Created At",
    ]
    rows = [
        [
            str(b.bill_id),
            str(b.amount),
            b.status.value if hasattr(b.status, "value") else str(b.status),
            b.paid_at.isoformat() if b.paid_at else "",
            b.created_at.isoformat() if b.created_at else "",
        ]
        for b in ledger.bills
    ]

    summary = {
        "Patient Name": ledger.patient_name,
        "Total Billed": str(ledger.total_billed),
        "Total Paid": str(ledger.total_paid),
        "Balance": str(ledger.balance),
    }

    file_bytes = export_report(
        body.format, headers, rows, title=f"Patient Ledger - {ledger.patient_name}", summary=summary
    )

    # Log audit event
    log_structured_audit_event(
        event="export_generated",
        tenant_id=tenant_id,
        resource_id=str(patient_id),
        actor_id=str(current_user.id),
        export_type=body.format.value,
        report_type="patient_financial",
        patient_id=str(patient_id),
    )

    content_type = _CONTENT_TYPE_MAP.get(body.format, "application/octet-stream")
    filename = f"patient_ledger_{patient_id}{_FILENAME_EXT_MAP.get(body.format, '.csv')}"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
