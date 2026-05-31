"""
Medication Schedule schemas — adherence tracking layer.

Architecture:
  PatientMedicationSchedule is DERIVED from Prescription + PrescriptionItem.
  It is a reminder/adherence layer ONLY.
  Prescription remains the canonical source-of-truth.

  Patients CANNOT:
  - edit prescribed dosage
  - alter prescription instructions
  - overwrite doctor records

  Patient actions (taken/skipped/snooze) affect adherence tracking ONLY.
  They NEVER mutate the Prescription or PrescriptionItem rows.

CRITICAL:
  - Patient access is strictly scoped to their own data
  - Prescription data is NEVER mutated through these schemas
  - Adherence actions are audited
  - Tenant isolation is enforced at the service layer
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ═════════════════════════════════════════════════════════════════════════════
# CREATE — Derive schedule from prescription item
# ═════════════════════════════════════════════════════════════════════════════


class MedicationScheduleCreate(BaseModel):
    """
    Create a medication schedule derived from a prescription item.

    Only the patient who owns the prescription can create a schedule.
    The prescription item data is snapshotted — never editable.
    """

    model_config = ConfigDict(from_attributes=True)

    prescription_item_id: UUID
    start_date: datetime
    end_date: datetime | None = None
    reminder_times: list[str] = Field(
        default_factory=list,
        description="Array of HH:MM strings for reminder scheduling",
    )


# ═════════════════════════════════════════════════════════════════════════════
# READ — Patient-facing schedule view
# ═════════════════════════════════════════════════════════════════════════════


class MedicationScheduleRead(BaseModel):
    """
    Patient-safe medication schedule read model.

    Exposes adherence tracking data + snapshot of prescription info.
    NEVER exposes internal audit fields or other patients' data.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medicine_name: str
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    instructions: str | None = None
    start_date: datetime
    end_date: datetime | None = None
    reminder_times: list[str] = Field(default_factory=list)
    taken_count: int = 0
    skipped_count: int = 0
    total_doses: int = 0
    is_active: bool = True
    status: str = "active"
    adherence_rate: float | None = Field(
        default=None,
        description="Computed: taken / (taken + skipped). None if no actions recorded.",
    )
    prescription_id: UUID
    prescription_item_id: UUID
    created_at: datetime

    # TODO: Phase 2 — Refill countdown
    # refill_by_date: date | None = None
    # remaining_refills: int | None = None

    # TODO: Phase 2 — Recurring medication schedule
    # is_recurring: bool = False
    # recurring_interval_days: int | None = None

    # TODO: Phase 2 — Family/dependent assignment
    # assigned_to: str | None = None  # "self" | "dependent_name"


# ═════════════════════════════════════════════════════════════════════════════
# ADHERENCE — Patient actions
# ═════════════════════════════════════════════════════════════════════════════


class AdherenceAction(BaseModel):
    """
    Patient adherence action on a medication schedule.

    These actions affect adherence tracking ONLY.
    They NEVER modify the Prescription or PrescriptionItem rows.
    """

    model_config = ConfigDict(from_attributes=True)

    action: str = Field(
        ...,
        description="One of: taken, skipped, snoozed",
        pattern=r"^(taken|skipped|snoozed)$",
    )
    scheduled_time: str | None = Field(
        default=None,
        description="Which reminder slot this corresponds to (HH:MM format)",
    )


class AdherenceActionResponse(BaseModel):
    """
    Response after recording an adherence action.

    Returns the updated schedule with new counts.
    """

    model_config = ConfigDict(from_attributes=True)

    schedule: MedicationScheduleRead
    message: str = "Adherence recorded successfully"


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD — Today's adherence summary
# ═════════════════════════════════════════════════════════════════════════════


class TodayAdherenceSummary(BaseModel):
    """
    Today's medication adherence summary for the patient dashboard.

    Lightweight engagement tracking — NOT gamification.
    """

    model_config = ConfigDict(from_attributes=True)

    total_due_today: int = 0
    taken_today: int = 0
    skipped_today: int = 0
    pending_today: int = 0
    adherence_rate_today: float = 0.0  # 0.0 - 1.0

    # Lightweight streak tracking
    current_streak_days: int = 0
    longest_streak_days: int = 0
    week_adherence_rate: float = 0.0  # 0.0 - 1.0 over last 7 days

    # TODO: Phase 2 — Apple Health / Google Fit sync status
    # health_kit_synced: bool = False
    # google_fit_synced: bool = False

    # TODO: Phase 2 — Wearable sync status
    # wearable_connected: bool = False

    # TODO: Phase 2 — Family/dependent adherence overview
    # dependent_adherence: list[DependentAdherenceSummary] = []


# ═════════════════════════════════════════════════════════════════════════════
# LIST — Paginated response
# ═════════════════════════════════════════════════════════════════════════════


class MedicationScheduleListResponse(BaseModel):
    """Paginated list of medication schedules."""

    model_config = ConfigDict(from_attributes=True)

    items: list[MedicationScheduleRead]
    total: int
    skip: int
    limit: int


# ═════════════════════════════════════════════════════════════════════════════
# UPDATE — Patient-safe updates only
# ═════════════════════════════════════════════════════════════════════════════


class MedicationScheduleUpdate(BaseModel):
    """
    Patient-safe updates to a medication schedule.

    Patients can ONLY update:
    - reminder_times (when to be reminded)
    - is_active (pause/resume tracking)
    - status (pause/completed)

    Patients CANNOT update:
    - medicine_name, dosage, frequency, duration, instructions
    - These are snapshotted from the prescription and are immutable.
    """

    model_config = ConfigDict(from_attributes=True)

    reminder_times: list[str] | None = None
    is_active: bool | None = None
    status: str | None = Field(
        default=None,
        description="One of: active, paused, completed",
        pattern=r"^(active|paused|completed)$",
    )
