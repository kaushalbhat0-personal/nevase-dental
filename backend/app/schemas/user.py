import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.user import UserRole
from app.schemas.doctor import DoctorCreate
from app.schemas.patient import PatientCreate


class SignupType(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"
    hospital = "hospital"


class UserCreate(BaseModel):
    email: str
    password: str
    role: UserRole | None = None
    """Required unless ``signup_type`` is ``hospital`` (backend uses ``admin``)."""
    doctor_profile: DoctorCreate | None = None
    patient_profile: PatientCreate | None = None
    signup_type: SignupType | None = None
    """Defaults from ``role`` for older clients. Use ``hospital`` for org signup."""
    organization_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Clinic or hospital name; required for signup_type=hospital",
    )

    @model_validator(mode="after")
    def validate_signup_payload(self) -> "UserCreate":
        st = self.signup_type
        if st is None:
            if self.role is None:
                raise ValueError("role or signup_type is required")
            if self.role == UserRole.patient:
                st = SignupType.patient
            elif self.role == UserRole.doctor:
                st = SignupType.doctor
            else:
                raise ValueError("signup_type is required (or use role patient|doctor for legacy)")

        if st == SignupType.patient:
            if self.patient_profile is None:
                raise ValueError("patient_profile is required for patient signup")
            return self.model_copy(update={"signup_type": st, "role": UserRole.patient})
        if st == SignupType.doctor:
            if self.doctor_profile is None:
                raise ValueError("doctor_profile is required for individual doctor signup")
            return self.model_copy(update={"signup_type": st, "role": UserRole.doctor})
        if st == SignupType.hospital:
            org = (self.organization_name or "").strip()
            if not org:
                raise ValueError("organization_name is required for hospital signup")
            if self.doctor_profile is None:
                raise ValueError("doctor_profile (owner) is required for hospital signup")
            return self.model_copy(
                update={
                    "signup_type": st,
                    "role": UserRole.admin,
                    "organization_name": org,
                }
            )
        raise ValueError("invalid signup_type")


class OrganizationUserCreate(BaseModel):
    """Super-admin provisioning: tenant-bound admin or staff account."""

    name: str | None = Field(
        default=None,
        max_length=200,
        description="Display label in UI only; not stored until User supports full name",
    )
    email: str
    password: str = Field(min_length=8)
    role: UserRole
    tenant_id: UUID

    @field_validator("role")
    @classmethod
    def role_must_be_org_staff(cls, v: UserRole) -> UserRole:
        if v not in (UserRole.admin, UserRole.staff):
            raise ValueError("role must be admin or staff")
        return v


class UserMeTenantBrief(BaseModel):
    """Tenant context for the authenticated user (GET /me); type is the UI/org-mode source of truth."""

    id: UUID
    type: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    roles: list[str] = Field(
        default_factory=list,
        description="Account role plus doctor when a doctor profile is linked to this user.",
    )
    is_active: bool
    is_owner: bool = False
    tenant_id: UUID | None = None
    doctor_id: UUID | None = Field(
        default=None,
        description="Primary doctor row when one is linked (SSOT for X-Data-Scope doctor context).",
    )
    doctor_profile_complete: bool | None = Field(
        default=None,
        description="True when `doctor_profiles` has all mandatory fields; null if not a doctor login.",
    )
    doctor_verification_status: str | None = Field(
        default=None,
        description="draft | pending | approved | rejected — marketplace verification.",
    )
    doctor_verification_rejection_reason: str | None = Field(
        default=None,
        description="When rejected, org/admin may store a reason for the clinician.",
    )
    tenant: UserMeTenantBrief | None = Field(
        default=None,
        description="Resolved from `users.tenant_id`; `type` is individual vs organization.",
    )
    created_at: datetime
    updated_at: datetime


class UserRoleUpdate(BaseModel):
    """Super-admin: promote a tenant doctor to administrator (same-tenant only)."""

    role: UserRole

    @field_validator("role")
    @classmethod
    def role_must_be_admin(cls, v: UserRole) -> UserRole:
        if v != UserRole.admin:
            raise ValueError("only admin role is supported for this endpoint")
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    roles: list[str] = Field(
        default_factory=list,
        description="Account role plus doctor when a doctor profile is linked to this user.",
    )
    is_active: bool
    is_owner: bool = False
    tenant_id: UUID | None = None
    doctor_id: UUID | None = Field(
        default=None,
        description="Linked active doctor id when a doctor roster row is attached to this user.",
    )
    doctor_profile_complete: bool | None = None
    doctor_verification_status: str | None = None
    doctor_verification_rejection_reason: str | None = None
    full_name: str = ""

    def __init__(self, **data):
        # Handle missing full_name gracefully
        if "full_name" not in data or data["full_name"] is None:
            data["full_name"] = data.get("email", "").split("@")[0]
        super().__init__(**data)
