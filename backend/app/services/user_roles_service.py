"""Derive effective application roles: account `User.role` plus `doctor` when a doctor row is linked."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import crud_doctor_profile
from app.models.doctor import Doctor
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.user import UserMeTenantBrief, UserRead, UserResponse


def _linked_doctor_id(db: Session, user: User) -> uuid.UUID | None:
    return db.execute(
        select(Doctor.id).where(
            Doctor.user_id == user.id,
            Doctor.is_deleted.is_(False),
        ).limit(1)
    ).scalar_one_or_none()


def compute_roles_for_user(db: Session, user: User) -> list[str]:
    """Return distinct roles, preserving account role order then appending `doctor` if a profile is linked."""
    roles, _did = roles_and_doctor_id_for_user(db, user)
    return roles


def roles_and_doctor_id_for_user(db: Session, user: User) -> tuple[list[str], uuid.UUID | None]:
    """Single-query friendly: roles for JWT/UI plus linked doctor row id (if any)."""
    did = _linked_doctor_id(db, user)
    seen: set[str] = set()
    out: list[str] = []
    if user.role is not None:
        v = user.role.value
        if v not in seen:
            seen.add(v)
            out.append(v)
    if did is not None:
        dv = UserRole.doctor.value
        if dv not in seen:
            out.append(dv)
    return out, did


def _doctor_profile_flags(
    db: Session, doctor_id: UUID | None
) -> tuple[bool | None, str | None, str | None]:
    if doctor_id is None:
        return None, None, None
    prof = crud_doctor_profile.get_by_doctor_id(db, doctor_id)
    if prof is None:
        return False, None, None
    reason = getattr(prof, "verification_rejection_reason", None)
    if reason is None or (isinstance(reason, str) and not reason.strip()):
        r = None
    else:
        r = str(reason).strip()
    return bool(prof.is_profile_complete), str(prof.verification_status), r


def user_read_with_roles(db: Session, user: User) -> UserRead:
    base = UserRead.model_validate(user)
    roles, doctor_id = roles_and_doctor_id_for_user(db, user)
    dcomp, vstat, vreason = _doctor_profile_flags(db, doctor_id)
    tenant_brief: UserMeTenantBrief | None = None
    if user.tenant_id is not None:
        row = db.get(Tenant, user.tenant_id)
        if row is not None:
            tenant_brief = UserMeTenantBrief(id=row.id, type=str(row.type))
    return base.model_copy(
        update={
            "roles": roles,
            "doctor_id": doctor_id,
            "doctor_profile_complete": dcomp,
            "doctor_verification_status": vstat,
            "doctor_verification_rejection_reason": vreason,
            "tenant": tenant_brief,
        }
    )


def user_response_with_roles(db: Session, user: User) -> UserResponse:
    base = UserResponse.model_validate(user)
    roles, doctor_id = roles_and_doctor_id_for_user(db, user)
    dcomp, vstat, vreason = _doctor_profile_flags(db, doctor_id)
    return base.model_copy(
        update={
            "roles": roles,
            "doctor_id": doctor_id,
            "doctor_profile_complete": dcomp,
            "doctor_verification_status": vstat,
            "doctor_verification_rejection_reason": vreason,
        }
    )
