"""
Queue service — business logic for clinic queue management.

Provides:
- Adding appointments to the queue with token generation
- Queue status transitions (call, complete, skip)
- Queue position and wait estimation
- Front desk and doctor queue views
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud import crud_clinic_queue
from app.models.clinic_queue import ClinicQueueEntry, ClinicQueueStatus
from app.schemas.clinic_queue import (
    QueueDashboardRead,
    QueueEntryRead,
    QueuePositionRead,
)
from app.services.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Default average consultation time in minutes (configurable in future)
DEFAULT_CONSULTATION_MINUTES = 15


def add_appointment_to_queue(
    db: Session,
    *,
    appointment_id: UUID,
    tenant_id: UUID,
    doctor_id: UUID,
    patient_id: UUID,
    created_by: UUID,
    priority: int = 0,
) -> ClinicQueueEntry:
    """Add an appointment to the queue with an auto-generated token number."""
    # Check if already in queue
    existing = crud_clinic_queue.get_queue_entry_by_appointment(db, appointment_id)
    if existing:
        logger.warning(
            "Appointment %s already in queue (entry %s, token %d)",
            appointment_id,
            existing.id,
            existing.token_number,
        )
        return existing

    token_number = crud_clinic_queue.get_next_token_number(db, doctor_id)

    entry = crud_clinic_queue.add_queue_entry(
        db=db,
        appointment_id=appointment_id,
        tenant_id=tenant_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        token_number=token_number,
        created_by=created_by,
        priority=priority,
    )
    logger.info(
        "Added appointment %s to queue: token %d for doctor %s",
        appointment_id,
        token_number,
        doctor_id,
    )
    return entry


def mark_called(db: Session, entry_id: UUID) -> ClinicQueueEntry:
    """Mark a queue entry as called (in_room)."""
    entry = crud_clinic_queue.get_queue_entry_by_id(db, entry_id)
    if not entry:
        raise NotFoundError(f"Queue entry {entry_id} not found")
    if entry.queue_status != ClinicQueueStatus.waiting:
        raise ValidationError(
            f"Cannot call entry {entry_id}: current status is {entry.queue_status.value}"
        )
    return crud_clinic_queue.update_queue_status(
        db, entry, ClinicQueueStatus.in_room
    )


def mark_completed(db: Session, entry_id: UUID) -> ClinicQueueEntry:
    """Mark a queue entry as completed."""
    entry = crud_clinic_queue.get_queue_entry_by_id(db, entry_id)
    if not entry:
        raise NotFoundError(f"Queue entry {entry_id} not found")
    if entry.queue_status not in (ClinicQueueStatus.waiting, ClinicQueueStatus.in_room):
        raise ValidationError(
            f"Cannot complete entry {entry_id}: current status is {entry.queue_status.value}"
        )
    return crud_clinic_queue.update_queue_status(
        db, entry, ClinicQueueStatus.completed
    )


def mark_skipped(db: Session, entry_id: UUID) -> ClinicQueueEntry:
    """Skip a queue entry (e.g., patient not ready when called)."""
    entry = crud_clinic_queue.get_queue_entry_by_id(db, entry_id)
    if not entry:
        raise NotFoundError(f"Queue entry {entry_id} not found")
    if entry.queue_status != ClinicQueueStatus.waiting:
        raise ValidationError(
            f"Cannot skip entry {entry_id}: current status is {entry.queue_status.value}"
        )
    return crud_clinic_queue.update_queue_status(
        db, entry, ClinicQueueStatus.skipped
    )


def get_doctor_queue(
    db: Session, doctor_id: UUID, tenant_id: UUID
) -> list[QueueEntryRead]:
    """Get today's queue for a specific doctor, enriched with display names."""
    entries = crud_clinic_queue.get_todays_queue_for_doctor(
        db, doctor_id, tenant_id
    )
    return [_enrich_entry(entry) for entry in entries]


def get_front_desk_queue(
    db: Session, tenant_id: UUID
) -> QueueDashboardRead:
    """Get the full front desk queue view with counts."""
    entries = crud_clinic_queue.get_todays_queue_for_tenant(db, tenant_id)

    total_waiting = sum(
        1 for e in entries if e.queue_status == ClinicQueueStatus.waiting
    )
    total_in_room = sum(
        1 for e in entries if e.queue_status == ClinicQueueStatus.in_room
    )
    total_completed = sum(
        1 for e in entries if e.queue_status == ClinicQueueStatus.completed
    )

    return QueueDashboardRead(
        total_waiting=total_waiting,
        total_in_room=total_in_room,
        total_completed_today=total_completed,
        entries=[_enrich_entry(e) for e in entries],
    )


def get_queue_position(
    db: Session, appointment_id: UUID
) -> QueuePositionRead:
    """Get the queue position and wait estimation for an appointment."""
    entry = crud_clinic_queue.get_queue_entry_by_appointment(db, appointment_id)
    if not entry:
        raise NotFoundError(
            f"No queue entry found for appointment {appointment_id}"
        )

    position = crud_clinic_queue.get_queue_position(db, entry)
    waiting_before = crud_clinic_queue.get_waiting_count_before(
        db, entry.doctor_id, entry.token_number
    )

    # Simple wait estimation: waiting_count_before * average consultation time
    estimated_wait = waiting_before * DEFAULT_CONSULTATION_MINUTES

    return QueuePositionRead(
        token_number=entry.token_number,
        position=position,
        waiting_count_before=waiting_before,
        estimated_wait_minutes=estimated_wait,
    )


def assign_room(
    db: Session, entry_id: UUID, room_number: str
) -> ClinicQueueEntry:
    """Assign or update the room number for a queue entry."""
    entry = crud_clinic_queue.get_queue_entry_by_id(db, entry_id)
    if not entry:
        raise NotFoundError(f"Queue entry {entry_id} not found")

    return crud_clinic_queue.update_queue_entry(
        db, entry, {"room_number": room_number}
    )


def update_prep_checklist(
    db: Session,
    entry_id: UUID,
    checklist: dict,
) -> ClinicQueueEntry:
    """Update the operational preparation checklist on a queue entry."""
    entry = crud_clinic_queue.get_queue_entry_by_id(db, entry_id)
    if not entry:
        raise NotFoundError(f"Queue entry {entry_id} not found")

    current_meta = entry.prep_metadata or {}
    current_meta.update(checklist)
    return crud_clinic_queue.update_queue_entry(
        db, entry, {"prep_metadata": current_meta}
    )


def _enrich_entry(entry: ClinicQueueEntry) -> QueueEntryRead:
    """Enrich a queue entry with resolved display names."""
    patient_name = entry.patient.name if entry.patient else ""
    doctor_name = entry.doctor.name if entry.doctor else ""
    appointment_time = entry.appointment.appointment_time if entry.appointment else None

    return QueueEntryRead(
        id=entry.id,
        appointment_id=entry.appointment_id,
        tenant_id=entry.tenant_id,
        doctor_id=entry.doctor_id,
        patient_id=entry.patient_id,
        queue_date=entry.queue_date,
        token_number=entry.token_number,
        queue_status=entry.queue_status,
        priority=entry.priority,
        room_number=entry.room_number,
        entered_at=entry.entered_at,
        called_at=entry.called_at,
        completed_at=entry.completed_at,
        created_by=entry.created_by,
        patient_name=patient_name,
        doctor_name=doctor_name,
        appointment_time=appointment_time,
    )
