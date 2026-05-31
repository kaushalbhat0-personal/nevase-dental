"""
Notification Domain Models — Phase 3D Communication Infrastructure.

Architecture:
  Notifications are DERIVED EVENTS.
  Source-of-truth remains: appointments, encounters, bills, prescriptions.

  NotificationEvent  →  NotificationDelivery (1:N)
       │
       └── CommunicationTemplate (tenant-scoped)

Tenant isolation is enforced at the model level via tenant_id FK.
All PHI/medical information is protected through tenant scoping.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
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


class NotificationEventType(str, enum.Enum):
    """Canonical event types — source-of-truth remains in core domain models."""

    appointment_booked = "appointment_booked"
    appointment_reminder = "appointment_reminder"
    appointment_completed = "appointment_completed"
    prescription_ready = "prescription_ready"
    bill_generated = "bill_generated"
    payment_received = "payment_received"
    follow_up_reminder = "follow_up_reminder"


class NotificationChannel(str, enum.Enum):
    """Multi-channel delivery support — future-safe for additional channels."""

    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"
    in_app = "in_app"


class NotificationDeliveryStatus(str, enum.Enum):
    """Delivery lifecycle — supports retry and read tracking."""

    pending = "pending"
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"


class NotificationEvent(Base):
    """
    Canonical notification event record.

    Events are created by business services (appointment, billing, etc.)
    and consumed by the notification service for multi-channel delivery.

    TODO: Phase 4 — Queue worker integration (Celery / RQ / AWS SQS)
    TODO: Phase 5 — HIPAA/GDPR retention policies for event logs
    """

    __tablename__ = "notification_events"

    __table_args__ = (
        Index("ix_notification_events_tenant_created", "tenant_id", "created_at"),
        Index("ix_notification_events_patient", "patient_id"),
        Index("ix_notification_events_type_created", "event_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[NotificationEventType] = mapped_column(
        Enum(NotificationEventType, name="notificationeventtype", native_enum=True),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="SET NULL"),
        nullable=True,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    bill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billings.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Structured payload — contains reference data, NOT full PHI.
    # PHI is resolved at template rendering time from source-of-truth models.
    payload: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

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

    # Relationships
    deliveries = relationship(
        "NotificationDelivery",
        back_populates="event",
        cascade="all, delete-orphan",
    )


class NotificationDelivery(Base):
    """
    Per-channel delivery tracking for a notification event.

    Each NotificationEvent can have multiple NotificationDelivery records
    (one per channel: email, SMS, WhatsApp, in-app).

    TODO: Phase 4 — Retry with exponential backoff
    TODO: Phase 4 — Delivery webhook callbacks from providers
    TODO: Phase 5 — Bounce / spam / open rate tracking
    """

    __tablename__ = "notification_deliveries"

    __table_args__ = (
        Index("ix_notification_delivery_status", "status"),
        Index("ix_notification_delivery_event", "notification_event_id"),
        Index("ix_notification_delivery_retry", "next_retry_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    notification_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notificationchannel", native_enum=True),
        nullable=False,
    )
    status: Mapped[NotificationDeliveryStatus] = mapped_column(
        Enum(
            NotificationDeliveryStatus,
            name="notificationdeliverystatus",
            native_enum=True,
        ),
        nullable=False,
        default=NotificationDeliveryStatus.pending,
    )
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    provider_response: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    event = relationship("NotificationEvent", back_populates="deliveries")


class CommunicationTemplate(Base):
    """
    Tenant-scoped communication templates.

    Templates define the subject and body for each event type × channel combination.
    Supports placeholders like {{patient_name}}, {{doctor_name}}, {{appointment_time}}.

    When tenant_id is NULL, the template is a system default.
    Tenants can override by creating their own template with the same template_type + channel.

    TODO: Phase 5 — Multilingual template rendering (locale-aware)
    TODO: Phase 5 — Patient communication preferences / consent management
    TODO: Phase 5 — Opt-out / unsubscribe handling
    """

    __tablename__ = "communication_templates"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "template_type",
            "channel",
            "locale",
            name="uq_template_tenant_type_channel_locale",
        ),
        Index("ix_communication_templates_tenant", "tenant_id"),
        Index("ix_communication_templates_type", "template_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )
    template_type: Mapped[NotificationEventType] = mapped_column(
        Enum(NotificationEventType, name="notificationeventtype", native_enum=True),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notificationchannel", native_enum=True),
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        server_default="en",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
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
