"""
Front desk service — receptionist operational actions.

Provides:
- mark_arrived: patient arrival
- check_in_patient: check-in after arrival
- cancel_appointment: operational cancellation
- mark_no_show: no-show recording
- create_walk_in: same-day walk-in appointment creation
- reschedule_hook: lightweight reschedule support

All transitions enforce valid state flows and log audit events.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud import crud_appointment, crud_clinic_queue
from app.models.appointment import Appointment, AppointmentStatus
from app.models.clinic_queue import ClinicQueueEntry, ClinicQueueStatus
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import create_appointment
from app.services.exceptions import NotFoundError, ValidationError
from app.services.queue_service import add_appointment_to_queue

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Valid state transitions for front desk operations
# ──────────────────────────────────────────────────────────────────────────────

_VALID_ARRIVAL_FROM = {
    AppointmentStatus.scheduled,
    AppointmentStatus.confirmed,
}

_VALID_CHECKIN_FROM = {
    AppointmentStatus.arrived,
}

_VALID_CANCEL_FROM = {
    AppointmentStatus.scheduled,
    AppointmentStatus.confirmed,
    AppointmentStatus.arrived,
    AppointmentStatus.checked_in,
    AppointmentStatus.vitals_completed,
    AppointmentStatus.waiting_for_doctor,
}

_VALID_NO_SHOW_FROM = {
    AppointmentStatus.arrived,
    AppointmentStatus.checked_in,
}


def _validate_appointment_tenant(
    appointment: Appointment, tenant_id: UUID
) -> None:
    """Validate that an appointment belongs to the expected tenant."""
    if appointment.tenant_id != tenant_id:
        raise ValidationError(
            f"Appointment {appointment.id} does not belong to tenant {tenant_id}"
        )


def mark_arrived(
    db: Session,
    appointment_id: UUID,
    current_user_id: UUID,
    tenant_id: UUID,
) -> Appointment:
    """Mark an appointment as arrived and add to the clinic queue."""
    appointment = _get_appointment_for_action(db, appointment_id, tenant_id)

    if appointment.status not in _VALID_ARRIVAL_FROM:
        raise ValidationError(
            f"Cannot mark arrived from status '{appointment.status.value}'. "
            f"Valid states: {[s.value for s in _VALID_ARRIVAL_FROM]}"
        )

    old_status = appointment.status
    appointment.status = AppointmentStatus.arrived
    db.add(appointment)
    db.flush()

    # Add to clinic queue
    add_appointment_to_queue(
        db=db,
        appointment_id=appointment.id,
        tenant_id=appointment.tenant_id,
        doctor_id=appointment.doctor_id,
        patient_id=appointment.patient_id,
        created_by=current_user_id,
    )

    _log_audit(
        event="appointment_arrived",
        appointment=appointment,
        actor_id=current_user_id,
        previous_status=old_status.value,
        new_status=AppointmentStatus.arrived.value,
    )

    logger.info(
        "Appointment %s marked arrived by user %s",
        appointment_id,
        current_user_id,
    )
    return appointment


def check_in_patient(
    db: Session,
    appointment_id: UUID,
    current_user_id: UUID,
    tenant_id: UUID,
) -> Appointment:
    """Check in a patient after arrival."""
    appointment = _get_appointment_for_action(db, appointment_id, tenant_id)

    if appointment.status not in _VALID_CHECKIN_FROM:
        raise ValidationError(
            f"Cannot check-in from status '{appointment.status.value}'. "
            f"Valid states: {[s.value for s in _VALID_CHECKIN_FROM]}"
        )

    old_status = appointment.status
    appointment.status = AppointmentStatus.checked_in
    db.add(appointment)
    db.flush()

    _log_audit(
        event="appointment_checked_in",
        appointment=appointment,
        actor_id=current_user_id,
        previous_status=old_status.value,
        new_status=AppointmentStatus.checked_in.value,
    )

    logger.info(
        "Appointment %s checked in by user %s",
        appointment_id,
        current_user_id,
    )
    return appointment


def cancel_appointment(
    db: Session,
    appointment_id: UUID,
    current_user_id: UUID,
    tenant_id: UUID,
) -> Appointment:
    """Cancel an appointment from any pre-consultation state."""
    appointment = _get_appointment_for_action(db, appointment_id, tenant_id)

    if appointment.status not in _VALID_CANCEL_FROM:
        raise ValidationError(
            f"Cannot cancel from status '{appointment.status.value}'. "
            f"Valid states: {[s.value for s in _VALID_CANCEL_FROM]}"
        )

    old_status = appointment.status
    appointment.status = AppointmentStatus.cancelled
    db.add(appointment)
    db.flush()

    # Remove from active queue if present
    queue_entry = crud_clinic_queue.get_active_queue_entry_for_appointment(
        db, appointment_id
    )
    if queue_entry:
        crud_clinic_queue.update_queue_status(
            db, queue_entry, ClinicQueueStatus.skipped
        )

    _log_audit(
        event="appointment_cancelled_by_front_desk",
        appointment=appointment,
        actor_id=current_user_id,
        previous_status=old_status.value,
        new_status=AppointmentStatus.cancelled.value,
    )

    logger.info(
        "Appointment %s cancelled by user %s",
        appointment_id,
        current_user_id,
    )
    return appointment


def mark_no_show(
    db: Session,
    appointment_id: UUID,
    current_user_id: UUID,
    tenant_id: UUID,
) -> Appointment:
    """Mark an appointment as no-show."""
    appointment = _get_appointment_for_action(db, appointment_id, tenant_id)

    if appointment.status not in _VALID_NO_SHOW_FROM:
        raise ValidationError(
            f"Cannot mark no-show from status '{appointment.status.value}'. "
            f"Valid states: {[s.value for s in _VALID_NO_SHOW_FROM]}"
        )

    old_status = appointment.status
    appointment.status = AppointmentStatus.no_show
    db.add(appointment)
    db.flush()

    # Remove from active queue
    queue_entry = crud_clinic_queue.get_active_queue_entry_for_appointment(
        db, appointment_id
    )
    if queue_entry:
        crud_clinic_queue.update_queue_status(
            db, queue_entry, ClinicQueueStatus.skipped
        )

    _log_audit(
        event="appointment_no_show",
        appointment=appointment,
        actor_id=current_user_id,
        previous_status=old_status.value,
        new_status=AppointmentStatus.no_show.value,
    )

    logger.info(
        "Appointment %s marked no-show by user %s",
        appointment_id,
        current_user_id,
    )
    return appointment


def create_walk_in(
    db: Session,
    patient_id: UUID,
    doctor_id: UUID,
    tenant_id: UUID,
    current_user_id: UUID,
) -> Appointment:
    """Create a same-day walk-in appointment and add to queue.

    Walk-ins bypass the scheduling flow: they are created with status=arrived
    and immediately added to the clinic queue.
    """
    now_utc = datetime.now(timezone.utc)

    # Create appointment using existing service with AppointmentCreate schema
    from app.models.user import User

    # We need a minimal User-like object for the create_appointment call
    # Since we're in a service context, we create the appointment directly
    # using the crud layer to avoid the full RBAC flow
    from app.crud import crud_appointment

    appointment_data = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": now_utc,
        "status": AppointmentStatus.arrived,
        "tenant_id": tenant_id,
        "created_by": current_user_id,
    }

    appointment = crud_appointment.add_appointment(db, appointment_data)
    db.flush()

    # Add to queue with priority for walk-ins
    add_appointment_to_queue(
        db=db,
        appointment_id=appointment.id,
        tenant_id=appointment.tenant_id,
        doctor_id=appointment.doctor_id,
        patient_id=appointment.patient_id,
        created_by=current_user_id,
        priority=1,  # Walk-ins get priority=1
    )

    _log_audit(
        event="walk_in_created",
        appointment=appointment,
        actor_id=current_user_id,
        previous_status="none",
        new_status=AppointmentStatus.arrived.value,
    )

    logger.info(
        "Walk-in appointment %s created for patient %s with doctor %s",
        appointment.id,
        patient_id,
        doctor_id,
    )
    return appointment


def reschedule_hook(
    db: Session,
    appointment_id: UUID,
    new_time: datetime,
    current_user_id: UUID,
    tenant_id: UUID,
) -> Appointment:
    """Lightweight reschedule: updates appointment time and resets to scheduled.

    This is a hook that calls the existing appointment update infrastructure.
    Full reschedule logic (availability validation, notification) is future scope.
    """
    appointment = _get_appointment_for_action(db, appointment_id, tenant_id)

    if appointment.status in (
        AppointmentStatus.completed,
        AppointmentStatus.cancelled,
        AppointmentStatus.no_show,
    ):
        raise ValidationError(
            f"Cannot reschedule appointment in terminal state '{appointment.status.value}'"
        )

    old_time = appointment.appointment_time
    old_status = appointment.status

    appointment.appointment_time = new_time
    appointment.status = AppointmentStatus.scheduled
    db.add(appointment)
    db.flush()

    _log_audit(
        event="appointment_rescheduled",
        appointment=appointment,
        actor_id=current_user_id,
        previous_status=old_status.value,
        new_status=AppointmentStatus.scheduled.value,
        extra={"old_time": str(old_time), "new_time": str(new_time)},
    )

    logger.info(
        "Appointment %s rescheduled from %s to %s by user %s",
        appointment_id,
        old_time,
        new_time,
        current_user_id,
    )
    return appointment


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


def _get_appointment_for_action(
    db: Session,
    appointment_id: UUID,
    tenant_id: UUID,
) -> Appointment:
    """Get and validate an appointment exists and belongs to the tenant."""
    appointment = crud_appointment.get_appointment(db, appointment_id)
    if not appointment:
        raise NotFoundError(f"Appointment {appointment_id} not found")
    _validate_appointment_tenant(appointment, tenant_id)
    return appointment


def _log_audit(
    event: str,
    appointment: Appointment,
    actor_id: UUID,
    previous_status: str,
    new_status: str,
    extra: dict | None = None,
) -> None:
    """Log a structured audit event for operational transitions."""
    audit_logger = logging.getLogger("audit")
    record = {
        "event": event,
        "tenant_id": str(appointment.tenant_id),
        "resource_id": str(appointment.id),
        "actor_id": str(actor_id),
        "appointment_id": str(appointment.id),
        "doctor_id": str(appointment.doctor_id),
        "patient_id": str(appointment.patient_id),
        "previous_status": previous_status,
        "new_status": new_status,
    }
    if extra:
        record.update(extra)
    audit_logger.info("[AUDIT] %s", json.dumps(record))
