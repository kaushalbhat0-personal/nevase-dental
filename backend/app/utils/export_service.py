"""
Export framework — reusable builders for CSV, XLSX-ready, and PDF-ready structures.

Exports are **derived artifacts** — they NEVER mutate financial records.
Export logic is decoupled from API routes for testability and reuse.

TODO: Phase 3C — Tally XML export
TODO: Phase 3C — Zoho Books API export
TODO: Phase 3C — QuickBooks Online export (QBO format)
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.schemas.reporting import (
    BillingReportAggregate,
    ExportFormat,
    InventoryLedgerRow,
    PatientFinancialLedger,
)

logger = logging.getLogger(__name__)


# ── CSV Export Builder ───────────────────────────────────────────────────────


class CsvExportBuilder:
    """
    Build CSV export from headers and rows.

    Usage:
        builder = CsvExportBuilder(["Name", "Amount"])
        builder.add_row(["John", "100.00"])
        csv_string = builder.build()
    """

    def __init__(self, headers: list[str]) -> None:
        self._headers = headers
        self._rows: list[list[str]] = []

    def add_row(self, row: list[str]) -> None:
        """Add a single row of string values."""
        self._rows.append(row)

    def add_rows(self, rows: list[list[str]]) -> None:
        """Add multiple rows."""
        self._rows.extend(rows)

    def build(self) -> str:
        """Return the CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self._headers)
        for row in self._rows:
            writer.writerow(row)
        return output.getvalue()

    def build_bytes(self) -> bytes:
        """Return CSV as bytes (for HTTP response)."""
        return self.build().encode("utf-8-sig")


# ── XLSX-ready Builder (structure only) ──────────────────────────────────────


class XlsxExportBuilder:
    """
    XLSX-ready structure builder.

    Actual XLSX generation requires openpyxl (optional dependency).
    This builder provides the structured data that can be passed to openpyxl.

    TODO: Phase 3B — Implement actual XLSX generation with openpyxl
    """

    def __init__(self, sheet_name: str = "Report") -> None:
        self._sheet_name = sheet_name
        self._headers: list[str] = []
        self._rows: list[list[str | int | float]] = []

    def set_headers(self, headers: list[str]) -> None:
        self._headers = headers

    def add_row(self, row: list[str | int | float]) -> None:
        self._rows.append(row)

    def add_rows(self, rows: list[list[str | int | float]]) -> None:
        self._rows.extend(rows)

    def get_structured_data(self) -> dict[str, Any]:
        """Return structured data ready for XLSX generation."""
        return {
            "sheet_name": self._sheet_name,
            "headers": self._headers,
            "rows": self._rows,
        }

    def build(self) -> bytes:
        """
        Build XLSX bytes.

        NOTE: Requires openpyxl. Returns empty bytes if not available.
        TODO: Phase 3B — Implement with openpyxl when dependency is added.
        """
        try:
            import openpyxl  # type: ignore[import-untyped]  # noqa: F811
            from openpyxl import Workbook  # type: ignore[import-untyped]

            wb = Workbook()
            ws = wb.active
            if ws is not None:
                ws.title = self._sheet_name
                if self._headers:
                    ws.append(self._headers)
                for row in self._rows:
                    ws.append([str(c) if isinstance(c, Decimal) else c for c in row])

            output = io.BytesIO()
            wb.save(output)
            return output.getvalue()
        except ImportError:
            logger.warning(
                "[EXPORT] openpyxl not installed. Install with: pip install openpyxl"
            )
            return b""

    def build_bytes(self) -> bytes:
        """Alias for build()."""
        return self.build()


# ── PDF-ready Builder (structure only) ───────────────────────────────────────


class PdfExportBuilder:
    """
    PDF-ready structure builder.

    Actual PDF rendering requires weasyprint or reportlab (optional dependency).
    This builder generates HTML that can be converted to PDF.

    TODO: Phase 3B — Implement actual PDF generation with weasyprint/reportlab
    """

    def __init__(self, title: str = "Report") -> None:
        self._title = title
        self._headers: list[str] = []
        self._rows: list[list[str]] = []
        self._summary: dict[str, str] = {}

    def set_summary(self, summary: dict[str, str]) -> None:
        """Set key-value summary pairs for the report header."""
        self._summary = summary

    def set_table(self, headers: list[str], rows: list[list[str]]) -> None:
        """Set the table data."""
        self._headers = headers
        self._rows = rows

    def build_html(self) -> str:
        """Return HTML string suitable for PDF conversion."""
        parts: list[str] = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="UTF-8">',
            f"<title>{self._title}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; font-size: 18px; }",
            "table { width: 100%; border-collapse: collapse; margin-top: 10px; }",
            "th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; font-size: 11px; }",
            "th { background-color: #f5f5f5; font-weight: bold; }",
            ".summary { margin-bottom: 15px; }",
            ".summary dt { font-weight: bold; margin-top: 4px; }",
            ".summary dd { margin-left: 10px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{self._title}</h1>",
        ]

        if self._summary:
            parts.append('<dl class="summary">')
            for key, value in self._summary.items():
                parts.append(f"<dt>{key}</dt><dd>{value}</dd>")
            parts.append("</dl>")

        if self._headers:
            parts.append("<table><thead><tr>")
            for h in self._headers:
                parts.append(f"<th>{h}</th>")
            parts.append("</tr></thead><tbody>")
            for row in self._rows:
                parts.append("<tr>")
                for cell in row:
                    parts.append(f"<td>{cell}</td>")
                parts.append("</tr>")
            parts.append("</tbody></table>")

        parts.append("</body></html>")
        return "\n".join(parts)

    def build(self) -> bytes:
        """
        Build PDF bytes.

        NOTE: Requires weasyprint. Returns empty bytes if not available.
        TODO: Phase 3B — Implement with weasyprint when dependency is added.
        """
        html = self.build_html()
        try:
            import weasyprint  # type: ignore[import-untyped]  # noqa: F401

            return weasyprint.HTML(string=html).write_pdf()  # type: ignore[no-any-return]
        except ImportError:
            logger.warning(
                "[EXPORT] weasyprint not installed. Install with: pip install weasyprint"
            )
            return b""


# ── Serializers ──────────────────────────────────────────────────────────────


def _fmt_dt(dt: datetime | None) -> str:
    """Format datetime for export."""
    if dt is None:
        return ""
    return dt.isoformat()


def _fmt_decimal(d: Decimal | None) -> str:
    """Format decimal for export."""
    if d is None:
        return "0.00"
    return f"{d:.2f}"


def serialize_billing_report_for_export(
    rows: list[BillingReportAggregate],
) -> tuple[list[str], list[list[str]]]:
    """
    Serialize billing report rows for CSV/XLSX/PDF export.

    Returns (headers, rows) where each row is a list of string values.
    """
    headers = [
        "Bill ID",
        "Patient Name",
        "Doctor Name",
        "Appointment Time",
        "Bill Amount",
        "Consultation Amount",
        "Inventory Amount",
        "Status",
        "Paid At",
        "Payment Method",
        "Created At",
    ]

    data_rows: list[list[str]] = []
    for row in rows:
        data_rows.append(
            [
                str(row.bill_id),
                row.patient_name,
                row.doctor_name or "",
                _fmt_dt(row.appointment_time),
                _fmt_decimal(row.bill_amount),
                _fmt_decimal(row.consultation_amount),
                _fmt_decimal(row.inventory_amount),
                row.status.value if hasattr(row.status, "value") else str(row.status),
                _fmt_dt(row.paid_at),
                row.paid_via or "",
                _fmt_dt(row.created_at),
            ]
        )

    return headers, data_rows


def serialize_inventory_ledger_for_export(
    rows: list[InventoryLedgerRow],
) -> tuple[list[str], list[list[str]]]:
    """
    Serialize inventory ledger rows for CSV/XLSX/PDF export.

    Returns (headers, rows) where each row is a list of string values.
    """
    headers = [
        "Movement ID",
        "Item Name",
        "Item Type",
        "Movement Type",
        "Quantity",
        "Running Stock",
        "Doctor ID",
        "Billing ID",
        "Encounter ID",
        "Actor ID",
        "Actor Role",
        "Created At",
    ]

    data_rows: list[list[str]] = []
    for row in rows:
        data_rows.append(
            [
                str(row.movement_id),
                row.item_name,
                row.item_type.value if hasattr(row.item_type, "value") else str(row.item_type),
                row.movement_type.value if hasattr(row.movement_type, "value") else str(row.movement_type),
                str(row.quantity),
                str(row.running_stock),
                str(row.doctor_id) if row.doctor_id else "",
                str(row.billing_id) if row.billing_id else "",
                str(row.encounter_id) if row.encounter_id else "",
                str(row.actor_id) if row.actor_id else "",
                row.actor_role or "",
                _fmt_dt(row.created_at),
            ]
        )

    return headers, data_rows


def serialize_patient_ledger_for_export(
    ledger: PatientFinancialLedger,
) -> dict[str, Any]:
    """
    Serialize patient financial ledger for export.

    Returns a dict with summary and bills sections.
    """
    return {
        "summary": {
            "patient_name": ledger.patient_name,
            "total_billed": _fmt_decimal(ledger.total_billed),
            "total_paid": _fmt_decimal(ledger.total_paid),
            "total_unpaid": _fmt_decimal(ledger.total_unpaid),
            "balance": _fmt_decimal(ledger.balance),
            "last_payment_at": _fmt_dt(ledger.last_payment_at),
        },
        "bills": [
            {
                "bill_id": str(b.bill_id),
                "amount": _fmt_decimal(b.amount),
                "status": b.status.value if hasattr(b.status, "value") else str(b.status),
                "paid_at": _fmt_dt(b.paid_at),
                "created_at": _fmt_dt(b.created_at),
            }
            for b in ledger.bills
        ],
        "encounters": [
            {
                "appointment_id": str(e.appointment_id),
                "appointment_time": _fmt_dt(e.appointment_time),
                "doctor_name": e.doctor_name,
                "has_bill": str(e.has_bill),
            }
            for e in ledger.encounters
        ],
    }


# ── Export Dispatcher ────────────────────────────────────────────────────────


def export_report(
    format: ExportFormat,
    headers: list[str],
    rows: list[list[str]],
    title: str = "Report",
    summary: dict[str, str] | None = None,
) -> bytes:
    """
    Export data in the requested format.

    Args:
        format: ExportFormat enum (csv, xlsx, pdf)
        headers: Column headers
        rows: Data rows (list of string lists)
        title: Report title (used for PDF)
        summary: Key-value summary (used for PDF)

    Returns:
        Bytes of the exported file.

    Raises:
        ValueError: If format is not supported.
    """
    if format == ExportFormat.csv:
        builder = CsvExportBuilder(headers)
        builder.add_rows(rows)
        return builder.build_bytes()

    if format == ExportFormat.xlsx:
        builder = XlsxExportBuilder(sheet_name=title[:31])  # Excel sheet name limit
        builder.set_headers(headers)
        builder.add_rows(rows)  # type: ignore[arg-type]
        return builder.build_bytes()

    if format == ExportFormat.pdf:
        builder = PdfExportBuilder(title=title)
        if summary:
            builder.set_summary(summary)
        builder.set_table(headers, rows)
        return builder.build()

    raise ValueError(f"Unsupported export format: {format}")
