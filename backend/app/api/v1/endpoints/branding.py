"""
Branding API endpoints — tenant organization profile + branding profile management.

Phase 3C — Tenant Branding + Organization Profile Foundation.

Authorization:
  - GET (read): Any authenticated user in the tenant scope
  - PUT (update): Only clinic admin, owner, independent doctor owner, super_admin
  - All reads are tenant-scoped and audit-logged

TODO: Phase 4 — Logo upload endpoint (multipart/form-data → object storage)
TODO: Phase 4 — Bulk branding import/export for hospital chains
TODO: Phase 4 — Department-level branding overrides
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_optional_scoped_tenant_id,
    require_structured_profile_complete,
)
from app.core.database import get_db
from app.core.request_context import get_request_id
from app.models.user import User
from app.schemas.tenant_branding_profile import (
    TenantBrandingProfileRead,
    TenantBrandingProfileUpdate,
)
from app.schemas.tenant_organization_profile import (
    TenantOrganizationProfileRead,
    TenantOrganizationProfileUpdate,
)
from app.services.document_service import (
    generate_encounter_summary_pdf,
    generate_invoice_pdf,
    generate_prescription_pdf,
)
from app.services.security_audit import log_structured_audit_event
from app.services.tenant_branding_service import (
    get_branding_profile,
    get_organization_profile,
    update_branding_profile,
    update_organization_profile,
)
from app.schemas.document import DocumentFormat

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/branding",
    tags=["branding"],
    dependencies=[Depends(require_structured_profile_complete)],
)


# ── Organization Profile ─────────────────────────────────────────────────────


@router.get(
    "/organization-profile",
    response_model=TenantOrganizationProfileRead | None,
)
def read_organization_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> TenantOrganizationProfileRead | None:
    """
    Read the organization profile for the current tenant scope.

    Returns None if no profile has been set up yet.
    All reads are tenant-scoped and audit-logged.
    """
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    profile = get_organization_profile(db, tenant_id, current_user=current_user)
    return profile


@router.put(
    "/organization-profile",
    response_model=TenantOrganizationProfileRead,
)
def update_organization_profile_endpoint(
    data: TenantOrganizationProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> TenantOrganizationProfileRead:
    """
    Update (or create) the organization profile for the current tenant.

    Authorization: Requires admin/owner privileges.
    All fields are optional (patch-style update).
    """
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    return update_organization_profile(db, current_user, tenant_id, data)


# ── Branding Profile ─────────────────────────────────────────────────────────


@router.get(
    "/profile",
    response_model=TenantBrandingProfileRead | None,
)
def read_branding_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> TenantBrandingProfileRead | None:
    """
    Read the branding profile for the current tenant scope.

    Returns None if no profile has been set up yet.
    All reads are tenant-scoped and audit-logged.
    """
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    profile = get_branding_profile(db, tenant_id, current_user=current_user)
    return profile


@router.put(
    "/profile",
    response_model=TenantBrandingProfileRead,
)
def update_branding_profile_endpoint(
    data: TenantBrandingProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> TenantBrandingProfileRead:
    """
    Update (or create) the branding profile for the current tenant.

    Authorization: Requires admin/owner privileges.
    All fields are optional (patch-style update).
    """
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    return update_branding_profile(db, current_user, tenant_id, data)


# ── Document Preview ─────────────────────────────────────────────────────────


@router.get(
    "/preview/{document_type}",
    response_class=HTMLResponse,
)
def preview_document(
    document_type: str = Path(
        ..., description="Document type: invoice, prescription, or encounter_summary"
    ),
    sample_bill_id: UUID | None = None,
    sample_appointment_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> str:
    """
    Generate an HTML preview of a document with current branding applied.

    Document types:
      - invoice (requires sample_bill_id)
      - prescription (requires sample_appointment_id)
      - encounter_summary (requires sample_appointment_id)

    Authorization: Requires admin/owner privileges.
    """
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # Verify admin/owner for preview
    from app.core.permissions import require_admin_or_owner
    require_admin_or_owner(db, current_user, tenant_id)

    try:
        if document_type == "invoice":
            if sample_bill_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="sample_bill_id is required for invoice preview",
                )
            html_bytes = generate_invoice_pdf(
                db, sample_bill_id, current_user, tenant_id, fmt=DocumentFormat.html
            )
        elif document_type == "prescription":
            if sample_appointment_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="sample_appointment_id is required for prescription preview",
                )
            html_bytes = generate_prescription_pdf(
                db, sample_appointment_id, current_user, tenant_id, fmt=DocumentFormat.html
            )
        elif document_type == "encounter_summary":
            if sample_appointment_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="sample_appointment_id is required for encounter_summary preview",
                )
            html_bytes = generate_encounter_summary_pdf(
                db, sample_appointment_id, current_user, tenant_id, fmt=DocumentFormat.html
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown document type: {document_type}. Supported: invoice, prescription, encounter_summary",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Document preview failed")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate preview: {exc}",
        ) from exc

    # Audit log
    log_structured_audit_event(
        event="document_preview_generated",
        tenant_id=tenant_id,
        resource_id=f"preview:{document_type}",
        actor_id=str(current_user.id),
        document_type=document_type,
        request_id=get_request_id(),
        status="success",
    )

    return html_bytes.decode("utf-8")
