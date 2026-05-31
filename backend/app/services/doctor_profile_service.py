from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.crud import crud_doctor_profile
from app.core.permissions import is_admin_or_owner
from app.models.doctor import Doctor
from app.models.doctor_profile import DoctorProfile
from app.models.tenant import TenantType
from app.models.user import User, UserRole
from app.schemas.doctor_profile import DoctorProfileUpdate, DoctorProfileWrite
from app.services.exceptions import ForbiddenError, StaleStateError, ValidationError

logger = logging.getLogger(__name__)

# Values stored in `doctor_profiles.verification_status` (String column).
VERIFICATION_DRAFT = "draft"
VERIFICATION_PENDING = "pending"
VERIFICATION_APPROVED = "approved"
VERIFICATION_REJECTED = "rejected"


def is_doctor_active(profile: DoctorProfile | None) -> bool:
    """True when marketplace verification allows full practice APIs (single source of truth)."""
    return profile is not None and profile.verification_status == VERIFICATION_APPROVED


def _append_verification_log(
    db: Session,
    *,
    doctor_id: UUID,
    from_status: str | None,
    to_status: str,
    reason: str | None,
    reviewed_by_user_id: UUID | None,
    tenant_id: UUID | None,
) -> None:
    logger.info(
        "Verification transition doctor=%s from=%s to=%s reason=%s reviewer=%s",
        doctor_id, from_status, to_status, reason, reviewed_by_user_id,
    )


def _assert_admin_review_transition(
    cur: str,
    new: str,
    *,
    is_super_admin: bool,
) -> None:
    if cur == new:
        return
    allowed = {
        VERIFICATION_DRAFT: {VERIFICATION_PENDING},
        VERIFICATION_PENDING: {VERIFICATION_APPROVED, VERIFICATION_REJECTED},
        VERIFICATION_REJECTED: {VERIFICATION_PENDING},
        VERIFICATION_APPROVED: set(),
    }
    if new in allowed.get(cur, set()):
        return
    if is_super_admin and cur == VERIFICATION_APPROVED and new in (
        VERIFICATION_PENDING,
        VERIFICATION_REJECTED,
        VERIFICATION_DRAFT,
    ):
        return
    raise ForbiddenError(f"Invalid transition {cur} -> {new}")


def _blank_to_none(s: str | None) -> str | None:
    if s is None:
        return None
    t = s.strip()
    return t if t else None


def is_profile_complete_fields(profile: DoctorProfile) -> bool:
    return all(
        [
            _blank_to_none(profile.full_name),
            _blank_to_none(profile.specialization),
            _blank_to_none(profile.registration_number),
            _blank_to_none(profile.phone),
            _blank_to_none(profile.qualification),
        ]
    )


def recompute_is_complete(profile: DoctorProfile) -> None:
    profile.is_profile_complete = is_profile_complete_fields(profile)


def _mirror_to_doctor_roster(db: Session, doctor: Doctor, profile: DoctorProfile) -> None:
    """Keep legacy `doctors` display fields aligned with the structured profile for list/detail APIs."""
    fn = _blank_to_none(profile.full_name)
    if fn:
        doctor.name = fn[:255]
    sp = _blank_to_none(profile.specialization)
    if sp:
        doctor.specialization = sp[:255]
    if profile.experience_years is not None:
        doctor.experience_years = profile.experience_years
    db.add(doctor)


def _apply_write_model(row: DoctorProfile, payload: DoctorProfileWrite) -> None:
    row.full_name = payload.full_name.strip()
    row.phone = _blank_to_none(payload.phone)
    row.profile_image = _blank_to_none(payload.profile_image)
    row.specialization = _blank_to_none(payload.specialization)
    row.experience_years = payload.experience_years
    row.qualification = _blank_to_none(payload.qualification)
    row.registration_number = _blank_to_none(payload.registration_number)
    row.registration_council = _blank_to_none(payload.registration_council)
    row.clinic_name = _blank_to_none(payload.clinic_name)
    row.address = _blank_to_none(payload.address)
    row.city = _blank_to_none(payload.city)
    row.state = _blank_to_none(payload.state)


def ensure_profile_for_doctor(db: Session, doctor: Doctor) -> DoctorProfile:
    """Ensure a `doctor_profiles` row exists; seed from the roster row when new."""
    existing = crud_doctor_profile.get_by_doctor_id(db, doctor.id)
    if existing is not None:
        return existing
    row = crud_doctor_profile.create_profile_tx(
        db,
        data={
            "doctor_id": doctor.id,
            "full_name": doctor.name,
            "specialization": doctor.specialization,
            "experience_years": doctor.experience_years,
            "verification_status": VERIFICATION_APPROVED,
        },
    )
    recompute_is_complete(row)
    db.add(row)
    db.flush()
    return row


def get_profile_read_model(db: Session, doctor_id: UUID) -> DoctorProfile | None:
    return crud_doctor_profile.get_by_doctor_id(db, doctor_id)


def upsert_profile_from_write(
    db: Session,
    doctor: Doctor,
    payload: DoctorProfileWrite,
) -> DoctorProfile:
    """Create or replace structured profile fields (POST/PUT body)."""
    row = crud_doctor_profile.get_by_doctor_id(db, doctor.id)
    if row is None:
        row = crud_doctor_profile.create_profile_tx(
            db,
            data={
                "doctor_id": doctor.id,
                "full_name": payload.full_name.strip(),
                "verification_status": VERIFICATION_APPROVED,
            },
        )
    _apply_write_model(row, payload)
    row.updated_at = datetime.now(timezone.utc)
    recompute_is_complete(row)
    _mirror_to_doctor_roster(db, doctor, row)
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def patch_profile(
    db: Session,
    doctor: Doctor,
    payload: DoctorProfileUpdate,
) -> DoctorProfile:
    row = ensure_profile_for_doctor(db, doctor)
    data = payload.model_dump(exclude_unset=True)
    for key, val in data.items():
        if val is None:
            continue
        if key == "full_name":
            row.full_name = str(val).strip()
        elif key == "experience_years":
            row.experience_years = val
        else:
            if isinstance(val, str):
                setattr(row, key, _blank_to_none(val))
            else:
                setattr(row, key, val)
    row.updated_at = datetime.now(timezone.utc)
    recompute_is_complete(row)
    _mirror_to_doctor_roster(db, doctor, row)
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def doctor_profile_complete_for_user(db: Session, *, user_id: UUID) -> bool | None:
    """None if this login is not linked to a doctor row; else completion flag."""
    from app.crud import crud_doctor

    doctor = crud_doctor.get_doctor_by_user_id(db, user_id)
    if doctor is None:
        return None
    prof = crud_doctor_profile.get_by_doctor_id(db, doctor.id)
    if prof is None:
        return False
    return bool(prof.is_profile_complete)


def submit_profile_for_verification(db: Session, doctor: Doctor) -> DoctorProfile:
    """Auto-approve profile (single clinic — no verification flow)."""
    row = ensure_profile_for_doctor(db, doctor)
    recompute_is_complete(row)
    row.verification_status = VERIFICATION_APPROVED
    row.verification_rejection_reason = None
    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def set_verification_status_admin(
    db: Session,
    *,
    doctor_id: UUID,
    status: str,
    reason: str | None = None,
    reviewed_by_user_id: UUID | None = None,
    is_super_admin: bool = False,
) -> DoctorProfile:
    """Approve, reject, or re-open marketplace verification (atomic when moving from a known prior state)."""
    from app.services.doctor_service import get_doctor_or_404_with_tenant

    doctor = get_doctor_or_404_with_tenant(db, doctor_id)
    prof = ensure_profile_for_doctor(db, doctor)

    st = status.strip().lower()
    if st not in (
        VERIFICATION_APPROVED,
        VERIFICATION_REJECTED,
        VERIFICATION_PENDING,
        VERIFICATION_DRAFT,
    ):
        raise ValidationError("Invalid verification status")

    cur = prof.verification_status
    if cur == st:
        return prof

    _assert_admin_review_transition(cur, st, is_super_admin=is_super_admin)

    if st == VERIFICATION_REJECTED:
        if not (reason or "").strip():
            raise ValidationError("Rejection reason required")
        final_rej = (reason or "").strip() or "No reason provided"
    else:
        final_rej = None

    now = datetime.now(timezone.utc)
    tenant_for_log = doctor.tenant_id

    upd = (
        update(DoctorProfile)
        .where(
            DoctorProfile.doctor_id == doctor.id,
            DoctorProfile.verification_status == cur,
        )
        .values(
            verification_status=st,
            verification_rejection_reason=final_rej if st == VERIFICATION_REJECTED else None,
            updated_at=now,
        )
    )
    res = db.execute(upd)
    db.flush()

    if (res.rowcount or 0) == 0:
        db.refresh(prof)
        if prof.verification_status == st:
            return prof
        raise StaleStateError(
            "Verification was updated by another reviewer; refresh and try again."
        )

    db.refresh(prof)
    log_reason = final_rej if st == VERIFICATION_REJECTED else None
    _append_verification_log(
        db,
        doctor_id=doctor.id,
        from_status=cur,
        to_status=st,
        reason=log_reason,
        reviewed_by_user_id=reviewed_by_user_id,
        tenant_id=tenant_for_log,
    )
    db.flush()
    db.refresh(prof)
    return prof


def can_verify_doctor_profile(
    db: Session,
    current_user: User,
    doctor: Doctor,
) -> bool:
    """
    True when this principal may set marketplace verification on ``doctor`` (single source of truth).

    - ``individual`` tenant: only ``super_admin``.
    - ``organization`` tenant: ``super_admin``, or an org admin/owner/staff member for that
      same tenant (no cross-tenant verification).
    """
    try:
        req: UUID | None = doctor.tenant_id if current_user.role != UserRole.super_admin else None
        assert_user_can_verify_doctor(db, current_user, doctor, request_tenant_id=req)
    except ForbiddenError:
        return False
    return True


def assert_user_can_verify_doctor(
    db: Session,
    current_user: User,
    doctor: Doctor,
    *,
    request_tenant_id: UUID | None = None,
) -> None:
    """Raise :class:`ForbiddenError` with a client-safe message when review is not allowed."""
    t = doctor.tenant
    if t is None or doctor.tenant_id is None:
        raise ForbiddenError("Doctor has no tenant; cannot verify")
    ttype = (t.type or "").strip().lower()
    if ttype == TenantType.individual.value:
        if current_user.role != UserRole.super_admin:
            raise ForbiddenError("Only super admin can verify individual doctors")
        return
    if ttype == TenantType.organization.value:
        if current_user.role == UserRole.super_admin:
            return
        if request_tenant_id is None or request_tenant_id != doctor.tenant_id:
            raise ForbiddenError("Not allowed to verify this doctor")
        if not is_admin_or_owner(db, current_user, doctor.tenant_id):
            raise ForbiddenError("Not allowed to verify this doctor")
        return
    raise ForbiddenError("Not allowed to verify this doctor")
