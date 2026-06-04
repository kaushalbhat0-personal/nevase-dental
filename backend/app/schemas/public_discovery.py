from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PublicTenantDoctorBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    specialization: str
    availability_status: str = "none"
    next_available_slot: str | None = None
    available_today: bool = False
    rating_average: float = 4.8
    review_count: int = 124
    distance_km: float = 0.0
    slots_today_count: int | None = None
    slots_tomorrow_count: int | None = None
    metrics_are_synthetic: bool = True


class PublicTenantDiscovery(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    doctor_count: int = 0
    type: str
    organization_label: str = "Clinic/Hospital"
    sole_doctor: PublicTenantDoctorBrief | None = None


class PublicDoctorProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    specialization: str
    experience: int
    qualification: str | None = None
    clinic_name: str | None = None
    address: str | None = None
    city: str | None = None
    profile_image: str | None = None
    verified: bool = False
    verification_status: str = "draft"
    timezone: str = "Asia/Kolkata"
    has_availability_windows: bool = False
    next_available_slot: str | None = None
    available_today: bool = False
    rating_average: float = 4.8
    review_count: int = 124
    distance_km: float = 0.0
    slots_today_count: int | None = None
    slots_tomorrow_count: int | None = None
    metrics_are_synthetic: bool = True
