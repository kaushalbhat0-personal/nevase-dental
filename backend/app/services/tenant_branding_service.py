"""
Tenant Branding Service — organization profile + branding profile management.

Phase 3C — Tenant Branding + Organization Profile Foundation.

Architecture:
  - Branding is TENANT-SCOPED (1:1 with tenants table)
  - Branding is PRESENTATIONAL metadata — NOT mixed with billing/clinical logic
  - Independent doctors are also tenants and support branding
  - All mutations require admin/owner authorization
  - All reads are tenant-scoped and audit-logged

TODO: Phase 4 — Object storage integration for logo uploads
TODO: Phase 4 — CDN URL generation
TODO: Phase 4 — Signed upload URL support
TODO: Phase 4 — Image optimization pipeline
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.permissions import require_admin_or_owner
from app.crud import crud_tenant_branding, crud_tenant_org_profile
from app.models.user import User
from app.schemas.tenant_branding_profile import (
    TenantBrandingProfileRead,
    TenantBrandingProfileUpdate,
)
from app.schemas.tenant_organization_profile import (
    TenantOrganizationProfileRead,
    TenantOrganizationProfileUpdate,
)
from app.services.security_audit import log_structured_audit_event

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# ORGANIZATION PROFILE
# ═════════════════════════════════════════════════════════════════════════════


def get_organization_profile(
    db: Session,
    tenant_id: UUID,
    *,
    current_user: User | None = None,
) -> TenantOrganizationProfileRead | None:
    """
    Fetch the organization profile for a tenant.

    Args:
        db: Database session.
        tenant_id: The tenant UUID.
        current_user: Optional user for audit logging.

    Returns:
        The organization profile read schema, or None if not set.
    """
    profile = crud_tenant_org_profile.get_by_tenant_id(db, tenant_id)
    if profile is None:
        return None

    # Audit log the read
    if current_user is not None:
        log_structured_audit_event(
            event="organization_profile_read",
            tenant_id=tenant_id,
            resource_id=str(profile.id),
            actor_id=str(current_user.id),
            status="success",
        )

    return TenantOrganizationProfileRead.model_validate(profile)


def update_organization_profile(
    db: Session,
    current_user: User,
    tenant_id: UUID,
    data: TenantOrganizationProfileUpdate,
) -> TenantOrganizationProfileRead:
    """
    Update (or create) the organization profile for a tenant.

    Authorization: Requires admin/owner privileges for the tenant.

    Args:
        db: Database session.
        current_user: The authenticated user.
        tenant_id: The tenant UUID.
        data: The update payload (all fields optional).

    Returns:
        The updated organization profile read schema.

    Raises:
        ForbiddenError: If the user is not authorized.
    """
    require_admin_or_owner(db, current_user, tenant_id)

    # Build update dict from non-None fields
    update_data: dict[str, Any] = {}
    changed_fields: list[str] = []
    for field_name in data.model_dump(exclude_none=True):
        value = getattr(data, field_name)
        if value is not None:
            update_data[field_name] = value
            changed_fields.append(field_name)

    profile = crud_tenant_org_profile.upsert(db, tenant_id, update_data)

    # Audit log
    log_structured_audit_event(
        event="organization_profile_updated",
        tenant_id=tenant_id,
        resource_id=str(profile.id),
        actor_id=str(current_user.id),
        changed_fields=",".join(changed_fields) if changed_fields else "none",
        status="success",
    )

    return TenantOrganizationProfileRead.model_validate(profile)


# ═════════════════════════════════════════════════════════════════════════════
# BRANDING PROFILE
# ═════════════════════════════════════════════════════════════════════════════


def get_branding_profile(
    db: Session,
    tenant_id: UUID,
    *,
    current_user: User | None = None,
) -> TenantBrandingProfileRead | None:
    """
    Fetch the branding profile for a tenant.

    Args:
        db: Database session.
        tenant_id: The tenant UUID.
        current_user: Optional user for audit logging.

    Returns:
        The branding profile read schema, or None if not set.
    """
    profile = crud_tenant_branding.get_by_tenant_id(db, tenant_id)
    if profile is None:
        return None

    # Audit log the read
    if current_user is not None:
        log_structured_audit_event(
            event="branding_profile_read",
            tenant_id=tenant_id,
            resource_id=str(profile.id),
            actor_id=str(current_user.id),
            status="success",
        )

    return TenantBrandingProfileRead.model_validate(profile)


def update_branding_profile(
    db: Session,
    current_user: User,
    tenant_id: UUID,
    data: TenantBrandingProfileUpdate,
) -> TenantBrandingProfileRead:
    """
    Update (or create) the branding profile for a tenant.

    Authorization: Requires admin/owner privileges for the tenant.

    Args:
        db: Database session.
        current_user: The authenticated user.
        tenant_id: The tenant UUID.
        data: The update payload (all fields optional).

    Returns:
        The updated branding profile read schema.

    Raises:
        ForbiddenError: If the user is not authorized.
    """
    require_admin_or_owner(db, current_user, tenant_id)

    # Build update dict from non-None fields
    update_data: dict[str, Any] = {}
    changed_fields: list[str] = []
    for field_name in data.model_dump(exclude_none=True):
        value = getattr(data, field_name)
        if value is not None:
            update_data[field_name] = value
            changed_fields.append(field_name)

    profile = crud_tenant_branding.upsert(db, tenant_id, update_data)

    # Audit log
    log_structured_audit_event(
        event="branding_updated",
        tenant_id=tenant_id,
        resource_id=str(profile.id),
        actor_id=str(current_user.id),
        changed_fields=",".join(changed_fields) if changed_fields else "none",
        status="success",
    )

    return TenantBrandingProfileRead.model_validate(profile)


# ═════════════════════════════════════════════════════════════════════════════
# BRANDING CONTEXT (for document rendering)
# ═════════════════════════════════════════════════════════════════════════════


def get_tenant_branding_context(
    db: Session,
    tenant_id: UUID,
) -> dict[str, Any]:
    """
    Fetch combined branding context for document rendering.

    Returns a flat dict with all organization + branding profile fields.
    Missing profiles return empty dicts (no crash).

    Args:
        db: Database session.
        tenant_id: The tenant UUID.

    Returns:
        A dict with 'organization' and 'branding' sub-dicts.
    """
    org_profile = crud_tenant_org_profile.get_by_tenant_id(db, tenant_id)
    brand_profile = crud_tenant_branding.get_by_tenant_id(db, tenant_id)

    org_data: dict[str, Any] = {}
    if org_profile is not None:
        org_data = {
            "organization_name": org_profile.organization_name,
            "legal_name": org_profile.legal_name,
            "logo_url": org_profile.logo_url,
            "phone": org_profile.phone,
            "email": org_profile.email,
            "website": org_profile.website,
            "address_line_1": org_profile.address_line_1,
            "address_line_2": org_profile.address_line_2,
            "city": org_profile.city,
            "state": org_profile.state,
            "postal_code": org_profile.postal_code,
            "country": org_profile.country,
            "gst_number": org_profile.gst_number,
            "registration_number": org_profile.registration_number,
            "timezone": org_profile.timezone,
            "currency": org_profile.currency,
            "prescription_footer": org_profile.prescription_footer,
            "invoice_footer": org_profile.invoice_footer,
        }

    brand_data: dict[str, Any] = {}
    if brand_profile is not None:
        brand_data = {
            "primary_color": brand_profile.primary_color,
            "secondary_color": brand_profile.secondary_color,
            "accent_color": brand_profile.accent_color,
            "document_header_style": brand_profile.document_header_style,
            "watermark_text": brand_profile.watermark_text,
            "prescription_template": brand_profile.prescription_template,
            "invoice_template": brand_profile.invoice_template,
        }

    return {
        "organization": org_data,
        "branding": brand_data,
    }
