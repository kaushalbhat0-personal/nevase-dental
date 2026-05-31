from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.doctor import Doctor, DoctorCreationIdempotency
from app.models.doctor_profile import DoctorProfile
from app.models.tenant import Tenant


def _doctor_profile_verification_clause(verification_status_normalized: str):
    """
    Filter by marketplace status. For ``pending``, require core identity fields so admins
    never review rows that could not have been submitted legitimately via the doctor API.
    """
    v = verification_status_normalized.strip().lower()
    base = DoctorProfile.verification_status == v
    if v != "pending":
        return base
    return and_(
        base,
        DoctorProfile.full_name.isnot(None),
        DoctorProfile.specialization.isnot(None),
        DoctorProfile.registration_number.isnot(None),
        DoctorProfile.phone.isnot(None),
    )


def get_doctor_idempotency_record(
    db: Session, user_id: UUID, idempotency_key: str
) -> DoctorCreationIdempotency | None:
    stmt = select(DoctorCreationIdempotency).where(
        DoctorCreationIdempotency.user_id == user_id,
        DoctorCreationIdempotency.idempotency_key == idempotency_key,
    )
    return db.scalars(stmt).first()


def record_doctor_idempotency(
    db: Session,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_hash: str,
    doctor_id: UUID,
) -> DoctorCreationIdempotency:
    row = DoctorCreationIdempotency(
        user_id=user_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        doctor_id=doctor_id,
    )
    db.add(row)
    db.flush()
    return row


def create_doctor(db: Session, doctor_data: dict[str, Any]) -> Doctor:
    doctor = Doctor(**doctor_data)
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def create_doctor_tx(db: Session, doctor_data: dict[str, Any]) -> Doctor:
    """
    Create a doctor within an existing transaction (no commit).
    """
    doctor = Doctor(**doctor_data)
    db.add(doctor)
    db.flush()
    db.refresh(doctor)
    return doctor


def get_doctor(db: Session, doctor_id: UUID) -> Doctor | None:
    stmt = select(Doctor).where(
        Doctor.id == doctor_id,
        Doctor.is_deleted == False,
    )
    return db.scalars(stmt).first()


def get_active_doctor_for_user_in_tenant(
    db: Session,
    *,
    user_id: UUID,
    tenant_id: UUID,
) -> Doctor | None:
    stmt = select(Doctor).where(
        Doctor.user_id == user_id,
        Doctor.tenant_id == tenant_id,
        Doctor.is_deleted == False,
        Doctor.is_active == True,
    )
    return db.scalars(stmt).first()


def get_doctor_by_user_id(db: Session, user_id: UUID) -> Doctor | None:
    stmt = (
        select(Doctor)
        .options(joinedload(Doctor.tenant))
        .where(
            Doctor.user_id == user_id,
            Doctor.is_deleted == False,
        )
    )
    return db.scalars(stmt).unique().first()


def get_doctors(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    specialization: str | None = None,
    *,
    only_marketplace_verified: bool = False,
) -> list[Doctor]:
    stmt = (
        select(Doctor)
        .order_by(Doctor.created_at.desc())
        .options(
            joinedload(Doctor.tenant),
            joinedload(Doctor.user),
            joinedload(Doctor.structured_profile),
        )
        .where(
            Doctor.is_active == True,
            Doctor.is_deleted == False,
        )
    )
    if search:
        stmt = stmt.where(Doctor.name.ilike(f"%{search}%"))
    if specialization:
        stmt = stmt.where(Doctor.specialization.ilike(f"%{specialization}%"))
    if user_id is not None:
        stmt = stmt.where(Doctor.user_id == user_id)
    if tenant_id is not None:
        stmt = stmt.where(Doctor.tenant_id == tenant_id)
    # Public listing safety: only show doctors attached to active tenants
    stmt = stmt.join(Doctor.tenant).where(Tenant.is_active == True)
    if only_marketplace_verified:
        stmt = stmt.join(DoctorProfile, DoctorProfile.doctor_id == Doctor.id).where(
            DoctorProfile.verification_status == "approved"
        )
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).unique().all())


def list_doctors_with_verification_status(
    db: Session,
    *,
    tenant_id: UUID | None,
    verification_status: str | None,
    skip: int = 0,
    limit: int = 100,
) -> list[Doctor]:
    """
    Doctors with a ``doctor_profiles`` row, optionally filtered by marketplace verification status.

    ``tenant_id`` None = all tenants (super-admin global view); else scope to one organization.

    When filtering by ``pending``, rows must have ``full_name``, ``specialization``,
    ``registration_number``, and ``phone`` set (non-NULL) so the admin queue stays clean.
    """
    stmt = (
        select(Doctor)
        .order_by(Doctor.created_at.desc())
        .options(
            joinedload(Doctor.tenant),
            joinedload(Doctor.user),
            joinedload(Doctor.structured_profile),
        )
        .join(DoctorProfile, DoctorProfile.doctor_id == Doctor.id)
        .join(Doctor.tenant)
        .where(
            Doctor.is_active == True,  # noqa: E712
            Doctor.is_deleted == False,  # noqa: E712
            Tenant.is_active == True,  # noqa: E712
        )
    )
    if tenant_id is not None:
        stmt = stmt.where(Doctor.tenant_id == tenant_id)
    if verification_status is not None and verification_status.strip() != "":
        stmt = stmt.where(_doctor_profile_verification_clause(verification_status))
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).unique().all())


def count_doctors_with_verification_status(
    db: Session,
    *,
    tenant_id: UUID | None,
    verification_status: str | None,
) -> int:
    """Row count for the same filters as :func:`list_doctors_with_verification_status`."""
    stmt = (
        select(func.count())
        .select_from(Doctor)
        .join(DoctorProfile, DoctorProfile.doctor_id == Doctor.id)
        .join(Doctor.tenant)
        .where(
            Doctor.is_active == True,  # noqa: E712
            Doctor.is_deleted == False,  # noqa: E712
            Tenant.is_active == True,  # noqa: E712
        )
    )
    if tenant_id is not None:
        stmt = stmt.where(Doctor.tenant_id == tenant_id)
    if verification_status is not None and verification_status.strip() != "":
        stmt = stmt.where(_doctor_profile_verification_clause(verification_status))
    return int(db.scalar(stmt) or 0)


def update_doctor(
    db: Session,
    doctor: Doctor,
    update_data: dict[str, Any],
) -> Doctor:
    for field, value in update_data.items():
        setattr(doctor, field, value)

    if "timezone" in update_data:
        from app.core.slot_cache_invalidation import schedule_invalidate_doctor_slot_cache_on_commit

        schedule_invalidate_doctor_slot_cache_on_commit(db, doctor.id)

    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def count_active_doctors_by_tenant_ids(
    db: Session,
    tenant_ids: list[UUID],
) -> dict[UUID, int]:
    """Active, non-deleted doctor counts per tenant (for derived org labels)."""
    if not tenant_ids:
        return {}
    stmt = (
        select(Doctor.tenant_id, func.count(Doctor.id))
        .where(
            Doctor.tenant_id.in_(tenant_ids),
            Doctor.is_active == True,  # noqa: E712
            Doctor.is_deleted == False,  # noqa: E712
        )
        .group_by(Doctor.tenant_id)
    )
    return {row[0]: int(row[1]) for row in db.execute(stmt).all()}


def delete_doctor(db: Session, doctor: Doctor) -> None:
    db.delete(doctor)
    db.commit()
