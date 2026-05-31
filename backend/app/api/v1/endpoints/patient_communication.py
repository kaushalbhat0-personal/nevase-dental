"""
Patient Communication API Endpoints — Phase P2 Patient Communication Center.

Architecture:
  These endpoints compose existing NotificationEvent data into a patient-friendly
  communication center view. They enforce strict patient-scoped access and NEVER
  expose provider delivery internals or audit metadata.

  NotificationEvent remains the source-of-truth.
  Communication delivery remains infrastructure-level.
  Patient UI CONSUMES communication aggregates — it does not own delivery workflows.

Authorization:
  - Patient-only access (non-patients receive 403)
  - Tenant isolation via existing data_scope patterns
  - Communication ownership validated by patient_id scoping
  - Provider delivery internals are NEVER exposed
  - Audit metadata is NEVER exposed
  - Internal notification payloads are NEVER exposed

TODO: Phase 3 — AI health assistant integration
TODO: Phase 3 — Conversational chat
TODO: Phase 3 — Care-plan nudges
TODO: Phase 3 — Medication adherence tracking
TODO: Phase 3 — Voice reminders
TODO: Phase 3 — Push notifications
TODO: Phase 3 — Family/dependent notifications
TODO: Phase 3 — Multilingual templates
TODO: Phase 3 — Patient-provider messaging
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_scoped_tenant_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.patient_communication import (
    CommunicationCard,
    CommunicationPreferencesRead,
    CommunicationPreferencesUpdate,
    CommunicationTimelineResponse,
    PatientCommunicationAggregate,
    ReminderListResponse,
)
from app.services import patient_communication_service
from app.services.patient_communication_preferences_service import (
    update_patient_preferences,
    validate_preferences,
)
from app.services.exceptions import ForbiddenError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/patient/communications",
    tags=["patient-communications"],
)


@router.get("", response_model=PatientCommunicationAggregate)
def get_patient_communication_aggregate(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> PatientCommunicationAggregate:
    """
    Get the full Patient Communication Aggregate for the authenticated patient.

    Returns a comprehensive communication center including:
    - Recent notifications (timeline)
    - Unread count
    - Reminders by urgency (urgent, upcoming, completed)
    - Communication preferences
    - Linked documents

    CRITICAL:
    - Patient access is strictly scoped to their own data
    - Provider delivery internals are NEVER exposed
    - Audit metadata is NEVER exposed
    - Internal notification payloads are NEVER exposed
    """
    return patient_communication_service.get_patient_communication_aggregate(
        db, current_user
    )


@router.get("/timeline", response_model=CommunicationTimelineResponse)
def get_patient_communication_timeline(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        default=20, ge=1, le=100, description="Maximum records to return"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> CommunicationTimelineResponse:
    """
    Get paginated communication cards for the patient timeline.

    Returns patient-safe communication cards ordered by time (newest first).
    Each card includes title, summary, timestamp, notification type,
    related doctor/clinic, CTA actions, and document download links.
    """
    cards, total = patient_communication_service.get_patient_communication_timeline(
        db, current_user, skip=skip, limit=limit
    )
    return CommunicationTimelineResponse(
        items=cards,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/reminders", response_model=ReminderListResponse)
def get_patient_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> ReminderListResponse:
    """
    Get reminders grouped by urgency for the patient.

    Visual hierarchy:
    - urgent: overdue follow-ups, unpaid bills past due
    - upcoming: tomorrow's appointments, upcoming follow-ups
    - completed: past visits, paid bills

    Future-ready for AI reminder prioritization and smart nudges.
    """
    reminders = patient_communication_service.get_patient_reminders(
        db, current_user
    )
    return ReminderListResponse(
        reminders_by_urgency=reminders,
        total_urgent=len(reminders.get("urgent", [])),
        total_upcoming=len(reminders.get("upcoming", [])),
        total_completed=len(reminders.get("completed", [])),
    )


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> dict:
    """
    Get the unread notification count for the patient.

    Returns a simple count for badge display in the UI.
    """
    count = patient_communication_service.get_unread_count(db, current_user)
    return {"unread_count": count}


@router.put("/{event_id}/read", status_code=status.HTTP_200_OK)
def mark_notification_as_read(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> dict:
    """
    Mark a notification event as read by the patient.

    Uses existing NotificationDelivery infrastructure.
    Creates or updates an in_app delivery record with status='read'.
    """
    try:
        result = patient_communication_service.mark_notification_as_read(
            db, current_user, event_id
        )
        return {"status": "read", "event_id": str(event_id)}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/preferences", response_model=CommunicationPreferencesRead)
def get_communication_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> CommunicationPreferencesRead:
    """
    Get communication preferences for the authenticated patient.

    Returns current channel preferences including:
    - Email notifications
    - SMS notifications
    - WhatsApp notifications
    - Reminder preferences
    - Quiet hours (future-ready)
    - Locale (future-ready)
    """
    from app.services.patient_communication_preferences_service import (
        get_or_create_patient_preferences,
    )
    from app.services.patient_workspace_service import _resolve_patient

    patient = _resolve_patient(db, current_user)
    prefs = get_or_create_patient_preferences(db, patient.id, patient.tenant_id)

    return CommunicationPreferencesRead(
        email_enabled=prefs.email_enabled,
        sms_enabled=prefs.sms_enabled,
        whatsapp_enabled=prefs.whatsapp_enabled,
        reminder_enabled=prefs.reminder_enabled,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end,
        locale=prefs.locale,
        opt_out_all=prefs.opt_out_all,
    )


@router.put("/preferences", response_model=CommunicationPreferencesRead)
def update_communication_preferences(
    data: CommunicationPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> CommunicationPreferencesRead:
    """
    Update communication preferences for the authenticated patient.

    ⚠️ CRITICAL: opt_out_all will NOT bypass critical healthcare notifications.
    Critical notifications (appointment reminders, urgent results,
    prescription readiness, follow-ups) are ALWAYS sent.

    Future-ready hooks:
    - Quiet hours
    - Multilingual communication
    - Consent management
    - Opt-out controls
    """
    from app.services.patient_communication_preferences_service import (
        get_or_create_patient_preferences,
        update_patient_preferences,
    )
    from app.services.patient_workspace_service import _resolve_patient

    patient = _resolve_patient(db, current_user)

    # Validate preferences
    warnings = validate_preferences(
        email_enabled=data.email_enabled,
        sms_enabled=data.sms_enabled,
        whatsapp_enabled=data.whatsapp_enabled,
        reminder_enabled=data.reminder_enabled,
        opt_out_all=data.opt_out_all,
    )

    if warnings:
        logger.info("Preference update warnings: %s", warnings)

    prefs = update_patient_preferences(
        db,
        patient.id,
        patient.tenant_id,
        email_enabled=data.email_enabled,
        sms_enabled=data.sms_enabled,
        whatsapp_enabled=data.whatsapp_enabled,
        reminder_enabled=data.reminder_enabled,
        quiet_hours_start=data.quiet_hours_start,
        quiet_hours_end=data.quiet_hours_end,
        locale=data.locale,
        opt_out_all=data.opt_out_all,
    )
    db.commit()

    return CommunicationPreferencesRead(
        email_enabled=prefs.email_enabled,
        sms_enabled=prefs.sms_enabled,
        whatsapp_enabled=prefs.whatsapp_enabled,
        reminder_enabled=prefs.reminder_enabled,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end,
        locale=prefs.locale,
        opt_out_all=prefs.opt_out_all,
    )
