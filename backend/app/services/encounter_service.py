"""
Encounter Aggregate service — canonical READ-ONLY aggregate for the encounter workspace.

This service loads the EncounterDetailAggregate in a small number of efficient queries.
It enforces invariants (tenant alignment, patient isolation) and logs structured warnings
for any violations without raising (fail-safe for reads).

Appointment remains the encounter anchor. No separate Encounter table exists.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.crud import crud_billing
from app.models.appointment import Appointment, Prescription
from app.models.billing import Billing
from app.models.inventory import AppointmentInventoryUsage
from app.models.user import User
from app.schemas.encounter import EncounterDetailAggregate, TimelineContext
from app.services import appointment_service
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


# ── Invariant helpers ──────────────────────────────────────────────────────


def _log_invariant_warning(
    message: str,
    *,
    appointment_id: UUID,
    **extra: object,
) -> None:
    """Log a structured warning for invariant violations (fail-safe for reads)."""
    logger.warning(
        "[ENCOUNTER_INVARIANT] %s appointment_id=%s %s",
        message,
        appointment_id,
        " ".join(f"{k}={v}" for k, v in extra.items()),
    )


def _validate_prescription_invariants(
    appointment: Appointment,
    prescriptions: list[Prescription],
) -> None:
    """Validate prescription invariants against the appointment. Logs warnings on violation."""
    for rx in prescriptions:
        if rx.tenant_id != appointment.tenant_id:
            _log_invariant_warning(
                "prescription.tenant_id != appointment.tenant_id",
                appointment_id=appointment.id,
                prescription_id=rx.id,
                rx_tenant=rx.tenant_id,
                appt_tenant=appointment.tenant_id,
            )
        if rx.patient_id != appointment.patient_id:
            _log_invariant_warning(
                "prescription.patient_id != appointment.patient_id",
                appointment_id=appointment.id,
                prescription_id=rx.id,
                rx_patient=rx.patient_id,
                appt_patient=appointment.patient_id,
            )


def _validate_bill_invariant(
    appointment: Appointment,
    bill: Billing | None,
) -> None:
    """Validate bill invariants against the appointment. Logs warnings on violation."""
    if bill is None:
        return
    if bill.appointment_id != appointment.id:
        _log_invariant_warning(
            "bill.appointment_id != appointment.id",
            appointment_id=appointment.id,
            bill_id=bill.id,
            bill_appointment=bill.appointment_id,
        )
    if bill.tenant_id is not None and bill.tenant_id != appointment.tenant_id:
        _log_invariant_warning(
            "bill.tenant_id != appointment.tenant_id",
            appointment_id=appointment.id,
            bill_id=bill.id,
            bill_tenant=bill.tenant_id,
            appt_tenant=appointment.tenant_id,
        )


def _validate_vitals_invariant(
    appointment: Appointment,
) -> None:
    """Vitals are scoped to appointment by FK; no cross-entity check needed beyond existence."""
    # Vitals are already scoped via AppointmentVitals.appointment_id FK.
    # No additional cross-entity invariant required.
    pass


def _enforce_encounter_invariants(
    appointment: Appointment,
    prescriptions: list[Prescription],
    bill: Billing | None,
) -> None:
    """
    Validate all encounter invariants for the aggregate.
    Fail-safe: logs structured warnings but does NOT raise for reads.
    """
    _validate_prescription_invariants(appointment, prescriptions)
    _validate_bill_invariant(appointment, bill)
    _validate_vitals_invariant(appointment)


# ── Query helpers ──────────────────────────────────────────────────────────


def _load_appointment_with_relations(
    db: Session,
    appointment_id: UUID,
) -> Appointment | None:
    """
    Load the appointment with all related entities eagerly loaded.
    This is the primary query — it loads everything in a small number of round-trips.
    """
    stmt = (
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .where(Appointment.is_deleted == False)
        .options(
            # Core relationships
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            # Vitals (one-to-one)
            selectinload(Appointment.vitals),
            # Prescriptions with items
            selectinload(Appointment.prescriptions).selectinload(Prescription.items),
            # Inventory usage with item details
            selectinload(Appointment.inventory_usages).joinedload(
                AppointmentInventoryUsage.item
            ),
        )
    )
    return db.scalars(stmt).unique().first()


def _load_timeline_context(
    db: Session,
    patient_id: UUID,
    exclude_appointment_id: UUID,
    limit: int = 5,
) -> TimelineContext:
    """Load lightweight patient history for encounter context."""
    stmt = (
        select(Appointment.id)
        .where(Appointment.patient_id == patient_id)
        .where(Appointment.is_deleted == False)
        .where(Appointment.id != exclude_appointment_id)
        .order_by(Appointment.appointment_time.desc())
        .limit(limit)
    )
    rows = db.scalars(stmt).all()
    return TimelineContext(
        previous_visit_count=len(rows),
        previous_appointment_ids=list(rows),
    )


# ── Main entry point ───────────────────────────────────────────────────────


def get_encounter_detail(
    db: Session,
    appointment_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    *,
    include_timeline: bool = True,
) -> EncounterDetailAggregate:
    """
    Load the canonical EncounterDetailAggregate for the given appointment.

    This is the SINGLE entry point for encounter workspace rendering.
    It performs efficient eager loading (selectinload/joinedload) to avoid N+1 queries.

    Authorization is delegated to ``appointment_service.authorize_appointment_read``
    which uses existing capability-based checks.

    Invariant violations are logged as structured warnings but do NOT raise
    (fail-safe for reads).

    Args:
        db: Database session.
        appointment_id: The appointment (encounter anchor) ID.
        current_user: The authenticated user.
        tenant_id: Resolved tenant scope from request.
        include_timeline: Whether to load patient history context (default: True).

    Returns:
        EncounterDetailAggregate with all related entities.

    Raises:
        NotFoundError: If the appointment does not exist.
    """
    # 1. Load appointment with all relations (1 query with eager loading)
    appointment = _load_appointment_with_relations(db, appointment_id)
    if appointment is None:
        raise NotFoundError("Encounter not found")

    # 2. Authorize access (capability-based, existing pattern)
    appointment_service.authorize_appointment_read(
        db,
        appointment,
        current_user,
        tenant_id,
        rbac_action="read_encounter_detail",
    )

    # 3. Load bill (1 simple query)
    bill = crud_billing.get_bill_by_appointment(db, appointment_id)

    # 4. Enforce invariants (fail-safe — logs warnings, does not raise)
    _enforce_encounter_invariants(
        appointment,
        list(appointment.prescriptions),
        bill,
    )

    # 5. Build the aggregate
    prescriptions_list = list(appointment.prescriptions)
    prescription_count = len(prescriptions_list)
    prescription_item_count = sum(len(rx.items) for rx in prescriptions_list)
    logger.info(
        "[ENCOUNTER_AGG_TRACE] get_encounter_detail: appointment=%s patient=%s tenant=%s "
        "prescriptions=%d prescription_items=%d bill=%s",
        appointment.id,
        appointment.patient_id,
        appointment.tenant_id,
        prescription_count,
        prescription_item_count,
        bill.id if bill else "None",
    )

    aggregate = EncounterDetailAggregate(
        appointment=appointment_service.appointment_to_read(db, appointment),
        patient=appointment.patient,
        doctor=appointment.doctor,
        vitals=appointment.vitals,
        prescriptions=prescriptions_list,
        inventory_usage=list(appointment.inventory_usages),
        bill=bill,
        timeline_context=None,
    )

    # 6. Optional timeline context (1 additional query)
    if include_timeline and appointment.patient_id:
        aggregate.timeline_context = _load_timeline_context(
            db,
            patient_id=appointment.patient_id,
            exclude_appointment_id=appointment.id,
        )

    return aggregate
