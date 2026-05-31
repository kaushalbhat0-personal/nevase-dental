from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    name: str
    age: int
    gender: str
    phone: str


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    age: int
    gender: str
    phone: str
    created_by: UUID
    created_at: datetime
    user_id: UUID | None = None
    clinical_notes: str | None = None


class PatientListRead(PatientRead):
    """GET /patients list item: same fields as PatientRead plus optional attending-doctor label."""

    doctor_name: str | None = None


class PatientUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    phone: str | None = None
    clinical_notes: str | None = None


class PatientMyDoctorRead(BaseModel):
    """Doctors the patient has booked (non-cancelled appointments), past or upcoming."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    specialization: str
    tenant_id: UUID
