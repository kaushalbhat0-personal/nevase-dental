"""
CRUD operations for PatientMedicationSchedule and MedicationAdherenceLog.

Architecture:
  These are DERIVED records — they NEVER mutate Prescription or PrescriptionItem.
  All operations enforce patient ownership and tenant isolation.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.patient_medication_schedule import (
    MedicationAdherenceLog,
    MedicationScheduleAdherenceAction,
    MedicationScheduleStatus,
    PatientMedicationSchedule,
)

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# CREATE
# ═════════════════════════════════════════════════════════════════════════════


def create_medication_schedule(
    db: Session,
    *,
    patient_id: UUID,
    prescription_id: UUID,
    prescription_item_id: UUID,
    tenant_id: UUID,
    medicine_name: str,
    dosage: str | None = None,
    frequency: str | None = None,
    duration: str | None = None,
    instructions: str | None = None,
    start_date: datetime,
    end_date: datetime | None = None,
    reminder_times: list[str] | None = None,
    total_doses: int = 0,
) -> PatientMedicationSchedule:
    """
    Create a new medication schedule derived from a prescription item.

    This is called by the service layer after validating ownership.
    Prescription data is snapshotted — NEVER editable after creation.
    """
    schedule = PatientMedicationSchedule(
        patient_id=patient_id,
        prescription_id=prescription_id,
        prescription_item_id=prescription_item_id,
        tenant_id=tenant_id,
        medicine_name=medicine_name,
        dosage=dosage,
        frequency=frequency,
        duration=duration,
        instructions=instructions,
        start_date=start_date,
        end_date=end_date,
        reminder_times=reminder_times or [],
        total_doses=total_doses,
        is_active=True,
        status=MedicationScheduleStatus.active,
    )
    db.add(schedule)
    db.flush()
    logger.info(
        "Created medication schedule %s for patient %s from prescription item %s",
        schedule.id,
        patient_id,
        prescription_item_id,
    )
    return schedule


# ═════════════════════════════════════════════════════════════════════════════
# READ
# ═════════════════════════════════════════════════════════════════════════════


def get_schedule_by_id(
    db: Session, schedule_id: UUID
) -> PatientMedicationSchedule | None:
    """Get a medication schedule by ID."""
    return db.get(PatientMedicationSchedule, schedule_id)


def get_active_schedules_for_patient(
    db: Session,
    patient_id: UUID,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[PatientMedicationSchedule], int]:
    """
    Get active medication schedules for a patient within their tenant.

    Tenant isolation: strictly scoped to patient_id + tenant_id.
    """
    query = select(PatientMedicationSchedule).where(
        PatientMedicationSchedule.patient_id == patient_id,
        PatientMedicationSchedule.tenant_id == tenant_id,
        PatientMedicationSchedule.is_active == True,
    )
    count_query = select(func.count()).select_from(query.subquery())

    total = db.scalar(count_query) or 0
    items = (
        db.execute(
            query.order_by(PatientMedicationSchedule.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    logger.info(
        "[SCHEDULE_QUERY_TRACE] get_active_schedules_for_patient: patient=%s tenant=%s returned=%d",
        patient_id,
        tenant_id,
        len(items),
    )
    return list(items), total


def get_all_schedules_for_patient(
    db: Session,
    patient_id: UUID,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
) -> tuple[list[PatientMedicationSchedule], int]:
    """
    Get all medication schedules for a patient (active + inactive).

    Tenant isolation: strictly scoped to patient_id + tenant_id.
    """
    conditions = [
        PatientMedicationSchedule.patient_id == patient_id,
        PatientMedicationSchedule.tenant_id == tenant_id,
    ]
    if status_filter:
        conditions.append(PatientMedicationSchedule.status == status_filter)

    query = select(PatientMedicationSchedule).where(*conditions)
    count_query = select(func.count()).select_from(query.subquery())

    total = db.scalar(count_query) or 0
    items = (
        db.execute(
            query.order_by(PatientMedicationSchedule.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    logger.info(
        "[SCHEDULE_QUERY_TRACE] get_all_schedules_for_patient: patient=%s tenant=%s returned=%d total=%d",
        patient_id,
        tenant_id,
        len(items),
        total,
    )
    return list(items), total


def get_due_medications(
    db: Session, patient_id: UUID, tenant_id: UUID
) -> list[PatientMedicationSchedule]:
    """
    Get medications that are due today for a patient.

    A medication is "due" if:
    - is_active = True
    - status = active
    - start_date <= now
    - end_date IS NULL OR end_date >= today
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    query = select(PatientMedicationSchedule).where(
        PatientMedicationSchedule.patient_id == patient_id,
        PatientMedicationSchedule.tenant_id == tenant_id,
        PatientMedicationSchedule.is_active == True,
        PatientMedicationSchedule.status == MedicationScheduleStatus.active,
        PatientMedicationSchedule.start_date <= now,
        (
            PatientMedicationSchedule.end_date.is_(None)
            | (PatientMedicationSchedule.end_date >= today_start)
        ),
    )
    items = db.execute(query.order_by(PatientMedicationSchedule.medicine_name)).scalars().all()
    return list(items)


def get_schedule_by_prescription_item(
    db: Session, prescription_item_id: UUID
) -> PatientMedicationSchedule | None:
    """Get the medication schedule for a specific prescription item (if one exists)."""
    query = select(PatientMedicationSchedule).where(
        PatientMedicationSchedule.prescription_item_id == prescription_item_id
    )
    return db.scalar(query)


# ═════════════════════════════════════════════════════════════════════════════
# UPDATE
# ═════════════════════════════════════════════════════════════════════════════


def update_schedule(
    db: Session,
    schedule_id: UUID,
    **kwargs: Any,
) -> PatientMedicationSchedule | None:
    """
    Update a medication schedule.

    Only patient-safe fields can be updated:
    - reminder_times
    - is_active
    - status

    Prescription-snapshot fields (medicine_name, dosage, etc.) are NEVER updated.
    """
    allowed_fields = {"reminder_times", "is_active", "status"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

    if not update_data:
        return get_schedule_by_id(db, schedule_id)

    stmt = (
        update(PatientMedicationSchedule)
        .where(PatientMedicationSchedule.id == schedule_id)
        .values(**update_data)
    )
    db.execute(stmt)
    db.flush()
    return get_schedule_by_id(db, schedule_id)


# ═════════════════════════════════════════════════════════════════════════════
# ADHERENCE LOG
# ═════════════════════════════════════════════════════════════════════════════


def create_adherence_log(
    db: Session,
    *,
    medication_schedule_id: UUID,
    patient_id: UUID,
    action: MedicationScheduleAdherenceAction,
    scheduled_time: str | None = None,
) -> MedicationAdherenceLog:
    """Record an adherence action in the audit log."""
    log_entry = MedicationAdherenceLog(
        medication_schedule_id=medication_schedule_id,
        patient_id=patient_id,
        action=action,
        scheduled_time=scheduled_time,
    )
    db.add(log_entry)
    db.flush()
    return log_entry


def get_adherence_logs_for_schedule(
    db: Session,
    schedule_id: UUID,
    *,
    limit: int = 100,
) -> list[MedicationAdherenceLog]:
    """Get adherence logs for a specific schedule."""
    query = (
        select(MedicationAdherenceLog)
        .where(MedicationAdherenceLog.medication_schedule_id == schedule_id)
        .order_by(MedicationAdherenceLog.actioned_at.desc())
        .limit(limit)
    )
    return list(db.execute(query).scalars().all())


def get_today_adherence_logs(
    db: Session, patient_id: UUID
) -> list[MedicationAdherenceLog]:
    """Get today's adherence logs for a patient."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    query = (
        select(MedicationAdherenceLog)
        .where(
            MedicationAdherenceLog.patient_id == patient_id,
            MedicationAdherenceLog.actioned_at >= today_start,
        )
        .order_by(MedicationAdherenceLog.actioned_at.desc())
    )
    return list(db.execute(query).scalars().all())


def get_week_adherence_logs(
    db: Session, patient_id: UUID
) -> list[MedicationAdherenceLog]:
    """Get adherence logs for the last 7 days for a patient."""
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    query = (
        select(MedicationAdherenceLog)
        .where(
            MedicationAdherenceLog.patient_id == patient_id,
            MedicationAdherenceLog.actioned_at >= week_ago,
        )
        .order_by(MedicationAdherenceLog.actioned_at.desc())
    )
    return list(db.execute(query).scalars().all())


# ═════════════════════════════════════════════════════════════════════════════
# STREAK COMPUTATION
# ═════════════════════════════════════════════════════════════════════════════


def compute_adherence_streak(
    db: Session, patient_id: UUID
) -> tuple[int, int, float]:
    """
    Compute lightweight adherence streak metrics.

    Returns:
        Tuple of (current_streak_days, longest_streak_days, week_adherence_rate)
    """
    logs = get_week_adherence_logs(db, patient_id)

    # Group logs by date
    from collections import defaultdict

    logs_by_date: dict[date, list[MedicationAdherenceLog]] = defaultdict(list)
    for log in logs:
        log_date = log.actioned_at.date()
        logs_by_date[log_date].append(log)

    # Compute week adherence rate
    total_actions = len(logs)
    taken_actions = sum(
        1 for log in logs if log.action == MedicationScheduleAdherenceAction.taken
    )
    week_rate = taken_actions / total_actions if total_actions > 0 else 0.0

    # Compute streak: consecutive days with at least one "taken" action
    today = datetime.now(timezone.utc).date()
    current_streak = 0
    check_date = today

    while check_date in logs_by_date:
        has_taken = any(
            log.action == MedicationScheduleAdherenceAction.taken
            for log in logs_by_date[check_date]
        )
        if has_taken:
            current_streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # Compute longest streak from available data
    sorted_dates = sorted(logs_by_date.keys(), reverse=True)
    longest_streak = 0
    temp_streak = 0
    prev_date = None

    for d in sorted_dates:
        has_taken = any(
            log.action == MedicationScheduleAdherenceAction.taken
            for log in logs_by_date[d]
        )
        if has_taken:
            if prev_date is None or (prev_date - d).days == 1:
                temp_streak += 1
            else:
                temp_streak = 1
            longest_streak = max(longest_streak, temp_streak)
            prev_date = d
        else:
            temp_streak = 0
            prev_date = None

    return current_streak, longest_streak, week_rate


# ═════════════════════════════════════════════════════════════════════════════
# DELETE
# ═════════════════════════════════════════════════════════════════════════════


def soft_delete_schedule(
    db: Session, schedule_id: UUID
) -> bool:
    """Soft-delete a medication schedule by marking it inactive."""
    stmt = (
        update(PatientMedicationSchedule)
        .where(PatientMedicationSchedule.id == schedule_id)
        .values(is_active=False, status=MedicationScheduleStatus.completed)
    )
    result = db.execute(stmt)
    db.flush()
    return result.rowcount > 0
