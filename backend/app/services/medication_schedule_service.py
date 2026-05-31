"""
Medication Schedule Service — adherence tracking layer.

Architecture:
  PatientMedicationSchedule is DERIVED from Prescription + PrescriptionItem.
  This service handles:
  1. Derivation — creating schedules from prescription items
  2. Adherence tracking — recording patient actions
  3. Dashboard queries — today's adherence, due medications
  4. Authorization — patient-only access, tenant isolation

  CRITICAL:
  - Prescription data is NEVER mutated through this service
  - Patient actions affect adherence tracking ONLY
  - All actions are audited via log_structured_audit_event
  - Tenant isolation is enforced at every entry point
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_medication_schedule
from app.models.patient_medication_schedule import (
    MedicationScheduleAdherenceAction,
    MedicationScheduleStatus,
)
from app.schemas.medication_schedule import (
    AdherenceAction,
    MedicationScheduleCreate,
    MedicationScheduleRead,
    MedicationScheduleUpdate,
    TodayAdherenceSummary,
)
from app.services import patient_service
from app.services.exceptions import ForbiddenError, NotFoundError
from app.services.security_audit import log_structured_audit_event

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Authorization helpers
# ═════════════════════════════════════════════════════════════════════════════


def _resolve_patient_id(db: Session, current_user) -> UUID:
    """Resolve the patient ID from the current user context.

    CRITICAL: current_user.id is the User UUID, NOT the Patient UUID.
    The Patient and User are separate tables with different UUIDs.
    We must use patient_service.get_patient_by_user_id() to resolve
    the actual Patient UUID from the User.

    Resolution order:
      1. current_user.patient_id — if the user object has a patient_id attribute
         (e.g., from a JWT claim or custom attribute).
      2. patient_service.get_patient_by_user_id() — authoritative DB lookup
         to map User UUID → Patient UUID via Patient.user_id FK.
    """
    # Priority 1: direct patient_id attribute (e.g., JWT claim)
    if hasattr(current_user, "patient_id") and current_user.patient_id:
        return UUID(str(current_user.patient_id))

    # Priority 2: resolve via DB lookup (User UUID → Patient UUID)
    try:
        patient = patient_service.get_patient_by_user_id(db, current_user.id)
        if patient:
            return UUID(str(patient.id))
    except (NotFoundError, ForbiddenError):
        pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only patients can access medication schedules",
    )


def _enforce_patient_access(
    db: Session, current_user, patient_id: UUID, tenant_id: UUID
) -> None:
    """Enforce that the current user is the patient and belongs to the tenant."""
    resolved_patient_id = _resolve_patient_id(db, current_user)
    if resolved_patient_id != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own medication schedules",
        )
    user_tenant = getattr(current_user, "tenant_id", None)
    if user_tenant and UUID(str(user_tenant)) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant mismatch",
        )


def _enforce_patient_role(current_user) -> None:
    """Enforce that only patients can access medication schedules."""
    role = getattr(current_user, "role", None)
    if role and role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can manage medication schedules",
        )


def _resolve_patient_tenant(db: Session, current_user) -> UUID:
    """
    Resolve tenant_id authoritatively.

    Resolution order:
      1. current_user.tenant_id — the user's own tenant is the primary source
         of truth for tenant membership.
      2. patient.tenant_id — fallback if current_user.tenant_id is unavailable,
         but only if it is a proper UUID (never empty).

    Raises:
        HTTPException 403: If tenant cannot be resolved, preserving
                           multi-tenant isolation guarantees.
    """
    # Priority 1: current_user.tenant_id (must be a real UUID)
    user_tenant = getattr(current_user, "tenant_id", None)
    if user_tenant is not None:
        try:
            return UUID(str(user_tenant))
        except (ValueError, TypeError):
            pass

    # Priority 2: fallback — resolve from Patient record
    try:
        patient = patient_service.get_patient_by_user_id(db, current_user.id)
        if patient.tenant_id:
            return UUID(str(patient.tenant_id))
    except (NotFoundError, ForbiddenError):
        pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Tenant context not available — cannot access medication schedules",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Derivation — Create schedule from prescription item
# ═════════════════════════════════════════════════════════════════════════════


def derive_schedule_from_prescription(
    db: Session,
    *,
    prescription_item_id: UUID,
    current_user,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    reminder_times: list[str] | None = None,
) -> MedicationScheduleRead:
    """
    Derive a medication schedule from a prescription item.

    This is the ONLY way to create a medication schedule.
    Prescription data is snapshotted — NEVER editable after creation.

    Args:
        db: Database session.
        prescription_item_id: The prescription item to derive from.
        current_user: The current authenticated user (must be patient).
        start_date: When to start the schedule (defaults to now).
        end_date: When to end the schedule (optional).
        reminder_times: Array of HH:MM strings for reminders.

    Returns:
        The created MedicationScheduleRead.

    Raises:
        HTTPException: If the patient doesn't own the prescription, or
                       if the prescription item doesn't exist.
    """
    _enforce_patient_role(current_user)
    patient_id = _resolve_patient_id(db, current_user)

    # Load the prescription item with its prescription
    from app.models.appointment import Prescription, PrescriptionItem

    prescription_item = db.get(PrescriptionItem, prescription_item_id)
    if not prescription_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription item not found",
        )

    prescription = db.get(Prescription, prescription_item.prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )

    # Validate ownership: the patient must own the prescription
    if UUID(str(prescription.patient_id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This prescription does not belong to you",
        )

    # Validate tenant isolation
    tenant_id = UUID(str(prescription.tenant_id))
    _enforce_patient_access(db, current_user, patient_id, tenant_id)

    # Check if a schedule already exists for this prescription item
    existing = crud_medication_schedule.get_schedule_by_prescription_item(
        db, prescription_item_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A medication schedule already exists for this prescription item",
        )

    # Snapshots prescription data
    now = datetime.now(timezone.utc)
    schedule = crud_medication_schedule.create_medication_schedule(
        db,
        patient_id=patient_id,
        prescription_id=prescription.id,
        prescription_item_id=prescription_item_id,
        tenant_id=tenant_id,
        medicine_name=prescription_item.medicine_name or "Unknown",
        dosage=prescription_item.dosage,
        frequency=prescription_item.frequency,
        duration=prescription_item.duration,
        instructions=prescription_item.instructions,
        start_date=start_date or now,
        end_date=end_date,
        reminder_times=reminder_times,
        total_doses=0,  # Computed later based on frequency + duration
    )

    # Audit log
    log_structured_audit_event(
        event="medication_schedule_created",
        tenant_id=tenant_id,
        resource_id=str(schedule.id),
        actor_id=str(patient_id),
        status="success",
        event_type="medication_schedule",
        patient_id=str(patient_id),
        prescription_id=str(prescription.id),
        prescription_item_id=str(prescription_item_id),
    )

    return _schedule_to_read(schedule)


def derive_schedules_for_prescription(
    db: Session,
    *,
    prescription_id: UUID,
    current_user,
) -> list[MedicationScheduleRead]:
    """
    Derive medication schedules for ALL items in a prescription.

    Called automatically when a prescription is issued during encounter completion.

    Args:
        db: Database session.
        prescription_id: The prescription to derive schedules from.
        current_user: The current authenticated user (must be patient).

    Returns:
        List of created MedicationScheduleRead objects.
    """
    from app.models.appointment import Prescription, PrescriptionItem

    prescription = db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )

    patient_id = _resolve_patient_id(db, current_user)
    if UUID(str(prescription.patient_id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This prescription does not belong to you",
        )

    # Get all items for this prescription
    from sqlalchemy import select

    items_query = select(PrescriptionItem).where(
        PrescriptionItem.prescription_id == prescription_id
    )
    items = list(db.execute(items_query).scalars().all())

    created_schedules: list[MedicationScheduleRead] = []
    now = datetime.now(timezone.utc)

    for item in items:
        # Skip if schedule already exists
        existing = crud_medication_schedule.get_schedule_by_prescription_item(
            db, item.id
        )
        if existing:
            continue

        schedule = crud_medication_schedule.create_medication_schedule(
            db,
            patient_id=patient_id,
            prescription_id=prescription_id,
            prescription_item_id=item.id,
            tenant_id=UUID(str(prescription.tenant_id)),
            medicine_name=item.medicine_name or "Unknown",
            dosage=item.dosage,
            frequency=item.frequency,
            duration=item.duration,
            instructions=item.instructions,
            start_date=now,
            end_date=None,
            reminder_times=[],
            total_doses=0,
        )
        created_schedules.append(_schedule_to_read(schedule))

    if created_schedules:
        log_structured_audit_event(
            event="medication_schedules_batch_created",
            tenant_id=UUID(str(prescription.tenant_id)),
            resource_id=str(prescription_id),
            actor_id=str(patient_id),
            status="success",
            event_type="medication_schedule",
            patient_id=str(patient_id),
            count=str(len(created_schedules)),
        )

    return created_schedules


# ═════════════════════════════════════════════════════════════════════════════
# Adherence Tracking
# ═════════════════════════════════════════════════════════════════════════════


def record_adherence(
    db: Session,
    *,
    schedule_id: UUID,
    action: AdherenceAction,
    current_user,
) -> MedicationScheduleRead:
    """
    Record a patient adherence action on a medication schedule.

    These actions affect adherence tracking ONLY.
    They NEVER modify the Prescription or PrescriptionItem rows.

    Args:
        db: Database session.
        schedule_id: The medication schedule to record adherence for.
        action: The adherence action (taken/skipped/snoozed).
        current_user: The current authenticated user (must be patient).

    Returns:
        Updated MedicationScheduleRead.
    """
    _enforce_patient_role(current_user)
    patient_id = _resolve_patient_id(db, current_user)

    schedule = crud_medication_schedule.get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication schedule not found",
        )

    # Validate ownership
    if UUID(str(schedule.patient_id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This medication schedule does not belong to you",
        )

    # Validate schedule is active
    if not schedule.is_active or schedule.status != MedicationScheduleStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record adherence for an inactive medication schedule",
        )

    # Map action string to enum
    action_map = {
        "taken": MedicationScheduleAdherenceAction.taken,
        "skipped": MedicationScheduleAdherenceAction.skipped,
        "snoozed": MedicationScheduleAdherenceAction.snoozed,
    }
    action_enum = action_map.get(action.action)
    if not action_enum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action.action}. Must be one of: taken, skipped, snoozed",
        )

    # Create adherence log
    crud_medication_schedule.create_adherence_log(
        db,
        medication_schedule_id=schedule_id,
        patient_id=patient_id,
        action=action_enum,
        scheduled_time=action.scheduled_time,
    )

    # Update counts on the schedule
    if action_enum == MedicationScheduleAdherenceAction.taken:
        schedule.taken_count = (schedule.taken_count or 0) + 1
    elif action_enum == MedicationScheduleAdherenceAction.skipped:
        schedule.skipped_count = (schedule.skipped_count or 0) + 1
    # Snoozed does not affect counts

    db.flush()

    # Audit log
    log_structured_audit_event(
        event="medication_adherence_recorded",
        tenant_id=schedule.tenant_id,
        resource_id=str(schedule_id),
        actor_id=str(patient_id),
        status="success",
        event_type="medication_adherence",
        patient_id=str(patient_id),
        action=action.action,
        scheduled_time=action.scheduled_time or "",
    )

    return _schedule_to_read(schedule)


# ═════════════════════════════════════════════════════════════════════════════
# Dashboard Queries
# ═════════════════════════════════════════════════════════════════════════════


def get_due_medications(
    db: Session,
    current_user,
) -> list[MedicationScheduleRead]:
    """
    Get medications due today for the current patient.

    Returns:
        List of MedicationScheduleRead for medications that are due today.
    """
    _enforce_patient_role(current_user)
    patient_id = _resolve_patient_id(db, current_user)
    tenant_id = _resolve_patient_tenant(db, current_user)

    schedules = crud_medication_schedule.get_due_medications(
        db, patient_id, tenant_id
    )
    return [_schedule_to_read(s) for s in schedules]


def get_today_adherence_summary(
    db: Session,
    current_user,
) -> TodayAdherenceSummary:
    """
    Get today's adherence summary for the patient dashboard.

    Returns:
        TodayAdherenceSummary with counts and streak data.
    """
    _enforce_patient_role(current_user)
    patient_id = _resolve_patient_id(db, current_user)

    # Get due medications
    tenant_id = _resolve_patient_tenant(db, current_user)
    due_meds = crud_medication_schedule.get_due_medications(
        db, patient_id, tenant_id
    )
    total_due = len(due_meds)

    # Get today's logs
    today_logs = crud_medication_schedule.get_today_adherence_logs(db, patient_id)
    taken_today = sum(
        1 for log in today_logs if log.action == MedicationScheduleAdherenceAction.taken
    )
    skipped_today = sum(
        1
        for log in today_logs
        if log.action == MedicationScheduleAdherenceAction.skipped
    )
    pending_today = max(0, total_due - taken_today - skipped_today)
    adherence_rate_today = taken_today / total_due if total_due > 0 else 0.0

    # Compute streaks
    current_streak, longest_streak, week_rate = (
        crud_medication_schedule.compute_adherence_streak(db, patient_id)
    )

    return TodayAdherenceSummary(
        total_due_today=total_due,
        taken_today=taken_today,
        skipped_today=skipped_today,
        pending_today=pending_today,
        adherence_rate_today=adherence_rate_today,
        current_streak_days=current_streak,
        longest_streak_days=longest_streak,
        week_adherence_rate=week_rate,
    )


# ═════════════════════════════════════════════════════════════════════════════
# List / Query
# ═════════════════════════════════════════════════════════════════════════════


def get_patient_schedules(
    db: Session,
    current_user,
    *,
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
    status_filter: str | None = None,
) -> tuple[list[MedicationScheduleRead], int]:
    """
    Get medication schedules for the current patient.

    Args:
        db: Database session.
        current_user: The current authenticated user (must be patient).
        skip: Number of records to skip (pagination).
        limit: Maximum number of records to return.
        active_only: If True, return only active schedules.
        status_filter: Optional status filter (active/completed/paused).

    Returns:
        Tuple of (list of MedicationScheduleRead, total count).
    """
    _enforce_patient_role(current_user)
    patient_id = _resolve_patient_id(db, current_user)
    tenant_id = _resolve_patient_tenant(db, current_user)

    if active_only:
        items, total = crud_medication_schedule.get_active_schedules_for_patient(
            db, patient_id, tenant_id, skip=skip, limit=limit
        )
    else:
        items, total = crud_medication_schedule.get_all_schedules_for_patient(
            db, patient_id, tenant_id, skip=skip, limit=limit, status_filter=status_filter
        )

    return [_schedule_to_read(s) for s in items], total


def get_schedule_detail(
    db: Session,
    schedule_id: UUID,
    current_user,
) -> MedicationScheduleRead:
    """
    Get a single medication schedule by ID.

    Args:
        db: Database session.
        schedule_id: The schedule ID.
        current_user: The current authenticated user (must be patient).

    Returns:
        MedicationScheduleRead.

    Raises:
        HTTPException: If not found or not owned by the patient.
    """
    _enforce_patient_role(current_user)
    patient_id = _resolve_patient_id(db, current_user)

    schedule = crud_medication_schedule.get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication schedule not found",
        )

    if UUID(str(schedule.patient_id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This medication schedule does not belong to you",
        )

    return _schedule_to_read(schedule)


# ═════════════════════════════════════════════════════════════════════════════
# Update
# ═════════════════════════════════════════════════════════════════════════════


def update_schedule(
    db: Session,
    schedule_id: UUID,
    updates: MedicationScheduleUpdate,
    current_user,
) -> MedicationScheduleRead:
    """
    Update patient-safe fields on a medication schedule.

    Patients can ONLY update:
    - reminder_times
    - is_active
    - status

    Prescription-snapshot fields are NEVER updated through this method.

    Args:
        db: Database session.
        schedule_id: The schedule ID.
        updates: The fields to update.
        current_user: The current authenticated user (must be patient).

    Returns:
        Updated MedicationScheduleRead.
    """
    _enforce_patient_role(current_user)
    patient_id = _resolve_patient_id(db, current_user)

    schedule = crud_medication_schedule.get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication schedule not found",
        )

    if UUID(str(schedule.patient_id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This medication schedule does not belong to you",
        )

    updated = crud_medication_schedule.update_schedule(
        db,
        schedule_id,
        reminder_times=updates.reminder_times,
        is_active=updates.is_active,
        status=updates.status,
    )

    if updated:
        log_structured_audit_event(
            event="medication_schedule_updated",
            tenant_id=updated.tenant_id,
            resource_id=str(schedule_id),
            actor_id=str(patient_id),
            status="success",
            event_type="medication_schedule",
            patient_id=str(patient_id),
        )

    return _schedule_to_read(updated) if updated else _schedule_to_read(schedule)


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════


def _schedule_to_read(
    schedule: PatientMedicationSchedule,
) -> MedicationScheduleRead:
    """Convert an ORM model to a Pydantic read schema."""
    total_actions = (schedule.taken_count or 0) + (schedule.skipped_count or 0)
    adherence_rate = (
        round((schedule.taken_count or 0) / total_actions, 2)
        if total_actions > 0
        else None
    )

    return MedicationScheduleRead(
        id=schedule.id,
        medicine_name=schedule.medicine_name,
        dosage=schedule.dosage,
        frequency=schedule.frequency,
        duration=schedule.duration,
        instructions=schedule.instructions,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        reminder_times=schedule.reminder_times or [],
        taken_count=schedule.taken_count or 0,
        skipped_count=schedule.skipped_count or 0,
        total_doses=schedule.total_doses or 0,
        is_active=schedule.is_active,
        status=schedule.status.value if schedule.status else "active",
        adherence_rate=adherence_rate,
        prescription_id=schedule.prescription_id,
        prescription_item_id=schedule.prescription_item_id,
        created_at=schedule.created_at,
    )
