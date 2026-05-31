"""
Clinic queue API endpoints for front desk and doctor queue views.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    get_optional_scoped_tenant_id,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.clinic_queue import (
    QueueDashboardRead,
    QueueEntryRead,
    QueuePositionRead,
    PrepChecklistUpdate,
    RoomAssignment,
)
from app.services import queue_service

router = APIRouter(
    prefix="/queue",
    tags=["queue"],
)


@router.get("/today", response_model=list[QueueEntryRead])
def get_todays_queue(
    doctor_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
):
    """Get today's queue. If doctor_id provided, returns queue for that doctor.
    Otherwise returns full tenant queue."""
    if not tenant_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )

    if doctor_id:
        return queue_service.get_doctor_queue(db, doctor_id, tenant_id)

    return queue_service.get_front_desk_queue(db, tenant_id).entries


@router.get("/today/front-desk", response_model=QueueDashboardRead)
def get_front_desk_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
):
    """Get the full front desk queue dashboard with counts."""
    if not tenant_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )
    return queue_service.get_front_desk_queue(db, tenant_id)


@router.get("/{appointment_id}/position", response_model=QueuePositionRead)
def get_queue_position(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get queue position and wait estimation for an appointment."""
    return queue_service.get_queue_position(db, appointment_id)


@router.post("/{entry_id}/call", response_model=QueueEntryRead)
def call_queue_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a queue entry as called (patient called to room)."""
    from app.services.queue_service import _enrich_entry
    from app.crud import crud_clinic_queue

    entry = queue_service.mark_called(db, entry_id)
    enriched = crud_clinic_queue.get_queue_entry_by_id(db, entry.id)
    if enriched:
        return _enrich_entry(enriched)
    from app.services.exceptions import NotFoundError
    raise NotFoundError("Queue entry not found after update")


@router.post("/{entry_id}/complete", response_model=QueueEntryRead)
def complete_queue_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a queue entry as completed."""
    from app.services.queue_service import _enrich_entry
    from app.crud import crud_clinic_queue

    entry = queue_service.mark_completed(db, entry_id)
    enriched = crud_clinic_queue.get_queue_entry_by_id(db, entry.id)
    if enriched:
        return _enrich_entry(enriched)
    from app.services.exceptions import NotFoundError
    raise NotFoundError("Queue entry not found after update")


@router.post("/{entry_id}/skip", response_model=QueueEntryRead)
def skip_queue_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Skip a queue entry."""
    from app.services.queue_service import _enrich_entry
    from app.crud import crud_clinic_queue

    entry = queue_service.mark_skipped(db, entry_id)
    enriched = crud_clinic_queue.get_queue_entry_by_id(db, entry.id)
    if enriched:
        return _enrich_entry(enriched)
    from app.services.exceptions import NotFoundError
    raise NotFoundError("Queue entry not found after update")


@router.put("/{entry_id}/room", response_model=QueueEntryRead)
def assign_room(
    entry_id: UUID,
    room: RoomAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Assign a room number to a queue entry."""
    from app.services.queue_service import _enrich_entry
    from app.crud import crud_clinic_queue

    entry = queue_service.assign_room(db, entry_id, room.room_number)
    enriched = crud_clinic_queue.get_queue_entry_by_id(db, entry.id)
    if enriched:
        return _enrich_entry(enriched)
    from app.services.exceptions import NotFoundError
    raise NotFoundError("Queue entry not found after update")


@router.put("/{entry_id}/prep-check", response_model=QueueEntryRead)
def update_prep_checklist(
    entry_id: UUID,
    checklist: PrepChecklistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update the operational preparation checklist for a queue entry."""
    from app.services.queue_service import _enrich_entry
    from app.crud import crud_clinic_queue

    entry = queue_service.update_prep_checklist(
        db, entry_id, checklist.model_dump(exclude_unset=True)
    )
    enriched = crud_clinic_queue.get_queue_entry_by_id(db, entry.id)
    if enriched:
        return _enrich_entry(enriched)
    from app.services.exceptions import NotFoundError
    raise NotFoundError("Queue entry not found after update")
