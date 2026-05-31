"""
Patient Medication Schedule model — adherence tracking layer.

Architecture:
  PatientMedicationSchedule is DERIVED from Prescription + PrescriptionItem.
  It is a reminder/adherence layer ONLY.
  Prescription remains the canonical source-of-truth.

  Patients CANNOT:
  - edit prescribed dosage
  - alter prescription instructions
  - overwrite doctor records

  Patient actions (taken/skipped/snooze) affect adherence tracking ONLY.
  They NEVER mutate the Prescription or PrescriptionItem rows.

Tenant isolation is enforced at the model level via tenant_id FK.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID

# ── JSON type: use portable JSON (works on PostgreSQL + SQLite) ──
# PostgreSQL JSONB is only needed in migrations for index/operator support.
# Runtime column definitions use portable JSON to keep tests working on SQLite.
JSONType = JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicationScheduleStatus(str, enum.Enum):
    """Lifecycle state of a patient medication schedule."""

    active = "active"
    completed = "completed"
    paused = "paused"


class MedicationScheduleAdherenceAction(str, enum.Enum):
    """Canonical patient adherence actions."""

    taken = "taken"
    skipped = "skipped"
    snoozed = "snoozed"


class PatientMedicationSchedule(Base):
    """
    Patient medication adherence tracking record.

    DERIVED from Prescription + PrescriptionItem — NEVER the source of truth.
    Patient actions on this model affect adherence tracking ONLY.
    Prescription data remains immutable.

    Future-ready hooks:
    # TODO: Apple Health integration — sync adherence events
    # TODO: Google Fit integration — sync adherence events
    # TODO: Wearable sync — smartwatch reminder delivery
    # TODO: Refill workflow — auto-detect low refill count
    # TODO: Recurring medications — auto-create next schedule on end_date
    # TODO: Family/dependent management — caregiver can view adherence
    # TODO: Chronic disease programs — group medications by condition
    # TODO: Multilingual reminder messages
    """

    __tablename__ = "patient_medication_schedules"

    __table_args__ = (
        Index("ix_med_schedule_patient_active", "patient_id", "is_active"),
        Index("ix_med_schedule_prescription_item", "prescription_item_id"),
        Index("ix_med_schedule_tenant", "tenant_id"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_med_schedule_date_range",
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
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prescriptions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    prescription_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prescription_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Snapshot of prescription data (read-only after creation) ──────────
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(128), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(128), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(128), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Schedule ──────────────────────────────────────────────────────────
    start_date: Mapped[date] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[date | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_times: Mapped[list | None] = mapped_column(
        JSONType,
        nullable=True,
        default=list,
        server_default="[]",
        comment="Array of HH:MM strings for reminder scheduling",
    )

    # ── Adherence tracking ────────────────────────────────────────────────
    taken_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    skipped_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_doses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Expected doses in this schedule period",
    )

    # ── State ─────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    status: Mapped[MedicationScheduleStatus] = mapped_column(
        Enum(
            MedicationScheduleStatus,
            name="medicationschedulestatus",
            native_enum=True,
        ),
        nullable=False,
        default=MedicationScheduleStatus.active,
    )

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────
    patient = relationship("Patient")
    prescription = relationship("Prescription")
    prescription_item = relationship("PrescriptionItem")
    tenant = relationship("Tenant")
    adherence_logs = relationship(
        "MedicationAdherenceLog",
        back_populates="medication_schedule",
        cascade="all, delete-orphan",
    )


class MedicationAdherenceLog(Base):
    """
    Individual adherence event log — audit trail for patient medication actions.

    Each log entry records a single patient action (taken/skipped/snoozed)
    against a medication schedule. This is the immutable audit trail.

    Future-ready hooks:
    # TODO: Apple Health integration — sync adherence events
    # TODO: Google Fit integration — sync adherence events
    # TODO: Wearable sync — smartwatch reminder delivery
    # TODO: Pharmacy integration — share adherence data with pharmacy
    # TODO: Medication stock tracking — link to inventory item
    # TODO: Pharmacy delivery — auto-order refill request
    """

    __tablename__ = "medication_adherence_logs"

    __table_args__ = (
        Index("ix_adherence_log_schedule", "medication_schedule_id"),
        Index("ix_adherence_log_patient_date", "patient_id", "actioned_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    medication_schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patient_medication_schedules.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[MedicationScheduleAdherenceAction] = mapped_column(
        Enum(
            MedicationScheduleAdherenceAction,
            name="medicationscheduleadherenceaction",
            native_enum=True,
        ),
        nullable=False,
    )
    actioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    scheduled_time: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
        comment="Which reminder slot this corresponds to (HH:MM format)",
    )

    # ── Relationships ─────────────────────────────────────────────────────
    medication_schedule = relationship(
        "PatientMedicationSchedule", back_populates="adherence_logs"
    )
    patient = relationship("Patient")
