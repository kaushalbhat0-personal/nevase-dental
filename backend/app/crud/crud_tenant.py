from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.tenant import Tenant, TenantCreationIdempotency, TenantType, UserTenant
from app.models.user import User, UserRole


def get_by_name(db: Session, name: str) -> Tenant | None:
    n = name.strip().lower()
    stmt = select(Tenant).where(func.lower(Tenant.name) == n).limit(1)
    return db.scalars(stmt).first()


def get_by_slug(db: Session, slug: str) -> Tenant | None:
    s = slug.strip().lower()
    stmt = select(Tenant).where(Tenant.slug == s).limit(1)
    return db.scalars(stmt).first()


def get_tenant_idempotency_record(
    db: Session, user_id: UUID, idempotency_key: str
) -> TenantCreationIdempotency | None:
    stmt = select(TenantCreationIdempotency).where(
        TenantCreationIdempotency.user_id == user_id,
        TenantCreationIdempotency.idempotency_key == idempotency_key,
    )
    return db.scalars(stmt).first()


def record_tenant_idempotency(
    db: Session,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_hash: str,
    tenant_id: UUID,
) -> TenantCreationIdempotency:
    row = TenantCreationIdempotency(
        user_id=user_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def delete_expired_tenant_idempotency_records(
    db: Session, *, older_than_days: int = 7
) -> int:
    """Remove stale idempotency rows (run from cron/worker). Returns rows deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    stmt = delete(TenantCreationIdempotency).where(
        TenantCreationIdempotency.created_at < cutoff
    )
    result = db.execute(stmt)
    return int(result.rowcount or 0)


def get_primary_admin_email_for_tenant(db: Session, tenant_id: UUID) -> str | None:
    stmt = (
        select(User.email)
        .join(UserTenant, UserTenant.user_id == User.id)
        .where(
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_primary == True,  # noqa: E712
        )
        .limit(1)
    )
    email = db.scalars(stmt).first()
    if email is not None:
        return str(email)
    stmt = (
        select(User.email)
        .join(UserTenant, UserTenant.user_id == User.id)
        .where(
            UserTenant.tenant_id == tenant_id,
            UserTenant.role == "admin",
        )
        .limit(1)
    )
    alt = db.scalars(stmt).first()
    return str(alt) if alt is not None else None


def create_tenant_tx(
    db: Session,
    *,
    name: str,
    type: TenantType | str = TenantType.organization,
    is_active: bool = True,
    address: str | None = None,
    phone: str | None = None,
    slug: str | None = None,
) -> Tenant:
    type_str: str = type.value if isinstance(type, TenantType) else str(type)
    tenant = Tenant(
        name=name,
        type=type_str,
        is_active=is_active,
        address=address,
        phone=phone,
        slug=slug,
    )
    db.add(tenant)
    db.flush()
    db.refresh(tenant)
    return tenant


def list_tenants(
    db: Session,
    *,
    type: str | None = None,
    type_in: tuple[str, ...] | None = None,
    is_active: bool | None = True,
    exclude_deleted: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[Tenant]:
    stmt = select(Tenant).order_by(Tenant.created_at.desc())
    if type_in is not None:
        stmt = stmt.where(Tenant.type.in_(type_in))
    elif type is not None:
        stmt = stmt.where(Tenant.type == type)
    if is_active is not None:
        stmt = stmt.where(Tenant.is_active == is_active)
    if exclude_deleted:
        stmt = stmt.where(Tenant.is_deleted == False)  # noqa: E712
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_user_tenant_row(
    db: Session,
    *,
    user_id: UUID,
    tenant_id: UUID,
) -> UserTenant | None:
    stmt = (
        select(UserTenant)
        .where(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .limit(1)
    )
    return db.scalars(stmt).first()


def create_user_tenant_tx(
    db: Session,
    *,
    user_id: UUID,
    tenant_id: UUID,
    role: str = "admin",
    is_primary: bool = True,
) -> UserTenant:
    ut = UserTenant(user_id=user_id, tenant_id=tenant_id, role=role, is_primary=is_primary)
    db.add(ut)
    db.flush()
    if is_primary:
        user = db.get(User, user_id)
        if user is not None and user.role != UserRole.super_admin:
            user.tenant_id = tenant_id
    db.refresh(ut)
    return ut


def demote_tenant_admins_to_doctors(db: Session, tenant_id: UUID) -> None:
    """
    Every user with ``users.tenant_id == tenant_id`` and role *admin* becomes *doctor*;
    the ``user_tenant`` row for that org is set to *doctor*; ``is_owner`` is cleared.
    """
    stmt = select(User).where(
        User.tenant_id == tenant_id,
        User.role == UserRole.admin,
    )
    for u in db.scalars(stmt).all():
        u.role = UserRole.doctor
        u.is_owner = False
        ut = get_user_tenant_row(db, user_id=u.id, tenant_id=tenant_id)
        if ut is not None:
            ut.role = "doctor"
        db.add(u)
    db.flush()

