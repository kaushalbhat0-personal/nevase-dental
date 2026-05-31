from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DoctorProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    doctor_id: UUID
    full_name: str
    specialization: str | None = None
    experience_years: int | None = None
    qualification: str | None = None
    registration_number: str | None = None
    registration_council: str | None = None
    clinic_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    profile_image: str | None = None
    is_profile_complete: bool
    verification_status: str
    verification_rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class DoctorProfileWrite(BaseModel):
    """Create or replace structured profile fields (empty strings are treated as null)."""

    full_name: str = Field(min_length=1, max_length=2000)
    phone: str | None = None
    profile_image: str | None = None
    specialization: str | None = None
    experience_years: int | None = Field(default=None, ge=0, le=80)
    qualification: str | None = None
    registration_number: str | None = None
    registration_council: str | None = None
    clinic_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None


class DoctorVerificationQueueItem(BaseModel):
    """One row for admin / super-admin review queues (GET /admin/doctor-profiles)."""

    doctor_id: UUID
    doctor_name: str
    tenant_id: UUID
    tenant_name: str
    tenant_type: str
    verification_status: str
    verification_rejection_reason: str | None = None


class DoctorVerificationQueueCounts(BaseModel):
    """Aggregate counts for the verification queue (same tenant scope as the list)."""

    pending: int
    approved: int
    rejected: int
    draft: int


class DoctorVerificationQueuePage(BaseModel):
    """Paginated queue for GET /admin/doctor-profiles."""

    items: list[DoctorVerificationQueueItem]
    total: int
    skip: int
    limit: int
    counts: DoctorVerificationQueueCounts


class DoctorProfileVerificationReview(BaseModel):
    """Admin/org: set marketplace verification on a doctor's structured profile."""

    status: str = Field(
        min_length=1,
        max_length=32,
        description="approved | pending | rejected",
    )
    reason: str | None = Field(
        default=None,
        max_length=4000,
        description="Required context when status is rejected; stored for clinician UX.",
    )


class DoctorProfileUpdate(BaseModel):
    """Partial update (same fields as write; all optional)."""

    full_name: str | None = Field(default=None, min_length=1, max_length=2000)
    phone: str | None = None
    profile_image: str | None = None
    specialization: str | None = None
    experience_years: int | None = Field(default=None, ge=0, le=80)
    qualification: str | None = None
    registration_number: str | None = None
    registration_council: str | None = None
    clinic_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
