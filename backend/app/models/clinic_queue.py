"""
ClinicQueueEntry — lightweight queue management for clinic operational flow.

This is an ADDITIVE model that does NOT alter the existing appointment/encounter
architecture. Queue entries are created alongside appointments for front desk
and nurse workflow tracking.

Queue entries are tenant-scoped and doctor-scoped for isolation.
Token numbers are sequential per doctor per calendar day.
"""

from __future__ import annotations

import enum
import json
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.core.database import Base


class JsonType(TypeDecorator):
    """Generic JSON type that works with both PostgreSQL (JSONB) and SQLite (Text)."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB

            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


class ClinicQueueStatus(str, enum.Enum):
    waiting = "waiting"
    in_room = "in_room"
    completed = "completed"
    skipped = "skipped"


class ClinicQueueEntry(Base):
    __tablename__ = "clinic_queue_entries"

    __table_args__ = (
        # Daily token uniqueness per doctor
        UniqueConstraint(
            "doctor_id",
            "queue_date",
            "token_number",
            name="uq_queue_token_daily",
        ),
        # Front desk view: tenant + status
        Index("ix_queue_tenant_status", "tenant_id", "queue_status"),
        # Doctor daily queue: doctor + date + status
        Index("ix_queue_doctor_date_status", "doctor_id", "queue_date", "queue_status"),
        # Appointment lookup
        Index("ix_queue_appointment", "appointment_id"),
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
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
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
    # The calendar date this queue entry belongs to (for daily token sequencing)
    # Uses Date type natively; SQLite stores as text, PostgreSQL as date
    queue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=func.current_date(),
    )
    # Sequential token number per doctor per day (1, 2, 3, ...)
    token_number: Mapped[int] = mapped_column(Integer, nullable=False)
    queue_status: Mapped[ClinicQueueStatus] = mapped_column(
        Enum(ClinicQueueStatus, name="clinicqueuestatus", native_enum=False, create_constraint=False),
        nullable=False,
        default=ClinicQueueStatus.waiting,
    )
    # Priority: 0=normal, 1=urgent walk-in, 2=emergency override
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Room assignment placeholder (future: room management CRUD)
    room_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Operational preparation checklist (JSON-compatible for both SQLite and PostgreSQL)
    prep_metadata: Mapped[dict | None] = mapped_column(
        JsonType,
        nullable=True,
        default=dict,
    )
    # Timing
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    appointment = relationship("Appointment")
    patient = relationship("Patient")
    doctor = relationship("Doctor")
    tenant = relationship("Tenant")
