from datetime import datetime, timezone
import hashlib
import json
import logging
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.data_scope import DataScopeKind, ResolvedDataScope
from app.core.metrics import inc_counter
from app.core.permissions import has_tenant_admin_privileges
from app.core.clinical_capabilities import has_clinician_capability
from app.core.workspace_context import ActiveWorkspace
from app.crud import crud_appointment, crud_billing, crud_medication_schedule
from app.models.appointment import Appointment, AppointmentStatus, Prescription
from app.models.patient_medication_schedule import PatientMedicationSchedule
from app.models.user import User, UserRole
from app.services import doctor_service, doctor_slot_service, inventory_service, patient_service
from app.utils.appointment_datetime import normalize_appointment_time_utc
from app.core.tenancy import non_nil_tenant_id
from app.services.appointment_invariant_enforcement import (
    AppointmentInvariantGuard,
    revalidate_appointment_invariants,
)
from app.services.appointment_invariants import validate_appointment_invariants
from app.services.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.services.security_audit import (
    assert_authorized,
    log_audit_mutation,
    log_structured_audit_event,
    log_rbac_mutation_violation,
)
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    MarkAppointmentCompletedRequest,
    PrescriptionCreate,
    VitalSignsCreate,
)

logger = logging.getLogger(__name__)

# Backward-compatible timezone resolution for naive datetimes sent by frontend.
# The frontend sends wall-clock time in the clinic's local timezone without an explicit
# UTC offset.  Historically the schema validator assumed UTC, which caused every
# appointment to fail for clinics east of UTC (e.g. Asia/Kolkata = UTC+5:30).
#
# Strategy:
#   - If the datetime is tz-aware it is already UTC (validated by Pydantic).  Pass through.
#   - If the datetime is naive, interpret it as the doctor's local timezone, then convert to UTC.
_DOCTOR_TZ_CACHE: dict[str, ZoneInfo] = {}


def _doctor_zoneinfo(doctor_tz_name: str | None) -> ZoneInfo:
    name = (doctor_tz_name or "UTC").strip() or "UTC"
    cached = _DOCTOR_TZ_CACHE.get(name)
    if cached is not None:
        return cached
    try:
        zi = ZoneInfo(name)
    except (ZoneInfoNotFoundError, OSError):
        logger.warning("ZoneInfo not found for %r, falling back to UTC", name)
        zi = ZoneInfo("UTC")
    _DOCTOR_TZ_CACHE[name] = zi
    return zi


def resolve_appointment_timezone(doctor, dt: datetime) -> datetime:
    """Return a UTC-normalized datetime, interpreting naive input as doctor local time."""
    if dt.tzinfo is None:
        tz = _doctor_zoneinfo(getattr(doctor, "timezone", None) or "UTC")
        return dt.replace(tzinfo=tz).astimezone(timezone.utc).replace(second=0, microsecond=0)
    return normalize_appointment_time_utc(dt)


def _appointment_audit_ctx(appt: Appointment) -> dict[str, str]:
    return {
        "doctor_id": str(appt.doctor_id),
        "patient_id": str(appt.patient_id),
    }


def _appointment_payload_hash(appointment_in: AppointmentCreate) -> str:
    body = appointment_in.model_dump(mode="json")
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _ensure_can_list_appointments(current_user: User) -> None:
    if current_user.role not in (
        UserRole.admin,
        UserRole.super_admin,
        UserRole.doctor,
        UserRole.patient,
        UserRole.staff,
    ):
        log_rbac_mutation_violation(current_user, "appointment")
        raise ForbiddenError("Not authorized")


def _validate_patient_and_doctor_exist(
    db: Session,
    patient_id: UUID,
    doctor_id: UUID,
) -> None:
    patient_service.get_patient_or_404(db, patient_id)
    doctor_service.get_doctor_or_404(db, doctor_id)


def _validate_doctor_availability(
    db: Session,
    doctor_id: UUID,
    appointment_time: datetime,
    existing_appointment_id: UUID | None = None,
) -> None:
    from datetime import timedelta

    appointment_time = normalize_appointment_time_utc(appointment_time)
    start_buffer = appointment_time - timedelta(minutes=30)
    end_buffer = appointment_time + timedelta(minutes=30)

    stmt = select(crud_appointment.Appointment).where(
        crud_appointment.Appointment.doctor_id == doctor_id,
        crud_appointment.Appointment.appointment_time >= start_buffer,
        crud_appointment.Appointment.appointment_time <= end_buffer,
        crud_appointment.Appointment.status == crud_appointment.AppointmentStatus.scheduled,
        crud_appointment.Appointment.is_deleted == False,
    )
    booked_appointments = list(db.scalars(stmt).all())

    for booked in booked_appointments:
        if existing_appointment_id is not None and booked.id == existing_appointment_id:
            continue
        booked_t = normalize_appointment_time_utc(booked.appointment_time)
        if abs((booked_t - appointment_time).total_seconds()) < 1800:
            raise ConflictError("Doctor already has an appointment within 30 minutes of this time slot")


def _validate_appointment_time_in_future(appointment_time: datetime) -> None:
    at = normalize_appointment_time_utc(appointment_time)
    if at <= datetime.now(timezone.utc):
        raise ValidationError("Cannot book past slots")


def _validate_slot_not_double_booked(
    db: Session,
    doctor_id: UUID,
    appointment_time: datetime,
    *,
    exclude_appointment_id: UUID | None = None,
) -> None:
    if crud_appointment.doctor_has_non_cancelled_appointment_at(
        db, doctor_id, appointment_time, exclude_appointment_id=exclude_appointment_id
    ):
        raise ValidationError("Slot already booked")


def _validate_patient_no_other_appointment_same_instant(
    db: Session,
    patient_id: UUID,
    appointment_time: datetime,
    *,
    exclude_appointment_id: UUID | None = None,
) -> None:
    if crud_appointment.patient_has_scheduled_appointment_at(
        db,
        patient_id,
        appointment_time,
        exclude_appointment_id=exclude_appointment_id,
    ):
        raise ValidationError("You already have an appointment at this time")


def _validate_appointment_can_be_completed_time(appointment_time: datetime) -> None:
    """
    Validate that an appointment can be completed based on its scheduled time.
    """
    from datetime import timedelta

    appointment_time = normalize_appointment_time_utc(appointment_time)
    now_utc = datetime.now(timezone.utc)
    grace_window = timedelta(minutes=15)
    completion_cutoff = appointment_time - grace_window

    if now_utc < completion_cutoff:
        remaining = completion_cutoff - now_utc
        minutes_remaining = int(remaining.total_seconds() / 60)
        raise ValidationError(
            f"Appointment cannot be completed before scheduled time. "
            f"Can complete in approximately {minutes_remaining} minutes."
        )


def _validate_appointment_can_be_completed(appointment: Appointment) -> None:
    _validate_appointment_can_be_completed_time(appointment.appointment_time)


def authorize_appointment_create(
    db: Session,
    appointment_in: AppointmentCreate,
    current_user: User,
    tenant_id: UUID | None,
) -> None:
    if current_user.role == UserRole.super_admin:
        return

    if current_user.role in (UserRole.admin, UserRole.staff) or (
        current_user.role == UserRole.doctor and current_user.is_owner
    ):
        doctor = doctor_service.get_doctor_or_404(db, appointment_in.doctor_id)
        assert_authorized(
            "create",
            "appointment",
            current_user,
            tenant_id,
            resource_tenant_id=doctor.tenant_id,
        )
        return

    if current_user.role == UserRole.doctor:
        try:
            doc = doctor_service.get_current_doctor(db, current_user)
        except ForbiddenError:
            log_rbac_mutation_violation(
                current_user, "appointment", action="create_appointment"
            )
            raise
        if doc.id != appointment_in.doctor_id:
            log_rbac_mutation_violation(
                current_user,
                "appointment",
                action="create_appointment",
                tenant_type=doc.tenant.type if doc.tenant else None,
            )
            raise ForbiddenError("Cannot create appointment for another doctor")
        return

    if current_user.role == UserRole.patient:
        try:
            acting_patient = patient_service.get_patient_by_user_id(db, current_user.id)
        except NotFoundError:
            log_rbac_mutation_violation(current_user, "appointment")
            raise ForbiddenError("Patient profile not found for this user")
        if acting_patient.id != appointment_in.patient_id:
            log_rbac_mutation_violation(current_user, "appointment")
            raise ForbiddenError("Cannot create appointment for another patient")
        return

    log_rbac_mutation_violation(current_user, "appointment")
    raise ForbiddenError("Not allowed to create appointments")


def create_appointment(
    db: Session,
    appointment_in: AppointmentCreate,
    current_user: User,
    tenant_id: UUID | None,
    idempotency_key: str | None = None,
) -> tuple[Appointment, bool]:
    """Returns (appointment, idempotent_replay) where idempotent_replay is True if this response replays a prior create."""
    logger.info(f"[RBAC] role={current_user.role}, user={current_user.id}")
    appt_in = appointment_in
    if current_user.role == UserRole.patient:
        ensured = patient_service.ensure_patient_profile_for_user_tx(
            db, current_user
        )
        appt_in = appt_in.model_copy(update={"patient_id": ensured.id})
    authorize_appointment_create(
        db,
        appt_in,
        current_user,
        tenant_id,
    )

    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip() or None

    body_hash = _appointment_payload_hash(appt_in)
    if idempotency_key:
        existing = crud_appointment.get_appointment_idempotency_record(
            db, current_user.id, idempotency_key
        )
        if existing is not None:
            if existing.request_hash != body_hash:
                raise ConflictError(
                    "Idempotency key reused with different request payload"
                )
            ap = get_appointment_or_404(db, existing.appointment_id)
            revalidate_appointment_invariants(db, ap)
            inc_counter("idempotency_replays_total")
            return (ap, True)

    _validate_patient_and_doctor_exist(
        db,
        patient_id=appt_in.patient_id,
        doctor_id=appt_in.doctor_id,
    )
    doctor = doctor_service.get_doctor_or_404(db, appt_in.doctor_id)
    doctor_service.require_doctor_tenant_for_scheduling(doctor)

    # Resolve naive appointment_time as doctor local time (P0.5 timezone mismatch fix)
    resolved_time = resolve_appointment_timezone(doctor, appt_in.appointment_time)
    appt_in = appt_in.model_copy(update={"appointment_time": resolved_time})

    doctor_tenant_id = non_nil_tenant_id(doctor.tenant_id)
    if not doctor_tenant_id:
        raise ValidationError("Tenant cannot be resolved")

    logger.info(
        "[BOOKING_FLOW_V2] patient_id=%s doctor_tenant=%s",
        appt_in.patient_id,
        doctor.tenant_id,
    )

    doctor_slot_service.assert_appointment_time_matches_doctor_slots(
        db, doctor, appt_in.appointment_time
    )
    _validate_doctor_availability(
        db,
        doctor_id=appt_in.doctor_id,
        appointment_time=appt_in.appointment_time,
    )
    _validate_slot_not_double_booked(db, appt_in.doctor_id, appt_in.appointment_time)
    _validate_patient_no_other_appointment_same_instant(
        db, appt_in.patient_id, appt_in.appointment_time
    )
    _validate_appointment_time_in_future(appt_in.appointment_time)
    appointment_data = appt_in.model_dump()
    appointment_data["created_by"] = current_user.id

    appointment_data["tenant_id"] = doctor_tenant_id
    appointment_data["doctor_id"] = appt_in.doctor_id
    appointment_data["patient_id"] = appt_in.patient_id

    try:
        appointment = crud_appointment.add_appointment(db, appointment_data)
        validate_appointment_invariants(appointment, doctor)
        if idempotency_key:
            crud_appointment.record_appointment_idempotency(
                db,
                user_id=current_user.id,
                idempotency_key=idempotency_key,
                request_hash=body_hash,
                appointment_id=appointment.id,
            )
        db.commit()
        db.refresh(appointment)
        doctor_slot_service.invalidate_slots_cache_for_appointment(db, doctor, appointment.appointment_time)
    except IntegrityError as e:
        db.rollback()
        if idempotency_key:
            existing = crud_appointment.get_appointment_idempotency_record(
                db, current_user.id, idempotency_key
            )
            if existing is not None and existing.request_hash == body_hash:
                ap = get_appointment_or_404(db, existing.appointment_id)
                revalidate_appointment_invariants(db, ap)
                inc_counter("idempotency_replays_total")
                return (ap, True)
        msg = str(getattr(e, "orig", e))
        if "uq_appointments_doctor_time_active" in msg or "uq_doctor_time" in msg:
            raise ValidationError("Slot already booked") from e
        raise

    reloaded = crud_appointment.get_appointment(db, appointment.id)
    if reloaded is None:
        raise NotFoundError("Appointment not found")
    revalidate_appointment_invariants(db, reloaded)
    log_audit_mutation(
        "create",
        current_user,
        "appointment",
        reloaded.id,
        reloaded.tenant_id,
        extra=_appointment_audit_ctx(reloaded),
    )
    return (reloaded, False)


def get_appointment_or_404(db: Session, appointment_id: UUID) -> Appointment:
    appointment = crud_appointment.get_appointment(db, appointment_id)
    if appointment is None:
        raise NotFoundError("Appointment not found")
    return appointment


def get_appointments(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 10,
    doctor_id: UUID | None = None,
    patient_id: UUID | None = None,
    tenant_id: UUID | None = None,
    *,
    list_type: str | None = None,
    appt_status: AppointmentStatus | None = None,
    data_scope: ResolvedDataScope,
) -> list[Appointment]:
    _ensure_can_list_appointments(current_user)
    logger.info(f"[RBAC] role={current_user.role}, user={current_user.id}")
    eff_doctor_id = doctor_id
    eff_patient_id = patient_id
    eff_tenant_id = tenant_id

    if current_user.role == UserRole.doctor:
        if (
            data_scope.kind == DataScopeKind.tenant
            and has_tenant_admin_privileges(current_user)
        ):
            eff_doctor_id = doctor_id
            eff_patient_id = None
        else:
            doc = doctor_service.get_current_doctor(db, current_user)
            eff_doctor_id = doc.id
            eff_patient_id = None
    elif current_user.role == UserRole.patient:
        patient = patient_service.get_patient_by_user_id(db, current_user.id)
        eff_patient_id = patient.id
        eff_doctor_id = None
    elif current_user.role in (UserRole.admin, UserRole.super_admin, UserRole.staff):
        if (
            data_scope.kind == DataScopeKind.doctor
            and data_scope.doctor_id is not None
        ):
            eff_doctor_id = data_scope.doctor_id

    appointments = crud_appointment.get_appointments(
        db,
        skip=skip,
        limit=limit,
        doctor_id=eff_doctor_id,
        patient_id=eff_patient_id,
        tenant_id=eff_tenant_id,
        list_type=list_type,
        appt_status=appt_status,
    )
    logger.info(
        "[APPOINTMENT_SCOPE] scope=%s eff_doctor_id=%s eff_tenant_id=%s user=%s returned=%d",
        data_scope.kind.value,
        eff_doctor_id,
        eff_tenant_id,
        current_user.id,
        len(appointments),
    )
    return appointments


def _completion_payload_hash(data: MarkAppointmentCompletedRequest) -> str:
    body = data.model_dump(mode="json")
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _appointment_completion_result_hash(
    *,
    appointment_id: UUID,
    appointment_status_value: str,
    billing_id: UUID | None,
) -> str:
    body = {
        "appointment_id": str(appointment_id),
        "status": appointment_status_value,
        "billing_id": str(billing_id) if billing_id is not None else None,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _create_appointment_vitals(
    db: Session,
    appointment: Appointment,
    vitals_data: VitalSignsCreate,
    current_user: User,
) -> None:
    if vitals_data is None:
        return
    if (
        vitals_data.temperature is None
        and vitals_data.bp_systolic is None
        and vitals_data.bp_diastolic is None
        and vitals_data.pulse is None
        and vitals_data.respiratory_rate is None
        and vitals_data.spo2 is None
        and vitals_data.weight is None
        and vitals_data.height is None
        and vitals_data.bmi is None
        and vitals_data.notes is None
    ):
        return
    crud_appointment.add_appointment_vitals(
        db,
        appointment_id=appointment.id,
        temperature=vitals_data.temperature,
        bp_systolic=vitals_data.bp_systolic,
        bp_diastolic=vitals_data.bp_diastolic,
        pulse=vitals_data.pulse,
        respiratory_rate=vitals_data.respiratory_rate,
        spo2=vitals_data.spo2,
        weight=vitals_data.weight,
        height=vitals_data.height,
        bmi=vitals_data.bmi,
        notes=vitals_data.notes,
    )
    log_structured_audit_event(
        event="vitals_recorded",
        tenant_id=appointment.tenant_id,
        resource_id=str(appointment.id),
        actor_id=str(current_user.id),
        appointment_id=str(appointment.id),
        patient_id=str(appointment.patient_id),
    )


def _validate_prescription_against_appointment(
    appointment: Appointment,
    prescription: PrescriptionCreate,
) -> None:
    if not prescription.notes and not prescription.items:
        raise ValidationError("Prescription must include notes or items")


def _derive_medication_schedules_from_prescription(
    db: Session,
    prescription: Prescription,
    appointment: Appointment,
) -> None:
    """
    Auto-derive PatientMedicationSchedule records from a prescription.

    This is called during encounter completion to ensure medication schedules
    are created as canonical patient records — independent of inventory or billing.

    Each PrescriptionItem becomes a PatientMedicationSchedule with:
    - medicine_name, dosage, frequency, duration, instructions snapshotted
    - start_date = encounter completed time
    - end_date = derived from duration if parseable, else NULL (ongoing)
    - is_active = True, status = active
    """
    from datetime import timedelta
    import re

    if not prescription.items:
        logger.info(
            "[RX_TRACE] _derive_medication_schedules: no items in prescription %s for appointment %s patient %s tenant %s",
            prescription.id,
            appointment.id,
            appointment.patient_id,
            appointment.tenant_id,
        )
        return

    now = datetime.now(timezone.utc)
    created_count = 0

    for item in prescription.items:
        # Try to parse duration into days for end_date calculation
        end_date: datetime | None = None
        if item.duration:
            # Match patterns like "7 days", "2 weeks", "1 month", "3 months"
            duration_match = re.match(
                r"(\d+)\s*(day|days|week|weeks|month|months|year|years)?",
                item.duration.strip(),
                re.IGNORECASE,
            )
            if duration_match:
                num = int(duration_match.group(1))
                unit = (duration_match.group(2) or "days").lower()
                if unit.startswith("day"):
                    end_date = now + timedelta(days=num)
                elif unit.startswith("week"):
                    end_date = now + timedelta(weeks=num)
                elif unit.startswith("month"):
                    end_date = now + timedelta(days=num * 30)
                elif unit.startswith("year"):
                    end_date = now + timedelta(days=num * 365)

        crud_medication_schedule.create_medication_schedule(
            db,
            patient_id=appointment.patient_id,
            prescription_id=prescription.id,
            prescription_item_id=item.id,
            tenant_id=appointment.tenant_id,
            medicine_name=item.medicine_name,
            dosage=item.dosage,
            frequency=item.frequency,
            duration=item.duration,
            instructions=item.instructions,
            start_date=now,
            end_date=end_date,
        )
        created_count += 1

    logger.info(
        "[RX_TRACE] _derive_medication_schedules: created %d schedules from prescription %s for appointment %s patient %s tenant %s",
        created_count,
        prescription.id,
        appointment.id,
        appointment.patient_id,
        appointment.tenant_id,
    )


def _create_appointment_prescriptions(
    db: Session,
    appointment: Appointment,
    prescriptions: list[PrescriptionCreate],
) -> None:
    if not prescriptions:
        logger.info(
            "[RX_TRACE] _create_appointment_prescriptions: no prescriptions for appointment %s patient %s tenant %s",
            appointment.id,
            appointment.patient_id,
            appointment.tenant_id,
        )
        return
    created_prescription_count = 0
    for prescription_payload in prescriptions:
        if not prescription_payload.notes and not prescription_payload.items:
            continue
        prescription = crud_appointment.add_prescription(
            db,
            appointment_id=appointment.id,
            doctor_id=appointment.doctor_id,
            patient_id=appointment.patient_id,
            tenant_id=appointment.tenant_id,
            notes=prescription_payload.notes,
        )
        for item_payload in prescription_payload.items:
            crud_appointment.add_prescription_item(
                db,
                prescription_id=prescription.id,
                line_data={
                    "medicine_name": item_payload.medicine_name,
                    "dosage": item_payload.dosage,
                    "frequency": item_payload.frequency,
                    "duration": item_payload.duration,
                    "instructions": item_payload.instructions,
                },
            )
        created_prescription_count += 1
        # Auto-derive medication schedules from this prescription
        _derive_medication_schedules_from_prescription(db, prescription, appointment)
        log_structured_audit_event(
            event="prescription_created",
            tenant_id=appointment.tenant_id,
            resource_id=str(prescription.id),
            actor_id=str(appointment.doctor_id),
            appointment_id=str(appointment.id),
            doctor_id=str(appointment.doctor_id),
            patient_id=str(appointment.patient_id),
            status="success",
        )
    logger.info(
        "[RX_TRACE] _create_appointment_prescriptions: created %d prescriptions for appointment %s patient %s tenant %s",
        created_prescription_count,
        appointment.id,
        appointment.patient_id,
        appointment.tenant_id,
    )


def create_prescription_for_appointment(
    db: Session,
    appointment_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    prescription_data: PrescriptionCreate,
) -> Prescription:
    appointment = get_appointment_or_404(db, appointment_id)
    authorize_appointment_access(
        db,
        appointment,
        current_user,
        tenant_id,
        rbac_action="create_prescription",
        require_assigned_doctor=True,
    )
    if appointment.tenant_id is None:
        raise ValidationError("Appointment tenant is not set")
    _validate_prescription_against_appointment(appointment, prescription_data)
    prescription = crud_appointment.add_prescription(
        db,
        appointment_id=appointment.id,
        doctor_id=appointment.doctor_id,
        patient_id=appointment.patient_id,
        tenant_id=appointment.tenant_id,
        notes=prescription_data.notes,
    )
    for item_payload in prescription_data.items:
        crud_appointment.add_prescription_item(
            db,
            prescription_id=prescription.id,
            line_data={
                "medicine_name": item_payload.medicine_name,
                "dosage": item_payload.dosage,
                "frequency": item_payload.frequency,
                "duration": item_payload.duration,
                "instructions": item_payload.instructions,
            },
        )
    # Auto-derive medication schedules from this prescription
    _derive_medication_schedules_from_prescription(db, prescription, appointment)
    log_structured_audit_event(
        event="prescription_created",
        tenant_id=appointment.tenant_id,
        resource_id=str(prescription.id),
        actor_id=str(current_user.id),
        appointment_id=str(appointment.id),
        doctor_id=str(appointment.doctor_id),
        patient_id=str(appointment.patient_id),
        status="success",
    )
    return prescription


def update_prescription(
    db: Session,
    prescription_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    update_data: PrescriptionCreate,
) -> Prescription:
    prescription = crud_appointment.get_prescription_by_id(db, prescription_id)
    if prescription is None:
        raise NotFoundError("Prescription not found")
    appointment = get_appointment_or_404(db, prescription.appointment_id)
    authorize_appointment_access(
        db,
        appointment,
        current_user,
        tenant_id,
        rbac_action="update_prescription",
        require_assigned_doctor=True,
    )
    _validate_prescription_against_appointment(appointment, update_data)
    crud_appointment.update_prescription(
        db,
        prescription,
        {
            "notes": update_data.notes,
            "items": [item.model_dump() for item in update_data.items],
        },
    )
    log_structured_audit_event(
        event="prescription_updated",
        tenant_id=appointment.tenant_id,
        resource_id=str(prescription.id),
        actor_id=str(current_user.id),
        appointment_id=str(appointment.id),
        doctor_id=str(appointment.doctor_id),
        patient_id=str(appointment.patient_id),
        status="success",
    )
    return prescription


def get_prescriptions_by_appointment(
    db: Session,
    appointment_id: UUID,
) -> list[Prescription]:
    appointment = get_appointment_or_404(db, appointment_id)
    return crud_appointment.get_prescriptions_for_appointment(db, appointment_id)


def appointment_to_read(db: Session, appt: Appointment) -> AppointmentRead:
    from app.services.billing_service import appointment_inventory_materials_selling_total

    total = appointment_inventory_materials_selling_total(db, appt.id)
    base = AppointmentRead.model_validate(appt)
    return base.model_copy(update={"inventory_materials_selling_total": total})


def mark_appointment_completed(
    db: Session,
    appointment_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    *,
    restrict_to_doctor_id: UUID | None = None,
    completion: MarkAppointmentCompletedRequest | None = None,
    idempotency_key: str | None = None,
    active_workspace: ActiveWorkspace | None = None,
) -> tuple[Appointment, bool]:
    """Returns (appointment, idempotent_replay). Replay is True when Idempotency-Key matched a prior body."""
    logger.debug("[TRACE_MC] entered mark_appointment_completed: user=%s role=%s appt_id=%s", current_user.id, current_user.role, appointment_id)
    appointment = crud_appointment.get_appointment_for_update_locked(db, appointment_id)
    if appointment is None:
        raise NotFoundError("Appointment not found")

    authorize_appointment_access(
        db,
        appointment,
        current_user,
        tenant_id,
        rbac_action="mark_appointment_completed",
        restrict_to_doctor_id=restrict_to_doctor_id,
        require_assigned_doctor=True,
        active_workspace=active_workspace,
    )

    logger.warning(
        "[SERVICE DEBUG] active_workspace=%s slug=%s role=%s",
        active_workspace,
        active_workspace.slug.value if active_workspace else None,
        current_user.role,
    )

    if settings.REQUIRE_APPOINTMENT_COMPLETION_IDEMPOTENCY_KEY:

        if idempotency_key is None or not str(idempotency_key).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key header is required to complete visits",
            )

    assigned_doctor = doctor_service.get_doctor_or_404(db, appointment.doctor_id)
    validate_appointment_invariants(appointment, assigned_doctor)
    now_utc = datetime.now(timezone.utc)

    # CRITICAL INVARIANT: Prevent completing future appointments.
    # This ensures that temporal grouping (past/upcoming) stays independent from status.
    # Only validate if the appointment is not already completed (allow idempotent replays).
    if appointment.status != AppointmentStatus.completed:
        _validate_appointment_can_be_completed(appointment)

    data = completion or MarkAppointmentCompletedRequest()
    ih = idempotency_key.strip() if idempotency_key else ""
    ih = ih or None
    req_hash = _completion_payload_hash(data) if ih else None

    if ih:
        existing = crud_appointment.get_appointment_completion_idempotency_record(
            db,
            appointment_id=appointment_id,
            idempotency_key=ih,
        )
        if existing is not None:
            if existing.request_hash != req_hash:
                raise ConflictError(
                    "Idempotency key reused with different request payload"
                )
            db.commit()
            reloaded = AppointmentInvariantGuard.finalize(db, appointment_id)
            bill_row = crud_billing.get_bill_by_appointment(db, appointment_id)
            current_billing_id = bill_row.id if bill_row else None
            current_outcome_hash = _appointment_completion_result_hash(
                appointment_id=reloaded.id,
                appointment_status_value=reloaded.status.value,
                billing_id=current_billing_id,
            )
            if existing.result_hash and current_outcome_hash != existing.result_hash:
                inc_counter("idempotency_outcome_hash_mismatch_total")
                logger.error(
                    "[APM_IDEMPOTENCY] replay outcome differs from stored snapshot (possible data "
                    "drift); appointment=%s stored=%s current=%s",
                    appointment_id,
                    existing.result_hash,
                    current_outcome_hash,
                )
                logger.warning(
                    "[IDEMPOTENCY] outcome hash mismatch appointment=%s", appointment_id,
                )
            inc_counter("appointments_completed_total")
            inc_counter("idempotency_replays_total")
            return reloaded, True

    if appointment.status == AppointmentStatus.completed:
        db.commit()
        return AppointmentInvariantGuard.finalize(db, appointment_id), False

    if appointment.status != AppointmentStatus.scheduled:
        raise ValidationError("Only scheduled visits can be completed")

    if data.items:
        inventory_service.consume_inventory_for_appointment(
            db,
            appointment,
            data.items,
            current_user,
            tenant_id,
        )
    # DEPRECATED: completion_notes is deprecated and no longer written for new visits.
    # Use clinical_notes for visit documentation. Preserved for backward compatibility.
    # if data.completion_notes is not None:
    #     appointment.completion_notes = data.completion_notes
    # clinical_notes = medical observations/treatment for THIS visit (preferred).
    if data.clinical_notes is not None:
        appointment.clinical_notes = data.clinical_notes
    # diagnosis = primary and differential diagnoses.
    if data.diagnosis is not None:
        appointment.diagnosis = data.diagnosis
    # treatment_summary = treatment provided, medications, follow-up plan.
    if data.treatment_summary is not None:
        appointment.treatment_summary = data.treatment_summary
    # SOAP notes: structured clinical documentation
    if data.subjective_notes is not None:
        appointment.subjective_notes = data.subjective_notes
    if data.objective_notes is not None:
        appointment.objective_notes = data.objective_notes
    if data.assessment_notes is not None:
        appointment.assessment_notes = data.assessment_notes
    if data.plan_notes is not None:
        appointment.plan_notes = data.plan_notes
    if any([
        data.subjective_notes is not None,
        data.objective_notes is not None,
        data.assessment_notes is not None,
        data.plan_notes is not None,
    ]):
        log_structured_audit_event(
            event="soap_updated",
            tenant_id=appointment.tenant_id,
            resource_id=str(appointment.id),
            actor_id=str(current_user.id),
            appointment_id=str(appointment.id),
            patient_id=str(appointment.patient_id),
        )
    if data.follow_up_date is not None:
        appointment.follow_up_date = data.follow_up_date
    if data.follow_up_notes is not None:
        appointment.follow_up_notes = data.follow_up_notes

    _create_appointment_vitals(db, appointment, data.vitals, current_user)  # type: ignore[arg-type]
    _create_appointment_prescriptions(db, appointment, data.prescriptions)

    appointment.status = AppointmentStatus.completed
    appointment.encounter_completed_at = now_utc
    if appointment.encounter_started_at is None:
        appointment.encounter_started_at = now_utc
    db.add(appointment)
    db.flush()

    # TODO: if encounter_started_at is later tracked by a Start Encounter action,
    # do not overwrite an existing start time here.
    if data.generate_bill:
        from app.schemas.billing import BillingCreate
        from app.services import billing_service

        mats = billing_service.appointment_inventory_materials_selling_total(
            db, appointment.id
        )
        base_fee = data.bill_consultation_amount
        if mats + base_fee <= Decimal("0"):
            raise ValidationError(
                "Cannot generate a bill: add medicines or enter a consultation fee greater than zero"
            )
        desc = "Consultation" if base_fee > Decimal("0") else None
        billing_service.create_bill(
            db,
            BillingCreate(
                patient_id=appointment.patient_id,
                appointment_id=appointment.id,
                amount=base_fee,
                currency="INR",
                description=desc,
                include_appointment_inventory_selling_total=True,
            ),
            current_user,
            tenant_id,
        )

    bill_for_snapshot = crud_billing.get_bill_by_appointment(db, appointment.id)
    billing_id_snapshot = bill_for_snapshot.id if bill_for_snapshot else None
    outcome_hash = _appointment_completion_result_hash(
        appointment_id=appointment.id,
        appointment_status_value=AppointmentStatus.completed.value,
        billing_id=billing_id_snapshot,
    )

    if ih:
        assert req_hash is not None
        idem_row = crud_appointment.record_appointment_completion_idempotency(
            db,
            appointment_id=appointment.id,
            user_id=current_user.id,
            idempotency_key=ih,
            request_hash=req_hash,
            result_hash=outcome_hash,
            billing_id=billing_id_snapshot,
        )
        if idem_row.request_hash != req_hash:
            raise ConflictError(
                "Idempotency key reused with different request payload"
            )
    db.commit()
    slot_doctor = doctor_service.get_doctor_or_404(db, appointment.doctor_id)
    doctor_slot_service.invalidate_slots_cache_for_appointment(
        db, slot_doctor, appointment.appointment_time
    )
    reloaded = AppointmentInvariantGuard.finalize(db, appointment_id)
    log_structured_audit_event(
        event="appointment_completed",
        tenant_id=reloaded.tenant_id,
        resource_id=str(reloaded.id),
        actor_id=str(current_user.id),
        appointment_id=str(reloaded.id),
        doctor_id=str(reloaded.doctor_id),
        patient_id=str(reloaded.patient_id),
        idempotency_key=ih,
        status="success",
    )
    inc_counter("appointments_completed_total")
    return reloaded, False


def _assert_doctor_assigned_to_appointment(
    db: Session,
    current_user: User,
    appointment: Appointment,
    *,
    rbac_action: str,
    restrict_to_doctor_id: UUID | None = None,
    active_workspace: ActiveWorkspace | None = None,
) -> None:
    logger.debug("[TRACE_MC] entered _assert_doctor_assigned_to_appointment: user=%s role=%s appt_doctor_id=%s restrict=%s", current_user.id, current_user.role, appointment.doctor_id, restrict_to_doctor_id)
    # Capability-based check: user must have a Doctor record linked via user_id
    # AND that doctor must be the assigned doctor for this appointment.
    # This works for ANY user role - admin, staff, or doctor - as long as they
    # have a valid Doctor record linked to their user account.
    #
    # CLINICIAN CAPABILITY: The user must have clinician capability (doctor role,
    # normalized doctor role, or linked Doctor record). Workspace context does NOT
    # grant clinical authority — a pure admin without a Doctor record cannot perform
    # clinical actions regardless of workspace.
    if not has_clinician_capability(db, current_user):
        log_rbac_mutation_violation(
            current_user,
            "appointment",
            action=rbac_action,
        )
        raise ForbiddenError("Only clinicians can perform this action")

    # Resolve the doctor identity for this user.
    # When restrict_to_doctor_id is provided (from data_scope), use it directly
    # to avoid ambiguity from get_doctor_by_user_id returning a different Doctor row.
    # Fall back to get_current_doctor when restrict_to_doctor_id is None.
    if restrict_to_doctor_id is not None:
        doc = doctor_service.get_doctor_or_404(db, restrict_to_doctor_id)
    else:
        doc = doctor_service.get_current_doctor(db, current_user)

    # Defensive logging for debugging authorization failures
    logger.warning(
        "[ENCOUNTER_AUTH_DEBUG] "
        "user=%s role=%s "
        "restrict_to_doctor_id=%s "
        "resolved_doctor_id=%s "
        "appointment_doctor_id=%s "
        "appointment_tenant_id=%s "
        "resolved_doctor_tenant_id=%s",
        current_user.id,
        current_user.role,
        restrict_to_doctor_id,
        doc.id,
        appointment.doctor_id,
        appointment.tenant_id,
        doc.tenant_id,
    )
    logger.warning(
        "[APM_AUTH] _assert_doctor_assigned_to_appointment: "
        "user_id=%s role=%s resolved_doctor_id=%s appointment_doctor_id=%s "
        "resolved_doctor_tenant_id=%s appointment_tenant_id=%s "
        "restrict_to_doctor_id=%s has_clinician_capability=True",
        current_user.id,
        current_user.role,
        doc.id,
        appointment.doctor_id,
        doc.tenant_id,
        appointment.tenant_id,
        restrict_to_doctor_id,
    )


    if non_nil_tenant_id(doc.tenant_id) != non_nil_tenant_id(appointment.tenant_id):
        log_rbac_mutation_violation(
            current_user,
            "appointment",
            action=rbac_action,
        )
        raise ForbiddenError("Cross-tenant access not allowed")
    if appointment.doctor_id != doc.id:
        log_rbac_mutation_violation(
            current_user,
            "appointment",
            action=rbac_action,
            tenant_type=doc.tenant.type if doc.tenant else None,
        )
        raise ForbiddenError("Only the assigned doctor can complete this appointment")


def authorize_appointment_access(
    db: Session,
    appointment: Appointment,
    current_user: User,
    tenant_id: UUID | None,
    *,
    rbac_action: str = "appointment_access",
    restrict_to_doctor_id: UUID | None = None,
    require_assigned_doctor: bool = False,
    active_workspace: ActiveWorkspace | None = None,
) -> None:
    # Authorization is capability-based:
    # A user may act as a doctor if they have a Doctor record linked via user_id.
    # Role (admin/doctor/staff) is NOT used for permission decisions here.
    logger.warning(
        "[AUTH_TRACE] authorize_appointment_access entry: "
        "user=%s role=%s require_assigned_doctor=%s restrict_to_doctor_id=%s "
        "appt_doctor_id=%s appt_tenant_id=%s rbac_action=%s",
        current_user.id, current_user.role, require_assigned_doctor,
        restrict_to_doctor_id, appointment.doctor_id, appointment.tenant_id,
        rbac_action,
    )

    if appointment.tenant_id is None:
        logger.warning("[AUTH_TRACE] BRANCH: appointment.tenant_id is None -> ValidationError")
        raise ValidationError("Appointment tenant is not set")

    if current_user.role == UserRole.super_admin:
        logger.warning("[AUTH_TRACE] BRANCH: super_admin")
        if (
            restrict_to_doctor_id is not None
            and appointment.doctor_id != restrict_to_doctor_id
        ):
            log_rbac_mutation_violation(
                current_user, "appointment", action=rbac_action
            )
            raise ForbiddenError("Not allowed to access this appointment")
        return

    if current_user.role == UserRole.patient:
        logger.warning("[AUTH_TRACE] BRANCH: patient")
        if require_assigned_doctor:
            log_rbac_mutation_violation(
                current_user,
                "appointment",
                action=rbac_action,
            )
            raise ForbiddenError("Only the assigned doctor can complete this appointment")
        try:
            acting_patient = patient_service.get_patient_by_user_id(db, current_user.id)
        except NotFoundError:
            log_rbac_mutation_violation(current_user, "appointment")
            raise ForbiddenError("Patient profile not found for this user")
        if appointment.patient_id != acting_patient.id:
            log_rbac_mutation_violation(current_user, "appointment")
            raise ForbiddenError("Not allowed to access this appointment")
        return

    assert_authorized(
        "access",
        "appointment",
        current_user,
        tenant_id,
        resource_tenant_id=appointment.tenant_id,
    )

    # Capability-based authorization: if require_assigned_doctor is True,
    # check if user has a Doctor record and is the assigned doctor.
    # This works for ANY user with a Doctor record (admin, staff, or doctor role).
    if require_assigned_doctor:
        logger.warning("[AUTH_TRACE] BRANCH: require_assigned_doctor=True -> _assert_doctor_assigned_to_appointment")
        _assert_doctor_assigned_to_appointment(
            db, current_user, appointment, rbac_action=rbac_action,
            restrict_to_doctor_id=restrict_to_doctor_id,
            active_workspace=active_workspace,
        )
        return

    if current_user.role in (UserRole.admin, UserRole.staff):
        logger.warning("[AUTH_TRACE] BRANCH: admin/staff")
        if (
            restrict_to_doctor_id is not None
            and appointment.doctor_id != restrict_to_doctor_id
        ):
            log_rbac_mutation_violation(
                current_user, "appointment", action=rbac_action
            )
            raise ForbiddenError("Not allowed to access this appointment")
        return

    if current_user.role == UserRole.doctor and current_user.is_owner:
        logger.warning("[AUTH_TRACE] BRANCH: doctor+is_owner")
        if restrict_to_doctor_id is None:
            return
        if appointment.doctor_id == restrict_to_doctor_id:
            return
        log_rbac_mutation_violation(
            current_user, "appointment", action=rbac_action
        )
        raise ForbiddenError("Not allowed to access this appointment")

    if current_user.role == UserRole.doctor:
        logger.warning("[AUTH_TRACE] BRANCH: doctor (non-owner)")
        _assert_doctor_assigned_to_appointment(
            db, current_user, appointment, rbac_action=rbac_action
        )
        return

    logger.warning("[AUTH_TRACE] BRANCH: fallback ForbiddenError (role=%s)", current_user.role)
    log_rbac_mutation_violation(current_user, "appointment")
    raise ForbiddenError("Not allowed to access this appointment")



authorize_appointment_read = authorize_appointment_access
authorize_appointment_update = authorize_appointment_access
authorize_appointment_delete = authorize_appointment_access


def _validate_status_regression(
    existing_status: AppointmentStatus,
    new_status: AppointmentStatus | None,
) -> None:
    if existing_status == AppointmentStatus.completed:
        raise ValidationError("Completed appointment cannot be modified")


def update_appointment(
    db: Session,
    appointment_id: UUID,
    appointment_in: AppointmentUpdate,
    current_user: User,
    tenant_id: UUID | None,
    *,
    restrict_to_doctor_id: UUID | None = None,
) -> Appointment:
    appointment = get_appointment_or_404(db, appointment_id)
    authorize_appointment_access(
        db,
        appointment,
        current_user,
        tenant_id,
        rbac_action="update_appointment",
        restrict_to_doctor_id=restrict_to_doctor_id,
    )

    update_data = appointment_in.model_dump(exclude_unset=True)

    patient_id = update_data.get("patient_id", appointment.patient_id)
    doctor_id = update_data.get("doctor_id", appointment.doctor_id)
    doctor_for_slot = doctor_service.get_doctor_or_404(db, doctor_id)
    doctor_service.require_doctor_tenant_for_scheduling(doctor_for_slot)
    doctor_tenant_id = non_nil_tenant_id(doctor_for_slot.tenant_id)
    if not doctor_tenant_id:
        raise ValidationError("Tenant cannot be resolved")
    if appointment.tenant_id != doctor_tenant_id:
        update_data["tenant_id"] = doctor_tenant_id

    if not update_data:
        revalidate_appointment_invariants(db, appointment)
        return appointment

    new_status = update_data.get("status")
    _validate_status_regression(appointment.status, new_status)

    appointment_time = update_data.get("appointment_time", appointment.appointment_time)
    if "appointment_time" in update_data:
        appointment_time = resolve_appointment_timezone(doctor_for_slot, appointment_time)
        update_data["appointment_time"] = appointment_time
    if new_status == AppointmentStatus.completed and appointment.status != AppointmentStatus.completed:
        _validate_appointment_can_be_completed_time(appointment_time)

    prev_doctor_id = appointment.doctor_id
    prev_appointment_time = appointment.appointment_time

    _validate_patient_and_doctor_exist(db, patient_id=patient_id, doctor_id=doctor_id)
    if appointment_time != prev_appointment_time or doctor_id != prev_doctor_id:
        doctor_slot_service.assert_appointment_time_matches_doctor_slots(
            db, doctor_for_slot, appointment_time
        )
    _validate_doctor_availability(
        db,
        doctor_id=doctor_id,
        appointment_time=appointment_time,
        existing_appointment_id=appointment.id,
    )
    if appointment_time != prev_appointment_time or doctor_id != prev_doctor_id:
        _validate_slot_not_double_booked(
            db,
            doctor_id,
            appointment_time,
            exclude_appointment_id=appointment.id,
        )
    if (
        appointment_time != prev_appointment_time
        or patient_id != appointment.patient_id
        or doctor_id != prev_doctor_id
    ):
        _validate_patient_no_other_appointment_same_instant(
            db,
            patient_id,
            appointment_time,
            exclude_appointment_id=appointment.id,
        )
    if "appointment_time" in update_data:
        _validate_appointment_time_in_future(appointment_time)
    updated = crud_appointment.update_appointment(db, appointment, update_data)
    if appointment_time != prev_appointment_time or doctor_id != prev_doctor_id:
        doctor_slot_service.invalidate_slots_cache_for_appointment(db, doctor_for_slot, appointment_time)
        prev_doctor = doctor_service.get_doctor_or_404(db, prev_doctor_id)
        doctor_slot_service.invalidate_slots_cache_for_appointment(db, prev_doctor, prev_appointment_time)
    log_audit_mutation(
        "update",
        current_user,
        "appointment",
        updated.id,
        updated.tenant_id,
        extra=_appointment_audit_ctx(updated),
    )
    reloaded = crud_appointment.get_appointment(db, updated.id)
    if reloaded is None:
        raise NotFoundError("Appointment not found")
    revalidate_appointment_invariants(db, reloaded)
    return reloaded


def delete_appointment(
    db: Session,
    appointment_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    *,
    restrict_to_doctor_id: UUID | None = None,
) -> Appointment:
    appointment = get_appointment_or_404(db, appointment_id)
    authorize_appointment_access(
        db,
        appointment,
        current_user,
        tenant_id,
        rbac_action="delete_appointment",
        restrict_to_doctor_id=restrict_to_doctor_id,
    )

    if appointment.status == AppointmentStatus.completed:
        raise ValidationError("Completed appointment cannot be deleted")

    revalidate_appointment_invariants(db, appointment)
    slot_doctor = doctor_service.get_doctor_or_404(db, appointment.doctor_id)
    slot_time = appointment.appointment_time
    deleted = crud_appointment.soft_delete_appointment(db, appointment)
    doctor_slot_service.invalidate_slots_cache_for_appointment(db, slot_doctor, slot_time)
    log_audit_mutation(
        "delete",
        current_user,
        "appointment",
        deleted.id,
        deleted.tenant_id,
        extra=_appointment_audit_ctx(deleted),
    )
    reloaded = crud_appointment.get_appointment(db, deleted.id, include_deleted=True)
    if reloaded is None:
        raise NotFoundError("Appointment not found")
    return reloaded
