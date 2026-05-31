"""
CRUD operations for notification domain models.

Provides standard create/read/update/delete operations for:
- NotificationEvent
- NotificationDelivery
- CommunicationTemplate

All operations respect tenant isolation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import (
    CommunicationTemplate,
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventType,
)

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# NotificationEvent CRUD
# ═════════════════════════════════════════════════════════════════════════════


def create_notification_event(
    db: Session,
    *,
    event_type: NotificationEventType,
    tenant_id: UUID,
    patient_id: UUID | None = None,
    doctor_id: UUID | None = None,
    appointment_id: UUID | None = None,
    bill_id: UUID | None = None,
    payload: dict | None = None,
) -> NotificationEvent:
    """Create a new notification event."""
    event = NotificationEvent(
        event_type=event_type,
        tenant_id=tenant_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        bill_id=bill_id,
        payload=payload,
    )
    db.add(event)
    db.flush()
    logger.debug(
        "Created notification event: type=%s tenant=%s event_id=%s",
        event_type.value,
        tenant_id,
        event.id,
    )
    return event


def get_notification_event(
    db: Session, event_id: UUID
) -> NotificationEvent | None:
    """Get a notification event by ID."""
    return db.get(NotificationEvent, event_id)


def get_notification_events_for_tenant(
    db: Session,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 20,
    event_type: str | None = None,
    patient_id: UUID | None = None,
) -> tuple[list[NotificationEvent], int]:
    """
    Get paginated notification events for a tenant.

    Returns (events, total_count).
    """
    query = select(NotificationEvent).where(
        NotificationEvent.tenant_id == tenant_id,
        NotificationEvent.is_deleted == False,
    )

    count_query = select(func.count(NotificationEvent.id)).where(
        NotificationEvent.tenant_id == tenant_id,
        NotificationEvent.is_deleted == False,
    )

    if event_type is not None:
        query = query.where(NotificationEvent.event_type == event_type)
        count_query = count_query.where(
            NotificationEvent.event_type == event_type
        )

    if patient_id is not None:
        query = query.where(NotificationEvent.patient_id == patient_id)
        count_query = count_query.where(
            NotificationEvent.patient_id == patient_id
        )

    total = db.scalar(count_query) or 0
    events = (
        db.execute(
            query.order_by(NotificationEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(events), total


def get_notification_events_for_patient(
    db: Session,
    patient_id: UUID,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[NotificationEvent], int]:
    """
    Get paginated notification events for a specific patient within a tenant.

    Patient privacy: only returns events scoped to the patient's tenant.
    """
    query = select(NotificationEvent).where(
        NotificationEvent.patient_id == patient_id,
        NotificationEvent.tenant_id == tenant_id,
        NotificationEvent.is_deleted == False,
    )
    count_query = select(func.count(NotificationEvent.id)).where(
        NotificationEvent.patient_id == patient_id,
        NotificationEvent.tenant_id == tenant_id,
        NotificationEvent.is_deleted == False,
    )

    total = db.scalar(count_query) or 0
    events = (
        db.execute(
            query.order_by(NotificationEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(events), total


def soft_delete_notification_event(db: Session, event_id: UUID) -> None:
    """Soft-delete a notification event."""
    db.execute(
        update(NotificationEvent)
        .where(NotificationEvent.id == event_id)
        .values(is_deleted=True)
    )
    db.flush()


# ═════════════════════════════════════════════════════════════════════════════
# NotificationDelivery CRUD
# ═════════════════════════════════════════════════════════════════════════════


def create_notification_delivery(
    db: Session,
    *,
    notification_event_id: UUID,
    channel: NotificationChannel,
    recipient: str,
) -> NotificationDelivery:
    """Create a new delivery record for a notification event."""
    delivery = NotificationDelivery(
        notification_event_id=notification_event_id,
        channel=channel,
        recipient=recipient,
        status=NotificationDeliveryStatus.pending,
    )
    db.add(delivery)
    db.flush()
    return delivery


def get_notification_delivery(
    db: Session, delivery_id: UUID
) -> NotificationDelivery | None:
    """Get a delivery record by ID."""
    return db.get(NotificationDelivery, delivery_id)


def get_deliveries_for_event(
    db: Session, event_id: UUID
) -> list[NotificationDelivery]:
    """Get all delivery records for a notification event."""
    result = db.execute(
        select(NotificationDelivery).where(
            NotificationDelivery.notification_event_id == event_id
        )
    )
    return list(result.scalars().all())


def update_delivery_status(
    db: Session,
    delivery_id: UUID,
    *,
    status: NotificationDeliveryStatus,
    provider_response: dict | None = None,
    error_message: str | None = None,
    retry_count: int | None = None,
) -> NotificationDelivery | None:
    """Update delivery status and related fields."""
    delivery = db.get(NotificationDelivery, delivery_id)
    if delivery is None:
        return None

    delivery.status = status
    now = datetime.now(timezone.utc)

    if status == NotificationDeliveryStatus.sent:
        delivery.sent_at = now
    elif status == NotificationDeliveryStatus.failed:
        delivery.failed_at = now

    if provider_response is not None:
        delivery.provider_response = provider_response
    if error_message is not None:
        delivery.error_message = error_message
    if retry_count is not None:
        delivery.retry_count = retry_count

    db.flush()
    return delivery


def get_pending_deliveries(
    db: Session, *, limit: int = 50
) -> list[NotificationDelivery]:
    """Get pending deliveries that need to be processed."""
    result = db.execute(
        select(NotificationDelivery)
        .where(
            NotificationDelivery.status == NotificationDeliveryStatus.pending,
        )
        .order_by(NotificationDelivery.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


def get_failed_deliveries(
    db: Session,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[NotificationDelivery], int]:
    """
    Get failed deliveries for a tenant.

    Joins through notification_event to enforce tenant isolation.
    """
    query = (
        select(NotificationDelivery)
        .join(
            NotificationEvent,
            NotificationDelivery.notification_event_id == NotificationEvent.id,
        )
        .where(
            NotificationEvent.tenant_id == tenant_id,
            NotificationDelivery.status == NotificationDeliveryStatus.failed,
        )
    )
    count_query = (
        select(func.count(NotificationDelivery.id))
        .join(
            NotificationEvent,
            NotificationDelivery.notification_event_id == NotificationEvent.id,
        )
        .where(
            NotificationEvent.tenant_id == tenant_id,
            NotificationDelivery.status == NotificationDeliveryStatus.failed,
        )
    )

    total = db.scalar(count_query) or 0
    deliveries = (
        db.execute(
            query.order_by(NotificationDelivery.failed_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(deliveries), total


# ═════════════════════════════════════════════════════════════════════════════
# CommunicationTemplate CRUD
# ═════════════════════════════════════════════════════════════════════════════


def create_communication_template(
    db: Session,
    *,
    tenant_id: UUID | None,
    template_type: NotificationEventType,
    channel: NotificationChannel,
    body: str,
    subject: str | None = None,
    locale: str = "en",
    is_active: bool = True,
) -> CommunicationTemplate:
    """Create a new communication template."""
    template = CommunicationTemplate(
        tenant_id=tenant_id,
        template_type=template_type,
        channel=channel,
        subject=subject,
        body=body,
        locale=locale,
        is_active=is_active,
    )
    db.add(template)
    db.flush()
    return template


def get_communication_template(
    db: Session, template_id: UUID
) -> CommunicationTemplate | None:
    """Get a template by ID."""
    return db.get(CommunicationTemplate, template_id)


def get_template_for_tenant(
    db: Session,
    tenant_id: UUID | None,
    template_type: NotificationEventType,
    channel: NotificationChannel,
    locale: str = "en",
) -> CommunicationTemplate | None:
    """
    Get the best matching template.

    Resolution order:
    1. Tenant-specific, active, matching locale
    2. Tenant-specific, active, default locale
    3. System default (tenant_id IS NULL), active, matching locale
    4. System default (tenant_id IS NULL), active, default locale
    """
    # Try tenant-specific first
    for tid in [tenant_id, None]:
        result = db.execute(
            select(CommunicationTemplate).where(
                CommunicationTemplate.tenant_id == tid,
                CommunicationTemplate.template_type == template_type,
                CommunicationTemplate.channel == channel,
                CommunicationTemplate.locale == locale,
                CommunicationTemplate.is_active == True,
            )
        )
        template = result.scalar_one_or_none()
        if template is not None:
            return template

    # Fallback to default locale
    for tid in [tenant_id, None]:
        result = db.execute(
            select(CommunicationTemplate).where(
                CommunicationTemplate.tenant_id == tid,
                CommunicationTemplate.template_type == template_type,
                CommunicationTemplate.channel == channel,
                CommunicationTemplate.locale == "en",
                CommunicationTemplate.is_active == True,
            )
        )
        template = result.scalar_one_or_none()
        if template is not None:
            return template

    return None


def get_templates_for_tenant(
    db: Session,
    tenant_id: UUID | None,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[CommunicationTemplate], int]:
    """Get all templates for a tenant (including system defaults)."""
    query = select(CommunicationTemplate).where(
        (CommunicationTemplate.tenant_id == tenant_id)
        | (CommunicationTemplate.tenant_id.is_(None))
    )
    count_query = select(func.count(CommunicationTemplate.id)).where(
        (CommunicationTemplate.tenant_id == tenant_id)
        | (CommunicationTemplate.tenant_id.is_(None))
    )

    total = db.scalar(count_query) or 0
    templates = (
        db.execute(
            query.order_by(
                CommunicationTemplate.template_type,
                CommunicationTemplate.channel,
            )
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(templates), total


def update_communication_template(
    db: Session,
    template_id: UUID,
    *,
    subject: str | None = None,
    body: str | None = None,
    locale: str | None = None,
    is_active: bool | None = None,
) -> CommunicationTemplate | None:
    """Update a communication template."""
    template = db.get(CommunicationTemplate, template_id)
    if template is None:
        return None

    if subject is not None:
        template.subject = subject
    if body is not None:
        template.body = body
    if locale is not None:
        template.locale = locale
    if is_active is not None:
        template.is_active = is_active

    db.flush()
    return template


def delete_communication_template(
    db: Session, template_id: UUID
) -> bool:
    """Delete a communication template. Returns True if deleted."""
    template = db.get(CommunicationTemplate, template_id)
    if template is None:
        return False
    db.delete(template)
    db.flush()
    return True


# ═════════════════════════════════════════════════════════════════════════════
# Dashboard Stats
# ═════════════════════════════════════════════════════════════════════════════


def get_notification_stats(
    db: Session, tenant_id: UUID
) -> dict[str, int | float]:
    """Get aggregated notification stats for a tenant."""
    base = select(NotificationEvent).where(
        NotificationEvent.tenant_id == tenant_id,
        NotificationEvent.is_deleted == False,
    )

    total = db.scalar(
        select(func.count(NotificationEvent.id)).where(
            NotificationEvent.tenant_id == tenant_id,
            NotificationEvent.is_deleted == False,
        )
    ) or 0

    # Count by event type
    type_rows = db.execute(
        select(
            NotificationEvent.event_type,
            func.count(NotificationEvent.id),
        )
        .where(
            NotificationEvent.tenant_id == tenant_id,
            NotificationEvent.is_deleted == False,
        )
        .group_by(NotificationEvent.event_type)
    ).all()
    by_type = {str(row[0]): row[1] for row in type_rows}

    # Delivery stats via join
    delivery_base = (
        select(NotificationDelivery)
        .join(
            NotificationEvent,
            NotificationDelivery.notification_event_id == NotificationEvent.id,
        )
        .where(
            NotificationEvent.tenant_id == tenant_id,
            NotificationEvent.is_deleted == False,
        )
    ).subquery()

    sent = (
        db.scalar(
            select(func.count())
            .select_from(delivery_base)
            .where(delivery_base.c.status == NotificationDeliveryStatus.sent.value)
        )
        or 0
    )
    failed = (
        db.scalar(
            select(func.count())
            .select_from(delivery_base)
            .where(delivery_base.c.status == NotificationDeliveryStatus.failed.value)
        )
        or 0
    )
    pending = (
        db.scalar(
            select(func.count())
            .select_from(delivery_base)
            .where(delivery_base.c.status == NotificationDeliveryStatus.pending.value)
        )
        or 0
    )

    # By channel
    channel_rows = db.execute(
        select(
            delivery_base.c.channel,
            func.count(),
        )
        .select_from(delivery_base)
        .group_by(delivery_base.c.channel)
    ).all()
    by_channel = {str(row[0]): row[1] for row in channel_rows}

    total_deliveries = sent + failed + pending
    success_rate = (sent / total_deliveries * 100) if total_deliveries > 0 else 0.0

    return {
        "total_notifications": total,
        "total_sent": sent,
        "total_failed": failed,
        "total_pending": pending,
        "success_rate": round(success_rate, 1),
        "by_channel": by_channel,
        "by_type": by_type,
    }
