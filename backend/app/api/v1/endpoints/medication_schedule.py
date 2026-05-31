"""
Medication Schedule API endpoints — patient-scoped adherence tracking.

Architecture:
  PatientMedicationSchedule is DERIVED from Prescription + PrescriptionItem.
  It is a reminder/adherence layer ONLY.
  Prescription remains the canonical source-of-truth.

  Patients CANNOT:
  - edit prescribed dosage
  - alter prescription instructions
  - overwrite doctor records

  Patient actions (taken/skipped/snooze) affect adherence tracking ONLY.
  They NEVER mutate the Prescription or PrescriptionItem rows.

CRITICAL:
  - Patient access is strictly scoped to their own data
  - Tenant isolation is enforced at the service layer
  - All adherence actions are audited
  - Prescription data is NEVER mutated through these endpoints
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.medication_schedule import (
    AdherenceAction,
    AdherenceActionResponse,
    MedicationScheduleCreate,
    MedicationScheduleListResponse,
    MedicationScheduleRead,
    MedicationScheduleUpdate,
    TodayAdherenceSummary,
)
from app.services import medication_schedule_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patient/medications", tags=["patient-medications"])


# ═════════════════════════════════════════════════════════════════════════════
# Derivation — Create schedule from prescription item
# ═════════════════════════════════════════════════════════════════════════════


@router.post(
    "/derive",
    response_model=MedicationScheduleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Derive a medication schedule from a prescription item",
    description="Creates an adherence tracking schedule from a prescription item. "
    "Prescription data is snapshotted and becomes immutable. "
    "Patient actions on this schedule affect adherence tracking ONLY.",
)
def derive_schedule(
    data: MedicationScheduleCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Derive a medication schedule from a prescription item."""
    return medication_schedule_service.derive_schedule_from_prescription(
        db,
        prescription_item_id=data.prescription_item_id,
        current_user=current_user,
        start_date=data.start_date,
        end_date=data.end_date,
        reminder_times=data.reminder_times,
    )


@router.post(
    "/derive/{prescription_id}",
    response_model=list[MedicationScheduleRead],
    status_code=status.HTTP_201_CREATED,
    summary="Derive schedules for all items in a prescription",
    description="Creates adherence tracking schedules for ALL items in a prescription. "
    "Skips items that already have schedules.",
)
def derive_schedules_for_prescription(
    prescription_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Derive medication schedules for all items in a prescription."""
    return medication_schedule_service.derive_schedules_for_prescription(
        db,
        prescription_id=prescription_id,
        current_user=current_user,
    )


# ═════════════════════════════════════════════════════════════════════════════
# List / Query
# ═════════════════════════════════════════════════════════════════════════════


@router.get(
    "",
    response_model=MedicationScheduleListResponse,
    summary="List medication schedules",
    description="Get all medication schedules for the current patient. "
    "Supports filtering by active status and pagination.",
)
def list_schedules(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    active_only: bool = Query(True),
    status_filter: str | None = Query(None, pattern=r"^(active|completed|paused)$"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List medication schedules for the current patient."""
    items, total = medication_schedule_service.get_patient_schedules(
        db,
        current_user,
        skip=skip,
        limit=limit,
        active_only=active_only,
        status_filter=status_filter,
    )
    return MedicationScheduleListResponse(
        items=items, total=total, skip=skip, limit=limit
    )


@router.get(
    "/due",
    response_model=list[MedicationScheduleRead],
    summary="Get medications due today",
    description="Get medications that are due today for the current patient. "
    "A medication is 'due' if it's active, within its date range, and has not been "
    "fully taken for the day.",
)
def get_due_medications(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get medications due today."""
    return medication_schedule_service.get_due_medications(db, current_user)


@router.get(
    "/summary",
    response_model=TodayAdherenceSummary,
    summary="Get today's adherence summary",
    description="Get today's medication adherence summary for the patient dashboard. "
    "Includes counts, adherence rate, and lightweight streak tracking.",
)
def get_adherence_summary(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get today's adherence summary."""
    return medication_schedule_service.get_today_adherence_summary(
        db, current_user
    )


@router.get(
    "/{schedule_id}",
    response_model=MedicationScheduleRead,
    summary="Get medication schedule detail",
    description="Get a single medication schedule by ID. "
    "Patient can only access their own schedules.",
)
def get_schedule(
    schedule_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a single medication schedule."""
    return medication_schedule_service.get_schedule_detail(
        db, schedule_id, current_user
    )


# ═════════════════════════════════════════════════════════════════════════════
# Adherence Actions
# ═════════════════════════════════════════════════════════════════════════════


@router.post(
    "/{schedule_id}/adherence",
    response_model=AdherenceActionResponse,
    summary="Record adherence action",
    description="Record a patient adherence action (taken/skipped/snoozed) "
    "on a medication schedule. These actions affect adherence tracking ONLY. "
    "They NEVER modify the Prescription or PrescriptionItem rows.",
)
def record_adherence(
    schedule_id: UUID,
    action: AdherenceAction,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Record an adherence action on a medication schedule."""
    schedule = medication_schedule_service.record_adherence(
        db,
        schedule_id=schedule_id,
        action=action,
        current_user=current_user,
    )
    return AdherenceActionResponse(
        schedule=schedule,
        message=f"Medication marked as {action.action}",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Update
# ═════════════════════════════════════════════════════════════════════════════


@router.patch(
    "/{schedule_id}",
    response_model=MedicationScheduleRead,
    summary="Update medication schedule",
    description="Update patient-safe fields on a medication schedule. "
    "Patients can ONLY update reminder_times, is_active, and status. "
    "Prescription-snapshot fields (medicine_name, dosage, etc.) are NEVER editable.",
)
def update_schedule(
    schedule_id: UUID,
    updates: MedicationScheduleUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update a medication schedule (patient-safe fields only)."""
    return medication_schedule_service.update_schedule(
        db, schedule_id, updates, current_user
    )
