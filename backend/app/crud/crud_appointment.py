from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.appointment import (
    Appointment,
    AppointmentCompletionIdempotency,
    AppointmentCreationIdempotency,
    AppointmentStatus,
    AppointmentVitals,
    Prescription,
    PrescriptionItem,
)
from app.models.inventory import AppointmentInventoryUsage
from app.models.patient import Patient
from app.utils.appointment_datetime import normalize_appointment_time_utc


def add_appointment(db: Session, appointment_data: dict[str, Any]) -> Appointment:
    appointment = Appointment(**appointment_data)
    db.add(appointment)
    db.flush()
    db.refresh(appointment)
    return appointment


def create_appointment(db: Session, appointment_data: dict[str, Any]) -> Appointment:
    appointment = add_appointment(db, appointment_data)
    db.commit()
    db.refresh(appointment)
    return appointment


def get_appointment_idempotency_record(
    db: Session, user_id: UUID, idempotency_key: str
) -> AppointmentCreationIdempotency | None:
    stmt = select(AppointmentCreationIdempotency).where(
        AppointmentCreationIdempotency.user_id == user_id,
        AppointmentCreationIdempotency.idempotency_key == idempotency_key,
    )
    return db.scalars(stmt).first()


def delete_expired_appointment_idempotency_records(
    db: Session, *, older_than_days: int = 365
) -> int:
    """Remove stale idempotency rows (run from cron/worker). Returns rows deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    stmt = delete(AppointmentCreationIdempotency).where(
        AppointmentCreationIdempotency.created_at < cutoff
    )
    result = db.execute(stmt)
    return int(result.rowcount or 0)


def record_appointment_idempotency(
    db: Session,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_hash: str,
    appointment_id: UUID,
) -> AppointmentCreationIdempotency:
    row = AppointmentCreationIdempotency(
        user_id=user_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        appointment_id=appointment_id,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def get_appointment_completion_idempotency_record(
    db: Session,
    *,
    appointment_id: UUID,
    idempotency_key: str,
) -> AppointmentCompletionIdempotency | None:
    stmt = select(AppointmentCompletionIdempotency).where(
        AppointmentCompletionIdempotency.appointment_id == appointment_id,
        AppointmentCompletionIdempotency.idempotency_key == idempotency_key,
    )
    return db.scalars(stmt).first()


def record_appointment_completion_idempotency(
    db: Session,
    *,
    appointment_id: UUID,
    user_id: UUID,
    idempotency_key: str,
    request_hash: str,
    result_hash: str | None = None,
    billing_id: UUID | None = None,
) -> AppointmentCompletionIdempotency:
    try:
        with db.begin_nested():
            row = AppointmentCompletionIdempotency(
                appointment_id=appointment_id,
                user_id=user_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                result_hash=result_hash,
                billing_id=billing_id,
            )
            db.add(row)
            db.flush()
            db.refresh(row)
        return row
    except IntegrityError:
        existing = get_appointment_completion_idempotency_record(
            db,
            appointment_id=appointment_id,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            raise
        return existing


def get_appointment(
    db: Session,
    appointment_id: UUID,
    *,
    include_deleted: bool = False,
) -> Appointment | None:
    stmt = (
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            selectinload(Appointment.inventory_usages).joinedload(
                AppointmentInventoryUsage.item
            ),
            selectinload(Appointment.vitals),
            selectinload(Appointment.prescriptions).selectinload(Prescription.items),
        )
    )
    if not include_deleted:
        stmt = stmt.where(Appointment.is_deleted == False)
    return db.scalars(stmt).first()


def get_appointment_for_update_locked(
    db: Session,
    appointment_id: UUID,
) -> Appointment | None:
    """Row lock (``FOR UPDATE``) for serializing mark-complete and avoiding double charge."""
    stmt = (
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .where(Appointment.is_deleted == False)
        .with_for_update(of=Appointment)
        .options(
            selectinload(Appointment.vitals),
            selectinload(Appointment.prescriptions).selectinload(Prescription.items),
        )
    )
    return db.scalars(stmt).first()


def add_prescription(
    db: Session,
    appointment_id: UUID,
    doctor_id: UUID,
    patient_id: UUID,
    tenant_id: UUID,
    notes: str | None = None,
) -> Prescription:
    prescription = Prescription(
        appointment_id=appointment_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        tenant_id=tenant_id,
        notes=notes,
    )
    db.add(prescription)
    db.flush()
    db.refresh(prescription)
    return prescription


def add_prescription_item(
    db: Session,
    prescription_id: UUID,
    line_data: dict[str, Any],
) -> PrescriptionItem:
    item = PrescriptionItem(
        prescription_id=prescription_id,
        medicine_name=line_data["medicine_name"],
        dosage=line_data.get("dosage"),
        frequency=line_data.get("frequency"),
        duration=line_data.get("duration"),
        instructions=line_data.get("instructions"),
    )
    db.add(item)
    db.flush()
    db.refresh(item)
    return item


def update_prescription(
    db: Session,
    prescription: Prescription,
    update_data: dict[str, Any],
) -> Prescription:
    if "notes" in update_data:
        prescription.notes = update_data["notes"]

    if "items" in update_data:
        prescription.items.clear()
        for item_data in update_data["items"]:
            prescription.items.append(
                PrescriptionItem(
                    medicine_name=item_data["medicine_name"],
                    dosage=item_data.get("dosage"),
                    frequency=item_data.get("frequency"),
                    duration=item_data.get("duration"),
                    instructions=item_data.get("instructions"),
                )
            )

    db.add(prescription)
    db.flush()
    db.refresh(prescription)
    return prescription


def get_prescription_by_id(db: Session, prescription_id: UUID) -> Prescription | None:
    stmt = (
        select(Prescription)
        .where(Prescription.id == prescription_id)
        .options(selectinload(Prescription.items))
    )
    return db.scalars(stmt).first()


def get_prescriptions_for_appointment(
    db: Session, appointment_id: UUID
) -> list[Prescription]:
    stmt = (
        select(Prescription)
        .where(Prescription.appointment_id == appointment_id)
        .options(selectinload(Prescription.items))
    )
    return list(db.scalars(stmt).all())


def get_appointments_by_ids(
    db: Session, appointment_ids: list[UUID]
) -> dict[UUID, Appointment]:
    if not appointment_ids:
        return {}
    stmt = (
        select(Appointment)
        .where(Appointment.id.in_(appointment_ids))
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            selectinload(Appointment.inventory_usages).joinedload(
                AppointmentInventoryUsage.item
            ),
            selectinload(Appointment.vitals),
            selectinload(Appointment.prescriptions).selectinload(Prescription.items),
        )
    )
    rows = db.scalars(stmt).unique().all()
    return {row.id: row for row in rows}


def get_appointments(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    doctor_id: UUID | None = None,
    patient_id: UUID | None = None,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    list_type: str | None = None,
    appt_status: AppointmentStatus | None = None,
) -> list[Appointment]:
    order_by: tuple = (Appointment.created_at.desc(),)
    if list_type == "past":
        order_by = (Appointment.appointment_time.desc(),)
    elif list_type == "upcoming":
        order_by = (Appointment.appointment_time.asc(),)

    stmt = (
        select(Appointment)
        .where(Appointment.is_deleted == False)
        .order_by(*order_by)
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            selectinload(Appointment.inventory_usages).joinedload(
                AppointmentInventoryUsage.item
            ),
            selectinload(Appointment.vitals),
            selectinload(Appointment.prescriptions).selectinload(Prescription.items),
        )
    )

    now_utc = datetime.now(timezone.utc)

    if list_type == "past":
        # Past tab: temporal past based solely on appointment date/time.
        stmt = stmt.where(Appointment.appointment_time < now_utc)
    elif list_type == "upcoming":
        stmt = stmt.where(Appointment.appointment_time >= now_utc)

    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if user_id is not None:
        stmt = stmt.join(Appointment.patient).where(Patient.user_id == user_id)
    if tenant_id is not None:
        stmt = stmt.where(Appointment.tenant_id == tenant_id)
    if appt_status is not None:
        stmt = stmt.where(Appointment.status == appt_status)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).unique().all())


def get_doctor_appointment_at_time(
    db: Session,
    doctor_id: UUID,
    appointment_time: datetime,
) -> Appointment | None:
    appointment_time = normalize_appointment_time_utc(appointment_time)
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_time == appointment_time,
        Appointment.status == AppointmentStatus.scheduled,
        Appointment.is_deleted == False,
    )
    return db.scalars(stmt).first()


def patient_has_scheduled_appointment_at(
    db: Session,
    patient_id: UUID,
    appointment_time: datetime,
    exclude_appointment_id: UUID | None = None,
) -> bool:
    """True if the patient already has a scheduled (active) appointment at this exact start instant."""
    appointment_time = normalize_appointment_time_utc(appointment_time)
    stmt = select(Appointment.id).where(
        Appointment.patient_id == patient_id,
        Appointment.appointment_time == appointment_time,
        Appointment.status == AppointmentStatus.scheduled,
        Appointment.is_deleted == False,
    )
    if exclude_appointment_id is not None:
        stmt = stmt.where(Appointment.id != exclude_appointment_id)
    return db.scalar(stmt.limit(1)) is not None


def doctor_has_non_cancelled_appointment_at(
    db: Session,
    doctor_id: UUID,
    appointment_time: datetime,
    exclude_appointment_id: UUID | None = None,
) -> bool:
    """True if an active (non-deleted, non-cancelled) appointment exists at this exact start time."""
    appointment_time = normalize_appointment_time_utc(appointment_time)
    stmt = select(Appointment.id).where(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_time == appointment_time,
        Appointment.is_deleted == False,
        Appointment.status != AppointmentStatus.cancelled,
    )
    if exclude_appointment_id is not None:
        stmt = stmt.where(Appointment.id != exclude_appointment_id)
    return db.scalar(stmt.limit(1)) is not None


def list_doctor_busy_slot_starts_for_day(
    db: Session,
    doctor_id: UUID,
    day_start_utc: datetime,
    day_end_utc: datetime,
) -> set[datetime]:
    """Appointment start times on [day_start, day_end) that block a slot (scheduled or completed)."""
    stmt = select(Appointment.appointment_time).where(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_time >= day_start_utc,
            Appointment.appointment_time < day_end_utc,
            Appointment.is_deleted == False,
            Appointment.status != AppointmentStatus.cancelled,
        )
    )
    rows = db.scalars(stmt).all()
    out: set[datetime] = set()
    for t in rows:
        out.add(normalize_appointment_time_utc(t))
    return out



def update_appointment(
    db: Session,
    appointment: Appointment,
    update_data: dict[str, Any],
) -> Appointment:
    for field, value in update_data.items():
        setattr(appointment, field, value)

    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def soft_delete_appointment(db: Session, appointment: Appointment) -> Appointment:
    appointment.is_deleted = True
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def add_appointment_vitals(
    db: Session,
    appointment_id: UUID,
    temperature: float | None = None,
    bp_systolic: int | None = None,
    bp_diastolic: int | None = None,
    pulse: int | None = None,
    respiratory_rate: int | None = None,
    spo2: int | None = None,
    weight: float | None = None,
    height: float | None = None,
    bmi: float | None = None,
    notes: str | None = None,
) -> AppointmentVitals:
    vitals = AppointmentVitals(
        appointment_id=appointment_id,
        temperature=temperature,
        bp_systolic=bp_systolic,
        bp_diastolic=bp_diastolic,
        pulse=pulse,
        respiratory_rate=respiratory_rate,
        spo2=spo2,
        weight=weight,
        height=height,
        bmi=bmi,
        notes=notes,
    )
    db.add(vitals)
    db.flush()
    db.refresh(vitals)
    return vitals


def update_appointment_vitals(
    db: Session,
    vitals: AppointmentVitals,
    update_data: dict[str, Any],
) -> AppointmentVitals:
    for field, value in update_data.items():
        setattr(vitals, field, value)
    db.add(vitals)
    db.flush()
    db.refresh(vitals)
    return vitals


def get_vitals_by_appointment(db: Session, appointment_id: UUID) -> AppointmentVitals | None:
    stmt = select(AppointmentVitals).where(AppointmentVitals.appointment_id == appointment_id)
    return db.scalars(stmt).first()
