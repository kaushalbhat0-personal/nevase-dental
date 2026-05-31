"""
Communication API Endpoints — Phase 3D Communication Infrastructure.

Provides REST endpoints for:
- Notification history (admin + patient views)
- Delivery status tracking
- Failed message management
- Communication template CRUD
- Template preview
- Resend actions
- Reminder settings
- Dashboard stats

Authorization:
- Tenant isolation enforced via assert_authorized / get_optional_scoped_tenant_id
- Patients: only see their own notifications
- Doctors: see notifications for their appointments
- Admins: full tenant-level view
- Super admins: cross-tenant access

TODO: Phase 4 — Queue worker integration
TODO: Phase 5 — Patient communication preferences
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.core.database import get_db
from app.crud import crud_notification
from app.models.notification import (
    NotificationChannel,
    NotificationEventType,
)
from app.models.user import User, UserRole
from app.schemas.notification import (
    CommunicationDashboardStats,
    CommunicationTemplateCreate,
    CommunicationTemplateList,
    CommunicationTemplateRead,
    CommunicationTemplateUpdate,
    NotificationDeliveryList,
    NotificationDeliveryRead,
    NotificationEventList,
    NotificationEventRead,
    ReminderSettings,
    ResendNotificationRequest,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
)
from app.services import notification_service, reminder_service
from app.services.notification_templates import (
    get_available_placeholders,
    render_subject,
    render_template,
)
from app.services.security_audit import assert_authorized

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/communications", tags=["communications"])


# ═════════════════════════════════════════════════════════════════════════════
# Notification Events
# ═════════════════════════════════════════════════════════════════════════════


@router.get("/notifications", response_model=NotificationEventList)
def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    event_type: str | None = Query(None),
    patient_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """
    List notification events for the current tenant.

    Admin: full tenant view.
    Patient: only their own notifications.
    Doctor: notifications for their patients (future).
    """
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context required",
        )

    # Patient scope
    if current_user.role == UserRole.patient:
        patient_id = current_user.patient_id
        if patient_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patient profile not found",
            )
        events, total = notification_service.get_notifications_for_patient(
            db, patient_id, tenant_id, skip=skip, limit=limit
        )
    else:
        # Admin / doctor / super_admin
        events, total = notification_service.get_notifications_for_tenant(
            db,
            tenant_id,
            skip=skip,
            limit=limit,
            event_type=event_type,
            patient_id=patient_id,
        )

    return NotificationEventList(
        items=[NotificationEventRead.model_validate(e) for e in events],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/notifications/{event_id}", response_model=NotificationEventRead)
def get_notification(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """Get a single notification event with delivery details."""
    event = crud_notification.get_notification_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Tenant isolation
    if event.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Patient scope
    if current_user.role == UserRole.patient:
        if event.patient_id != current_user.patient_id:
            raise HTTPException(status_code=403, detail="Access denied")

    return NotificationEventRead.model_validate(event)


# ═════════════════════════════════════════════════════════════════════════════
# Delivery Tracking
# ═════════════════════════════════════════════════════════════════════════════


@router.get(
    "/notifications/{event_id}/deliveries",
    response_model=NotificationDeliveryList,
)
def get_deliveries(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """Get all delivery records for a notification event."""
    event = crud_notification.get_notification_event(db, event_id)
    if event is None or event.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Notification not found")

    deliveries = notification_service.get_delivery_details(db, event_id)
    return NotificationDeliveryList(
        items=[NotificationDeliveryRead.model_validate(d) for d in deliveries],
        total=len(deliveries),
        skip=0,
        limit=len(deliveries),
    )


@router.get("/deliveries/failed", response_model=NotificationDeliveryList)
def list_failed_deliveries(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """List failed deliveries for the current tenant."""
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context required")

    deliveries, total = crud_notification.get_failed_deliveries(
        db, tenant_id, skip=skip, limit=limit
    )
    return NotificationDeliveryList(
        items=[NotificationDeliveryRead.model_validate(d) for d in deliveries],
        total=total,
        skip=skip,
        limit=limit,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Resend Actions
# ═════════════════════════════════════════════════════════════════════════════


@router.post("/deliveries/{delivery_id}/resend", status_code=status.HTTP_200_OK)
def resend_delivery(
    delivery_id: UUID,
    request: ResendNotificationRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """Resend a failed delivery."""
    delivery = crud_notification.get_notification_delivery(db, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found")

    # Verify tenant access via event
    event = crud_notification.get_notification_event(db, delivery.notification_event_id)
    if event is None or event.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    channel_override = request.channel if request else None
    success = notification_service.retry_failed_delivery(
        db, delivery_id, channel_override=channel_override
    )

    if success:
        return {"status": "sent", "delivery_id": str(delivery_id)}
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resend failed",
        )


# ═════════════════════════════════════════════════════════════════════════════
# Communication Templates
# ═════════════════════════════════════════════════════════════════════════════


@router.get("/templates", response_model=CommunicationTemplateList)
def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """List communication templates for the current tenant."""
    templates, total = crud_notification.get_templates_for_tenant(
        db, tenant_id, skip=skip, limit=limit
    )
    return CommunicationTemplateList(
        items=[CommunicationTemplateRead.model_validate(t) for t in templates],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/templates/{template_id}", response_model=CommunicationTemplateRead)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """Get a single communication template."""
    template = crud_notification.get_communication_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    # Tenant isolation: system templates (tenant_id IS NULL) are visible to all
    if template.tenant_id is not None and template.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return CommunicationTemplateRead.model_validate(template)


@router.post(
    "/templates",
    response_model=CommunicationTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    data: CommunicationTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """Create a new communication template for the current tenant."""
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context required")

    # Validate event type and channel
    try:
        event_type = NotificationEventType(data.template_type)
        channel = NotificationChannel(data.channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    template = crud_notification.create_communication_template(
        db,
        tenant_id=tenant_id,
        template_type=event_type,
        channel=channel,
        subject=data.subject,
        body=data.body,
        locale=data.locale,
        is_active=data.is_active,
    )
    db.commit()
    return CommunicationTemplateRead.model_validate(template)


@router.put("/templates/{template_id}", response_model=CommunicationTemplateRead)
def update_template(
    template_id: UUID,
    data: CommunicationTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """Update a communication template."""
    template = crud_notification.get_communication_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    # Only tenant-owned templates can be updated
    if template.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    template = crud_notification.update_communication_template(
        db,
        template_id,
        subject=data.subject,
        body=data.body,
        locale=data.locale,
        is_active=data.is_active,
    )
    db.commit()
    return CommunicationTemplateRead.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """Delete a communication template."""
    template = crud_notification.get_communication_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    crud_notification.delete_communication_template(db, template_id)
    db.commit()


# ═════════════════════════════════════════════════════════════════════════════
# Template Preview
# ═════════════════════════════════════════════════════════════════════════════


@router.post("/templates/preview", response_model=TemplatePreviewResponse)
def preview_template(
    request: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """Preview a rendered template with test data."""
    template = None

    if request.template_id:
        template = crud_notification.get_communication_template(
            db, request.template_id
        )
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
    elif request.template_type and request.channel:
        # Use built-in default template
        from app.services.notification_templates import get_default_template

        event_type = NotificationEventType(request.template_type)
        channel = NotificationChannel(request.channel)
        default = get_default_template(event_type, channel)
        if default is None:
            raise HTTPException(status_code=404, detail="Default template not found")

        subject = render_subject(default.get("subject"), request.test_context)
        body = render_template(default.get("body", ""), request.test_context)
        return TemplatePreviewResponse(
            subject=subject,
            body=body,
            template_type=request.template_type,
            channel=request.channel,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide template_id or template_type + channel",
        )

    # Render from DB template
    subject = render_subject(template.subject, request.test_context)
    body = render_template(template.body, request.test_context)
    return TemplatePreviewResponse(
        subject=subject,
        body=body,
        template_type=template.template_type.value,
        channel=template.channel.value,
    )


@router.get("/templates/placeholders")
def list_placeholders():
    """Get all available template placeholders with descriptions."""
    return get_available_placeholders()


# ═════════════════════════════════════════════════════════════════════════════
# Dashboard Stats
# ═════════════════════════════════════════════════════════════════════════════


@router.get("/dashboard/stats", response_model=CommunicationDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """Get aggregated notification stats for the admin dashboard."""
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context required")

    stats = notification_service.get_dashboard_stats(db, tenant_id)
    return CommunicationDashboardStats(**stats)


# ═════════════════════════════════════════════════════════════════════════════
# Reminder Settings (Future)
# ═════════════════════════════════════════════════════════════════════════════


@router.get("/reminder-settings", response_model=ReminderSettings)
def get_reminder_settings(
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """
    Get reminder settings for the current tenant.

    TODO: Phase 5 — Persist reminder settings per tenant
    """
    return ReminderSettings()


@router.put("/reminder-settings", response_model=ReminderSettings)
def update_reminder_settings(
    settings: ReminderSettings,
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """
    Update reminder settings for the current tenant.

    TODO: Phase 5 — Persist reminder settings per tenant
    """
    return settings


# ═════════════════════════════════════════════════════════════════════════════
# Manual Reminder Trigger (Admin)
# ═════════════════════════════════════════════════════════════════════════════


@router.post("/reminders/trigger", status_code=status.HTTP_200_OK)
def trigger_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: UUID | None = Depends(deps.get_optional_scoped_tenant_id),
):
    """
    Manually trigger reminder generation.

    Admin-only. Designed for testing and manual override.
    In production, reminders are generated by scheduled tasks.
    """
    if current_user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(status_code=403, detail="Admin access required")

    results = reminder_service.process_all_reminders(db)
    return {"status": "completed", "results": results}
