"""Tenant admin vs practice owner (solo doctor) privilege checks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.crud import crud_tenant
from app.models.user import User, UserRole
from app.services.exceptions import ForbiddenError


def has_tenant_admin_privileges(user: User) -> bool:
    """
    True if the user may use org-wide admin APIs (metrics dashboard, full billing, etc.).

    Includes super_admin, admin, staff, and practice owner (``is_owner`` doctor).
    """
    if user.role in (UserRole.admin, UserRole.staff, UserRole.super_admin):
        return True
    return user.role == UserRole.doctor and bool(
        getattr(user, "is_owner", False)
    )


def is_admin_or_owner(db: Session, user: User, tenant_id: UUID) -> bool:
    """
    True when the user is a member of ``tenant_id`` and has admin or owner-level power there.

    super_admin: always true (callers may still require ``X-Tenant-ID`` as today).
    """
    if user.role == UserRole.super_admin:
        return True
    ut = crud_tenant.get_user_tenant_row(
        db, user_id=user.id, tenant_id=tenant_id
    )
    if ut is None:
        return False
    if user.role in (UserRole.admin, UserRole.staff):
        return True
    if user.is_owner and user.role == UserRole.doctor:
        return True
    return False


def require_admin_or_owner(db: Session, user: User, tenant_id: UUID) -> None:
    if not is_admin_or_owner(db, user, tenant_id):
        raise ForbiddenError("Admin access required")
