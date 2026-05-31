from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    get_current_user,
    get_current_user_optional,
    get_optional_scoped_tenant_id,
    get_optional_scoped_tenant_id_active,
    get_optional_scoped_tenant_id_optional_user,
    get_scoped_tenant_id,
    get_scoped_tenant_id_active,
    require_current_user_admin_or_owner,
    require_doctor_verification_approved,
)
from app.core.database import get_db
from app.core.tenant_context import resolve_tenant_id_for_scoped_request
from app.crud import crud_doctor_profile
from app.models.user import User, UserRole
from app.schemas.user import UserRead
from app.schemas.doctor import (
    DoctorAvailabilityCopyRequest,
    DoctorAvailabilityCreate,
    DoctorAvailabilityRead,
    DoctorAvailabilityUpdate,
    DoctorCreate,
    DoctorDayMeta,
    DoctorRead,
    DoctorScheduleDayRead,
    DoctorSlotRead,
    DoctorTimeOffCreate,
    DoctorTimeOffRead,
    DoctorTimeOffUpdate,
    DoctorUpdate,
)
from app.services import doctor_availability_service, doctor_service, doctor_slot_service
from app.services.exceptions import ValidationError
from app.services.user_roles_service import user_read_with_roles

router = APIRouter(prefix="/doctors", tags=["doctors"])


def _radius_km_from_query(radius: str | None, *, has_coords: bool) -> float | None:
    default: float | None = 5.0 if has_coords else None
    if radius is None or radius.strip() == "":
        return default
    s = radius.strip().lower().replace(" ", "")
    if s.endswith("km"):
        s = s[:-2]
    try:
        v = float(s)
        return v if v > 0 else default
    except ValueError:
        return default


@router.post("", response_model=DoctorRead, status_code=201)
def create_doctor(
    payload: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id_active),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> DoctorRead:
    doctor = doctor_service.create_doctor(
        db,
        payload,
        tenant_id=effective_tenant_id,
        user_id=None,
        current_user=current_user,
        idempotency_key=idempotency_key,
    )
    db.commit()
    db.refresh(doctor)
    doctor_service.hydrate_doctor_availability_flags(db, [doctor])
    return doctor


@router.get("", response_model=list[DoctorRead])
def read_doctors(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1),
    available_today: bool = Query(
        default=False,
        description="Only doctors with at least one bookable slot later today (local to each doctor)",
    ),
    lat: float | None = Query(
        default=None,
        description="Patient latitude (WGS84); use with lng and optional radius for nearby filtering",
    ),
    lng: float | None = Query(
        default=None,
        description="Patient longitude (WGS84); use with lat and optional radius for nearby filtering",
    ),
    radius: str | None = Query(
        default=None,
        description='Search radius, e.g. "5" or "5km"; defaults to 5 km when lat/lng are set',
    ),
    specialization: str | None = Query(
        default=None,
        min_length=1,
        description="Filter by substring match on doctor.specialization (case-insensitive)",
    ),
    include_availability_hint: bool = Query(
        default=False,
        description="Populate availability_status on each doctor (extra slot computation per row)",
    ),
    only_verified: bool = Query(
        default=False,
        description="Only doctors with marketplace-approved structured profiles (patients always get this filter)",
    ),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-ID"),
) -> list[DoctorRead]:
    if current_user is None:
        tenant_id = None
    elif current_user.role == UserRole.patient:
        tenant_id = None
    else:
        tenant_id = resolve_tenant_id_for_scoped_request(db, current_user, x_tenant_id)
    has_coords = lat is not None and lng is not None
    if (lat is None) ^ (lng is None):
        raise ValidationError("lat and lng must be provided together")
    radius_km = _radius_km_from_query(radius, has_coords=has_coords)
    enforce_verified = only_verified or (
        current_user is not None and current_user.role == UserRole.patient
    )
    return doctor_service.get_doctors(
        db,
        current_user,
        skip=skip,
        limit=limit,
        search=search,
        tenant_id=tenant_id,
        available_today=available_today,
        latitude=lat,
        longitude=lng,
        radius_km=radius_km,
        specialization=specialization,
        include_availability_hint=include_availability_hint,
        only_marketplace_verified=enforce_verified,
    )


@router.patch("/{doctor_id}/promote", response_model=UserRead)
def promote_doctor_to_admin(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_current_user_admin_or_owner),
    tenant_id: UUID = Depends(get_scoped_tenant_id_active),
) -> UserRead:
    user = doctor_service.promote_doctor_to_admin(db, doctor_id, tenant_id)
    db.commit()
    db.refresh(user)
    return user_read_with_roles(db, user)


@router.get("/{doctor_id}/slots", response_model=list[DoctorSlotRead])
def read_doctor_slots(
    doctor_id: UUID,
    on_date: date = Query(
        ...,
        alias="date",
        description="Calendar day (YYYY-MM-DD) in the doctor's configured timezone (IANA)",
    ),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id_optional_user),
) -> list[DoctorSlotRead]:
    return doctor_slot_service.get_doctor_slots_for_date(db, doctor_id, on_date, current_user, tenant_id)


@router.get("/{doctor_id}/schedule/day", response_model=DoctorScheduleDayRead)
def read_doctor_schedule_day(
    doctor_id: UUID,
    on_date: date = Query(
        ...,
        alias="date",
        description="Calendar day (YYYY-MM-DD) in the doctor's configured timezone (IANA)",
    ),
    next_from: date | None = Query(
        default=None,
        alias="from",
        description="Start scan for next-available from this calendar day; omit to use today in the doctor's timezone",
    ),
    horizon_days: int = Query(
        default=14,
        ge=1,
        le=60,
        description="Maximum number of calendar days to scan for next available",
    ),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id_optional_user),
) -> DoctorScheduleDayRead:
    slots, full_off, next_s = doctor_slot_service.get_doctor_schedule_day(
        db,
        doctor_id,
        on_date,
        current_user,
        tenant_id,
        next_from=next_from,
        horizon_days=horizon_days,
    )
    return DoctorScheduleDayRead(
        slots=slots, full_day_time_off=full_off, next_available=next_s
    )


@router.get(
    "/{doctor_id}/availability-windows",
    response_model=list[DoctorAvailabilityRead],
)
def list_doctor_availability_windows(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
) -> list[DoctorAvailabilityRead]:
    return doctor_availability_service.list_availability_windows(
        db, doctor_id, current_user, tenant_id
    )


@router.get("/{doctor_id}/day-meta", response_model=DoctorDayMeta)
def read_doctor_day_meta(
    doctor_id: UUID,
    on_date: date = Query(
        ...,
        alias="date",
        description="Calendar day (YYYY-MM-DD) in the doctor's configured timezone (IANA)",
    ),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id_optional_user),
) -> DoctorDayMeta:
    full_day = doctor_slot_service.get_doctor_day_meta(db, doctor_id, on_date, current_user, tenant_id)
    return DoctorDayMeta(full_day_time_off=full_day)


@router.get("/{doctor_id}/next-available", response_model=DoctorSlotRead | None)
def read_doctor_next_available_slot(
    doctor_id: UUID,
    from_date: date = Query(
        ...,
        alias="from",
        description="Start scanning from this calendar day (YYYY-MM-DD) in the doctor's timezone",
    ),
    horizon_days: int = Query(
        default=14,
        ge=1,
        le=60,
        description="Maximum number of calendar days to scan from the effective start date",
    ),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id_optional_user),
) -> DoctorSlotRead | None:
    return doctor_slot_service.get_next_available_slot_for_doctor(
        db, doctor_id, from_date, current_user, tenant_id, horizon_days=horizon_days
    )


@router.post(
    "/{doctor_id}/availability-windows",
    response_model=DoctorAvailabilityRead,
    status_code=201,
)
def create_doctor_availability_window(
    doctor_id: UUID,
    payload: DoctorAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
    _verified: None = Depends(require_doctor_verification_approved),
) -> DoctorAvailabilityRead:
    try:
        row = doctor_availability_service.create_availability_window(
            db, doctor_id, payload, current_user, tenant_id
        )
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        raise


@router.post(
    "/{doctor_id}/availability-windows/copy",
    response_model=list[DoctorAvailabilityRead],
    status_code=200,
)
def copy_doctor_availability_windows(
    doctor_id: UUID,
    payload: DoctorAvailabilityCopyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
    _verified: None = Depends(require_doctor_verification_approved),
) -> list[DoctorAvailabilityRead]:
    try:
        doctor_availability_service.copy_availability_to_days(
            db, doctor_id, payload, current_user, tenant_id
        )
        db.commit()
        return doctor_availability_service.list_availability_windows(
            db, doctor_id, current_user, tenant_id
        )
    except Exception:
        db.rollback()
        raise


@router.put(
    "/{doctor_id}/availability-windows/{window_id}",
    response_model=DoctorAvailabilityRead,
)
def update_doctor_availability_window(
    doctor_id: UUID,
    window_id: UUID,
    payload: DoctorAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
) -> DoctorAvailabilityRead:
    try:
        row = doctor_availability_service.update_availability_window(
            db, doctor_id, window_id, payload, current_user, tenant_id
        )
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        raise


@router.delete(
    "/{doctor_id}/availability-windows/{window_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_doctor_availability_window(
    doctor_id: UUID,
    window_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
) -> Response:
    try:
        doctor_availability_service.delete_availability_window(
            db, doctor_id, window_id, current_user, tenant_id
        )
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception:
        db.rollback()
        raise


@router.get(
    "/{doctor_id}/time-off",
    response_model=list[DoctorTimeOffRead],
)
def list_doctor_time_off(
    doctor_id: UUID,
    from_date: date | None = Query(
        default=None,
        description="Filter entries on or after this date (inclusive)",
    ),
    to_date: date | None = Query(
        default=None,
        description="Filter entries on or before this date (inclusive)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
) -> list[DoctorTimeOffRead]:
    return doctor_availability_service.list_time_off(
        db, doctor_id, current_user, tenant_id, from_date=from_date, to_date=to_date
    )


@router.post(
    "/{doctor_id}/time-off",
    response_model=DoctorTimeOffRead,
    status_code=201,
)
def create_doctor_time_off(
    doctor_id: UUID,
    payload: DoctorTimeOffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
    _verified: None = Depends(require_doctor_verification_approved),
) -> DoctorTimeOffRead:
    try:
        row = doctor_availability_service.create_time_off(
            db, doctor_id, payload, current_user, tenant_id
        )
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        raise


@router.put(
    "/{doctor_id}/time-off/{time_off_id}",
    response_model=DoctorTimeOffRead,
)
def update_doctor_time_off(
    doctor_id: UUID,
    time_off_id: UUID,
    payload: DoctorTimeOffUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
) -> DoctorTimeOffRead:
    try:
        row = doctor_availability_service.update_time_off(
            db, doctor_id, time_off_id, payload, current_user, tenant_id
        )
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        raise


@router.delete(
    "/{doctor_id}/time-off/{time_off_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_doctor_time_off(
    doctor_id: UUID,
    time_off_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
) -> Response:
    try:
        doctor_availability_service.delete_time_off(
            db, doctor_id, time_off_id, current_user, tenant_id
        )
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception:
        db.rollback()
        raise


@router.get("/{doctor_id}", response_model=DoctorRead)
def read_doctor(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> DoctorRead:
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    doctor_service.authorize_doctor_read(db, doctor, current_user, tenant_id)
    doctor_service.hydrate_doctor_availability_flags(db, [doctor])
    prof = crud_doctor_profile.get_by_doctor_id(db, doctor.id)
    setattr(
        doctor,
        "verification_status",
        prof.verification_status if prof is not None else None,
    )
    return doctor


@router.put("/{doctor_id}", response_model=DoctorRead)
def update_doctor(
    doctor_id: UUID,
    payload: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
) -> DoctorRead:
    return doctor_service.update_doctor(db, doctor_id, payload, current_user, tenant_id)


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
) -> Response:
    doctor_service.delete_doctor(db, doctor_id, current_user, tenant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
