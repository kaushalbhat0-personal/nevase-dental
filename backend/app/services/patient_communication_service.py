"""
Patient Communication Aggregate Service — Phase P2 Patient Communication Center.

Architecture:
  This service builds the PatientCommunicationAggregate by composing existing
  NotificationEvent data into a patient-friendly view.
  
  NotificationEvent remains the source-of-truth.
  Communication delivery remains infrastructure-level.
  Patient UI CONSUMES communication aggregates — it does not own delivery workflows.

CRITICAL:
  - Patient identity is resolved from current_user (never from request params)
  - Provider delivery internals are NEVER exposed
  - Audit metadata is NEVER exposed
  - Internal notification payloads are NEVER exposed
  - Tenant isolation is strictly enforced

TODO: Phase 3 — AI reminder prioritization
TODO: Phase 3 — Smart nudges
TODO: Phase 3 — Medication adherence tracking
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.crud import crud_notification
from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Billing
from app.models.doctor import Doctor
from app.models.notification import (
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventType,
)
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.patient_communication import (
    CommunicationCard,
    CommunicationPreferencesRead,
    DocumentLink,
    PatientCommunicationAggregate,
    ReminderCard,
)
from app.services import patient_service
from app.services.exceptions import ForbiddenError, NotFoundError
from app.services.security_audit import log_structured_audit_event

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _resolve_patient(db: Session, current_user: User) -> Patient:
    """Resolve the patient record for the current user. Raises ForbiddenError if not a patient."""
    if current_user.role != UserRole.patient:
        raise ForbiddenError("Only patients can access communication center")
    try:
        return patient_service.get_patient_by_user_id(db, current_user.id)
    except NotFoundError:
        raise ForbiddenError("Patient profile not found for this user")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _get_event_title(event_type: NotificationEventType) -> str:
    """Get a human-readable title for a notification event type."""
    titles = {
        NotificationEventType.appointment_booked: "Appointment Booked",
        NotificationEventType.appointment_reminder: "Appointment Reminder",
        NotificationEventType.appointment_completed: "Visit Completed",
        NotificationEventType.prescription_ready: "Prescription Ready",
        NotificationEventType.bill_generated: "Invoice Generated",
        NotificationEventType.payment_received: "Payment Received",
        NotificationEventType.follow_up_reminder: "Follow-up Reminder",
    }
    return titles.get(event_type, "Notification")


def _get_event_summary(event_type: NotificationEventType) -> str:
    """Get a human-readable summary for a notification event type."""
    summaries = {
        NotificationEventType.appointment_booked: "Your appointment has been confirmed.",
        NotificationEventType.appointment_reminder: "You have an appointment coming up.",
        NotificationEventType.appointment_completed: "Your recent visit has been completed.",
        NotificationEventType.prescription_ready: "Your prescription is ready to view.",
        NotificationEventType.bill_generated: "A new invoice has been generated.",
        NotificationEventType.payment_received: "Your payment has been received.",
        NotificationEventType.follow_up_reminder: "It's time for your follow-up.",
    }
    return summaries.get(event_type, "You have a new notification.")


def _is_urgent_event(event_type: NotificationEventType) -> bool:
    """Determine if a notification event type is urgent."""
    urgent_types = {
        NotificationEventType.follow_up_reminder,
    }
    return event_type in urgent_types


def _get_cta_actions(event_type: NotificationEventType) -> list[str]:
    """Get CTA actions for a notification event type."""
    actions = {
        NotificationEventType.appointment_booked: ["view_details"],
        NotificationEventType.appointment_reminder: ["view_details", "reschedule"],
        NotificationEventType.appointment_completed: ["view_encounter"],
        NotificationEventType.prescription_ready: ["view_prescription", "download_document"],
        NotificationEventType.bill_generated: ["view_invoice", "pay_now"],
        NotificationEventType.payment_received: ["view_invoice"],
        NotificationEventType.follow_up_reminder: ["schedule_now", "view_details"],
    }
    return actions.get(event_type, ["view_details"])


def _build_communication_card(
    event: NotificationEvent,
    doctor_name: str | None = None,
    clinic_name: str | None = None,
    is_read: bool = False,
    linked_documents: list[DocumentLink] | None = None,
) -> CommunicationCard:
    """Build a patient-safe CommunicationCard from a NotificationEvent."""
    return CommunicationCard(
        id=event.id,
        event_type=event.event_type.value if event.event_type else "unknown",
        title=_get_event_title(event.event_type),
        summary=_get_event_summary(event.event_type),
        created_at=event.created_at,
        is_read=is_read,
        is_urgent=_is_urgent_event(event.event_type),
        doctor_name=doctor_name,
        clinic_name=clinic_name,
        linked_appointment_id=event.appointment_id,
        linked_bill_id=event.bill_id,
        linked_documents=linked_documents or [],
        cta_actions=_get_cta_actions(event.event_type),
    )


def _build_reminder_card(
    event: NotificationEvent,
    urgency: str,
    doctor_name: str | None = None,
    clinic_name: str | None = None,
) -> ReminderCard:
    """Build a ReminderCard from a NotificationEvent."""
    return ReminderCard(
        id=event.id,
        event_type=event.event_type.value if event.event_type else "unknown",
        title=_get_event_title(event.event_type),
        reminder_date=event.created_at,
        urgency=urgency,
        doctor_name=doctor_name,
        clinic_name=clinic_name,
        linked_appointment_id=event.appointment_id,
        linked_bill_id=event.bill_id,
        cta_actions=_get_cta_actions(event.event_type),
    )


def _get_doctor_name_for_event(db: Session, event: NotificationEvent) -> str | None:
    """Resolve doctor name from a notification event."""
    if event.doctor_id:
        doctor = db.get(Doctor, event.doctor_id)
        if doctor:
            return doctor.name
    return None


def _get_clinic_name_for_event(db: Session, event: NotificationEvent) -> str | None:
    """Resolve clinic name from a notification event."""
    if event.doctor_id:
        doctor = db.get(Doctor, event.doctor_id)
        if doctor:
            return getattr(doctor, "clinic_name", None)
    return None


def _get_linked_documents(
    db: Session,
    event: NotificationEvent,
    patient_id: UUID,
) -> list[DocumentLink]:
    """Get document links associated with a notification event.
    
    Reuses existing document generation APIs.
    Documents are only linked if they belong to the patient.
    """
    documents: list[DocumentLink] = []
    
    if event.appointment_id:
        # Check for encounter summary
        appointment = db.get(Appointment, event.appointment_id)
        if appointment and appointment.patient_id == patient_id:
            if appointment.status == AppointmentStatus.completed:
                documents.append(
                    DocumentLink(
                        document_type="encounter_summary",
                        appointment_id=event.appointment_id,
                    )
                )
            # Check for prescription
            if appointment.prescriptions:
                documents.append(
                    DocumentLink(
                        document_type="prescription",
                        appointment_id=event.appointment_id,
                    )
                )
    
    if event.bill_id:
        # Check for invoice
        bill = db.get(Billing, event.bill_id)
        if bill:
            documents.append(
                DocumentLink(
                    document_type="invoice",
                    appointment_id=event.appointment_id,
                )
            )
    
    return documents


def _get_read_event_ids(
    db: Session,
    patient_id: UUID,
    event_ids: list[UUID],
) -> set[UUID]:
    """Get the set of event IDs that have been read by the patient.
    
    Uses existing NotificationDelivery records with status='read' for in_app channel.
    This preserves the existing delivery tracking infrastructure.
    """
    if not event_ids:
        return set()
    
    result = db.execute(
        select(NotificationDelivery.notification_event_id)
        .where(
            NotificationDelivery.notification_event_id.in_(event_ids),
            NotificationDelivery.status == NotificationDeliveryStatus.read,
        )
    )
    return {row[0] for row in result}


def _mark_event_as_read(
    db: Session,
    event_id: UUID,
    patient_id: UUID,
    tenant_id: UUID,
) -> bool:
    """Mark a notification event as read by updating delivery status.
    
    Uses existing NotificationDelivery infrastructure.
    Creates or updates an in_app delivery record with status='read'.
    """
    # Check if there's already an in_app delivery
    delivery = db.execute(
        select(NotificationDelivery)
        .where(
            NotificationDelivery.notification_event_id == event_id,
        )
        .limit(1)
    ).scalar_one_or_none()
    
    if delivery:
        # Update existing delivery to read
        crud_notification.update_delivery_status(
            db,
            delivery.id,
            status=NotificationDeliveryStatus.read,
        )
        return True
    
    # Create a new in_app delivery record with read status
    crud_notification.create_notification_delivery(
        db,
        notification_event_id=event_id,
        channel="in_app",
        recipient=str(patient_id),
    )
    # Update to read
    # We need to find the delivery we just created
    new_delivery = db.execute(
        select(NotificationDelivery)
        .where(
            NotificationDelivery.notification_event_id == event_id,
            NotificationDelivery.channel == "in_app",
        )
        .order_by(NotificationDelivery.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    
    if new_delivery:
        crud_notification.update_delivery_status(
            db,
            new_delivery.id,
            status=NotificationDeliveryStatus.read,
        )
        return True
    
    return False


# ── Main service functions ───────────────────────────────────────────────────


def get_patient_communication_aggregate(
    db: Session,
    current_user: User,
) -> PatientCommunicationAggregate:
    """
    Build the full PatientCommunicationAggregate for the authenticated patient.

    This is the SINGLE entry point for the patient communication center.
    It composes existing NotificationEvent data into a patient-friendly view.

    Args:
        db: Database session.
        current_user: The authenticated user (must be patient role).

    Returns:
        PatientCommunicationAggregate with all communication data.

    Raises:
        ForbiddenError: If the user is not a patient.
    """
    patient = _resolve_patient(db, current_user)
    now = _now_utc()

    # ── 1. Load notification events for this patient ───────────────────────
    events, total = crud_notification.get_notification_events_for_patient(
        db, patient.id, patient.tenant_id, skip=0, limit=50
    )

    # ── 2. Get read status for events ──────────────────────────────────────
    event_ids = [e.id for e in events]
    read_ids = _get_read_event_ids(db, patient.id, event_ids)

    # ── 3. Build communication cards ───────────────────────────────────────
    recent_notifications: list[CommunicationCard] = []
    reminders_by_urgency: dict[str, list[ReminderCard]] = {
        "urgent": [],
        "upcoming": [],
        "completed": [],
    }
    all_documents: list[DocumentLink] = []

    for event in events:
        doctor_name = _get_doctor_name_for_event(db, event)
        clinic_name = _get_clinic_name_for_event(db, event)
        is_read = event.id in read_ids
        linked_docs = _get_linked_documents(db, event, patient.id)
        all_documents.extend(linked_docs)

        # Build communication card
        card = _build_communication_card(
            event,
            doctor_name=doctor_name,
            clinic_name=clinic_name,
            is_read=is_read,
            linked_documents=linked_docs,
        )
        recent_notifications.append(card)

        # Build reminder cards by urgency
        if event.event_type in (
            NotificationEventType.appointment_reminder,
            NotificationEventType.follow_up_reminder,
        ):
            # Determine urgency based on event type and timing
            if event.event_type == NotificationEventType.follow_up_reminder:
                urgency = "urgent"
            elif event.event_type == NotificationEventType.appointment_reminder:
                # Check if the appointment is in the past
                if event.appointment_id:
                    appointment = db.get(Appointment, event.appointment_id)
                    if appointment and appointment.appointment_time < now:
                        urgency = "completed"
                    else:
                        urgency = "upcoming"
                else:
                    urgency = "upcoming"
            else:
                urgency = "upcoming"

            reminder = _build_reminder_card(
                event,
                urgency=urgency,
                doctor_name=doctor_name,
                clinic_name=clinic_name,
            )
            reminders_by_urgency[urgency].append(reminder)

    # ── 4. Load communication preferences ──────────────────────────────────
    from app.services.patient_communication_preferences_service import (
        get_patient_preferences,
    )

    try:
        prefs = get_patient_preferences(db, patient.id, patient.tenant_id)
        preferences = CommunicationPreferencesRead(
            email_enabled=prefs.email_enabled,
            sms_enabled=prefs.sms_enabled,
            whatsapp_enabled=prefs.whatsapp_enabled,
            reminder_enabled=prefs.reminder_enabled,
            quiet_hours_start=prefs.quiet_hours_start,
            quiet_hours_end=prefs.quiet_hours_end,
            locale=prefs.locale,
            opt_out_all=prefs.opt_out_all,
        )
    except NotFoundError:
        preferences = CommunicationPreferencesRead()

    # ── 5. Compute unread count ────────────────────────────────────────────
    unread_count = len([c for c in recent_notifications if not c.is_read])

    # ── 6. Deduplicate documents ───────────────────────────────────────────
    seen_docs: set[tuple[str, str | None]] = set()
    unique_documents: list[DocumentLink] = []
    for doc in all_documents:
        key = (doc.document_type, str(doc.appointment_id) if doc.appointment_id else "")
        if key not in seen_docs:
            seen_docs.add(key)
            unique_documents.append(doc)

    # ── 7. Log audit event ─────────────────────────────────────────────────
    log_structured_audit_event(
        event="communication_aggregate_viewed",
        tenant_id=patient.tenant_id,
        resource_id=str(patient.id),
        actor_id=str(current_user.id),
        status="success",
        unread_count=unread_count,
        total_notifications=len(recent_notifications),
    )

    # ── 8. Assemble aggregate ──────────────────────────────────────────────
    return PatientCommunicationAggregate(
        recent_notifications=recent_notifications,
        unread_count=unread_count,
        reminders_by_urgency=reminders_by_urgency,
        preferences=preferences,
        linked_documents=unique_documents,
    )


def get_patient_communication_timeline(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[CommunicationCard], int]:
    """
    Get paginated communication cards for the patient timeline.

    Args:
        db: Database session.
        current_user: The authenticated user (must be patient role).
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        Tuple of (list of CommunicationCard, total count).
    """
    patient = _resolve_patient(db, current_user)

    events, total = crud_notification.get_notification_events_for_patient(
        db, patient.id, patient.tenant_id, skip=skip, limit=limit
    )

    event_ids = [e.id for e in events]
    read_ids = _get_read_event_ids(db, patient.id, event_ids)

    cards: list[CommunicationCard] = []
    for event in events:
        doctor_name = _get_doctor_name_for_event(db, event)
        clinic_name = _get_clinic_name_for_event(db, event)
        is_read = event.id in read_ids
        linked_docs = _get_linked_documents(db, event, patient.id)

        cards.append(
            _build_communication_card(
                event,
                doctor_name=doctor_name,
                clinic_name=clinic_name,
                is_read=is_read,
                linked_documents=linked_docs,
            )
        )

    return cards, total


def get_patient_reminders(
    db: Session,
    current_user: User,
) -> dict[str, list[ReminderCard]]:
    """
    Get reminders grouped by urgency for the patient.

    Args:
        db: Database session.
        current_user: The authenticated user (must be patient role).

    Returns:
        Dict with 'urgent', 'upcoming', 'completed' lists of ReminderCard.
    """
    patient = _resolve_patient(db, current_user)
    now = _now_utc()

    # Get reminder-type events
    events, _ = crud_notification.get_notification_events_for_patient(
        db, patient.id, patient.tenant_id, skip=0, limit=100
    )

    reminders_by_urgency: dict[str, list[ReminderCard]] = {
        "urgent": [],
        "upcoming": [],
        "completed": [],
    }

    for event in events:
        if event.event_type not in (
            NotificationEventType.appointment_reminder,
            NotificationEventType.follow_up_reminder,
        ):
            continue

        doctor_name = _get_doctor_name_for_event(db, event)
        clinic_name = _get_clinic_name_for_event(db, event)

        if event.event_type == NotificationEventType.follow_up_reminder:
            urgency = "urgent"
        elif event.event_type == NotificationEventType.appointment_reminder:
            if event.appointment_id:
                appointment = db.get(Appointment, event.appointment_id)
                if appointment and appointment.appointment_time < now:
                    urgency = "completed"
                else:
                    urgency = "upcoming"
            else:
                urgency = "upcoming"
        else:
            urgency = "upcoming"

        reminder = _build_reminder_card(
            event,
            urgency=urgency,
            doctor_name=doctor_name,
            clinic_name=clinic_name,
        )
        reminders_by_urgency[urgency].append(reminder)

    return reminders_by_urgency


class PatientCommunicationService:
    """Class-based wrapper for patient communication operations.
    
    Provides the interface expected by tests that instantiate the service
    with db and current_user parameters.
    """
    
    def __init__(self, db: Session, current_user: User) -> None:
        self.db = db
        self.current_user = current_user
    
    def get_aggregate(self) -> PatientCommunicationAggregate:
        return get_patient_communication_aggregate(self.db, self.current_user)
    
    def get_timeline(self, skip: int = 0, limit: int = 20) -> PatientCommunicationAggregate:
        cards, total = get_patient_communication_timeline(self.db, self.current_user, skip=skip, limit=limit)
        # Return a simple aggregate-like object for test compatibility
        from collections import namedtuple
        TimelineResult = namedtuple("TimelineResult", ["items", "total", "skip", "limit"])
        return TimelineResult(items=cards, total=total, skip=skip, limit=limit)
    
    def get_reminders(self) -> dict[str, list[ReminderCard]]:
        return get_patient_reminders(self.db, self.current_user)
    
    def get_unread_count(self) -> int:
        return get_unread_count(self.db, self.current_user)
    
    def mark_as_read(self, event_id: UUID) -> bool:
        return mark_notification_as_read(self.db, self.current_user, event_id)


def get_unread_count(
    db: Session,
    current_user: User,
) -> int:
    """
    Get the unread notification count for the patient.

    Args:
        db: Database session.
        current_user: The authenticated user (must be patient role).

    Returns:
        Number of unread notifications.
    """
    patient = _resolve_patient(db, current_user)

    events, total = crud_notification.get_notification_events_for_patient(
        db, patient.id, patient.tenant_id, skip=0, limit=100
    )

    event_ids = [e.id for e in events]
    read_ids = _get_read_event_ids(db, patient.id, event_ids)

    return total - len(read_ids)


def mark_notification_as_read(
    db: Session,
    current_user: User,
    event_id: UUID,
) -> bool:
    """
    Mark a notification event as read by the patient.

    Uses existing NotificationDelivery infrastructure.
    Creates or updates an in_app delivery record with status='read'.

    Args:
        db: Database session.
        current_user: The authenticated user (must be patient role).
        event_id: The notification event ID to mark as read.

    Returns:
        True if successfully marked as read.

    Raises:
        ForbiddenError: If the user is not a patient or doesn't own the notification.
        NotFoundError: If the notification event is not found.
    """
    patient = _resolve_patient(db, current_user)

    # Verify the event belongs to this patient
    event = crud_notification.get_notification_event(db, event_id)
    if event is None:
        raise NotFoundError("Notification not found")
    if event.patient_id != patient.id:
        raise ForbiddenError("This notification does not belong to you")
    if event.tenant_id != patient.tenant_id:
        raise ForbiddenError("Tenant mismatch")

    result = _mark_event_as_read(db, event_id, patient.id, patient.tenant_id)
    db.flush()

    # Log audit event
    log_structured_audit_event(
        event="communication_viewed",
        tenant_id=patient.tenant_id,
        resource_id=str(event_id),
        actor_id=str(current_user.id),
        status="success",
    )

    return result
