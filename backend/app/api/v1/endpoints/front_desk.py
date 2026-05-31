"""
Front desk API endpoints for receptionist operational actions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    get_optional_scoped_tenant_id,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.appointment import AppointmentRead
from app.services import front_desk_service

router = APIRouter(
    prefix="/appointments",
    tags=["front-desk"],
)


class WalkInCreate(BaseModel):
    patient_id: UUID
    doctor_id: UUID


class RescheduleRequest(BaseModel):
    new_time: datetime


@router.post("/{appointment_id}/arrive", response_model=AppointmentRead)
def mark_arrived(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
):
    """Mark an appointment as arrived and add to clinic queue."""
    if not tenant_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )
    return front_desk_service.mark_arrived(
        db, appointment_id, current_user.id, tenant_id
    )


@router.post("/{appointment_id}/check-in", response_model=AppointmentRead)
def check_in_patient(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
):
    """Check in a patient after arrival."""
    if not tenant_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )
    return front_desk_service.check_in_patient(
        db, appointment_id, current_user.id, tenant_id
    )


@router.post("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
):
    """Cancel an appointment from any pre-consultation state."""
    if not tenant_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )
    return front_desk_service.cancel_appointment(
        db, appointment_id, current_user.id, tenant_id
    )


@router.post("/{appointment_id}/no-show", response_model=AppointmentRead)
def mark_no_show(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
):
    """Mark an appointment as no-show."""
    if not tenant_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )
    return front_desk_service.mark_no_show(
        db, appointment_id, current_user.id, tenant_id
    )


@router.post("/walk-in", response_model=AppointmentRead, status_code=201)
def create_walk_in(
    payload: WalkInCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
):
    """Create a same-day walk-in appointment and add to queue."""
    if not tenant_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )
    return front_desk_service.create_walk_in(
        db,
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        tenant_id=tenant_id,
        current_user_id=current_user.id,
    )


@router.post("/{appointment_id}/reschedule", response_model=AppointmentRead)
def reschedule_appointment(
    appointment_id: UUID,
    payload: RescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
):
    """Reschedule an appointment (lightweight hook)."""
    if not tenant_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )
    return front_desk_service.reschedule_hook(
        db, appointment_id, payload.new_time, current_user.id, tenant_id
    )
