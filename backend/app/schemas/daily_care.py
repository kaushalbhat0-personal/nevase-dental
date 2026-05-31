"""
Daily Care Dashboard Aggregate schema — Phase P3 Daily Care Dashboard + Adherence Experience.

Architecture:
  DailyCareDashboardAggregate is a READ-ONLY aggregate that composes existing domain data.
  It does NOT create new database tables or duplicate source-of-truth data.

  Sections:
  1. MedicinesDueToday — derived from PatientMedicationSchedule + MedicationAdherenceLog
  2. UpcomingCare — derived from appointments, follow-ups, communications
  3. ContinueCare — derived from recent doctors, prescriptions
  4. HealthTimelinePreview — mini preview cards from recent encounters
  5. QuickActions — static + dynamic action shortcuts

CRITICAL:
  - Patient access is strictly scoped to their own data
  - Prescription data is NEVER mutated through this aggregate
  - Adherence actions affect tracking ONLY
  - No shadow adherence systems are created
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Medicines Due Today
# ═════════════════════════════════════════════════════════════════════════════


class MedicationDueItem(BaseModel):
    """A single medication due for the patient today."""

    model_config = ConfigDict(from_attributes=True)

    schedule_id: UUID
    medicine_name: str
    dosage: str | None = None
    frequency: str | None = None
    instructions: str | None = None
    reminder_times: list[str] = Field(default_factory=list)

    # Adherence state for today
    adherence_status: str = "pending"  # "pending" | "taken" | "skipped" | "snoozed"
    scheduled_time: str | None = Field(
        default=None,
        description="Which reminder slot this corresponds to (HH:MM)",
    )

    # Prescription reference (immutable)
    prescription_id: UUID
    prescription_item_id: UUID


class MedicinesDueToday(BaseModel):
    """Grouped medications due today."""

    model_config = ConfigDict(from_attributes=True)

    due_now: list[MedicationDueItem] = Field(
        default_factory=list,
        description="Medications due within the current hour window",
    )
    upcoming: list[MedicationDueItem] = Field(
        default_factory=list,
        description="Medications due later today",
    )
    overdue: list[MedicationDueItem] = Field(
        default_factory=list,
        description="Medications past their scheduled time without action",
    )
    completed: list[MedicationDueItem] = Field(
        default_factory=list,
        description="Medications already taken today",
    )
    total_due: int = 0
    taken_count: int = 0
    skipped_count: int = 0
    pending_count: int = 0

    # Lightweight adherence metrics
    adherence_rate_today: float = 0.0  # 0.0 - 1.0
    current_streak_days: int = 0
    longest_streak_days: int = 0
    week_adherence_rate: float = 0.0  # 0.0 - 1.0 over last 7 days

    # TODO: Phase 4 — Apple Health / Google Fit sync status
    # health_kit_synced: bool = False
    # google_fit_synced: bool = False

    # TODO: Phase 4 — Wearable sync status
    # wearable_connected: bool = False

    # TODO: Phase 4 — Family/dependent adherence overview
    # dependent_adherence: list[DependentAdherenceSummary] = []


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Upcoming Care
# ═════════════════════════════════════════════════════════════════════════════


class UpcomingAppointmentBrief(BaseModel):
    """Brief upcoming appointment for the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    appointment_time: datetime
    doctor_name: str
    doctor_specialization: str | None = None
    clinic_name: str | None = None
    status: str


class FollowUpBrief(BaseModel):
    """Brief follow-up for the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    doctor_name: str
    follow_up_date: datetime
    follow_up_notes: str | None = None
    is_overdue: bool = False


class UpcomingCare(BaseModel):
    """Upcoming care section of the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    next_appointment: UpcomingAppointmentBrief | None = None
    upcoming_follow_ups: list[FollowUpBrief] = Field(default_factory=list)
    overdue_follow_ups: list[FollowUpBrief] = Field(default_factory=list)
    unread_communications: int = 0
    pending_care_tasks: int = 0

    # TODO: Phase 4 — Telemedicine link for next appointment
    # telemedicine_url: str | None = None

    # TODO: Phase 4 — Pre-visit instructions
    # pre_visit_instructions: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Continue Care
# ═════════════════════════════════════════════════════════════════════════════


class RecentDoctorBrief(BaseModel):
    """Brief doctor info for continue care."""

    model_config = ConfigDict(from_attributes=True)

    doctor_id: UUID
    doctor_name: str
    specialization: str | None = None
    clinic_name: str | None = None
    last_visit: datetime | None = None
    has_prescription: bool = False


class RecentPrescriptionBrief(BaseModel):
    """Brief prescription info for continue care."""

    model_config = ConfigDict(from_attributes=True)

    prescription_id: UUID
    appointment_id: UUID
    doctor_name: str | None = None
    created_at: datetime
    medicine_count: int = 0


class ContinueCare(BaseModel):
    """Continue care section of the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    recent_doctors: list[RecentDoctorBrief] = Field(
        default_factory=list,
        description="Doctors the patient has visited recently, for rebooking",
    )
    recent_prescriptions: list[RecentPrescriptionBrief] = Field(
        default_factory=list,
        description="Recent prescriptions for download/reference",
    )

    # TODO: Phase 4 — Active treatment plans
    # active_treatment_plans: list[TreatmentPlanBrief] = []

    # TODO: Phase 4 — Chronic disease programs
    # chronic_programs: list[ChronicProgramBrief] = []


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Health Timeline Preview
# ═════════════════════════════════════════════════════════════════════════════


class TimelinePreviewCard(BaseModel):
    """Mini preview card from a recent encounter."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    appointment_time: datetime
    doctor_name: str
    doctor_specialization: str | None = None
    diagnosis: str | None = None
    treatment_summary: str | None = None
    has_prescription: bool = False
    has_encounter_summary: bool = False


class HealthTimelinePreview(BaseModel):
    """Health timeline preview section of the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    recent_cards: list[TimelinePreviewCard] = Field(
        default_factory=list,
        description="Last 3 encounter preview cards",
    )
    total_encounters: int = 0

    # TODO: Phase 4 — Upcoming scheduled encounters
    # upcoming_encounters: list[TimelinePreviewCard] = []


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Quick Actions
# ═════════════════════════════════════════════════════════════════════════════


class QuickAction(BaseModel):
    """A quick action shortcut for the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    icon: str  # lucide icon name
    route: str
    description: str | None = None
    is_future: bool = False  # True for TODO future-ready actions


class QuickActions(BaseModel):
    """Quick actions section of the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    actions: list[QuickAction] = Field(default_factory=list)


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD AGGREGATE
# ═════════════════════════════════════════════════════════════════════════════


class DailyCareDashboardAggregate(BaseModel):
    """
    Canonical READ-ONLY aggregate for the Today's Care Dashboard.

    This is the SINGLE entry point for the patient's daily care view.
    It composes existing domain data — it does NOT create new tables.

    Sections:
    1. MedicinesDueToday — adherence tracking for today's medications
    2. UpcomingCare — next appointment, follow-ups, pending tasks
    3. ContinueCare — recent doctors, prescriptions for continuity
    4. HealthTimelinePreview — mini preview cards from recent encounters
    5. QuickActions — action shortcuts

    CRITICAL:
    - Patient access is strictly scoped to their own data
    - Prescription data is NEVER mutated through this aggregate
    - Adherence actions affect tracking ONLY
    - No shadow adherence systems are created
    """

    model_config = ConfigDict(from_attributes=True)

    # ── Section 1: Medicines Due Today ─────────────────────────────────────
    medicines_due_today: MedicinesDueToday = Field(
        default_factory=MedicinesDueToday
    )

    # ── Section 2: Upcoming Care ───────────────────────────────────────────
    upcoming_care: UpcomingCare = Field(default_factory=UpcomingCare)

    # ── Section 3: Continue Care ───────────────────────────────────────────
    continue_care: ContinueCare = Field(default_factory=ContinueCare)

    # ── Section 4: Health Timeline Preview ─────────────────────────────────
    health_timeline_preview: HealthTimelinePreview = Field(
        default_factory=HealthTimelinePreview
    )

    # ── Section 5: Quick Actions ───────────────────────────────────────────
    quick_actions: QuickActions = Field(default_factory=QuickActions)

    # ══════════════════════════════════════════════════════════════════════
    # FUTURE EXTENSION HOOKS (Phase 4+)
    # ══════════════════════════════════════════════════════════════════════
    #
    # TODO: Wearable integration — daily activity summary
    # TODO: Refill reminders — prescriptions nearing depletion
    # TODO: Pharmacy ordering — one-tap refill request
    # TODO: Family medication management — caregiver view
    # TODO: Chronic disease programs — condition-specific care plans
    # TODO: Vaccination schedules — upcoming vaccine reminders
    # TODO: Apple Health / Google Fit sync — biometric data
    # TODO: Smart notification batching — grouped by urgency
