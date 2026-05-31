from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crud import crud_doctor, crud_tenant, crud_user
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.user import OrganizationUserCreate, UserRoleUpdate
from app.services.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError


def provision_organization_user(
    db: Session,
    actor: User,
    payload: OrganizationUserCreate,
) -> User:
    if actor.role != UserRole.super_admin:
        raise ForbiddenError("Only super administrators can provision organization users")

    email_norm = payload.email.lower().strip()
    if crud_user.get_user_by_email(db, email_norm):
        raise ConflictError("Email already registered")

    tenant = db.get(Tenant, payload.tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found")
    if not tenant.is_active:
        raise ValidationError("Tenant is not active")

    if payload.role == UserRole.admin:
        crud_tenant.demote_tenant_admins_to_doctors(db, payload.tenant_id)

    hashed = hash_password(payload.password)
    new_user: dict = {
        "email": email_norm,
        "hashed_password": hashed,
        "role": payload.role,
        "tenant_id": payload.tenant_id,
    }
    if payload.role == UserRole.admin:
        new_user["is_owner"] = True
    user = crud_user.create_user_tx(db, new_user)
    crud_tenant.create_user_tenant_tx(
        db,
        user_id=user.id,
        tenant_id=payload.tenant_id,
        role=payload.role.value,
        is_primary=True,
    )
    return user


def update_user_role_in_tenant(
    db: Session,
    actor: User,
    target_user_id: UUID,
    tenant_id: UUID,
    payload: UserRoleUpdate,
) -> User:
    """
    Super-admin only: set a user to ``admin`` when they are an active doctor in ``tenant_id``.
    Idempotent if the user is already an admin in that organization.
    """
    if actor.role != UserRole.super_admin:
        raise ForbiddenError("Only super administrators can change user roles")
    if payload.role != UserRole.admin:
        raise ValidationError("Only promotion to admin is supported")

    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found")
    if not tenant.is_active:
        raise ValidationError("Tenant is not active")

    target = crud_user.get_user(db, target_user_id)
    if target is None:
        raise NotFoundError("User not found")
    if target.role == UserRole.super_admin:
        raise ForbiddenError("Cannot change super administrator role")
    if target.role == UserRole.patient:
        raise ValidationError("Patients cannot be promoted with this action")

    doctor = crud_doctor.get_active_doctor_for_user_in_tenant(
        db, user_id=target_user_id, tenant_id=tenant_id
    )
    if doctor is None:
        if target.role == UserRole.admin:
            ut = crud_tenant.get_user_tenant_row(
                db, user_id=target_user_id, tenant_id=tenant_id
            )
            if ut is not None and ut.role == "admin":
                return target
        raise NotFoundError(
            "No active doctor profile for this user in the selected organization"
        )

    crud_tenant.demote_tenant_admins_to_doctors(db, tenant_id)

    target.role = UserRole.admin
    target.is_owner = True
    target.tenant_id = tenant_id

    ut = crud_tenant.get_user_tenant_row(
        db, user_id=target_user_id, tenant_id=tenant_id
    )
    if ut is not None:
        ut.role = "admin"
    else:
        crud_tenant.create_user_tenant_tx(
            db,
            user_id=target_user_id,
            tenant_id=tenant_id,
            role=UserRole.admin.value,
            is_primary=True,
        )

    db.add(target)
    db.flush()
    db.refresh(target)
    return target
