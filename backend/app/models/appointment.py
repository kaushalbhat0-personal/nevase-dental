import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, desc, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    arrived = "arrived"
    checked_in = "checked_in"
    vitals_completed = "vitals_completed"
    waiting_for_doctor = "waiting_for_doctor"
    in_consultation = "in_consultation"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class Appointment(Base):
    __tablename__ = "appointments"

    __table_args__ = (
        Index("idx_user_doctor_time", "created_by", "doctor_id", "appointment_time"),
        Index(
            "idx_appointments_patient_tenant",
            "patient_id",
            "tenant_id",
        ),
        Index(
            "ix_appointments_tenant_patient_created",
            "tenant_id",
            "patient_id",
            desc("created_at"),
            postgresql_where=text("is_deleted = false"),
        ),
        # Same-doctor/same-time uniqueness for active visits (~scheduled/completed):
        # Postgres predicates omit cancelled rows so reused slots after cancellation stay usable.
        Index(
            "uq_appointments_doctor_time_active",
            "doctor_id",
            "appointment_time",
            unique=True,
            postgresql_where=text("is_deleted = false AND status <> 'cancelled'::appointmentstatus"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    # Actual clinical encounter timing. These are server-generated only and
    # must not replace the scheduled appointment slot.
    encounter_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    encounter_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointmentstatus", native_enum=True),
        nullable=False,
        default=AppointmentStatus.scheduled,
    )
    # TODO: support explicit in_progress workflow and Start Encounter action.
    # TODO: use encounter_started_at/encounter_completed_at for encounter duration analytics,
    # TODO: preserve SOAP chronology, AI summary timing, telemedicine duration,
    # TODO: and clinic wait-time metrics.
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    # DEPRECATED: completion_notes is deprecated and should not be written to for new visits.
    # Use clinical_notes for medical encounter documentation.
    # This field is preserved for backward compatibility with existing data.
    # Operational completion metadata should be stored elsewhere if needed.
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # clinical_notes = medical observations/treatment documentation for THIS visit/encounter.
    # This is the primary field for clinical encounter documentation.
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # diagnosis = primary and differential diagnoses recorded during this visit.
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # treatment_summary = treatment provided, medications prescribed, follow-up plan.
    treatment_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SOAP notes: structured clinical documentation
    subjective_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    billing = relationship("Billing", back_populates="appointment", uselist=False)
    inventory_usages = relationship(
        "AppointmentInventoryUsage",
        back_populates="appointment",
        cascade="all, delete-orphan",
    )
    follow_up_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    follow_up_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    vitals = relationship(
        "AppointmentVitals",
        back_populates="appointment",
        uselist=False,
        cascade="all, delete-orphan",
    )
    prescriptions = relationship(
        "Prescription",
        back_populates="appointment",
        cascade="all, delete-orphan",
    )


class AppointmentCreationIdempotency(Base):
    """Stores Idempotency-Key + body hash for POST /appointments deduplication."""

    __tablename__ = "appointment_creation_idempotency"

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_appointment_idempotency_user_key"),
        Index("ix_appointment_idempotency_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AppointmentVitals(Base):
    __tablename__ = "appointment_vitals"

    __table_args__ = (
        UniqueConstraint("appointment_id", name="uq_appointment_vitals_appointment"),
        Index("ix_appointment_vitals_appointment", "appointment_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
    )
    temperature: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    bp_systolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bp_diastolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pulse: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spo2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    bmi: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    appointment = relationship("Appointment", back_populates="vitals")


class Prescription(Base):
    __tablename__ = "prescriptions"

    __table_args__ = (
        Index("ix_prescriptions_appointment", "appointment_id"),
        Index("ix_prescriptions_patient", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    appointment = relationship("Appointment", back_populates="prescriptions")
    doctor = relationship("Doctor")
    patient = relationship("Patient")
    tenant = relationship("Tenant")
    items = relationship(
        "PrescriptionItem",
        back_populates="prescription",
        cascade="all, delete-orphan",
    )


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    __table_args__ = (
        Index("ix_prescription_items_prescription", "prescription_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(128), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(128), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(128), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    prescription = relationship("Prescription", back_populates="items")


class AppointmentCompletionIdempotency(Base):
    """Idempotency-Key + body hash for POST .../mark-completed deduplication."""

    __tablename__ = "appointment_completion_idempotency"

    __table_args__ = (
        UniqueConstraint(
            "appointment_id",
            "idempotency_key",
            name="uq_completion_idempotency",
        ),
        Index("ix_appt_completion_idempotency_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    #: SHA256 of canonical JSON `{appointment_id, status, billing_id}` after successful completion.
    result_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    billing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billings.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
