"""
Clinic queue schemas for front desk and doctor queue views.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.clinic_queue import ClinicQueueStatus


class QueueEntryRead(BaseModel):
    """Single queue entry with patient and appointment context."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    appointment_id: UUID
    tenant_id: UUID
    doctor_id: UUID
    patient_id: UUID
    queue_date: date
    token_number: int
    queue_status: ClinicQueueStatus
    priority: int
    room_number: str | None = None
    entered_at: datetime
    called_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: UUID

    # Resolved display fields (populated by service layer)
    patient_name: str = ""
    doctor_name: str = ""
    appointment_time: datetime | None = None


class QueuePositionRead(BaseModel):
    """Queue position and wait estimation."""
    token_number: int
    position: int
    waiting_count_before: int
    estimated_wait_minutes: int | None = None


class QueueDashboardRead(BaseModel):
    """Aggregated queue view for front desk."""
    total_waiting: int
    total_in_room: int
    total_completed_today: int
    entries: list[QueueEntryRead]


class PrepChecklistUpdate(BaseModel):
    """Operational preparation checklist items."""
    id_verified: bool = False
    consent_signed: bool = False
    insurance_confirmed: bool = False


class RoomAssignment(BaseModel):
    """Assign or update room number for a queue entry."""
    room_number: str
