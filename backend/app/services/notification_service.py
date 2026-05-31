"""
Notification Service — Phase 3D Communication Infrastructure.

Architecture:
  Notifications are DERIVED EVENTS.
  Business services emit events via this service.
  The notification service handles all communication concerns.

  Responsibilities:
  1. Event generation — create NotificationEvent records from business actions
  2. Template resolution — find and render the right template for event × channel
  3. Channel dispatch — route through provider abstraction
  4. Delivery tracking — update delivery status, handle retries
  5. Audit logging — log all notification lifecycle events

  IMPORTANT:
  - Business services call create_*_event() methods — NOT delivery methods
  - Delivery is async-safe and queue-ready
  - All PHI stays in source-of-truth models, not in notification payloads
  - Branding context is resolved from tenant branding profiles

  TODO: Phase 4 — Queue worker integration (Celery / RQ / AWS SQS)
  TODO: Phase 4 — Retry with exponential backoff
  TODO: Phase 4 — Push notification support (Firebase / APNs)
  TODO: Phase 5 — Patient communication preferences / consent management
  TODO: Phase 5 — Opt-out / unsubscribe handling
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud import crud_notification
from app.models.notification import (
    CommunicationTemplate,
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventType,
)
from app.services.notification_providers import (
    BaseProvider,
    ProviderResponse,
    get_provider,
)
from app.services.notification_templates import (
    get_default_template,
    render_subject,
    render_template,
)
from app.services.security_audit import log_structured_audit_event

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Event Generation
# ═════════════════════════════════════════════════════════════════════════════


def create_appointment_booked_event(
    db: Session,
    *,
    tenant_id: UUID,
    patient_id: UUID,
    doctor_id: UUID,
    appointment_id: UUID,
    payload: dict[str, Any] | None = None,
) -> NotificationEvent:
    """
    Create a notification event for a booked appointment.

    Called by appointment_service after successful appointment creation.
    """
    event = crud_notification.create_notification_event(
        db,
        event_type=NotificationEventType.appointment_booked,
        tenant_id=tenant_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        payload=payload,
    )
    _log_notification_audit(
        event="notification_created",
        event_obj=event,
        extra={"event_type": NotificationEventType.appointment_booked.value},
    )
    return event


def create_appointment_completed_event(
    db: Session,
    *,
    tenant_id: UUID,
    patient_id: UUID,
    doctor_id: UUID,
    appointment_id: UUID,
    payload: dict[str, Any] | None = None,
) -> NotificationEvent:
    """
    Create a notification event for a completed appointment.

    Called by appointment_service after successful appointment completion.
    """
    event = crud_notification.create_notification_event(
        db,
        event_type=NotificationEventType.appointment_completed,
        tenant_id=tenant_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        payload=payload,
    )
    _log_notification_audit(
        event="notification_created",
        event_obj=event,
        extra={"event_type": NotificationEventType.appointment_completed.value},
    )
    return event


def create_bill_generated_event(
    db: Session,
    *,
    tenant_id: UUID,
    patient_id: UUID,
    bill_id: UUID,
    appointment_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> NotificationEvent:
    """
    Create a notification event for a generated bill.

    Called by billing_service after successful bill creation.
    """
    event = crud_notification.create_notification_event(
        db,
        event_type=NotificationEventType.bill_generated,
        tenant_id=tenant_id,
        patient_id=patient_id,
        bill_id=bill_id,
        appointment_id=appointment_id,
        payload=payload,
    )
    _log_notification_audit(
        event="notification_created",
        event_obj=event,
        extra={"event_type": NotificationEventType.bill_generated.value},
    )
    return event


def create_payment_received_event(
    db: Session,
    *,
    tenant_id: UUID,
    patient_id: UUID,
    bill_id: UUID,
    appointment_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> NotificationEvent:
    """
    Create a notification event for a received payment.

    Called by billing_service after successful payment processing.
    """
    event = crud_notification.create_notification_event(
        db,
        event_type=NotificationEventType.payment_received,
        tenant_id=tenant_id,
        patient_id=patient_id,
        bill_id=bill_id,
        appointment_id=appointment_id,
        payload=payload,
    )
    _log_notification_audit(
        event="notification_created",
        event_obj=event,
        extra={"event_type": NotificationEventType.payment_received.value},
    )
    return event


def create_prescription_ready_event(
    db: Session,
    *,
    tenant_id: UUID,
    patient_id: UUID,
    doctor_id: UUID,
    appointment_id: UUID,
    payload: dict[str, Any] | None = None,
) -> NotificationEvent:
    """
    Create a notification event for a ready prescription.

    Called by encounter_service or appointment_service after prescription creation.
    """
    event = crud_notification.create_notification_event(
        db,
        event_type=NotificationEventType.prescription_ready,
        tenant_id=tenant_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        payload=payload,
    )
    _log_notification_audit(
        event="notification_created",
        event_obj=event,
        extra={"event_type": NotificationEventType.prescription_ready.value},
    )
    return event


def create_reminder_event(
    db: Session,
    *,
    tenant_id: UUID,
    patient_id: UUID,
    doctor_id: UUID,
    appointment_id: UUID,
    event_type: NotificationEventType,
    payload: dict[str, Any] | None = None,
) -> NotificationEvent:
    """
    Create a reminder notification event.

    Called by reminder_service for scheduled reminders.
    event_type should be appointment_reminder or follow_up_reminder.
    """
    event = crud_notification.create_notification_event(
        db,
        event_type=event_type,
        tenant_id=tenant_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        payload=payload,
    )
    _log_notification_audit(
        event="reminder_triggered",
        event_obj=event,
        extra={"event_type": event_type.value},
    )
    return event


# ═════════════════════════════════════════════════════════════════════════════
# Template Resolution
# ═════════════════════════════════════════════════════════════════════════════


def resolve_template(
    db: Session,
    tenant_id: UUID | None,
    event_type: NotificationEventType,
    channel: NotificationChannel,
) -> CommunicationTemplate | dict[str, str] | None:
    """
    Resolve the best template for an event type and channel.

    Resolution order:
    1. Tenant-specific template from DB
    2. System default template from DB (tenant_id IS NULL)
    3. Built-in default template from notification_templates module

    Returns:
        CommunicationTemplate ORM object, dict with 'subject'/'body', or None.
    """
    # Try DB templates first
    db_template = crud_notification.get_template_for_tenant(
        db, tenant_id, event_type, channel
    )
    if db_template is not None:
        return db_template

    # Fall back to built-in defaults
    default = get_default_template(event_type, channel)
    if default is not None:
        return default

    logger.warning(
        "No template found for event_type=%s channel=%s tenant=%s",
        event_type.value,
        channel.value,
        tenant_id,
    )
    return None


def build_rendering_context(
    db: Session,
    tenant_id: UUID | None,
    event: NotificationEvent,
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a rendering context with branding and event data.

    Resolves tenant branding for clinic name, phone, address.
    Merges with event payload data.

    Args:
        db: Database session.
        tenant_id: Tenant UUID for branding resolution.
        event: The notification event (for payload data).
        extra_context: Additional context values to merge.

    Returns:
        Dict with all placeholders resolved.
    """
    context: dict[str, Any] = {}

    # Load branding context
    if tenant_id is not None:
        try:
            from app.services.tenant_branding_service import get_tenant_branding_context

            branding = get_tenant_branding_context(db, tenant_id)
            org = branding.get("organization", {}) or {}
            context["clinic_name"] = org.get("organization_name") or "Clinic"
            context["clinic_phone"] = org.get("phone") or ""
            # Build address string
            addr_parts = [
                org.get("address_line_1"),
                org.get("city"),
                org.get("state"),
                org.get("postal_code"),
            ]
            context["clinic_address"] = ", ".join(
                [p for p in addr_parts if p]
            ) or ""
        except Exception:
            logger.warning(
                "Failed to load branding for tenant %s, using defaults", tenant_id
            )
            context["clinic_name"] = "Clinic"
            context["clinic_phone"] = ""
            context["clinic_address"] = ""
    else:
        context["clinic_name"] = "Clinic"
        context["clinic_phone"] = ""
        context["clinic_address"] = ""

    # Merge event payload
    if event.payload:
        context.update(event.payload)

    # Merge extra context (overrides payload)
    if extra_context:
        context.update(extra_context)

    return context


# ═════════════════════════════════════════════════════════════════════════════
# Channel Dispatch
# ═════════════════════════════════════════════════════════════════════════════


def dispatch_notification(
    db: Session,
    event_id: UUID,
    channels: list[NotificationChannel] | None = None,
    recipient_override: str | None = None,
) -> list[UUID]:
    """
    Dispatch a notification event through specified channels.

    Creates delivery records and attempts immediate delivery via providers.
    Failed deliveries are recorded for retry.

    Args:
        db: Database session.
        event_id: The notification event to dispatch.
        channels: Channels to dispatch through. Defaults to [email, sms].
        recipient_override: Override recipient (for testing/preview).

    Returns:
        List of delivery record IDs created.
    """
    event = crud_notification.get_notification_event(db, event_id)
    if event is None:
        logger.error("Cannot dispatch: event %s not found", event_id)
        return []

    if channels is None:
        channels = [NotificationChannel.email, NotificationChannel.sms]

    delivery_ids: list[UUID] = []

    for channel in channels:
        # Resolve template
        template = resolve_template(
            db, event.tenant_id, event.event_type, channel
        )
        if template is None:
            logger.warning(
                "No template for event=%s channel=%s, skipping",
                event_id,
                channel.value,
            )
            continue

        # Build rendering context
        context = build_rendering_context(db, event.tenant_id, event)

        # Render content
        if isinstance(template, CommunicationTemplate):
            body = render_template(template.body, context)
            subject = render_subject(template.subject, context)
        else:
            body = render_template(template.get("body", ""), context)
            subject = render_subject(template.get("subject"), context)

        # Determine recipient
        recipient = recipient_override or _resolve_recipient(db, event, channel)
        if not recipient:
            logger.warning(
                "No recipient for event=%s channel=%s, skipping",
                event_id,
                channel.value,
            )
            continue

        # Create delivery record
        delivery = crud_notification.create_notification_delivery(
            db,
            notification_event_id=event_id,
            channel=channel,
            recipient=recipient,
        )
        delivery_ids.append(delivery.id)

        # Attempt delivery via provider
        try:
            provider = get_provider(channel.value)
            provider_response = provider.send(
                recipient=recipient,
                subject=subject,
                body=body,
            )

            if provider_response.status == "sent":
                crud_notification.update_delivery_status(
                    db,
                    delivery.id,
                    status=NotificationDeliveryStatus.sent,
                    provider_response=provider_response.raw_response,
                )
                _log_notification_audit(
                    event="notification_sent",
                    event_obj=event,
                    extra={
                        "delivery_id": str(delivery.id),
                        "channel": channel.value,
                        "provider_id": provider_response.provider_id,
                    },
                )
            else:
                crud_notification.update_delivery_status(
                    db,
                    delivery.id,
                    status=NotificationDeliveryStatus.failed,
                    error_message=provider_response.error_message,
                    provider_response=provider_response.raw_response,
                )
                _log_notification_audit(
                    event="notification_failed",
                    event_obj=event,
                    extra={
                        "delivery_id": str(delivery.id),
                        "channel": channel.value,
                        "error": provider_response.error_message,
                    },
                )

        except Exception as exc:
            logger.error(
                "Provider error for event=%s channel=%s: %s",
                event_id,
                channel.value,
                exc,
            )
            crud_notification.update_delivery_status(
                db,
                delivery.id,
                status=NotificationDeliveryStatus.failed,
                error_message=str(exc),
            )
            _log_notification_audit(
                event="notification_failed",
                event_obj=event,
                extra={
                    "delivery_id": str(delivery.id),
                    "channel": channel.value,
                    "error": str(exc),
                },
            )

    db.flush()
    return delivery_ids


def _resolve_recipient(
    db: Session,
    event: NotificationEvent,
    channel: NotificationChannel,
) -> str | None:
    """
    Resolve the recipient address for a notification event and channel.

    For now, returns a placeholder. Future implementations will look up
    patient/doctor contact info from their profiles.

    TODO: Phase 4 — Look up patient email/phone from patient profile
    TODO: Phase 4 — Look up doctor email/phone from doctor profile
    TODO: Phase 5 — Respect patient communication preferences
    """
    # Placeholder: return a mock recipient based on event data
    # In production, this would query patient/doctor profiles
    if event.patient_id:
        return f"patient_{event.patient_id}@example.com"
    if event.doctor_id:
        return f"doctor_{event.doctor_id}@example.com"
    return None


# ═════════════════════════════════════════════════════════════════════════════
# Delivery Retry
# ═════════════════════════════════════════════════════════════════════════════


def retry_failed_delivery(
    db: Session,
    delivery_id: UUID,
    channel_override: str | None = None,
) -> bool:
    """
    Retry a failed delivery.

    Args:
        db: Database session.
        delivery_id: The delivery record to retry.
        channel_override: Optionally retry via a different channel.

    Returns:
        True if retry was successful, False otherwise.
    """
    delivery = crud_notification.get_notification_delivery(db, delivery_id)
    if delivery is None:
        logger.error("Cannot retry: delivery %s not found", delivery_id)
        return False

    event = crud_notification.get_notification_event(db, delivery.notification_event_id)
    if event is None:
        logger.error("Cannot retry: event for delivery %s not found", delivery_id)
        return False

    channel_str = channel_override or delivery.channel.value
    channel = NotificationChannel(channel_str)

    # Resolve template
    template = resolve_template(db, event.tenant_id, event.event_type, channel)
    if template is None:
        logger.warning("No template for retry event=%s channel=%s", event.id, channel_str)
        return False

    # Build context and render
    context = build_rendering_context(db, event.tenant_id, event)
    if isinstance(template, CommunicationTemplate):
        body = render_template(template.body, context)
        subject = render_subject(template.subject, context)
    else:
        body = render_template(template.get("body", ""), context)
        subject = render_subject(template.get("subject"), context)

    # Attempt delivery
    try:
        provider = get_provider(channel_str)
        provider_response = provider.send(
            recipient=delivery.recipient,
            subject=subject,
            body=body,
        )

        new_retry_count = (delivery.retry_count or 0) + 1

        if provider_response.status == "sent":
            crud_notification.update_delivery_status(
                db,
                delivery.id,
                status=NotificationDeliveryStatus.sent,
                provider_response=provider_response.raw_response,
                retry_count=new_retry_count,
            )
            _log_notification_audit(
                event="notification_sent",
                event_obj=event,
                extra={
                    "delivery_id": str(delivery.id),
                    "channel": channel_str,
                    "retry": True,
                    "provider_id": provider_response.provider_id,
                },
            )
            return True
        else:
            crud_notification.update_delivery_status(
                db,
                delivery.id,
                status=NotificationDeliveryStatus.failed,
                error_message=provider_response.error_message,
                provider_response=provider_response.raw_response,
                retry_count=new_retry_count,
            )
            return False

    except Exception as exc:
        logger.error("Retry failed for delivery %s: %s", delivery_id, exc)
        crud_notification.update_delivery_status(
            db,
            delivery.id,
            status=NotificationDeliveryStatus.failed,
            error_message=str(exc),
            retry_count=(delivery.retry_count or 0) + 1,
        )
        return False


# ═════════════════════════════════════════════════════════════════════════════
# Query Helpers
# ═════════════════════════════════════════════════════════════════════════════


def get_notifications_for_patient(
    db: Session,
    patient_id: UUID,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[NotificationEvent], int]:
    """
    Get notifications for a patient within their tenant.

    Patient privacy: strictly scoped to patient_id + tenant_id.
    """
    return crud_notification.get_notification_events_for_patient(
        db, patient_id, tenant_id, skip=skip, limit=limit
    )


def get_notifications_for_tenant(
    db: Session,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 20,
    event_type: str | None = None,
    patient_id: UUID | None = None,
) -> tuple[list[NotificationEvent], int]:
    """
    Get notifications for a tenant (admin view).

    Tenant isolation: strictly scoped to tenant_id.
    """
    return crud_notification.get_notification_events_for_tenant(
        db,
        tenant_id,
        skip=skip,
        limit=limit,
        event_type=event_type,
        patient_id=patient_id,
    )


def get_delivery_details(
    db: Session, event_id: UUID
) -> list[Any]:
    """Get all delivery records for a notification event."""
    return crud_notification.get_deliveries_for_event(db, event_id)


def get_dashboard_stats(
    db: Session, tenant_id: UUID
) -> dict[str, Any]:
    """Get aggregated notification stats for the admin dashboard."""
    return crud_notification.get_notification_stats(db, tenant_id)


# ═════════════════════════════════════════════════════════════════════════════
# Audit Logging
# ═════════════════════════════════════════════════════════════════════════════


def _log_notification_audit(
    event: str,
    event_obj: NotificationEvent,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Log a structured audit event for notification lifecycle.

    Communications are medico-legal artifacts.
    All notification lifecycle events are audited.
    """
    log_structured_audit_event(
        event=event,
        tenant_id=event_obj.tenant_id,
        resource_id=str(event_obj.id),
        actor_id="system",
        status="success",
        event_type=event_obj.event_type.value if event_obj.event_type else None,
        patient_id=str(event_obj.patient_id) if event_obj.patient_id else None,
        **(extra or {}),
    )
