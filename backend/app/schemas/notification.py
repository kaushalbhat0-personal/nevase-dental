"""
Notification schemas — Pydantic models for API layer.

These define the wire format for notification events, delivery records,
communication templates, and reminder configurations.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Notification Event ──────────────────────────────────────────────────────


class NotificationEventRead(BaseModel):
    """Read model for notification events — returned to API consumers."""

    id: UUID
    event_type: str
    tenant_id: UUID
    patient_id: UUID | None = None
    doctor_id: UUID | None = None
    appointment_id: UUID | None = None
    bill_id: UUID | None = None
    payload: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationEventList(BaseModel):
    """Paginated list of notification events."""

    items: list[NotificationEventRead]
    total: int
    skip: int
    limit: int


# ── Notification Delivery ───────────────────────────────────────────────────


class NotificationDeliveryRead(BaseModel):
    """Read model for delivery records."""

    id: UUID
    notification_event_id: UUID
    channel: str
    status: str
    recipient: str
    sent_at: datetime | None = None
    failed_at: datetime | None = None
    provider_response: dict | None = None
    retry_count: int = 0
    error_message: str | None = None
    next_retry_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationDeliveryList(BaseModel):
    """Paginated list of delivery records."""

    items: list[NotificationDeliveryRead]
    total: int
    skip: int
    limit: int


# ── Communication Template ──────────────────────────────────────────────────


class CommunicationTemplateCreate(BaseModel):
    """Create a new communication template."""

    template_type: str
    channel: str
    subject: str | None = None
    body: str
    locale: str = "en"
    is_active: bool = True


class CommunicationTemplateUpdate(BaseModel):
    """Update an existing communication template."""

    subject: str | None = None
    body: str | None = None
    locale: str | None = None
    is_active: bool | None = None


class CommunicationTemplateRead(BaseModel):
    """Read model for communication templates."""

    id: UUID
    tenant_id: UUID | None = None
    template_type: str
    channel: str
    subject: str | None = None
    body: str
    locale: str = "en"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommunicationTemplateList(BaseModel):
    """Paginated list of templates."""

    items: list[CommunicationTemplateRead]
    total: int
    skip: int
    limit: int


# ── Template Preview ────────────────────────────────────────────────────────


class TemplatePreviewRequest(BaseModel):
    """Request to preview a rendered template with test data."""

    template_id: UUID | None = None
    template_type: str | None = None
    channel: str | None = None
    test_context: dict = Field(default_factory=dict)


class TemplatePreviewResponse(BaseModel):
    """Rendered template preview."""

    subject: str | None = None
    body: str
    template_type: str
    channel: str


# ── Resend Request ──────────────────────────────────────────────────────────


class ResendNotificationRequest(BaseModel):
    """Request to resend a notification via a specific channel."""

    delivery_id: UUID
    channel: str | None = None  # If None, resend via original channel


# ── Reminder Settings ───────────────────────────────────────────────────────


class ReminderSettings(BaseModel):
    """Tenant-level reminder configuration (future: persisted settings)."""

    twenty_four_hour_enabled: bool = True
    two_hour_enabled: bool = True
    follow_up_enabled: bool = True
    reminder_channels: list[str] = Field(default_factory=lambda: ["email", "sms"])


# ── Dashboard Stats ─────────────────────────────────────────────────────────


class CommunicationDashboardStats(BaseModel):
    """Aggregated stats for the admin communication dashboard."""

    total_notifications: int = 0
    total_sent: int = 0
    total_failed: int = 0
    total_pending: int = 0
    success_rate: float = 0.0
    by_channel: dict[str, int] = Field(default_factory=dict)
    by_type: dict[str, int] = Field(default_factory=dict)
