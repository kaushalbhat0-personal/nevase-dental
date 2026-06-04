from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.appointment import AppointmentStatus
from app.schemas.inventory import InventoryUseLine
from app.utils.appointment_datetime import normalize_appointment_time_utc


class PatientMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class DoctorMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    timezone: str


class AppointmentCreate(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    appointment_time: datetime
    status: AppointmentStatus = AppointmentStatus.scheduled

    @field_validator("appointment_time")
    @classmethod
    def _normalize_appointment_time(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            return normalize_appointment_time_utc(v)
        return v.replace(second=0, microsecond=0)


class AppointmentInventoryUsageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: UUID
    quantity: int
    item_name: str = ""

    @model_validator(mode="before")
    @classmethod
    def _flatten_item_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        item = getattr(data, "item", None)
        name = getattr(item, "name", "") if item is not None else ""
        try:
            return {
                "item_id": getattr(data, "item_id"),
                "quantity": getattr(data, "quantity"),
                "item_name": name,
            }
        except AttributeError:
            return data


class VitalSignsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    temperature: float | None = None
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    pulse: int | None = None
    respiratory_rate: int | None = None
    spo2: int | None = None
    weight: float | None = None
    height: float | None = None
    bmi: float | None = None
    notes: str | None = None
    created_at: datetime | None = None


class PrescriptionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medicine_name: str
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    instructions: str | None = None


class PrescriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    appointment_id: UUID
    doctor_id: UUID
    patient_id: UUID
    tenant_id: UUID
    notes: str | None = None
    created_at: datetime
    items: list[PrescriptionItemRead] = Field(default_factory=list)


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    tenant_id: UUID
    appointment_time: datetime
    status: AppointmentStatus
    created_by: UUID
    created_at: datetime
    # DEPRECATED: completion_notes is deprecated. Use clinical_notes for visit documentation.
    # Preserved for backward compatibility with existing data.
    completion_notes: str | None = None
    # clinical_notes = medical observations/treatment for THIS visit (preferred field).
    clinical_notes: str | None = None
    # diagnosis = primary and differential diagnoses.
    diagnosis: str | None = None
    # treatment_summary = treatment provided, medications, follow-up plan.
    treatment_summary: str | None = None
    # SOAP notes: structured clinical documentation
    subjective_notes: str | None = None
    objective_notes: str | None = None
    assessment_notes: str | None = None
    plan_notes: str | None = None
    follow_up_date: datetime | None = None
    follow_up_notes: str | None = None
    encounter_started_at: datetime | None = None
    encounter_completed_at: datetime | None = None

    @field_validator("encounter_started_at", "encounter_completed_at", mode="before")
    @classmethod
    def _normalize_encounter_datetime(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    vitals: VitalSignsRead | None = None
    prescriptions: list[PrescriptionRead] = Field(default_factory=list)

    patient: PatientMini
    doctor: DoctorMini
    inventory_usages: list[AppointmentInventoryUsageRead] = Field(default_factory=list)
    inventory_materials_selling_total: Decimal | None = Field(
        default=None,
        description="Σ quantity × item selling_price for recorded usage (matches billing materials addon).",
    )


class PrescriptionItemCreate(BaseModel):
    medicine_name: str = Field(..., min_length=1, max_length=255)
    dosage: str | None = Field(None, max_length=128)
    frequency: str | None = Field(None, max_length=128)
    duration: str | None = Field(None, max_length=128)
    instructions: str | None = Field(None, max_length=5_000)


class PrescriptionCreate(BaseModel):
    notes: str | None = Field(None, max_length=10_000)
    items: list[PrescriptionItemCreate] = Field(default_factory=list)


class VitalSignsCreate(BaseModel):
    temperature: float | None = Field(None, ge=25, le=110)
    bp_systolic: int | None = Field(None, ge=30, le=250)
    bp_diastolic: int | None = Field(None, ge=30, le=180)
    pulse: int | None = Field(None, ge=20, le=220)
    respiratory_rate: int | None = Field(None, ge=8, le=60)
    spo2: int | None = Field(None, ge=50, le=100)
    weight: float | None = Field(None, ge=0, le=500)
    height: float | None = Field(None, ge=30, le=250)
    bmi: float | None = Field(None, ge=10, le=70)
    notes: str | None = Field(None, max_length=10_000)


class MarkAppointmentCompletedRequest(BaseModel):
    # DEPRECATED: completion_notes is deprecated and will be ignored for new visits.
    # Use clinical_notes for visit documentation.
    # This field is preserved for backward compatibility; existing data is not migrated.
    completion_notes: str | None = Field(None, max_length=50_000)
    # clinical_notes = medical observations/treatment for THIS visit (preferred).
    clinical_notes: str | None = Field(None, max_length=50_000)
    # diagnosis = primary and differential diagnoses.
    diagnosis: str | None = Field(None, max_length=50_000)
    # treatment_summary = treatment provided, medications, follow-up plan.
    treatment_summary: str | None = Field(None, max_length=50_000)
    # SOAP notes: structured clinical documentation
    subjective_notes: str | None = Field(None, max_length=50_000)
    objective_notes: str | None = Field(None, max_length=50_000)
    assessment_notes: str | None = Field(None, max_length=50_000)
    plan_notes: str | None = Field(None, max_length=50_000)
    items: list[InventoryUseLine] = Field(default_factory=list)
    prescriptions: list[PrescriptionCreate] = Field(default_factory=list)
    vitals: VitalSignsCreate | None = None
    follow_up_date: datetime | None = None
    follow_up_notes: str | None = Field(None, max_length=10_000)
    generate_bill: bool = False
    bill_consultation_amount: Decimal = Field(
        default_factory=lambda: Decimal("0"),
        ge=0,
        description="Base consultation fee (INR) when generate_bill is true (materials are added separately).",
    )


class AppointmentUpdate(BaseModel):
    patient_id: UUID | None = None
    doctor_id: UUID | None = None
    appointment_time: datetime | None = None
    status: AppointmentStatus | None = None

    @field_validator("appointment_time")
    @classmethod
    def _normalize_appointment_time(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        if v.tzinfo is not None:
            return normalize_appointment_time_utc(v)
        return v.replace(second=0, microsecond=0)
