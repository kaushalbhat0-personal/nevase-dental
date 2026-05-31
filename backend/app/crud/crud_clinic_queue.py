"""
CRUD operations for ClinicQueueEntry.

All operations are tenant-scoped for isolation.
Token numbers are sequential per doctor per calendar day.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.models.clinic_queue import ClinicQueueEntry, ClinicQueueStatus


def add_queue_entry(
    db: Session,
    *,
    appointment_id: UUID,
    tenant_id: UUID,
    doctor_id: UUID,
    patient_id: UUID,
    token_number: int,
    created_by: UUID,
    priority: int = 0,
) -> ClinicQueueEntry:
    """Create a new queue entry with the given token number."""
    entry = ClinicQueueEntry(
        appointment_id=appointment_id,
        tenant_id=tenant_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        token_number=token_number,
        priority=priority,
        created_by=created_by,
    )
    db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry


def get_queue_entry_by_id(db: Session, entry_id: UUID) -> ClinicQueueEntry | None:
    """Get a single queue entry by ID."""
    stmt = select(ClinicQueueEntry).where(ClinicQueueEntry.id == entry_id)
    return db.scalars(stmt).first()


def get_queue_entry_by_appointment(
    db: Session, appointment_id: UUID
) -> ClinicQueueEntry | None:
    """Get the queue entry for a given appointment."""
    stmt = select(ClinicQueueEntry).where(
        ClinicQueueEntry.appointment_id == appointment_id
    )
    return db.scalars(stmt).first()


def get_next_token_number(db: Session, doctor_id: UUID) -> int:
    """Get the next sequential token number for a doctor today."""
    today = date.today()
    stmt = select(func.coalesce(func.max(ClinicQueueEntry.token_number), 0)).where(
        ClinicQueueEntry.doctor_id == doctor_id,
        func.date(ClinicQueueEntry.entered_at) == today,
    )
    max_token = db.scalar(stmt) or 0
    return max_token + 1


def get_todays_queue_for_doctor(
    db: Session, doctor_id: UUID, tenant_id: UUID
) -> list[ClinicQueueEntry]:
    """Get today's queue entries for a specific doctor, ordered by token number."""
    today = date.today()
    stmt = (
        select(ClinicQueueEntry)
        .where(
            ClinicQueueEntry.doctor_id == doctor_id,
            ClinicQueueEntry.tenant_id == tenant_id,
            func.date(ClinicQueueEntry.entered_at) == today,
        )
        .order_by(ClinicQueueEntry.token_number.asc())
        .options(
            joinedload(ClinicQueueEntry.patient),
            joinedload(ClinicQueueEntry.appointment),
        )
    )
    return list(db.scalars(stmt).unique().all())


def get_todays_queue_for_tenant(
    db: Session, tenant_id: UUID
) -> list[ClinicQueueEntry]:
    """Get today's queue entries for the entire tenant (front desk view)."""
    today = date.today()
    stmt = (
        select(ClinicQueueEntry)
        .where(
            ClinicQueueEntry.tenant_id == tenant_id,
            func.date(ClinicQueueEntry.entered_at) == today,
        )
        .order_by(ClinicQueueEntry.token_number.asc())
        .options(
            joinedload(ClinicQueueEntry.patient),
            joinedload(ClinicQueueEntry.doctor),
            joinedload(ClinicQueueEntry.appointment),
        )
    )
    return list(db.scalars(stmt).unique().all())


def update_queue_status(
    db: Session, entry: ClinicQueueEntry, new_status: ClinicQueueStatus
) -> ClinicQueueEntry:
    """Update the queue status and timing fields as appropriate."""
    now_utc = datetime.now(timezone.utc)

    if new_status == ClinicQueueStatus.in_room and entry.called_at is None:
        entry.called_at = now_utc
    if new_status == ClinicQueueStatus.completed and entry.completed_at is None:
        entry.completed_at = now_utc

    entry.queue_status = new_status
    db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry


def update_queue_entry(
    db: Session, entry: ClinicQueueEntry, update_data: dict[str, Any]
) -> ClinicQueueEntry:
    """Update arbitrary fields on a queue entry."""
    for field, value in update_data.items():
        if hasattr(entry, field):
            setattr(entry, field, value)
    db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry


def get_queue_position(
    db: Session, entry: ClinicQueueEntry
) -> int:
    """Get the 1-based position of this entry in the waiting queue for its doctor."""
    today = date.today()
    stmt = select(func.count(ClinicQueueEntry.id)).where(
        ClinicQueueEntry.doctor_id == entry.doctor_id,
        ClinicQueueEntry.tenant_id == entry.tenant_id,
        func.date(ClinicQueueEntry.entered_at) == today,
        ClinicQueueEntry.queue_status == ClinicQueueStatus.waiting,
        ClinicQueueEntry.token_number < entry.token_number,
    )
    count_before = db.scalar(stmt) or 0
    return count_before + 1


def get_waiting_count_before(
    db: Session, doctor_id: UUID, token_number: int
) -> int:
    """Count waiting entries before a given token number for wait estimation."""
    today = date.today()
    stmt = select(func.count(ClinicQueueEntry.id)).where(
        ClinicQueueEntry.doctor_id == doctor_id,
        func.date(ClinicQueueEntry.entered_at) == today,
        ClinicQueueEntry.queue_status == ClinicQueueStatus.waiting,
        ClinicQueueEntry.token_number < token_number,
    )
    return db.scalar(stmt) or 0


def get_todays_completed_count(db: Session, doctor_id: UUID) -> int:
    """Count completed queue entries for a doctor today."""
    today = date.today()
    stmt = select(func.count(ClinicQueueEntry.id)).where(
        ClinicQueueEntry.doctor_id == doctor_id,
        func.date(ClinicQueueEntry.entered_at) == today,
        ClinicQueueEntry.queue_status == ClinicQueueStatus.completed,
    )
    return db.scalar(stmt) or 0


def get_active_queue_entry_for_appointment(
    db: Session, appointment_id: UUID
) -> ClinicQueueEntry | None:
    """Get the active (non-completed, non-skipped) queue entry for an appointment."""
    stmt = select(ClinicQueueEntry).where(
        ClinicQueueEntry.appointment_id == appointment_id,
        ClinicQueueEntry.queue_status.in_(
            [ClinicQueueStatus.waiting, ClinicQueueStatus.in_room]
        ),
    )
    return db.scalars(stmt).first()
