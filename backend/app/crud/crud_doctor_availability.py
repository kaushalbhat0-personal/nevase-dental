from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.slot_cache_invalidation import schedule_invalidate_doctor_slot_cache_on_commit
from app.models.doctor_availability import DoctorAvailability, DoctorTimeOff


def doctor_has_any_availability(db: Session, doctor_id: UUID) -> bool:
    stmt = select(func.count()).select_from(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor_id)
    return int(db.scalar(stmt) or 0) > 0


def count_availability_windows_by_doctor_ids(db: Session, doctor_ids: list[UUID]) -> dict[UUID, int]:
    if not doctor_ids:
        return {}
    stmt = (
        select(DoctorAvailability.doctor_id, func.count())
        .where(DoctorAvailability.doctor_id.in_(doctor_ids))
        .group_by(DoctorAvailability.doctor_id)
    )
    return {row[0]: int(row[1]) for row in db.execute(stmt).all()}


def list_availability_for_doctor_day(db: Session, doctor_id: UUID, day_of_week: int) -> list[DoctorAvailability]:
    stmt = (
        select(DoctorAvailability)
        .where(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.day_of_week == day_of_week,
        )
        .order_by(DoctorAvailability.start_time)
    )
    return list(db.scalars(stmt).all())


def list_all_availability_for_doctor(db: Session, doctor_id: UUID) -> list[DoctorAvailability]:
    stmt = (
        select(DoctorAvailability)
        .where(DoctorAvailability.doctor_id == doctor_id)
        .order_by(DoctorAvailability.day_of_week, DoctorAvailability.start_time)
    )
    return list(db.scalars(stmt).all())


def get_availability_window(db: Session, window_id: UUID) -> DoctorAvailability | None:
    stmt = select(DoctorAvailability).where(DoctorAvailability.id == window_id)
    return db.scalars(stmt).first()


def delete_availability_window(db: Session, window: DoctorAvailability) -> None:
    doctor_id = window.doctor_id
    db.delete(window)
    db.flush()
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)


def replace_availability_day_from_templates(
    db: Session,
    *,
    doctor_id: UUID,
    day_of_week: int,
    tenant_id: UUID,
    template_windows: list[DoctorAvailability],
) -> None:
    """Remove all availability rows for the doctor on ``day_of_week``, then insert copies of ``template_windows``."""
    stmt = delete(DoctorAvailability).where(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.day_of_week == day_of_week,
    )
    db.execute(stmt)
    for tw in template_windows:
        row = DoctorAvailability(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            start_time=tw.start_time,
            end_time=tw.end_time,
            slot_duration=tw.slot_duration,
            tenant_id=tenant_id,
        )
        db.add(row)
    db.flush()
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)


def list_time_off_for_doctor_on_date(db: Session, doctor_id: UUID, target_date: date) -> list[DoctorTimeOff]:
    stmt = select(DoctorTimeOff).where(
        DoctorTimeOff.doctor_id == doctor_id,
        DoctorTimeOff.off_date == target_date,
    )
    return list(db.scalars(stmt).all())


def list_time_off_for_doctor(
    db: Session,
    doctor_id: UUID,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[DoctorTimeOff]:
    stmt = select(DoctorTimeOff).where(DoctorTimeOff.doctor_id == doctor_id)
    if from_date is not None:
        stmt = stmt.where(DoctorTimeOff.off_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(DoctorTimeOff.off_date <= to_date)
    stmt = stmt.order_by(DoctorTimeOff.off_date, DoctorTimeOff.id)
    return list(db.scalars(stmt).all())


def get_time_off(db: Session, time_off_id: UUID) -> DoctorTimeOff | None:
    stmt = select(DoctorTimeOff).where(DoctorTimeOff.id == time_off_id)
    return db.scalars(stmt).first()


def create_time_off(
    db: Session,
    *,
    doctor_id: UUID,
    off_date: date,
    start_time: time | None,
    end_time: time | None,
    tenant_id: UUID,
) -> DoctorTimeOff:
    row = DoctorTimeOff(
        doctor_id=doctor_id,
        off_date=off_date,
        start_time=start_time,
        end_time=end_time,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)
    return row


def update_time_off_row(
    db: Session,
    row: DoctorTimeOff,
    *,
    off_date: date,
    start_time: time | None,
    end_time: time | None,
) -> DoctorTimeOff:
    row.off_date = off_date
    row.start_time = start_time
    row.end_time = end_time
    db.add(row)
    db.flush()
    db.refresh(row)
    schedule_invalidate_doctor_slot_cache_on_commit(db, row.doctor_id)
    return row


def delete_time_off(db: Session, row: DoctorTimeOff) -> None:
    doctor_id = row.doctor_id
    db.delete(row)
    db.flush()
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)


def _time_ranges_overlap(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    base = date(2000, 1, 1)
    ta0 = datetime.combine(base, a_start)
    ta1 = datetime.combine(base, a_end)
    tb0 = datetime.combine(base, b_start)
    tb1 = datetime.combine(base, b_end)
    return ta0 < tb1 and tb0 < ta1


def availability_overlaps_existing(
    db: Session,
    doctor_id: UUID,
    day_of_week: int,
    start_time: time,
    end_time: time,
    *,
    exclude_window_id: UUID | None = None,
) -> bool:
    if start_time >= end_time:
        return False
    windows = list_availability_for_doctor_day(db, doctor_id, day_of_week)
    for w in windows:
        if exclude_window_id is not None and w.id == exclude_window_id:
            continue
        if _time_ranges_overlap(start_time, end_time, w.start_time, w.end_time):
            return True
    return False


def create_availability_window(
    db: Session,
    *,
    doctor_id: UUID,
    day_of_week: int,
    start_time: time,
    end_time: time,
    slot_duration: int,
    tenant_id: UUID,
) -> DoctorAvailability:
    if availability_overlaps_existing(db, doctor_id, day_of_week, start_time, end_time):
        raise ValueError("Availability window overlaps an existing window for this day")
    row = DoctorAvailability(
        doctor_id=doctor_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        slot_duration=slot_duration,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    schedule_invalidate_doctor_slot_cache_on_commit(db, doctor_id)
    return row


def update_availability_window(
    db: Session,
    window: DoctorAvailability,
    *,
    day_of_week: int | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
    slot_duration: int | None = None,
) -> DoctorAvailability:
    eff_dow = day_of_week if day_of_week is not None else window.day_of_week
    eff_start = start_time if start_time is not None else window.start_time
    eff_end = end_time if end_time is not None else window.end_time
    if eff_start >= eff_end:
        raise ValueError("Availability end time must be after start time")
    if availability_overlaps_existing(
        db,
        window.doctor_id,
        eff_dow,
        eff_start,
        eff_end,
        exclude_window_id=window.id,
    ):
        raise ValueError("Availability window overlaps an existing window for this day")
    if day_of_week is not None:
        window.day_of_week = day_of_week
    if start_time is not None:
        window.start_time = start_time
    if end_time is not None:
        window.end_time = end_time
    if slot_duration is not None:
        window.slot_duration = slot_duration
    db.add(window)
    db.flush()
    db.refresh(window)
    schedule_invalidate_doctor_slot_cache_on_commit(db, window.doctor_id)
    return window
