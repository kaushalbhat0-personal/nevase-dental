"""
CRUD for TenantOrganizationProfile — upsert pattern (1:1 with tenant).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tenant_branding import TenantOrganizationProfile


def get_by_tenant_id(
    db: Session,
    tenant_id: UUID,
) -> TenantOrganizationProfile | None:
    """Fetch the organization profile for a tenant, or None."""
    return (
        db.query(TenantOrganizationProfile)
        .filter(TenantOrganizationProfile.tenant_id == tenant_id)
        .first()
    )


def upsert(
    db: Session,
    tenant_id: UUID,
    data: dict,
) -> TenantOrganizationProfile:
    """
    Create or update the organization profile for a tenant.

    Args:
        db: Database session.
        tenant_id: The tenant UUID.
        data: Dictionary of fields to set (only non-None values applied).

    Returns:
        The updated or created TenantOrganizationProfile.
    """
    profile = get_by_tenant_id(db, tenant_id)
    if profile is None:
        profile = TenantOrganizationProfile(tenant_id=tenant_id)
        db.add(profile)

    for key, value in data.items():
        if value is not None and hasattr(profile, key):
            setattr(profile, key, value)

    db.flush()
    db.refresh(profile)
    return profile
