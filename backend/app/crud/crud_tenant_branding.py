"""
CRUD for TenantBrandingProfile — upsert pattern (1:1 with tenant).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tenant_branding import TenantBrandingProfile


def get_by_tenant_id(
    db: Session,
    tenant_id: UUID,
) -> TenantBrandingProfile | None:
    """Fetch the branding profile for a tenant, or None."""
    return (
        db.query(TenantBrandingProfile)
        .filter(TenantBrandingProfile.tenant_id == tenant_id)
        .first()
    )


def upsert(
    db: Session,
    tenant_id: UUID,
    data: dict,
) -> TenantBrandingProfile:
    """
    Create or update the branding profile for a tenant.

    Args:
        db: Database session.
        tenant_id: The tenant UUID.
        data: Dictionary of fields to set (only non-None values applied).

    Returns:
        The updated or created TenantBrandingProfile.
    """
    profile = get_by_tenant_id(db, tenant_id)
    if profile is None:
        profile = TenantBrandingProfile(tenant_id=tenant_id)
        db.add(profile)

    for key, value in data.items():
        if value is not None and hasattr(profile, key):
            setattr(profile, key, value)

    db.flush()
    db.refresh(profile)
    return profile
