from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis import redis_delete, redis_delete_pattern, redis_get, redis_set
from app.crud import crud_appointment, crud_doctor_availability
from app.models.doctor import Doctor
from app.models.doctor_availability import DoctorAvailability, DoctorTimeOff
from app.models.user import User
from app.schemas.doctor import DoctorSlotRead
from app.services import doctor_service
from app.services.exceptions import ValidationError
from app.utils.appointment_datetime import normalize_appointment_time_utc

logger = logging.getLogger(__name__)

_SLOTS_CACHE_TTL_SEC = 60


def _zoneinfo_or_utc(name: str, *, context: str) -> ZoneInfo:
    """Resolve IANA zone; fall back to UTC if missing or invalid (e.g. minimal images without tzdata)."""
    label = (name or "UTC").strip() or "UTC"
    try:
        return ZoneInfo(label)
    except (ZoneInfoNotFoundError, OSError) as e:
        logger.warning("ZoneInfo failed for %r (%s); using UTC: %s", label, context, e)
        try:
            return ZoneInfo("UTC")
        except (ZoneInfoNotFoundError, OSError) as e2:
            raise RuntimeError(
                "IANA time zone data unavailable; install the tzdata package."
            ) from e2


def _doctor_zoneinfo(doctor: Doctor) -> ZoneInfo:
    tz_name = (doctor.timezone or "UTC").strip() or "UTC"
    return _zoneinfo_or_utc(tz_name, context=f"doctor_id={doctor.id}")


def _utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _slot_compare_key(dt: datetime) -> datetime:
    return normalize_appointment_time_utc(dt)


def _local_day_bounds_utc(doctor_tz: ZoneInfo, target_date: date) -> tuple[datetime, datetime]:
    """UTC instants covering [00:00, next day) for target_date in doctor_tz."""
    day_start_local = datetime.combine(target_date, time(0, 0), tzinfo=doctor_tz)
    day_end_local = day_start_local + timedelta(days=1)
    return day_start_local.astimezone(timezone.utc), day_end_local.astimezone(timezone.utc)


def _safe_combine_local(doctor_tz: ZoneInfo, target_date: date, t: time) -> datetime | None:
    """Wall-clock local instant; None if the clock time does not exist on that calendar day (DST gap)."""
    try:
        return datetime.combine(target_date, t.replace(tzinfo=None), tzinfo=doctor_tz)
    except (ValueError, OverflowError, OSError):
        return None


def _utc_round_trip_consistent_with_local_wall(cur: datetime, doctor_tz: ZoneInfo, target_date: date) -> bool:
    """True if this UTC instant's local wall clock re-resolves to the same UTC (DST-safe, fold-safe)."""
    if cur.tzinfo is None:
        cur = cur.replace(tzinfo=timezone.utc)
    loc = cur.astimezone(doctor_tz)
    if loc.date() != target_date:
        return False
    try:
        reb = datetime(
            loc.year,
            loc.month,
            loc.day,
            loc.hour,
            loc.minute,
            loc.second,
            loc.microsecond,
            tzinfo=doctor_tz,
            fold=getattr(loc, "fold", 0),
        )
    except (ValueError, OverflowError, OSError):
        return False
    return _slot_compare_key(reb) == _slot_compare_key(cur)


def _iter_slot_starts_utc(
    target_date: date,
    start_t: time,
    end_t: time,
    slot_minutes: int,
    doctor_tz: ZoneInfo,
) -> Iterator[datetime]:
    window_start = _safe_combine_local(doctor_tz, target_date, start_t)
    window_end = _safe_combine_local(doctor_tz, target_date, end_t)
    if window_start is None or window_end is None:
        logger.debug(
            "Skipping availability window with nonexistent local boundary on %s in %s",
            target_date,
            getattr(doctor_tz, "key", doctor_tz),
        )
        return
    if slot_minutes <= 0 or window_start >= window_end:
        return
    if not _utc_round_trip_consistent_with_local_wall(window_start, doctor_tz, target_date):
        return
    step = timedelta(minutes=slot_minutes)
    cur = window_start
    while cur < window_end:
        slot_end = cur + step
        if slot_end > window_end:
            break
        if not _utc_round_trip_consistent_with_local_wall(cur, doctor_tz, target_date):
            cur += step
            continue
        yield _slot_compare_key(cur)
        cur += step


def _time_off_blocks_full_day(rows: list[DoctorTimeOff]) -> bool:
    for row in rows:
        st = getattr(row, "start_time", None)
        et = getattr(row, "end_time", None)
        if st is None and et is None:
            return True
        if (st is None) ^ (et is None):
            return True
    return False


def _partial_time_off_local_ranges(rows: list[DoctorTimeOff]) -> list[tuple[time, time]]:
    out: list[tuple[time, time]] = []
    for row in rows:
        st = getattr(row, "start_time", None)
        et = getattr(row, "end_time", None)
        if st is not None and et is not None:
            st_n = st.replace(second=0, microsecond=0)
            et_n = et.replace(second=0, microsecond=0)
            if st_n >= et_n:
                continue
            out.append((st_n, et_n))
    return out


def _merge_sorted_time_ranges(ranges: list[tuple[time, time]]) -> list[tuple[time, time]]:
    if not ranges:
        return []
    ranges = sorted(ranges, key=lambda x: (x[0], x[1]))
    merged: list[tuple[time, time]] = [ranges[0]]
    for s, e in ranges[1:]:
        ps, pe = merged[-1]
        if s <= pe:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged


def _clip_partial_ranges_to_availability(
    partial_ranges: list[tuple[time, time]],
    windows: list[DoctorAvailability],
) -> list[tuple[time, time]]:
    """Intersect partial time-off with availability windows so odd ranges cannot produce inconsistent blocking."""
    clipped: list[tuple[time, time]] = []
    for a, b in partial_ranges:
        for w in windows:
            ws = w.start_time.replace(second=0, microsecond=0)
            we = w.end_time.replace(second=0, microsecond=0)
            if ws >= we:
                continue
            lo = max(a, ws)
            hi = min(b, we)
            if lo < hi:
                clipped.append((lo, hi))
    return _merge_sorted_time_ranges(clipped)


def _slot_overlaps_partial_time_off(
    slot_start_utc: datetime,
    slot_minutes: int,
    target_date: date,
    doctor_tz: ZoneInfo,
    partial_ranges: list[tuple[time, time]],
) -> bool:
    """True if [slot_start, slot_start+duration) overlaps any partial time-off interval in local time."""
    if not partial_ranges:
        return False
    if slot_start_utc.tzinfo is None:
        slot_start_utc = slot_start_utc.replace(tzinfo=timezone.utc)
    slot_start_local = slot_start_utc.astimezone(doctor_tz)
    if slot_start_local.date() != target_date:
        return False
    slot_end_local = slot_start_local + timedelta(minutes=slot_minutes)
    for a, b in partial_ranges:
        off_a = _safe_combine_local(doctor_tz, target_date, a)
        off_b = _safe_combine_local(doctor_tz, target_date, b)
        if off_a is None or off_b is None or off_a >= off_b:
            continue
        if slot_start_local < off_b and off_a < slot_end_local:
            return True
    return False


def _compute_slots(
    db: Session,
    doctor: Doctor,
    target_date: date,
) -> list[DoctorSlotRead]:
    doctor_tz = _doctor_zoneinfo(doctor)
    time_off_rows = crud_doctor_availability.list_time_off_for_doctor_on_date(db, doctor.id, target_date)
    if _time_off_blocks_full_day(time_off_rows):
        return []

    partial_ranges = _partial_time_off_local_ranges(time_off_rows)

    dow = target_date.weekday()
    windows = crud_doctor_availability.list_availability_for_doctor_day(db, doctor.id, dow)
    if not windows:
        return []

    if settings.DOCTOR_SLOT_CLIP_PARTIAL_TIME_OFF_TO_AVAILABILITY and partial_ranges:
        partial_ranges = _clip_partial_ranges_to_availability(partial_ranges, windows)
    partial_ranges = _merge_sorted_time_ranges(partial_ranges)

    day_start_utc, day_end_utc = _local_day_bounds_utc(doctor_tz, target_date)
    busy = crud_appointment.list_doctor_busy_slot_starts_for_day(db, doctor.id, day_start_utc, day_end_utc)

    slots: list[DoctorSlotRead] = []
    for w in windows:
        dur = w.slot_duration
        for start_dt in _iter_slot_starts_utc(target_date, w.start_time, w.end_time, dur, doctor_tz):
            if _slot_overlaps_partial_time_off(start_dt, dur, target_date, doctor_tz, partial_ranges):
                continue
            slots.append(
                DoctorSlotRead(
                    start=start_dt,
                    available=start_dt not in busy,
                    duration_minutes=dur,
                )
            )

    slots.sort(key=lambda s: s.start)
    now_utc = datetime.now(timezone.utc)
    # Booking UX: only expose future slot starts (past intervals are not bookable).
    slots = [s for s in slots if _utc_naive(s.start) > now_utc]
    return slots


def _get_cached_slots_for_doctor_date(
    db: Session,
    doctor: Doctor,
    target_date: date,
) -> list[DoctorSlotRead]:
    if not settings.DOCTOR_SLOT_CACHE_ENABLED:
        return _compute_slots(db, doctor, target_date)

    key = f"slots:{doctor.id}:{target_date.isoformat()}"
    cached = redis_get(key)
    if cached is not None:
        return [DoctorSlotRead.model_validate(x) for x in cached]

    slots = _compute_slots(db, doctor, target_date)
    redis_set(key, [s.model_dump(mode="json") for s in slots], ttl=_SLOTS_CACHE_TTL_SEC)
    return slots


def get_doctor_slots_for_date(
    db: Session,
    doctor_id: UUID,
    target_date: date,
    current_user: User | None,
    tenant_id: UUID | None,
) -> list[DoctorSlotRead]:
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    doctor_service.authorize_doctor_read_for_slots(db, doctor, current_user, tenant_id)
    return _get_cached_slots_for_doctor_date(db, doctor, target_date)


def get_doctor_day_meta(
    db: Session,
    doctor_id: UUID,
    target_date: date,
    current_user: User | None,
    tenant_id: UUID | None,
) -> bool:
    """True if the doctor has whole-day time off on target_date (no slots for that reason)."""
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    doctor_service.authorize_doctor_read_for_slots(db, doctor, current_user, tenant_id)
    time_off_rows = crud_doctor_availability.list_time_off_for_doctor_on_date(db, doctor.id, target_date)
    return _time_off_blocks_full_day(time_off_rows)


def _next_available_from_doctor(
    db: Session,
    doctor: Doctor,
    from_date: date,
    *,
    horizon_days: int = 14,
) -> DoctorSlotRead | None:
    """Next bookable future slot; caller must have loaded *doctor* and checked authorization."""
    doctor_tz = _doctor_zoneinfo(doctor)
    today_local = datetime.now(doctor_tz).date()
    start_d = from_date if from_date >= today_local else today_local
    now_utc = datetime.now(timezone.utc)
    for offset in range(horizon_days):
        d = start_d + timedelta(days=offset)
        slots = _get_cached_slots_for_doctor_date(db, doctor, d)
        for s in slots:
            if not s.available:
                continue
            st = _utc_naive(s.start)
            if st <= now_utc:
                continue
            return s
    return None


def get_next_available_slot_for_doctor(
    db: Session,
    doctor_id: UUID,
    from_date: date,
    current_user: User | None,
    tenant_id: UUID | None,
    *,
    horizon_days: int = 14,
) -> DoctorSlotRead | None:
    """First available future slot from from_date (inclusive), within horizon_days, in doctor local calendar."""
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    doctor_service.authorize_doctor_read_for_slots(db, doctor, current_user, tenant_id)
    return _next_available_from_doctor(
        db, doctor, from_date, horizon_days=horizon_days
    )


def get_doctor_schedule_day(
    db: Session,
    doctor_id: UUID,
    target_date: date,
    current_user: User | None,
    tenant_id: UUID | None,
    *,
    next_from: date | None = None,
    horizon_days: int = 14,
) -> tuple[list[DoctorSlotRead], bool, DoctorSlotRead | None]:
    """
    One round-trip: slots for *target_date*, full-day time-off flag, and next available from *next_from*
    (or today in the doctor's timezone when *next_from* is None).
    """
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    doctor_service.authorize_doctor_read_for_slots(db, doctor, current_user, tenant_id)
    slots = _get_cached_slots_for_doctor_date(db, doctor, target_date)
    time_off_rows = crud_doctor_availability.list_time_off_for_doctor_on_date(
        db, doctor.id, target_date
    )
    full_day = _time_off_blocks_full_day(time_off_rows)
    scan_from = next_from
    if scan_from is None:
        scan_from = datetime.now(_doctor_zoneinfo(doctor)).date()
    next_s = _next_available_from_doctor(
        db, doctor, scan_from, horizon_days=horizon_days
    )
    return slots, full_day, next_s


def invalidate_slots_cache_for_doctor_date(doctor_id: UUID, target_date: date) -> None:
    if not settings.DOCTOR_SLOT_CACHE_ENABLED:
        return
    key = f"slots:{doctor_id}:{target_date.isoformat()}"
    redis_delete(key)


def invalidate_all_slots_cache_for_doctor(doctor_id: UUID) -> None:
    """Remove all slot list keys for this doctor: ``slots:{doctor_id}:*``."""
    if not settings.DOCTOR_SLOT_CACHE_ENABLED:
        return
    pattern = f"slots:{doctor_id}:*"
    redis_delete_pattern(pattern)


def invalidate_slots_cache_for_appointment(db: Session, doctor: Doctor, appointment_time_utc: datetime) -> None:
    doctor_tz = _doctor_zoneinfo(doctor)
    at = _utc_naive(appointment_time_utc)
    local_d = at.astimezone(doctor_tz).date()
    invalidate_slots_cache_for_doctor_date(doctor.id, local_d)


def collect_allowed_slot_starts_utc_for_booking(
    db: Session,
    doctor: Doctor,
    appointment_time_utc: datetime,
) -> set[datetime]:
    """Slot starts (UTC, tz-aware) that match doctor schedule for the local calendar day of the appointment."""
    doctor_tz = _doctor_zoneinfo(doctor)
    at = _utc_naive(appointment_time_utc)
    target_date = at.astimezone(doctor_tz).date()
    slots = _compute_slots(db, doctor, target_date)
    return {_slot_compare_key(s.start) for s in slots}


def assert_appointment_time_matches_doctor_slots(
    db: Session,
    doctor: Doctor,
    appointment_time_utc: datetime,
) -> None:
    allowed = collect_allowed_slot_starts_utc_for_booking(db, doctor, appointment_time_utc)
    at = _slot_compare_key(appointment_time_utc)
    if at not in allowed:
        raise ValidationError("Appointment time is not within an available slot for this doctor")


def compute_doctor_availability_status_for_list(db: Session, doctor: Doctor) -> str:
    """
    Lightweight booking hint for list cards (no auth — caller must only use for already-visible doctors).

    Returns:
        available_today — at least one bookable slot later today (doctor-local calendar).
        next_available_tomorrow — no slot today; next bookable slot falls on tomorrow (local).
        none — otherwise (no windows, fully booked horizon, or next opening after tomorrow).
    """
    doctor_tz = _doctor_zoneinfo(doctor)
    today_local = datetime.now(doctor_tz).date()
    now_utc = datetime.now(timezone.utc)
    slots = _get_cached_slots_for_doctor_date(db, doctor, today_local)
    if any(s.available and _utc_naive(s.start) > now_utc for s in slots):
        return "available_today"
    tomorrow_local = today_local + timedelta(days=1)
    next_s = _next_available_from_doctor(db, doctor, today_local, horizon_days=14)
    if next_s is None:
        return "none"
    next_local_date = _utc_naive(next_s.start).astimezone(doctor_tz).date()
    if next_local_date == tomorrow_local:
        return "next_available_tomorrow"
    return "none"


def compute_public_marketplace_slot_meta(
    db: Session,
    doctor: Doctor,
) -> tuple[datetime | None, bool, str]:
    """
    Slot hints for public discovery (approved doctors only — no auth).

    Returns (next_bookable_start_utc, available_today, availability_status).
    """
    st = compute_doctor_availability_status_for_list(db, doctor)
    doctor_tz = _doctor_zoneinfo(doctor)
    today_local = datetime.now(doctor_tz).date()
    next_s = _next_available_from_doctor(db, doctor, today_local, horizon_days=14)
    next_start = _utc_naive(next_s.start) if next_s is not None else None
    available_today = st == "available_today"
    return next_start, available_today, st


def count_bookable_slots_on_local_date(
    db: Session,
    doctor: Doctor,
    local_date: date,
) -> int:
    """Bookable slot count for a doctor-local calendar day (today excludes past starts)."""
    doctor_tz = _doctor_zoneinfo(doctor)
    today_local = datetime.now(doctor_tz).date()
    now_utc = datetime.now(timezone.utc)
    slots = _get_cached_slots_for_doctor_date(db, doctor, local_date)
    if local_date < today_local:
        return 0
    if local_date > today_local:
        return sum(1 for s in slots if s.available)
    return sum(1 for s in slots if s.available and _utc_naive(s.start) > now_utc)


def public_marketplace_slots_today_tomorrow_counts(
    db: Session,
    doctor: Doctor,
) -> tuple[int, int]:
    """(slots_today_count, slots_tomorrow_count) for list/profile cards."""
    doctor_tz = _doctor_zoneinfo(doctor)
    today_local = datetime.now(doctor_tz).date()
    tomorrow_local = today_local + timedelta(days=1)
    return (
        count_bookable_slots_on_local_date(db, doctor, today_local),
        count_bookable_slots_on_local_date(db, doctor, tomorrow_local),
    )
