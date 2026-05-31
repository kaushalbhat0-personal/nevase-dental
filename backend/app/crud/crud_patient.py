from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.data_scope import apply_patient_scope
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User


def create_patient(db: Session, patient_data: dict[str, Any]) -> Patient:
    patient = Patient(**patient_data)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def create_patient_tx(db: Session, patient_data: dict[str, Any]) -> Patient:
    """
    Create a patient within an existing transaction (no commit).
    """
    patient = Patient(**patient_data)
    db.add(patient)
    db.flush()
    db.refresh(patient)
    return patient


def get_patient(db: Session, patient_id: UUID) -> Patient | None:
    return db.get(Patient, patient_id)


def get_patient_by_user_id(db: Session, user_id: UUID) -> Patient | None:
    stmt = select(Patient).where(Patient.user_id == user_id)
    return db.scalars(stmt).first()


def patient_has_appointment_with_doctor(
    db: Session, patient_id: UUID, doctor_id: UUID
) -> bool:
    stmt = select(func.count(Appointment.id)).where(
        Appointment.patient_id == patient_id,
        Appointment.doctor_id == doctor_id,
        Appointment.is_deleted == False,
    )
    n = db.scalar(stmt)
    return bool(n and n > 0)


def patient_has_active_appointment_in_tenant(
    db: Session, patient_id: UUID, tenant_id: UUID
) -> bool:
    stmt = select(func.count(Appointment.id)).where(
        Appointment.patient_id == patient_id,
        Appointment.tenant_id == tenant_id,
        Appointment.is_deleted == False,  # noqa: E712
    )
    n = db.scalar(stmt)
    return bool(n and n > 0)


def patient_member_of_tenant(tenant_id: UUID):
    """
    Legacy predicate — prefer :func:`apply_patient_scope` or
    :func:`patient_has_active_appointment_in_tenant`.
    """
    return Patient.tenant_id == tenant_id


def _primary_doctor_name_in_tenant_subquery(tenant_id: UUID):
    """
    For tenant-scoped lists: one deterministic doctor label per patient (min name among
    doctors for non-deleted appointments with ``Appointment.tenant_id`` in this tenant).
    NULL if the patient has no non-deleted appointment with ``Appointment.tenant_id``
    in this tenant.
    """
    return (
        select(func.min(Doctor.name))
        .select_from(Appointment)
        .join(Doctor, Doctor.id == Appointment.doctor_id)
        .where(
            Appointment.patient_id == Patient.id,
            Appointment.tenant_id == tenant_id,
            Appointment.is_deleted == False,  # noqa: E712
        )
        .correlate(Patient)
        .scalar_subquery()
    )


def get_patients(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    linked_doctor_id: UUID | None = None,
    *,
    data_scope_kind: Literal["doctor", "tenant"] = "tenant",
) -> list[tuple[Patient, str | None]]:
    """
    List patients using :func:`apply_patient_scope` (tenant=appointment in tenant;
    doctor=appointment EXISTS). Returns ``(Patient, doctor_name)``; doctor_name
    is set for tenant admin lists when derivable from appointments in that tenant.
    """
    if user_id is not None:
        stmt = select(Patient).order_by(Patient.created_at.desc())
        if search:
            stmt = stmt.where(Patient.name.ilike(f"%{search}%"))
        stmt = stmt.where(Patient.user_id == user_id)
        stmt = stmt.offset(skip).limit(limit)
        return [(p, None) for p in list(db.scalars(stmt).all())]

    if data_scope_kind == "tenant" and tenant_id is not None:
        doc_name_sq = _primary_doctor_name_in_tenant_subquery(tenant_id)
        stmt = select(Patient, doc_name_sq).order_by(Patient.created_at.desc())
        if search:
            stmt = stmt.where(Patient.name.ilike(f"%{search}%"))
        stmt = apply_patient_scope(
            stmt,
            current_user,
            data_scope_kind="tenant",
            tenant_id=tenant_id,
        )
        stmt = stmt.offset(skip).limit(limit)
        rows = list(db.execute(stmt).all())
        return [(row[0], row[1]) for row in rows]

    if data_scope_kind == "doctor":
        stmt = select(Patient).order_by(Patient.created_at.desc())
        if search:
            stmt = stmt.where(Patient.name.ilike(f"%{search}%"))
        stmt = apply_patient_scope(
            stmt,
            current_user,
            data_scope_kind="doctor",
            doctor_id=linked_doctor_id,
            tenant_id=tenant_id,
        )
        stmt = stmt.offset(skip).limit(limit)
        return [(p, None) for p in list(db.scalars(stmt).all())]

    return []


def update_patient(
    db: Session,
    patient: Patient,
    update_data: dict[str, Any],
) -> Patient:
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def delete_patient(db: Session, patient: Patient) -> None:
    db.delete(patient)
    db.commit()
