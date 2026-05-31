"""
Document Generation API endpoints — canonical document rendering layer.

Documents are DERIVED ARTIFACTS:
  canonical backend aggregate → document renderer → generated artifact

All endpoints:
  - Use existing authorization patterns (capability-based)
  - Consume existing aggregates (read-only)
  - Generate documents on-demand (no premature persistence)
  - Log audit events for compliance
  - Return StreamingResponse with application/pdf

TODO: Phase 3C — Cached generation with ETag/If-None-Match
TODO: Phase 3C — Signed URLs for document downloads
TODO: Phase 3C — Email delivery pipeline
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_optional_scoped_tenant_id,
    require_structured_profile_complete,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.document import DocumentFormat
from app.services.document_service import (
    generate_encounter_summary_pdf,
    generate_invoice_pdf,
    generate_patient_statement_pdf,
    generate_prescription_pdf,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(require_structured_profile_complete)],
)


_CONTENT_TYPE_MAP = {
    DocumentFormat.pdf: "application/pdf",
    DocumentFormat.html: "text/html",
}

_FILENAME_EXT_MAP = {
    DocumentFormat.pdf: ".pdf",
    DocumentFormat.html: ".html",
}


def _build_pdf_response(
    pdf_bytes: bytes,
    filename: str,
    fmt: DocumentFormat = DocumentFormat.pdf,
) -> Response:
    """Build a streaming response for PDF download."""
    content_type = _CONTENT_TYPE_MAP.get(fmt, "application/octet-stream")
    ext = _FILENAME_EXT_MAP.get(fmt, ".bin")
    return Response(
        content=pdf_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}{ext}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# ── Invoice PDF ─────────────────────────────────────────────────────────────


@router.get("/invoice/{bill_id}")
def download_invoice(
    bill_id: UUID,
    fmt: DocumentFormat = Query(
        default=DocumentFormat.pdf,
        description="Output format: pdf or html (for preview)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> Response:
    """
    Download invoice PDF for the given bill.

    Authorization:
    - Assigned doctor (via appointment)
    - Clinic admin/owner (tenant scope)
    - Authorized patient (own bills)
    - Super admin

    Pipeline:
    Billing aggregate → document renderer → PDF bytes
    """
    pdf_bytes = generate_invoice_pdf(
        db, bill_id, current_user, tenant_id, fmt=fmt
    )
    return _build_pdf_response(
        pdf_bytes,
        filename=f"invoice_{bill_id}",
        fmt=fmt,
    )


# ── Patient Statement PDF ───────────────────────────────────────────────────


@router.get("/statement/{patient_id}")
def download_patient_statement(
    patient_id: UUID,
    fmt: DocumentFormat = Query(
        default=DocumentFormat.pdf,
        description="Output format: pdf or html (for preview)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> Response:
    """
    Download patient financial statement PDF.

    Authorization:
    - Assigned doctor (has patient relationship)
    - Clinic admin/owner (tenant scope)
    - Authorized patient (own statement)
    - Super admin

    Pipeline:
    PatientFinancialLedger → document renderer → PDF bytes
    """
    pdf_bytes = generate_patient_statement_pdf(
        db, patient_id, current_user, tenant_id, fmt=fmt
    )
    return _build_pdf_response(
        pdf_bytes,
        filename=f"statement_{patient_id}",
        fmt=fmt,
    )


# ── Prescription PDF ────────────────────────────────────────────────────────


@router.get("/prescription/{appointment_id}")
def download_prescription(
    appointment_id: UUID,
    fmt: DocumentFormat = Query(
        default=DocumentFormat.pdf,
        description="Output format: pdf or html (for preview)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> Response:
    """
    Download prescription PDF for the given appointment.

    CRITICAL: Only prescription model data is used — NOT inventory usage.

    Authorization:
    - Assigned doctor
    - Clinic admin/owner (tenant scope)
    - Authorized patient (own prescriptions)
    - Super admin

    Pipeline:
    EncounterDetailAggregate → document renderer → PDF bytes
    """
    pdf_bytes = generate_prescription_pdf(
        db, appointment_id, current_user, tenant_id, fmt=fmt
    )
    return _build_pdf_response(
        pdf_bytes,
        filename=f"prescription_{appointment_id}",
        fmt=fmt,
    )


# ── Encounter Summary PDF ───────────────────────────────────────────────────


@router.get("/encounter-summary/{appointment_id}")
def download_encounter_summary(
    appointment_id: UUID,
    fmt: DocumentFormat = Query(
        default=DocumentFormat.pdf,
        description="Output format: pdf or html (for preview)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> Response:
    """
    Download encounter summary PDF for the given appointment.

    This becomes the future AI-summary delivery surface.

    Authorization:
    - Assigned doctor
    - Clinic admin/owner (tenant scope)
    - Authorized patient (own encounters)
    - Super admin

    Pipeline:
    EncounterDetailAggregate → document renderer → PDF bytes
    """
    pdf_bytes = generate_encounter_summary_pdf(
        db, appointment_id, current_user, tenant_id, fmt=fmt
    )
    return _build_pdf_response(
        pdf_bytes,
        filename=f"encounter_summary_{appointment_id}",
        fmt=fmt,
    )
