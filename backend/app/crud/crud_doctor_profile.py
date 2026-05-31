from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.doctor_profile import DoctorProfile


def get_by_doctor_id(db: Session, doctor_id: UUID) -> DoctorProfile | None:
    return db.scalars(
        select(DoctorProfile).where(DoctorProfile.doctor_id == doctor_id).limit(1)
    ).first()


def create_profile_tx(db: Session, *, data: dict) -> DoctorProfile:
    row = DoctorProfile(**data)
    db.add(row)
    db.flush()
    db.refresh(row)
    return row
