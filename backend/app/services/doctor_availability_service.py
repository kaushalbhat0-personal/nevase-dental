from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.slot_cache_invalidation import schedule_invalidate_doctor_slot_cache_on_commit
from app.crud import crud_doctor_availability
from app.models.doctor_availability import DoctorAvailability, DoctorTimeOff
from app.models.user import User
from app.schemas.doctor import (
    DoctorAvailabilityCopyRequest,
    DoctorAvailabilityCreate,
    DoctorAvailabilityUpdate,
    DoctorTimeOffCreate,
    DoctorTimeOffUpdate,
)
from app.services import doctor_service
from app.services.exceptions import NotFoundError, ValidationError


def _span_minutes(start_t: time, end_t: time) -> float:
    d0 = date(2000, 1, 1)
    return (datetime.combine(d0, end_t) - datetime.combine(d0, start_t)).total_seconds() / 60.0


def list_availability_windows(
    db: Session,
    doctor_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
) -> list[DoctorAvailability]:
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    doctor_service.authorize_doctor_read(db, doctor, current_user, tenant_id)
    return crud_doctor_availability.list_all_availability_for_doctor(db, doctor_id)


def create_availability_window(
    db: Session,
    doctor_id: UUID,
    payload: DoctorAvailabilityCreate,
    current_user: User,
    tenant_id: UUID | None,
) -> DoctorAvailability:
    doctor = doctor_service.get_doctor_or_404_with_tenant(db, doctor_id)
    doctor_service.authorize_doctor_update(db, doctor, current_user, tenant_id)
    if doctor.tenant_id is None:
        raise ValidationError("Doctor tenant is not set")
    if payload.start_time >= payload.end_time:
        raise ValidationError("Availability end time must be after start time")
    if _span_minutes(payload.start_time, payload.end_time) < float(payload.slot_duration):
        raise ValidationError("Window is too short to fit a slot of this duration")
    try:
        row = crud_doctor_availability.create_availability_window(
            db,
            doctor_id=doctor_id,
            day_of_week=payload.day_of_week,
            start_time=payload.start_time,
            end_time=payload.end_time,
            slot_duration=payload.slot_duration,
            tenant_id=doctor.tenant_id,
        )
    except ValueError as e:
        raise ValidationError(str(e)) from e
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)
    return row


def update_availability_window(
    db: Session,
    doctor_id: UUID,
    window_id: UUID,
    payload: DoctorAvailabilityUpdate,
    current_user: User,
    tenant_id: UUID | None,
) -> DoctorAvailability:
    doctor = doctor_service.get_doctor_or_404_with_tenant(db, doctor_id)
    doctor_service.authorize_doctor_update(db, doctor, current_user, tenant_id)
    window = crud_doctor_availability.get_availability_window(db, window_id)
    if window is None or window.doctor_id != doctor_id:
        raise NotFoundError("Availability window not found")
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return window
    eff_start = data.get("start_time", window.start_time)
    eff_end = data.get("end_time", window.end_time)
    eff_slot = data.get("slot_duration", window.slot_duration)
    if _span_minutes(eff_start, eff_end) < float(eff_slot):
        raise ValidationError("Window is too short to fit a slot of this duration")
    try:
        row = crud_doctor_availability.update_availability_window(
            db,
            window,
            day_of_week=data.get("day_of_week"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            slot_duration=data.get("slot_duration"),
        )
    except ValueError as e:
        raise ValidationError(str(e)) from e
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)
    return row


def delete_availability_window(
    db: Session,
    doctor_id: UUID,
    window_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
) -> None:
    doctor = doctor_service.get_doctor_or_404_with_tenant(db, doctor_id)
    doctor_service.authorize_doctor_update(db, doctor, current_user, tenant_id)
    window = crud_doctor_availability.get_availability_window(db, window_id)
    if window is None or window.doctor_id != doctor_id:
        raise NotFoundError("Availability window not found")
    crud_doctor_availability.delete_availability_window(db, window)
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)


def copy_availability_to_days(
    db: Session,
    doctor_id: UUID,
    payload: DoctorAvailabilityCopyRequest,
    current_user: User,
    tenant_id: UUID | None,
) -> None:
    doctor = doctor_service.get_doctor_or_404_with_tenant(db, doctor_id)
    doctor_service.authorize_doctor_update(db, doctor, current_user, tenant_id)
    if doctor.tenant_id is None:
        raise ValidationError("Doctor tenant is not set")

    source_rows = crud_doctor_availability.list_availability_for_doctor_day(db, doctor_id, payload.source_day)
    if not source_rows:
        raise ValidationError("No availability windows to copy for the source day")

    for w in source_rows:
        if w.start_time >= w.end_time:
            raise ValidationError("Availability end time must be after start time")
        if _span_minutes(w.start_time, w.end_time) < float(w.slot_duration):
            raise ValidationError("Window is too short to fit a slot of this duration")

    target_days = sorted({d for d in payload.target_days if d != payload.source_day and 0 <= d <= 6})

    for dow in target_days:
        crud_doctor_availability.replace_availability_day_from_templates(
            db,
            doctor_id=doctor_id,
            day_of_week=dow,
            tenant_id=doctor.tenant_id,
            template_windows=source_rows,
        )
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)


def _assert_time_off_shape(start_t: time | None, end_t: time | None) -> None:
    if (start_t is None) ^ (end_t is None):
        raise ValidationError(
            "For partial time off, set both start and end; for a full day off, leave both empty."
        )
    if start_t is not None and end_t is not None and start_t >= end_t:
        raise ValidationError("Time off end time must be after start time.")


def _existing_time_off_for_date(
    db: Session, doctor_id: UUID, off_date: date, *, exclude_id: UUID | None = None
) -> DoctorTimeOff | None:
    stmt = select(DoctorTimeOff).where(
        DoctorTimeOff.doctor_id == doctor_id,
        DoctorTimeOff.off_date == off_date,
    )
    if exclude_id is not None:
        stmt = stmt.where(DoctorTimeOff.id != exclude_id)
    return db.scalars(stmt).first()


def list_time_off(
    db: Session,
    doctor_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[DoctorTimeOff]:
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    doctor_service.authorize_doctor_read(db, doctor, current_user, tenant_id)
    return crud_doctor_availability.list_time_off_for_doctor(
        db, doctor_id, from_date=from_date, to_date=to_date
    )


def create_time_off(
    db: Session,
    doctor_id: UUID,
    payload: DoctorTimeOffCreate,
    current_user: User,
    tenant_id: UUID | None,
) -> DoctorTimeOff:
    doctor = doctor_service.get_doctor_or_404_with_tenant(db, doctor_id)
    doctor_service.authorize_doctor_update(db, doctor, current_user, tenant_id)
    if doctor.tenant_id is None:
        raise ValidationError("Doctor tenant is not set")
    _assert_time_off_shape(payload.start_time, payload.end_time)
    if _existing_time_off_for_date(db, doctor_id, payload.off_date) is not None:
        raise ValidationError("This date already has a time off entry")
    row = crud_doctor_availability.create_time_off(
        db,
        doctor_id=doctor_id,
        off_date=payload.off_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        tenant_id=doctor.tenant_id,
    )
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)
    return row


def update_time_off(
    db: Session,
    doctor_id: UUID,
    time_off_id: UUID,
    payload: DoctorTimeOffUpdate,
    current_user: User,
    tenant_id: UUID | None,
) -> DoctorTimeOff:
    doctor = doctor_service.get_doctor_or_404_with_tenant(db, doctor_id)
    doctor_service.authorize_doctor_update(db, doctor, current_user, tenant_id)
    row = crud_doctor_availability.get_time_off(db, time_off_id)
    if row is None or row.doctor_id != doctor_id:
        raise NotFoundError("Time off entry not found")
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return row
    off_date = data.get("off_date", row.off_date)
    st = row.start_time if "start_time" not in data else data["start_time"]
    et = row.end_time if "end_time" not in data else data["end_time"]
    _assert_time_off_shape(st, et)
    if off_date != row.off_date:
        conflict = _existing_time_off_for_date(db, doctor_id, off_date, exclude_id=row.id)
        if conflict is not None:
            raise ValidationError("Another time off entry already exists for that date")
    row = crud_doctor_availability.update_time_off_row(db, row, off_date=off_date, start_time=st, end_time=et)
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)
    return row


def delete_time_off(
    db: Session,
    doctor_id: UUID,
    time_off_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
) -> None:
    doctor = doctor_service.get_doctor_or_404_with_tenant(db, doctor_id)
    doctor_service.authorize_doctor_update(db, doctor, current_user, tenant_id)
    row = crud_doctor_availability.get_time_off(db, time_off_id)
    if row is None or row.doctor_id != doctor_id:
        raise NotFoundError("Time off entry not found")
    crud_doctor_availability.delete_time_off(db, row)
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)
