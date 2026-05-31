"""
Daily Care Dashboard Aggregate Service — Phase P3 Daily Care Dashboard + Adherence Experience.

Architecture:
  DailyCareDashboardAggregate is a READ-ONLY aggregate that composes existing domain data.
  It does NOT create new database tables or duplicate source-of-truth data.

  This service builds the aggregate by composing:
  1. medication_schedule_service — for Medicines Due Today + adherence metrics
  2. patient_workspace_service — for Upcoming Care, Continue Care, Timeline Preview
  3. patient_communication_service — for unread communications count
  4. Direct queries — for recent doctors, prescriptions, quick actions

CRITICAL:
  - Patient access is strictly scoped to their own data
  - Prescription data is NEVER mutated through this aggregate
  - Adherence actions affect tracking ONLY
  - No shadow adherence systems are created
  - Tenant isolation is enforced at every entry point
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.crud import crud_medication_schedule
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.patient_medication_schedule import (
    MedicationAdherenceLog,
    MedicationScheduleAdherenceAction,
    MedicationScheduleStatus,
    PatientMedicationSchedule,
)
from app.models.appointment import Prescription, PrescriptionItem
from app.models.user import User, UserRole
from app.schemas.daily_care import (
    ContinueCare,
    DailyCareDashboardAggregate,
    FollowUpBrief,
    HealthTimelinePreview,
    MedicinesDueToday,
    MedicationDueItem,
    QuickAction,
    QuickActions,
    RecentDoctorBrief,
    RecentPrescriptionBrief,
    TimelinePreviewCard,
    UpcomingAppointmentBrief,
    UpcomingCare,
)
from app.services import patient_service
from app.services.exceptions import ForbiddenError, NotFoundError

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Authorization helpers
# ═════════════════════════════════════════════════════════════════════════════


def _resolve_patient(db: Session, current_user: User) -> Patient:
    """Resolve the patient record for the current user. Raises ForbiddenError if not a patient."""
    if current_user.role != UserRole.patient:
        raise ForbiddenError("Only patients can access the daily care dashboard")
    try:
        return patient_service.get_patient_by_user_id(db, current_user.id)
    except NotFoundError:
        raise ForbiddenError("Patient profile not found for this user")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Medicines Due Today
# ═════════════════════════════════════════════════════════════════════════════


def _get_medicines_due_today(
    db: Session,
    patient: Patient,
) -> MedicinesDueToday:
    """
    Build the Medicines Due Today section.

    Groups medications by:
    - due_now: reminder time matches current hour
    - upcoming: reminder time is later today
    - overdue: reminder time has passed today without action
    - completed: already taken today

    Also computes lightweight adherence metrics.
    """
    now = _now_utc()
    current_hour = now.hour
    current_time_str = now.strftime("%H:%M")

    # Get due medications
    due_schedules = crud_medication_schedule.get_due_medications(
        db, UUID(str(patient.id)), UUID(str(patient.tenant_id))
    )

    # Get today's adherence logs
    today_logs = crud_medication_schedule.get_today_adherence_logs(
        db, UUID(str(patient.id))
    )

    # Build a lookup of schedule_id -> today's actions
    schedule_actions: dict[UUID, list[MedicationAdherenceLog]] = {}
    for log in today_logs:
        sid = UUID(str(log.medication_schedule_id))
        if sid not in schedule_actions:
            schedule_actions[sid] = []
        schedule_actions[sid].append(log)

    # Build MedicationDueItem for each schedule
    all_items: list[MedicationDueItem] = []
    for schedule in due_schedules:
        reminder_times = schedule.reminder_times or []
        if not reminder_times:
            # No specific reminder times — treat as due now
            actions = schedule_actions.get(UUID(str(schedule.id)), [])
            adherence_status = "pending"
            for action in actions:
                if action.action == MedicationScheduleAdherenceAction.taken:
                    adherence_status = "taken"
                    break
                elif action.action == MedicationScheduleAdherenceAction.skipped:
                    adherence_status = "skipped"
                    break
                elif action.action == MedicationScheduleAdherenceAction.snoozed:
                    adherence_status = "snoozed"
                    break

            all_items.append(
                MedicationDueItem(
                    schedule_id=schedule.id,
                    medicine_name=schedule.medicine_name,
                    dosage=schedule.dosage,
                    frequency=schedule.frequency,
                    instructions=schedule.instructions,
                    reminder_times=reminder_times,
                    adherence_status=adherence_status,
                    scheduled_time=None,
                    prescription_id=schedule.prescription_id,
                    prescription_item_id=schedule.prescription_item_id,
                )
            )
        else:
            for rt in reminder_times:
                actions = schedule_actions.get(UUID(str(schedule.id)), [])
                # Find action matching this reminder time
                adherence_status = "pending"
                for action in actions:
                    if action.scheduled_time == rt:
                        if action.action == MedicationScheduleAdherenceAction.taken:
                            adherence_status = "taken"
                        elif action.action == MedicationScheduleAdherenceAction.skipped:
                            adherence_status = "skipped"
                        elif action.action == MedicationScheduleAdherenceAction.snoozed:
                            adherence_status = "snoozed"
                        break

                all_items.append(
                    MedicationDueItem(
                        schedule_id=schedule.id,
                        medicine_name=schedule.medicine_name,
                        dosage=schedule.dosage,
                        frequency=schedule.frequency,
                        instructions=schedule.instructions,
                        reminder_times=reminder_times,
                        adherence_status=adherence_status,
                        scheduled_time=rt,
                        prescription_id=schedule.prescription_id,
                        prescription_item_id=schedule.prescription_item_id,
                    )
                )

    # Group by adherence status and time
    due_now: list[MedicationDueItem] = []
    upcoming: list[MedicationDueItem] = []
    overdue: list[MedicationDueItem] = []
    completed: list[MedicationDueItem] = []

    for item in all_items:
        if item.adherence_status == "taken":
            completed.append(item)
            continue

        if item.scheduled_time:
            # Compare scheduled time with current time
            try:
                hour, minute = map(int, item.scheduled_time.split(":"))
                scheduled_minutes = hour * 60 + minute
                current_minutes = current_hour * 60 + now.minute

                if scheduled_minutes <= current_minutes + 15 and scheduled_minutes >= current_minutes - 15:
                    # Within ~15 min window of current time
                    if item.adherence_status == "pending":
                        due_now.append(item)
                    else:
                        overdue.append(item)
                elif scheduled_minutes > current_minutes:
                    upcoming.append(item)
                else:
                    # Past scheduled time, not taken
                    if item.adherence_status == "pending":
                        overdue.append(item)
                    else:
                        # skipped or snoozed
                        upcoming.append(item)
            except (ValueError, IndexError):
                upcoming.append(item)
        else:
            # No scheduled time — treat as due now if pending
            if item.adherence_status == "pending":
                due_now.append(item)
            else:
                completed.append(item)

    # Compute counts
    total_due = len(all_items)
    taken_count = len(completed)
    skipped_count = sum(1 for i in all_items if i.adherence_status == "skipped")
    pending_count = sum(1 for i in all_items if i.adherence_status == "pending")
    adherence_rate_today = taken_count / total_due if total_due > 0 else 0.0

    # Compute streaks
    current_streak, longest_streak, week_rate = (
        crud_medication_schedule.compute_adherence_streak(
            db, UUID(str(patient.id))
        )
    )

    return MedicinesDueToday(
        due_now=due_now,
        upcoming=upcoming,
        overdue=overdue,
        completed=completed,
        total_due=total_due,
        taken_count=taken_count,
        skipped_count=skipped_count,
        pending_count=pending_count,
        adherence_rate_today=adherence_rate_today,
        current_streak_days=current_streak,
        longest_streak_days=longest_streak,
        week_adherence_rate=week_rate,
    )


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Upcoming Care
# ═════════════════════════════════════════════════════════════════════════════


def _get_upcoming_care(
    db: Session,
    patient: Patient,
) -> UpcomingCare:
    """
    Build the Upcoming Care section.

    Composes:
    - Next scheduled appointment
    - Upcoming and overdue follow-ups
    - Unread communications count
    """
    now = _now_utc()

    # ── Next appointment ────────────────────────────────────────────────────
    next_appt_stmt = (
        select(Appointment)
        .where(Appointment.patient_id == patient.id)
        .where(Appointment.is_deleted == False)
        .where(Appointment.status == AppointmentStatus.scheduled)
        .where(Appointment.appointment_time > now)
        .options(joinedload(Appointment.doctor))
        .order_by(Appointment.appointment_time.asc())
        .limit(1)
    )
    next_appt = db.scalar(next_appt_stmt)

    next_appointment_brief = None
    if next_appt:
        doctor_name = next_appt.doctor.name if next_appt.doctor else "Unknown Doctor"
        specialization = (
            getattr(next_appt.doctor, "specialization", None)
            if next_appt.doctor
            else None
        )
        next_appointment_brief = UpcomingAppointmentBrief(
            id=next_appt.id,
            appointment_time=next_appt.appointment_time,
            doctor_name=doctor_name,
            doctor_specialization=specialization,
            clinic_name=None,
            status=next_appt.status.value if next_appt.status else "scheduled",
        )

    # ── Follow-ups ──────────────────────────────────────────────────────────
    follow_up_stmt = (
        select(Appointment)
        .where(Appointment.patient_id == patient.id)
        .where(Appointment.is_deleted == False)
        .where(Appointment.follow_up_date.isnot(None))
        .options(joinedload(Appointment.doctor))
        .order_by(Appointment.follow_up_date.asc())
    )
    follow_up_appts = list(db.scalars(follow_up_stmt).unique().all())

    upcoming_follow_ups: list[FollowUpBrief] = []
    overdue_follow_ups: list[FollowUpBrief] = []

    for appt in follow_up_appts:
        if appt.follow_up_date is None:
            continue
        doctor_name = appt.doctor.name if appt.doctor else "Unknown Doctor"
        is_overdue = appt.follow_up_date < now

        brief = FollowUpBrief(
            appointment_id=appt.id,
            doctor_name=doctor_name,
            follow_up_date=appt.follow_up_date,
            follow_up_notes=appt.follow_up_notes,
            is_overdue=is_overdue,
        )

        if is_overdue:
            overdue_follow_ups.append(brief)
        else:
            upcoming_follow_ups.append(brief)

    # ── Unread communications ───────────────────────────────────────────────
    # Count unread notification events using NotificationDelivery read-status.
    # Architecture: NotificationEvent = event source-of-truth.
    # Read-tracking lives on NotificationDelivery.status, NOT on NotificationEvent.
    from app.models.notification import NotificationDelivery, NotificationDeliveryStatus, NotificationEvent

    # Subquery: event IDs that have at least one delivery marked as 'read'
    read_subq = (
        select(NotificationDelivery.notification_event_id)
        .distinct()
        .where(NotificationDelivery.status == NotificationDeliveryStatus.read)
        .subquery()
    )

    unread_stmt = (
        select(func.count())
        .select_from(NotificationEvent)
        .where(
            NotificationEvent.patient_id == patient.id,
            ~NotificationEvent.id.in_(select(read_subq)),
        )
    )
    unread_count = db.scalar(unread_stmt) or 0

    # ── Pending care tasks ──────────────────────────────────────────────────
    # Count: overdue follow-ups + pending medications
    pending_tasks = len(overdue_follow_ups)

    return UpcomingCare(
        next_appointment=next_appointment_brief,
        upcoming_follow_ups=upcoming_follow_ups,
        overdue_follow_ups=overdue_follow_ups,
        unread_communications=unread_count,
        pending_care_tasks=pending_tasks,
    )


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Continue Care
# ═════════════════════════════════════════════════════════════════════════════


def _get_continue_care(
    db: Session,
    patient: Patient,
) -> ContinueCare:
    """
    Build the Continue Care section.

    Surfaces:
    - Recent doctors the patient has visited
    - Recent prescriptions for download/reference
    """
    now = _now_utc()

    # ── Recent doctors ──────────────────────────────────────────────────────
    # Get distinct doctors from completed appointments, ordered by most recent
    recent_doctors_stmt = (
        select(Appointment.doctor_id, Doctor.name, Doctor.specialization)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .where(Appointment.patient_id == patient.id)
        .where(Appointment.is_deleted == False)
        .where(Appointment.status == AppointmentStatus.completed)
        .order_by(
            Appointment.doctor_id,
            Appointment.appointment_time.desc(),
        )
        .distinct(Appointment.doctor_id)
        .limit(5)
    )
    recent_doctor_rows = list(db.execute(recent_doctors_stmt).all())

    recent_doctors: list[RecentDoctorBrief] = []
    for row in recent_doctor_rows:
        # Get last visit date for this doctor
        last_visit_stmt = (
            select(Appointment.appointment_time)
            .where(
                Appointment.patient_id == patient.id,
                Appointment.doctor_id == row.doctor_id,
                Appointment.status == AppointmentStatus.completed,
            )
            .order_by(Appointment.appointment_time.desc())
            .limit(1)
        )
        last_visit = db.scalar(last_visit_stmt)

        # Check if there's an active prescription from this doctor
        rx_stmt = (
            select(func.count())
            .select_from(Prescription)
            .join(Appointment, Prescription.appointment_id == Appointment.id)
            .where(
                Appointment.patient_id == patient.id,
                Appointment.doctor_id == row.doctor_id,
            )
        )
        has_rx = (db.scalar(rx_stmt) or 0) > 0

        recent_doctors.append(
            RecentDoctorBrief(
                doctor_id=row.doctor_id,
                doctor_name=row.name or "Unknown Doctor",
                specialization=row.specialization,
                last_visit=last_visit,
                has_prescription=has_rx,
            )
        )

    # ── Recent prescriptions ────────────────────────────────────────────────
    rx_stmt = (
        select(Prescription)
        .join(Appointment, Prescription.appointment_id == Appointment.id)
        .where(Appointment.patient_id == patient.id)
        .where(Appointment.is_deleted == False)
        .options(
            joinedload(Prescription.appointment).joinedload(Appointment.doctor),
            selectinload(Prescription.items),
        )
        .order_by(Prescription.created_at.desc())
        .limit(5)
    )
    recent_rxs = list(db.scalars(rx_stmt).unique().all())

    recent_prescriptions: list[RecentPrescriptionBrief] = []
    for rx in recent_rxs:
        doctor_name = (
            rx.appointment.doctor.name if rx.appointment and rx.appointment.doctor else None
        )
        recent_prescriptions.append(
            RecentPrescriptionBrief(
                prescription_id=rx.id,
                appointment_id=rx.appointment_id,
                doctor_name=doctor_name,
                created_at=rx.created_at,
                medicine_count=len(rx.items) if rx.items else 0,
            )
        )

    return ContinueCare(
        recent_doctors=recent_doctors,
        recent_prescriptions=recent_prescriptions,
    )


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Health Timeline Preview
# ═════════════════════════════════════════════════════════════════════════════


def _get_health_timeline_preview(
    db: Session,
    patient: Patient,
) -> HealthTimelinePreview:
    """
    Build the Health Timeline Preview section.

    Returns the last 3 encounter preview cards.
    """
    # Get total encounter count
    total_stmt = (
        select(func.count())
        .select_from(Appointment)
        .where(
            Appointment.patient_id == patient.id,
            Appointment.is_deleted == False,
            Appointment.status == AppointmentStatus.completed,
        )
    )
    total_encounters = db.scalar(total_stmt) or 0

    # Get last 3 completed appointments
    recent_stmt = (
        select(Appointment)
        .where(Appointment.patient_id == patient.id)
        .where(Appointment.is_deleted == False)
        .where(Appointment.status == AppointmentStatus.completed)
        .options(
            joinedload(Appointment.doctor),
            selectinload(Appointment.prescriptions),
        )
        .order_by(Appointment.appointment_time.desc())
        .limit(3)
    )
    recent_appts = list(db.scalars(recent_stmt).unique().all())

    recent_cards: list[TimelinePreviewCard] = []
    for appt in recent_appts:
        doctor_name = appt.doctor.name if appt.doctor else "Unknown Doctor"
        specialization = (
            getattr(appt.doctor, "specialization", None) if appt.doctor else None
        )
        has_rx = len(appt.prescriptions) > 0 if appt.prescriptions else False

        recent_cards.append(
            TimelinePreviewCard(
                appointment_id=appt.id,
                appointment_time=appt.appointment_time,
                doctor_name=doctor_name,
                doctor_specialization=specialization,
                diagnosis=appt.diagnosis,
                treatment_summary=appt.treatment_summary,
                has_prescription=has_rx,
                has_encounter_summary=True,
            )
        )

    return HealthTimelinePreview(
        recent_cards=recent_cards,
        total_encounters=total_encounters,
    )


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Quick Actions
# ═════════════════════════════════════════════════════════════════════════════


def _get_quick_actions() -> QuickActions:
    """
    Build the Quick Actions section.

    Returns a curated list of action shortcuts.
    Future-ready actions are marked with is_future=True.
    """
    actions = [
        QuickAction(
            id="book_appointment",
            label="Book Appointment",
            icon="CalendarPlus",
            route="/patient/doctors",
            description="Find and book a doctor",
        ),
        QuickAction(
            id="view_medicines",
            label="My Medicines",
            icon="Pill",
            route="/patient/medicines",
            description="View your medication schedules",
        ),
        QuickAction(
            id="download_prescription",
            label="Download Prescription",
            icon="FileText",
            route="/patient/documents",
            description="Access your prescriptions",
        ),
        QuickAction(
            id="message_center",
            label="Messages",
            icon="MessageSquare",
            route="/patient/communications",
            description="View communications and reminders",
        ),
        QuickAction(
            id="view_timeline",
            label="Care Timeline",
            icon="Timeline",
            route="/patient/timeline",
            description="Your complete health history",
        ),
        # ── Future-ready actions ────────────────────────────────────────────
        # TODO: Phase 4 — Upload reports
        QuickAction(
            id="upload_reports",
            label="Upload Reports",
            icon="Upload",
            route="#",
            description="Upload lab reports and documents",
            is_future=True,
        ),
        # TODO: Phase 4 — Pharmacy ordering
        QuickAction(
            id="refill_medication",
            label="Refill Medication",
            icon="ShoppingCart",
            route="#",
            description="Order prescription refills",
            is_future=True,
        ),
        # TODO: Phase 4 — Family management
        QuickAction(
            id="family_care",
            label="Family Care",
            icon="Users",
            route="#",
            description="Manage family medications",
            is_future=True,
        ),
    ]

    return QuickActions(actions=actions)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN AGGREGATE
# ═════════════════════════════════════════════════════════════════════════════


def get_daily_care_dashboard(
    db: Session,
    current_user: User,
) -> DailyCareDashboardAggregate:
    """
    Build the full DailyCareDashboardAggregate for the authenticated patient.

    This is the SINGLE entry point for the Today's Care Dashboard.
    It composes existing domain data in a small number of efficient queries.

    Args:
        db: Database session.
        current_user: The authenticated user (must be patient role).

    Returns:
        DailyCareDashboardAggregate with all 5 dashboard sections.

    Raises:
        ForbiddenError: If the user is not a patient.
    """
    patient = _resolve_patient(db, current_user)

    # Build all sections
    medicines_due_today = _get_medicines_due_today(db, patient)
    upcoming_care = _get_upcoming_care(db, patient)
    continue_care = _get_continue_care(db, patient)
    health_timeline_preview = _get_health_timeline_preview(db, patient)
    quick_actions = _get_quick_actions()

    return DailyCareDashboardAggregate(
        medicines_due_today=medicines_due_today,
        upcoming_care=upcoming_care,
        continue_care=continue_care,
        health_timeline_preview=health_timeline_preview,
        quick_actions=quick_actions,
    )
