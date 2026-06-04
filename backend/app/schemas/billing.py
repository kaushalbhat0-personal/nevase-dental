from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.billing import BillingStatus
from app.schemas.patient import PatientRead


def _parse_date(v: str | datetime | None) -> datetime | None:
    """Parse date from string (YYYY-MM-DD, DD-MM-YYYY) or datetime object."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        v = v.strip()
        # Handle YYYY-MM-DD format from frontend date input
        if len(v) == 10 and v[4] == '-' and v[7] == '-':
            return datetime.strptime(v, "%Y-%m-%d")
        # Handle DD-MM-YYYY format (e.g., "20-04-2026")
        if len(v) == 10 and v[2] == '-' and v[5] == '-':
            return datetime.strptime(v, "%d-%m-%Y")
        # Try ISO format
        try:
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            pass
    return None


class BillingCreate(BaseModel):
    patient_id: UUID
    appointment_id: UUID | None = None
    amount: Decimal = Field(..., ge=Decimal("0.00"))
    status: BillingStatus = BillingStatus.unpaid
    currency: str = "INR"
    idempotency_key: str | None = None
    description: str | None = None
    due_date: datetime | str | None = None
    include_appointment_inventory_selling_total: bool = Field(
        False,
        description=(
            "When true and appointment_id is set, adds sum(qty × item selling_price) "
            "from visit inventory usage to amount and lists per-line medicines in description."
        ),
    )

    @field_validator("due_date", mode="before")
    @classmethod
    def parse_due_date(cls, v: str | datetime | None) -> datetime | None:
        return _parse_date(v)

    @field_validator("appointment_id")
    @classmethod
    def validate_appointment_id(cls, v: UUID | None) -> UUID | None:
        # Allow null for now - service layer handles validation
        return v


class BillingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    amount: Decimal
    status: BillingStatus
    description: str | None
    due_date: datetime | None
    paid_at: datetime | None
    payment_id: str | None
    payment_method: str | None
    currency: str
    idempotency_key: str | None
    is_deleted: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    patient: PatientRead | None = None


class BillingUpdate(BaseModel):
    patient_id: UUID | None = None
    appointment_id: UUID | None = None
    amount: Decimal | None = Field(None, ge=Decimal("0.00"))
    status: BillingStatus | None = None
    paid_at: datetime | None = None
    payment_id: str | None = None
    payment_method: str | None = None
    currency: str | None = None
    idempotency_key: str | None = None
    is_deleted: bool | None = None


class BillingEventCreate(BaseModel):
    billing_id: UUID
    previous_status: str | None = None
    new_status: str
    event_type: str
    event_metadata: str | None = None


class BillingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    billing_id: UUID
    previous_status: str | None
    new_status: str
    event_type: str
    event_metadata: str | None
    created_by: UUID | None
    created_at: datetime
