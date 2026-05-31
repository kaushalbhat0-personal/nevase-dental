"""
Clinic Operations service — read-only aggregation for operational visibility.

This service queries existing models (Appointment, ClinicQueueEntry, Billing,
InventoryItem, InventoryStock, etc.) to produce operational
dashboard views, tasks, activity streams, alerts, and doctor visibility.

NO new database models are created. This is a pure query/aggregation layer.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytz
from sqlalchemy import and_, case, exists, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Billing, BillingStatus
from app.models.clinic_queue import ClinicQueueEntry, ClinicQueueStatus
from app.models.doctor import Doctor
from app.models.inventory import InventoryItem, InventoryStock
from app.models.patient import Patient

from app.schemas.clinic_operations import (
    ActiveConsultationItem,
    ActivityStreamItem,
    ActivityStreamResponse,
    ActivityType,
    AlertCategory,
    AlertSeverity,
    ClinicOperationsDashboard,
    DoctorOperationAction,
    DoctorOperationsView,
    DoctorQueueSlot,
    DoctorQueueSummary,
    IncompleteEncounterItem,
    LowStockAlertItem,
    OperationalAlertItem,
    OperationalAlertList,
    OperationalTaskItem,
    OperationalTaskList,
    OverdueAppointmentItem,
    PendingBillItem,
    TaskCategory,
    TaskPriority,
    TodaySummaryCard,
    WaitingPatientItem,
)

logger = logging.getLogger(__name__)

# IST timezone for "today" calculations
IST = pytz.timezone("Asia/Kolkata")


def _now_ist() -> datetime:
    return datetime.now(IST)


def _today_start_ist() -> datetime:
    now = _now_ist()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _today_end_ist() -> datetime:
    return _today_start_ist() + timedelta(days=1)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# 1. TODAY SUMMARY
# ═════════════════════════════════════════════════════════════════════════════


def get_today_summary(db: Session, tenant_id: UUID) -> TodaySummaryCard:
    """Compute today's summary KPIs for a tenant."""
    today_start = _today_start_ist()
    today_end = _today_end_ist()

    # Waiting patients: queue entries with waiting status
    waiting_patients = (
        db.query(func.count(ClinicQueueEntry.id))
        .filter(
            ClinicQueueEntry.tenant_id == tenant_id,
            ClinicQueueEntry.queue_status == ClinicQueueStatus.waiting,
            ClinicQueueEntry.queue_date == date.today(),
        )
        .scalar()
        or 0
    )

    # Active consultations: appointments in_consultation today
    active_consultations = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.in_consultation,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
        )
        .scalar()
        or 0
    )

    # Overdue appointments: past scheduled time, not completed/cancelled/no_show
    now = _utc_now()
    overdue_appointments = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.appointment_time < now,
            Appointment.is_deleted == False,  # noqa: E712
            ~Appointment.status.in_(
                [
                    AppointmentStatus.completed,
                    AppointmentStatus.cancelled,
                    AppointmentStatus.no_show,
                ]
            ),
        )
        .scalar()
        or 0
    )

    # Pending bills
    pending_bills_count = (
        db.query(func.count(Billing.id))
        .filter(
            Billing.tenant_id == tenant_id,
            Billing.status == BillingStatus.unpaid,
            Billing.is_deleted == False,  # noqa: E712
        )
        .scalar()
        or 0
    )
    pending_bills_amount = (
        db.query(func.coalesce(func.sum(Billing.amount), 0))
        .filter(
            Billing.tenant_id == tenant_id,
            Billing.status == BillingStatus.unpaid,
            Billing.is_deleted == False,  # noqa: E712
        )
        .scalar()
        or 0
    )

    # Incomplete encounters: completed today but missing clinical notes or billing
    incomplete_encounters = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.completed,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
            or_(
                Appointment.clinical_notes.is_(None),
                Appointment.clinical_notes == "",
                ~exists().where(
                    Billing.appointment_id == Appointment.id,
                    Billing.is_deleted == False,  # noqa: E712
                ),
            ),
        )
        .scalar()
        or 0
    )

    # Low stock alerts
    low_stock_alerts = (
        db.query(func.count(InventoryItem.id))
        .select_from(InventoryItem)
        .join(InventoryStock, InventoryStock.item_id == InventoryItem.id)
        .filter(
            InventoryItem.tenant_id == tenant_id,
            InventoryItem.is_active == True,  # noqa: E712
            InventoryItem.low_stock_threshold.isnot(None),
            InventoryStock.quantity <= InventoryItem.low_stock_threshold,
        )
        .scalar()
        or 0
    )

    # Total appointments today
    total_appointments_today = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
        )
        .scalar()
        or 0
    )

    return TodaySummaryCard(
        waiting_patients=waiting_patients,
        active_consultations=active_consultations,
        overdue_appointments=overdue_appointments,
        pending_bills_count=pending_bills_count,
        pending_bills_amount=float(pending_bills_amount),
        incomplete_encounters=incomplete_encounters,
        low_stock_alerts=low_stock_alerts,
    total_appointments_today=total_appointments_today,
    )


# ═════════════════════════════════════════════════════════════════════════════
# 2. DOCTOR QUEUE SUMMARIES
# ═════════════════════════════════════════════════════════════════════════════


def get_doctor_queue_summaries(db: Session, tenant_id: UUID) -> list[DoctorQueueSummary]:
    """Per-doctor queue summaries for the dashboard."""
    today_start = _today_start_ist()
    today_end = _today_end_ist()

    doctors = (
        db.query(Doctor)
        .filter(
            Doctor.tenant_id == tenant_id,
            Doctor.is_deleted == False,  # noqa: E712
        )
        .all()
    )

    summaries: list[DoctorQueueSummary] = []
    for doc in doctors:
        # Waiting count
        waiting_count = (
            db.query(func.count(ClinicQueueEntry.id))
            .filter(
                ClinicQueueEntry.doctor_id == doc.id,
                ClinicQueueEntry.queue_status == ClinicQueueStatus.waiting,
                ClinicQueueEntry.queue_date == date.today(),
            )
            .scalar()
            or 0
        )

        # In consultation count
        in_consultation_count = (
            db.query(func.count(Appointment.id))
            .filter(
                Appointment.doctor_id == doc.id,
                Appointment.tenant_id == tenant_id,
                Appointment.status == AppointmentStatus.in_consultation,
                Appointment.is_deleted == False,  # noqa: E712
                Appointment.appointment_time >= today_start,
                Appointment.appointment_time < today_end,
            )
            .scalar()
            or 0
        )

        # Completed today
        completed_today = (
            db.query(func.count(Appointment.id))
            .filter(
                Appointment.doctor_id == doc.id,
                Appointment.tenant_id == tenant_id,
                Appointment.status == AppointmentStatus.completed,
                Appointment.is_deleted == False,  # noqa: E712
                Appointment.appointment_time >= today_start,
                Appointment.appointment_time < today_end,
            )
            .scalar()
            or 0
        )

        # Next patient name
        next_entry = (
            db.query(ClinicQueueEntry)
            .filter(
                ClinicQueueEntry.doctor_id == doc.id,
                ClinicQueueEntry.queue_status == ClinicQueueStatus.waiting,
                ClinicQueueEntry.queue_date == date.today(),
            )
            .order_by(ClinicQueueEntry.token_number.asc())
            .first()
        )
        next_patient_name = None
        if next_entry:
            patient = db.get(Patient, next_entry.patient_id)
            if patient:
                next_patient_name = patient.name

        # Determine status
        status = "idle"
        if in_consultation_count > 0:
            status = "active"
        elif waiting_count > 0:
            status = "active"

        summaries.append(
            DoctorQueueSummary(
                doctor_id=doc.id,
                doctor_name=doc.name or "Unknown",
                waiting_count=waiting_count,
                in_consultation_count=in_consultation_count,
                completed_today=completed_today,
                next_patient_name=next_patient_name,
                status=status,
            )
        )

    return summaries


# ═════════════════════════════════════════════════════════════════════════════
# 3. WAITING PATIENTS
# ═════════════════════════════════════════════════════════════════════════════


def get_waiting_patients(db: Session, tenant_id: UUID) -> list[WaitingPatientItem]:
    """Patients currently waiting in the clinic."""
    now = _utc_now()
    entries = (
        db.query(ClinicQueueEntry)
        .filter(
            ClinicQueueEntry.tenant_id == tenant_id,
            ClinicQueueEntry.queue_status == ClinicQueueStatus.waiting,
            ClinicQueueEntry.queue_date == date.today(),
        )
        .order_by(ClinicQueueEntry.priority.desc(), ClinicQueueEntry.token_number.asc())
        .all()
    )

    items: list[WaitingPatientItem] = []
    for entry in entries:
        patient = db.get(Patient, entry.patient_id)
        doctor = db.get(Doctor, entry.doctor_id)
        wait_minutes = 0
        if entry.entered_at:
            wait_minutes = int((now - entry.entered_at).total_seconds() / 60)

        items.append(
            WaitingPatientItem(
                appointment_id=entry.appointment_id,
                patient_id=entry.patient_id,
                patient_name=patient.name if patient else "Unknown",
                doctor_id=entry.doctor_id,
                doctor_name=doctor.name if doctor else "Unknown",
                status=entry.queue_status.value,
                token_number=entry.token_number,
                wait_time_minutes=wait_minutes,
                arrived_at=entry.entered_at,
                priority=entry.priority,
            )
        )

    return items


# ═════════════════════════════════════════════════════════════════════════════
# 4. ACTIVE CONSULTATIONS
# ═════════════════════════════════════════════════════════════════════════════


def get_active_consultations(db: Session, tenant_id: UUID) -> list[ActiveConsultationItem]:
    """Consultations currently in progress."""
    today_start = _today_start_ist()
    today_end = _today_end_ist()
    now = _utc_now()

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.in_consultation,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
        )
        .order_by(Appointment.encounter_started_at.asc())
        .all()
    )

    items: list[ActiveConsultationItem] = []
    for appt in appointments:
        patient = db.get(Patient, appt.patient_id)
        doctor = db.get(Doctor, appt.doctor_id)
        duration = 0
        if appt.encounter_started_at:
            duration = int((now - appt.encounter_started_at).total_seconds() / 60)

        items.append(
            ActiveConsultationItem(
                appointment_id=appt.id,
                patient_id=appt.patient_id,
                patient_name=patient.name if patient else "Unknown",
                doctor_id=appt.doctor_id,
                doctor_name=doctor.name if doctor else "Unknown",
                started_at=appt.encounter_started_at,
                duration_minutes=duration,
            )
        )

    return items


# ═════════════════════════════════════════════════════════════════════════════
# 5. OVERDUE APPOINTMENTS
# ═════════════════════════════════════════════════════════════════════════════


def get_overdue_appointments(db: Session, tenant_id: UUID) -> list[OverdueAppointmentItem]:
    """Appointments past their scheduled time, not yet completed."""
    now = _utc_now()

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.appointment_time < now,
            Appointment.is_deleted == False,  # noqa: E712
            ~Appointment.status.in_(
                [
                    AppointmentStatus.completed,
                    AppointmentStatus.cancelled,
                    AppointmentStatus.no_show,
                ]
            ),
        )
        .order_by(Appointment.appointment_time.asc())
        .limit(50)
        .all()
    )

    items: list[OverdueAppointmentItem] = []
    for appt in appointments:
        patient = db.get(Patient, appt.patient_id)
        doctor = db.get(Doctor, appt.doctor_id)
        minutes_overdue = int((now - appt.appointment_time).total_seconds() / 60)

        items.append(
            OverdueAppointmentItem(
                appointment_id=appt.id,
                patient_id=appt.patient_id,
                patient_name=patient.name if patient else "Unknown",
                doctor_id=appt.doctor_id,
                doctor_name=doctor.name if doctor else "Unknown",
                appointment_time=appt.appointment_time,
                status=appt.status.value,
                minutes_overdue=minutes_overdue,
            )
        )

    return items


# ═════════════════════════════════════════════════════════════════════════════
# 6. PENDING BILLS
# ═════════════════════════════════════════════════════════════════════════════


def get_pending_bills(db: Session, tenant_id: UUID) -> list[PendingBillItem]:
    """Unpaid bills requiring action."""
    now = _utc_now()

    bills = (
        db.query(Billing)
        .filter(
            Billing.tenant_id == tenant_id,
            Billing.status == BillingStatus.unpaid,
            Billing.is_deleted == False,  # noqa: E712
        )
        .order_by(Billing.created_at.asc())
        .limit(50)
        .all()
    )

    items: list[PendingBillItem] = []
    for bill in bills:
        patient = db.get(Patient, bill.patient_id)
        days_pending = 0
        if bill.created_at:
            days_pending = (now - bill.created_at).days

        items.append(
            PendingBillItem(
                bill_id=bill.id,
                appointment_id=bill.appointment_id,
                patient_id=bill.patient_id,
                patient_name=patient.name if patient else "Unknown",
                amount=float(bill.amount),
                created_at=bill.created_at,
                days_pending=days_pending,
            )
        )

    return items


# ═════════════════════════════════════════════════════════════════════════════
# 7. INCOMPLETE ENCOUNTERS
# ═════════════════════════════════════════════════════════════════════════════


def get_incomplete_encounters(db: Session, tenant_id: UUID) -> list[IncompleteEncounterItem]:
    """Completed appointments missing clinical documentation or billing."""
    today_start = _today_start_ist()
    today_end = _today_end_ist()

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.completed,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
            or_(
                Appointment.clinical_notes.is_(None),
                Appointment.clinical_notes == "",
                ~exists().where(
                    Billing.appointment_id == Appointment.id,
                    Billing.is_deleted == False,  # noqa: E712
                ),
            ),
        )
        .order_by(Appointment.appointment_time.desc())
        .limit(50)
        .all()
    )

    items: list[IncompleteEncounterItem] = []
    for appt in appointments:
        patient = db.get(Patient, appt.patient_id)
        doctor = db.get(Doctor, appt.doctor_id)

        missing_notes = not appt.clinical_notes or appt.clinical_notes.strip() == ""
        missing_billing = not (
            db.query(Billing)
            .filter(
                Billing.appointment_id == appt.id,
                Billing.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        missing_prescriptions = not appt.prescriptions or len(appt.prescriptions) == 0

        items.append(
            IncompleteEncounterItem(
                appointment_id=appt.id,
                patient_id=appt.patient_id,
                patient_name=patient.name if patient else "Unknown",
                doctor_id=appt.doctor_id,
                doctor_name=doctor.name if doctor else "Unknown",
                completed_at=appt.encounter_completed_at or appt.appointment_time,
                missing_clinical_notes=missing_notes,
                missing_prescriptions=missing_prescriptions,
                missing_billing=missing_billing,
            )
        )

    return items


# ═════════════════════════════════════════════════════════════════════════════
# 8. LOW STOCK ALERTS
# ═════════════════════════════════════════════════════════════════════════════


def get_low_stock_alerts(db: Session, tenant_id: UUID) -> list[LowStockAlertItem]:
    """Inventory items below their low-stock threshold."""
    rows = (
        db.query(InventoryItem, InventoryStock)
        .join(InventoryStock, InventoryStock.item_id == InventoryItem.id)
        .filter(
            InventoryItem.tenant_id == tenant_id,
            InventoryItem.is_active == True,  # noqa: E712
            InventoryItem.low_stock_threshold.isnot(None),
            InventoryStock.quantity <= InventoryItem.low_stock_threshold,
            InventoryStock.doctor_id.is_(None),  # Only tenant-level stock
        )
        .order_by(InventoryStock.quantity.asc())
        .all()
    )

    items: list[LowStockAlertItem] = []
    for item, stock in rows:
        items.append(
            LowStockAlertItem(
                item_id=item.id,
                item_name=item.name,
                current_quantity=stock.quantity,
                low_stock_threshold=item.low_stock_threshold or 0,
                unit=item.unit,
                days_until_out=None,  # Would need consumption rate data
            )
        )

    return items





# ═════════════════════════════════════════════════════════════════════════════
# 10. FULL DASHBOARD AGGREGATE
# ═════════════════════════════════════════════════════════════════════════════


def get_clinic_operations_dashboard(
    db: Session, tenant_id: UUID
) -> ClinicOperationsDashboard:
    """Build the complete clinic operations dashboard."""
    summary = get_today_summary(db, tenant_id)
    doctor_queues = get_doctor_queue_summaries(db, tenant_id)
    waiting_patients = get_waiting_patients(db, tenant_id)
    active_consultations = get_active_consultations(db, tenant_id)
    overdue_appointments = get_overdue_appointments(db, tenant_id)
    pending_bills = get_pending_bills(db, tenant_id)
    incomplete_encounters = get_incomplete_encounters(db, tenant_id)
    low_stock_alerts = get_low_stock_alerts(db, tenant_id)

    return ClinicOperationsDashboard(
        summary=summary,
        doctor_queues=doctor_queues,
        waiting_patients=waiting_patients,
        active_consultations=active_consultations,
        overdue_appointments=overdue_appointments,
        pending_bills=pending_bills,
        incomplete_encounters=incomplete_encounters,
        low_stock_alerts=low_stock_alerts,
    )


# ═════════════════════════════════════════════════════════════════════════════
# 11. OPERATIONAL TASKS
# ═════════════════════════════════════════════════════════════════════════════


def get_operational_tasks(db: Session, tenant_id: UUID) -> OperationalTaskList:
    """Compute operational tasks from existing data."""
    tasks: list[OperationalTaskItem] = []
    now = _utc_now()
    today_start = _today_start_ist()
    today_end = _today_end_ist()

    # ── Incomplete encounter tasks (high priority) ──
    incomplete = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.completed,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
            or_(
                Appointment.clinical_notes.is_(None),
                Appointment.clinical_notes == "",
            ),
        )
        .limit(20)
        .all()
    )
    for appt in incomplete:
        patient = db.get(Patient, appt.patient_id)
        doctor = db.get(Doctor, appt.doctor_id)
        tasks.append(
            OperationalTaskItem(
                id=f"encounter-{appt.id}",
                category=TaskCategory.encounter,
                priority=TaskPriority.high,
                title="Incomplete encounter documentation",
                description=f"Clinical notes missing for {patient.name if patient else 'Unknown'}'s visit",
                entity_id=appt.id,
                patient_name=patient.name if patient else None,
                doctor_name=doctor.name if doctor else None,
                action_label="Complete notes",
                action_url=f"/doctor/appointments/{appt.id}",
                created_at=appt.encounter_completed_at or appt.appointment_time,
            )
        )

    # ── Pending bill tasks (high priority) ──
    pending_bills = (
        db.query(Billing)
        .filter(
            Billing.tenant_id == tenant_id,
            Billing.status == BillingStatus.unpaid,
            Billing.is_deleted == False,  # noqa: E712
        )
        .limit(20)
        .all()
    )
    for bill in pending_bills:
        patient = db.get(Patient, bill.patient_id)
        tasks.append(
            OperationalTaskItem(
                id=f"billing-{bill.id}",
                category=TaskCategory.billing,
                priority=TaskPriority.high,
                title=f"Pending bill — ₹{float(bill.amount):.0f}",
                description=f"Unpaid bill for {patient.name if patient else 'Unknown'}",
                entity_id=bill.id,
                patient_name=patient.name if patient else None,
                action_label="Process payment",
                action_url=f"/billing?id={bill.id}",
                created_at=bill.created_at,
            )
        )

    # ── Low stock tasks (medium priority) ──
    low_stock_items = (
        db.query(InventoryItem)
        .join(InventoryStock, InventoryStock.item_id == InventoryItem.id)
        .filter(
            InventoryItem.tenant_id == tenant_id,
            InventoryItem.is_active == True,  # noqa: E712
            InventoryItem.low_stock_threshold.isnot(None),
            InventoryStock.quantity <= InventoryItem.low_stock_threshold,
            InventoryStock.doctor_id.is_(None),
        )
        .limit(20)
        .all()
    )
    for item in low_stock_items:
        tasks.append(
            OperationalTaskItem(
                id=f"inventory-{item.id}",
                category=TaskCategory.inventory,
                priority=TaskPriority.medium,
                title=f"Low stock: {item.name}",
                description=f"Below threshold ({item.low_stock_threshold})",
                entity_id=item.id,
                action_label="Order stock",
                action_url="/admin/inventory",
                created_at=_utc_now(),
            )
        )

    # ── Overdue follow-up tasks (medium priority) ──
    overdue_followups = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.follow_up_date.isnot(None),
            Appointment.follow_up_date < now,
            Appointment.is_deleted == False,  # noqa: E712
        )
        .limit(20)
        .all()
    )
    for appt in overdue_followups:
        patient = db.get(Patient, appt.patient_id)
        doctor = db.get(Doctor, appt.doctor_id)
        tasks.append(
            OperationalTaskItem(
                id=f"followup-{appt.id}",
                category=TaskCategory.follow_up,
                priority=TaskPriority.medium,
                title="Overdue follow-up",
                description=f"Follow-up callback needed for {patient.name if patient else 'Unknown'}",
                entity_id=appt.id,
                patient_name=patient.name if patient else None,
                doctor_name=doctor.name if doctor else None,
                action_label="Schedule follow-up",
                action_url=f"/doctor/appointments/{appt.id}",
                created_at=appt.follow_up_date,
            )
        )

    # Sort into priority buckets
    high: list[OperationalTaskItem] = []
    medium: list[OperationalTaskItem] = []
    low: list[OperationalTaskItem] = []

    for t in tasks:
        if t.priority == TaskPriority.high:
            high.append(t)
        elif t.priority == TaskPriority.medium:
            medium.append(t)
        else:
            low.append(t)

    return OperationalTaskList(
        high_priority=high,
        medium_priority=medium,
        low_priority=low,
        total_count=len(tasks),
    )


# ═════════════════════════════════════════════════════════════════════════════
# 12. ACTIVITY STREAM
# ═════════════════════════════════════════════════════════════════════════════


def get_activity_stream(
    db: Session, tenant_id: UUID, skip: int = 0, limit: int = 50
) -> ActivityStreamResponse:
    """Build clinic activity stream from existing data."""
    items: list[ActivityStreamItem] = []
    today_start = _today_start_ist()
    today_end = _today_end_ist()

    # ── Patient arrivals (from queue entries) ──
    arrivals = (
        db.query(ClinicQueueEntry)
        .filter(
            ClinicQueueEntry.tenant_id == tenant_id,
            ClinicQueueEntry.queue_date == date.today(),
        )
        .order_by(ClinicQueueEntry.entered_at.desc())
        .limit(20)
        .all()
    )
    for entry in arrivals:
        patient = db.get(Patient, entry.patient_id)
        doctor = db.get(Doctor, entry.doctor_id)
        items.append(
            ActivityStreamItem(
                id=f"arrival-{entry.id}",
                activity_type=ActivityType.patient_arrived,
                title=f"{patient.name if patient else 'Patient'} arrived",
                description=f"Token #{entry.token_number} — Dr. {doctor.name if doctor else 'Unknown'}",
                patient_name=patient.name if patient else None,
                doctor_name=doctor.name if doctor else None,
                entity_id=entry.appointment_id,
                created_at=entry.entered_at,
                icon="user-check",
            )
        )

    # ── Consultation started ──
    consultations_started = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.in_consultation,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
        )
        .order_by(Appointment.encounter_started_at.desc())
        .limit(20)
        .all()
    )
    for appt in consultations_started:
        patient = db.get(Patient, appt.patient_id)
        doctor = db.get(Doctor, appt.doctor_id)
        items.append(
            ActivityStreamItem(
                id=f"consult-start-{appt.id}",
                activity_type=ActivityType.consultation_started,
                title=f"Consultation started — {patient.name if patient else 'Unknown'}",
                description=f"With Dr. {doctor.name if doctor else 'Unknown'}",
                patient_name=patient.name if patient else None,
                doctor_name=doctor.name if doctor else None,
                entity_id=appt.id,
                created_at=appt.encounter_started_at or appt.appointment_time,
                icon="stethoscope",
            )
        )

    # ── Consultation completed ──
    consultations_completed = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.completed,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
        )
        .order_by(Appointment.encounter_completed_at.desc())
        .limit(20)
        .all()
    )
    for appt in consultations_completed:
        patient = db.get(Patient, appt.patient_id)
        doctor = db.get(Doctor, appt.doctor_id)
        items.append(
            ActivityStreamItem(
                id=f"consult-end-{appt.id}",
                activity_type=ActivityType.consultation_completed,
                title=f"Consultation completed — {patient.name if patient else 'Unknown'}",
                description=f"By Dr. {doctor.name if doctor else 'Unknown'}",
                patient_name=patient.name if patient else None,
                doctor_name=doctor.name if doctor else None,
                entity_id=appt.id,
                created_at=appt.encounter_completed_at or appt.appointment_time,
                icon="check-circle",
            )
        )

    # ── Bills generated today ──
    bills = (
        db.query(Billing)
        .filter(
            Billing.tenant_id == tenant_id,
            Billing.is_deleted == False,  # noqa: E712
            Billing.created_at >= today_start,
            Billing.created_at < today_end,
        )
        .order_by(Billing.created_at.desc())
        .limit(20)
        .all()
    )
    for bill in bills:
        patient = db.get(Patient, bill.patient_id)
        items.append(
            ActivityStreamItem(
                id=f"bill-{bill.id}",
                activity_type=ActivityType.bill_generated,
                title=f"Bill generated — ₹{float(bill.amount):.0f}",
                description=f"For {patient.name if patient else 'Unknown'} ({bill.status.value})",
                patient_name=patient.name if patient else None,
                entity_id=bill.id,
                created_at=bill.created_at,
                icon="receipt",
            )
        )

    # Sort all items by created_at descending
    items.sort(key=lambda x: x.created_at, reverse=True)

    # Paginate
    total = len(items)
    paginated = items[skip : skip + limit]

    return ActivityStreamResponse(
        items=paginated,
        total=total,
        skip=skip,
        limit=limit,
    )


# ═════════════════════════════════════════════════════════════════════════════
# 13. OPERATIONAL ALERTS
# ═════════════════════════════════════════════════════════════════════════════


def get_operational_alerts(db: Session, tenant_id: UUID) -> OperationalAlertList:
    """Compute operational alerts from existing data."""
    alerts: list[OperationalAlertItem] = []
    now = _utc_now()
    today_start = _today_start_ist()
    today_end = _today_end_ist()

    # ── Low stock alerts (critical) ──
    low_stock_items = (
        db.query(InventoryItem)
        .join(InventoryStock, InventoryStock.item_id == InventoryItem.id)
        .filter(
            InventoryItem.tenant_id == tenant_id,
            InventoryItem.is_active == True,  # noqa: E712
            InventoryItem.low_stock_threshold.isnot(None),
            InventoryStock.quantity <= InventoryItem.low_stock_threshold,
            InventoryStock.doctor_id.is_(None),
        )
        .order_by(InventoryStock.quantity.asc())
        .limit(10)
        .all()
    )
    for item in low_stock_items:
        stock_qty = 0
        if hasattr(item, "stock") and item.stock:
            stock_qty = item.stock.quantity
        alerts.append(
            OperationalAlertItem(
                id=f"low-stock-{item.id}",
                category=AlertCategory.low_stock,
                severity=AlertSeverity.critical,
                title=f"Low stock: {item.name}",
                description=f"Current: {stock_qty} (threshold: {item.low_stock_threshold})",
                entity_id=item.id,
                created_at=now,
            )
        )

    # ── Overdue appointments (high) ──
    overdue_count = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.appointment_time < now,
            Appointment.is_deleted == False,  # noqa: E712
            ~Appointment.status.in_(
                [
                    AppointmentStatus.completed,
                    AppointmentStatus.cancelled,
                    AppointmentStatus.no_show,
                ]
            ),
        )
        .scalar()
        or 0
    )
    if overdue_count > 0:
        alerts.append(
            OperationalAlertItem(
                id="overdue-appointments",
                category=AlertCategory.overdue_appointments,
                severity=AlertSeverity.high,
                title=f"{overdue_count} overdue appointment(s)",
                description="Patients waiting past scheduled time",
                entity_id=None,
                created_at=now,
            )
        )

    # ── Pending billing (high) ──
    pending_bills_count = (
        db.query(func.count(Billing.id))
        .filter(
            Billing.tenant_id == tenant_id,
            Billing.status == BillingStatus.unpaid,
            Billing.is_deleted == False,  # noqa: E712
        )
        .scalar()
        or 0
    )
    if pending_bills_count > 0:
        alerts.append(
            OperationalAlertItem(
                id="pending-billing",
                category=AlertCategory.pending_billing,
                severity=AlertSeverity.high,
                title=f"{pending_bills_count} pending bill(s)",
                description="Unpaid bills requiring action",
                entity_id=None,
                created_at=now,
            )
        )

    # ── Delayed queue (medium) ──
    long_waiting = (
        db.query(func.count(ClinicQueueEntry.id))
        .filter(
            ClinicQueueEntry.tenant_id == tenant_id,
            ClinicQueueEntry.queue_status == ClinicQueueStatus.waiting,
            ClinicQueueEntry.queue_date == date.today(),
            ClinicQueueEntry.entered_at.isnot(None),
            ClinicQueueEntry.entered_at < (now - timedelta(minutes=30)),
        )
        .scalar()
        or 0
    )
    if long_waiting > 0:
        alerts.append(
            OperationalAlertItem(
                id="delayed-queue",
                category=AlertCategory.delayed_queue,
                severity=AlertSeverity.medium,
                title=f"{long_waiting} patient(s) waiting >30 min",
                description="Queue delay detected",
                entity_id=None,
                created_at=now,
            )
        )

    # ── Missed follow-ups (medium) ──
    missed_followups = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.follow_up_date.isnot(None),
            Appointment.follow_up_date < now,
            Appointment.is_deleted == False,  # noqa: E712
        )
        .scalar()
        or 0
    )
    if missed_followups > 0:
        alerts.append(
            OperationalAlertItem(
                id="missed-followups",
                category=AlertCategory.missed_followups,
                severity=AlertSeverity.medium,
                title=f"{missed_followups} missed follow-up(s)",
                description="Overdue follow-up callbacks",
                entity_id=None,
                created_at=now,
            )
        )

    # Sort by severity
    severity_order = {
        AlertSeverity.critical: 0,
        AlertSeverity.high: 1,
        AlertSeverity.medium: 2,
        AlertSeverity.low: 3,
    }
    alerts.sort(key=lambda a: severity_order.get(a.severity, 99))

    return OperationalAlertList(
        alerts=alerts,
        total_count=len(alerts),
    )


# ═════════════════════════════════════════════════════════════════════════════
# 14. DOCTOR OPERATIONS VIEW
# ═════════════════════════════════════════════════════════════════════════════


def get_doctor_operations_view(
    db: Session, tenant_id: UUID, doctor_id: UUID
) -> DoctorOperationsView:
    """Build a doctor-specific operations view."""
    today_start = _today_start_ist()
    today_end = _today_end_ist()
    now = _utc_now()

    # ── Queue slots ──
    queue_entries = (
        db.query(ClinicQueueEntry)
        .filter(
            ClinicQueueEntry.doctor_id == doctor_id,
            ClinicQueueEntry.queue_date == date.today(),
            ClinicQueueEntry.queue_status == ClinicQueueStatus.waiting,
        )
        .order_by(ClinicQueueEntry.token_number.asc())
        .all()
    )

    queue_slots: list[DoctorQueueSlot] = []
    for entry in queue_entries:
        patient = db.get(Patient, entry.patient_id)
        wait_minutes = 0
        if entry.entered_at:
            wait_minutes = int((now - entry.entered_at).total_seconds() / 60)
        queue_slots.append(
            DoctorQueueSlot(
                appointment_id=entry.appointment_id,
                patient_id=entry.patient_id,
                patient_name=patient.name if patient else "Unknown",
                token_number=entry.token_number,
                wait_time_minutes=wait_minutes,
                priority=entry.priority,
                arrived_at=entry.entered_at,
            )
        )

    # ── Active consultation ──
    active_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.in_consultation,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
        )
        .first()
    )

    active_consultation = None
    if active_appointment:
        patient = db.get(Patient, active_appointment.patient_id)
        duration = 0
        if active_appointment.encounter_started_at:
            duration = int((now - active_appointment.encounter_started_at).total_seconds() / 60)
        active_consultation = ActiveConsultationItem(
            appointment_id=active_appointment.id,
            patient_id=active_appointment.patient_id,
            patient_name=patient.name if patient else "Unknown",
            doctor_id=active_appointment.doctor_id,
            doctor_name=None,
            started_at=active_appointment.encounter_started_at,
            duration_minutes=duration,
        )

    # ── Waiting count ──
    waiting_count = len(queue_slots)

    # ── Completed today ──
    completed_today = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.completed,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
        )
        .scalar()
        or 0
    )

    # ── Quick actions ──
    actions: list[DoctorOperationAction] = []

    if active_appointment:
        actions.append(
            DoctorOperationAction(
                label="Finish encounter",
                action="finish_encounter",
                appointment_id=active_appointment.id,
                icon="check-circle",
            )
        )
    elif queue_slots:
        actions.append(
            DoctorOperationAction(
                label="Call next patient",
                action="call_next",
                appointment_id=queue_slots[0].appointment_id,
                icon="user-plus",
            )
        )

    if queue_slots:
        actions.append(
            DoctorOperationAction(
                label="Mark ready",
                action="mark_ready",
                appointment_id=queue_slots[0].appointment_id,
                icon="thumbs-up",
            )
        )

    return DoctorOperationsView(
        doctor_id=doctor_id,
        queue_slots=queue_slots,
        active_consultation=active_consultation,
        waiting_count=waiting_count,
        completed_today=completed_today,
        actions=actions,
    )


# ═════════════════════════════════════
