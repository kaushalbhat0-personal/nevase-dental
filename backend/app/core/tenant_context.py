from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.metrics import inc_counter
from app.core.tenancy import non_nil_tenant_id
from app.models.tenant import Tenant, UserTenant
from app.models.user import User, UserRole
from app.services.exceptions import ForbiddenError, ValidationError

logger = logging.getLogger(__name__)

MISSING_X_TENANT_ID_MSG = "X-Tenant-ID header is required for scoped operations"


def is_member_of_tenant(db: Session, user_id: UUID, tenant_id: UUID) -> bool:
    stmt = (
        select(UserTenant.id)
        .where(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .limit(1)
    )
    return db.scalar(stmt) is not None


def get_primary_tenant_id_from_db(db: Session, user_id: UUID) -> UUID | None:
    """
    Canonical org for the user, from ``user_tenant`` (not from a possibly stale ``users.tenant_id`` alone):
    primary membership first, otherwise the oldest row.
    """

    stmt = (
        select(UserTenant.tenant_id)
        .where(UserTenant.user_id == user_id)
        .order_by(UserTenant.is_primary.desc(), UserTenant.created_at.asc())
        .limit(1)
    )
    return db.scalar(stmt)


def _ensure_tenant_scope_is_valid(db: Session, tenant_id: UUID) -> None:
    scope_row = db.get(Tenant, tenant_id)
    if scope_row is None:
        raise ValidationError("Tenant not found")
    if scope_row.is_deleted:
        raise ValidationError("Organization is deactivated")
    if not scope_row.is_active:
        raise ValidationError("Tenant is not active")


def resolve_request_tenant(
    db: Session,
    current_user: User,
    header_tenant_id: UUID | None,
) -> UUID | None:
    """
    Effective tenant for admin-style requests: always grounded in ``user_tenant`` membership.

    - ``super_admin``: optional ``X-Tenant-ID`` filters to one org (validated when present).
    - Everyone else: no header → primary membership from DB; with header → must be a member.
    """
    if current_user.role == UserRole.super_admin:
        if header_tenant_id is not None:
            _ensure_tenant_scope_is_valid(db, header_tenant_id)
        return header_tenant_id
    if current_user.role == UserRole.patient:
        return None

    if header_tenant_id is None:
        primary = get_primary_tenant_id_from_db(db, current_user.id)
        if primary is None:
            raise ValidationError("Tenant context is not configured for this user")
        _ensure_tenant_scope_is_valid(db, primary)
        return primary

    if not is_member_of_tenant(db, current_user.id, header_tenant_id):
        raise ForbiddenError("Invalid tenant context")
    _ensure_tenant_scope_is_valid(db, header_tenant_id)
    return header_tenant_id


def get_current_tenant_id(user: User, db: Session) -> UUID | None:
    """
    Canonical home tenant for the user (JWT and X-Tenant-ID validation).

    - super_admin: None (no fixed org)
    - patient: None here; patient APIs scope by user/patient row, not this helper
    - others: ``users.tenant_id`` when set, else legacy primary ``user_tenant`` row
    """

    if user.role == UserRole.super_admin:
        return None
    if user.role == UserRole.patient:
        return None
    if user.tenant_id is not None:
        return user.tenant_id

    stmt_primary = (
        select(UserTenant.tenant_id)
        .where(
            UserTenant.user_id == user.id,
            UserTenant.is_primary == True,  # noqa: E712
        )
        .limit(1)
    )
    tenant_id = db.scalar(stmt_primary)
    if tenant_id is not None:
        return tenant_id

    if user.role == UserRole.doctor:
        stmt_doctor = (
            select(UserTenant.tenant_id)
            .where(
                UserTenant.user_id == user.id,
                UserTenant.role == "doctor",
            )
            .order_by(UserTenant.created_at.asc())
            .limit(1)
        )
        tenant_id = db.scalar(stmt_doctor)
        if tenant_id is not None:
            return tenant_id

    stmt_any = (
        select(UserTenant.tenant_id)
        .where(UserTenant.user_id == user.id)
        .order_by(UserTenant.created_at.asc())
        .limit(1)
    )
    return db.scalar(stmt_any)


def resolve_tenant_id_for_scoped_request(
    db: Session,
    user: User,
    x_tenant_id: UUID | None,
) -> UUID | None:
    """
    Effective tenant for the request: ``X-Tenant-ID`` when provided, otherwise the user's home tenant.

    - patient: None (doctor/slot reads use separate RBAC).
    - super_admin: ``X-Tenant-ID`` required; must exist and be active (cross-tenant override).
    - admin / doctor / staff: home tenant required; optional header must match home (no spoofing).
    """
    if user.role == UserRole.patient:
        return None

    if user.role == UserRole.super_admin:
        if x_tenant_id is None:
            raise ValidationError(MISSING_X_TENANT_ID_MSG)
        row = db.get(Tenant, x_tenant_id)
        if row is None:
            raise ValidationError("Tenant not found")
        if row.is_deleted:
            raise ValidationError("Organization is deactivated")
        if not row.is_active:
            raise ValidationError("Tenant is not active")
        return x_tenant_id

    home = get_current_tenant_id(user, db)
    if home is None:
        raise ValidationError("Tenant context is not configured for this user")

    chosen = x_tenant_id if x_tenant_id is not None else home
    if chosen != home:
        raise ForbiddenError("X-Tenant-ID does not match your organization")
    scope_row = db.get(Tenant, chosen)
    if scope_row is None:
        raise ValidationError("Tenant not found")
    if scope_row.is_deleted:
        raise ValidationError("Organization is deactivated")
    return chosen


def align_operation_tenant_with_resource(
    current_user: User,
    request_tenant_id: UUID | None,
    resource_tenant_id: UUID | None,
) -> UUID | None:
    """
    For mutations on an existing tenant-scoped row, enforce that the scoped request org matches
    the resource org instead of trusting the header alone (especially ``super_admin``).

    Non-super admins keep ``request_tenant_id`` unchanged; they are already constrained by
    ``resolve_tenant_id_for_scoped_request``.
    """
    if current_user.role != UserRole.super_admin:
        return request_tenant_id
    rt = non_nil_tenant_id(resource_tenant_id)
    if rt is None:
        return request_tenant_id
    rq = non_nil_tenant_id(request_tenant_id)
    if rq is not None and rq != rt:
        inc_counter("cross_tenant_blocked_total")
        logger.warning(
            "[AUDIT] cross_tenant_blocked user=%s role=%s resource_org=%s request_org=%s",
            current_user.id,
            current_user.role,
            rt,
            rq,
        )
        raise ForbiddenError("Tenant scope does not match this resource organization")
    return rt
