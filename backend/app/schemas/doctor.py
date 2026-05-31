from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class DoctorCreate(BaseModel):
    name: str
    specialization: str
    experience_years: int
    timezone: str | None = Field(
        default=None,
        description="IANA timezone for availability and slots; defaults to Asia/Kolkata (IST)",
    )
    account_email: EmailStr | None = Field(
        default=None,
        description="Required with account_password when an administrator creates a doctor under a tenant",
    )
    account_password: str | None = Field(
        default=None,
        description="Login password for the new doctor user (admin/super_admin tenant-scoped creation only); min 8 chars when set",
    )


class DoctorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None = Field(
        default=None,
        description="Linked login user id; required to promote doctor to admin",
    )
    name: str
    specialization: str
    experience_years: int
    tenant_id: UUID | None = None
    tenant_type: str | None = None
    tenant_organization_label: str | None = Field(
        default=None,
        description='Derived from active doctors in the tenant: "Clinic/Hospital" or '
        '"Individual Doctor". Complements raw tenant_type.',
    )
    tenant_name: str | None = None
    created_at: datetime
    timezone: str = Field(
        default="Asia/Kolkata",
        description="IANA timezone for availability windows and slot dates (wall-clock times are in this zone)",
    )
    has_availability_windows: bool = Field(
        default=False,
        description="True if this doctor has at least one recurring availability window configured",
    )
    linked_user_email: str | None = Field(
        default=None,
        description="Email of the linked login user when user_id is set",
    )
    linked_user_role: str | None = Field(
        default=None,
        description="Role of the linked login user (e.g. admin, doctor) for UI badges",
    )
    availability_status: str | None = Field(
        default=None,
        description="When requested: available_today | next_available_tomorrow | none",
    )
    verification_status: str | None = Field(
        default=None,
        description="Marketplace verification on structured profile: draft | pending | approved | rejected",
    )
    verified: bool = Field(
        default=False,
        description="True when marketplace verification status is approved (badge-friendly).",
    )


class DoctorUpdate(BaseModel):
    name: str | None = None
    specialization: str | None = None
    experience_years: int | None = None
    timezone: str | None = Field(
        default=None,
        description="IANA timezone for availability and slots (e.g. Asia/Kolkata)",
    )


class DoctorSlotRead(BaseModel):
    """One bookable slot start time for a doctor on a given calendar day (UTC)."""

    model_config = ConfigDict(from_attributes=False)

    start: datetime = Field(description="Slot start in UTC")
    available: bool = Field(description="False if an active appointment already occupies this start time")
    duration_minutes: int = Field(
        gt=0,
        description="Length of the slot in minutes (from the doctor's availability window slot_duration).",
    )


class DoctorDayMeta(BaseModel):
    """Per-day hints for the schedule UI (independent of generated slot rows)."""

    full_day_time_off: bool = Field(
        description="True when time off blocks the entire calendar day (no slots will be offered).",
    )


class DoctorScheduleDayRead(BaseModel):
    """Slots, day-level time-off hint, and next bookable slot in one response."""

    slots: list[DoctorSlotRead]
    full_day_time_off: bool
    next_available: DoctorSlotRead | None = None


class DoctorAvailabilityCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="Monday=0 .. Sunday=6")
    start_time: time
    end_time: time
    slot_duration: int = Field(gt=0, description="Slot length in minutes")


class DoctorAvailabilityUpdate(BaseModel):
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    slot_duration: int | None = Field(default=None, gt=0)


class DoctorAvailabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    doctor_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration: int
    tenant_id: UUID
    created_at: datetime


class DoctorAvailabilityCopyRequest(BaseModel):
    """Copy all availability windows from ``source_day`` onto each listed ``target_days`` (source day is ignored)."""

    source_day: int = Field(ge=0, le=6, description="Monday=0 .. Sunday=6")
    target_days: list[int] = Field(
        min_length=1,
        description="Weekdays to overwrite; values 0..6; same as source_day are skipped",
    )

    @model_validator(mode="after")
    def _validate_target_days(self) -> DoctorAvailabilityCopyRequest:
        for d in self.target_days:
            if not 0 <= d <= 6:
                raise ValueError("Each target day must be between 0 and 6")
        return self


class DoctorTimeOffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    doctor_id: UUID
    off_date: date
    start_time: time | None
    end_time: time | None
    tenant_id: UUID
    created_at: datetime


class DoctorTimeOffCreate(BaseModel):
    off_date: date
    start_time: time | None = None
    end_time: time | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> "DoctorTimeOffCreate":
        st, et = self.start_time, self.end_time
        if (st is None) ^ (et is None):
            raise ValueError("For partial time off, set both start and end; for a full day off, leave both empty.")
        if st is not None and et is not None and st >= et:
            raise ValueError("End time must be after start time for partial time off.")
        return self


class DoctorTimeOffUpdate(BaseModel):
    """Unsent fields are left unchanged. Service merges and validates the resulting range."""

    off_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
