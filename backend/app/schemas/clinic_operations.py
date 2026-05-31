"""
Clinic Operations schemas — read-only aggregates for operational visibility.

These are QUERY-ONLY schemas. No new database models are created.
All data is computed/aggregated from existing models (Appointment, ClinicQueueEntry,
Billing, InventoryItem, InventoryStock, PurchaseOrder, etc.).
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ═════════════════════════════════════════════════════════════════════════════
# 1. OPERATIONAL DASHBOARDS
# ═════════════════════════════════════════════════════════════════════════════


class TodaySummaryCard(BaseModel):
    """Quick-glance KPI cards for the ops dashboard header."""

    model_config = ConfigDict(from_attributes=True)

    waiting_patients: int = 0
    active_consultations: int = 0
    overdue_appointments: int = 0
    pending_bills_count: int = 0
    pending_bills_amount: float = 0.0
    incomplete_encounters: int = 0
    low_stock_alerts: int = 0
    total_appointments_today: int = 0


class DoctorQueueSummary(BaseModel):
    """Per-doctor queue status for the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    doctor_id: UUID
    doctor_name: str
    waiting_count: int = 0
    in_consultation_count: int = 0
    completed_today: int = 0
    avg_wait_minutes: int | None = None
    next_patient_name: str | None = None
    status: str = "idle"  # 'active' | 'idle' | 'away'


class WaitingPatientItem(BaseModel):
    """A patient currently waiting in the clinic."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    status: str
    token_number: int | None = None
    wait_time_minutes: int = 0
    arrived_at: datetime | None = None
    priority: int = 0


class ActiveConsultationItem(BaseModel):
    """A consultation currently in progress."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    started_at: datetime | None = None
    duration_minutes: int = 0


class OverdueAppointmentItem(BaseModel):
    """An appointment that is past its scheduled time and not yet completed."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    appointment_time: datetime
    status: str
    minutes_overdue: int = 0


class PendingBillItem(BaseModel):
    """An unpaid bill requiring action."""

    model_config = ConfigDict(from_attributes=True)

    bill_id: UUID
    appointment_id: UUID | None = None
    patient_id: UUID
    patient_name: str
    amount: float
    created_at: datetime
    days_pending: int = 0


class IncompleteEncounterItem(BaseModel):
    """A completed appointment missing clinical documentation or billing."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    completed_at: datetime | None = None
    missing_clinical_notes: bool = False
    missing_prescriptions: bool = False
    missing_billing: bool = False


class LowStockAlertItem(BaseModel):
    """An inventory item below its low-stock threshold."""

    model_config = ConfigDict(from_attributes=True)

    item_id: UUID
    item_name: str
    current_quantity: int = 0
    low_stock_threshold: int = 0
    unit: str = ""
    days_until_out: int | None = None


class ClinicOperationsDashboard(BaseModel):
    """Complete clinic operations dashboard aggregate."""

    model_config = ConfigDict(from_attributes=True)

    summary: TodaySummaryCard
    doctor_queues: list[DoctorQueueSummary] = Field(default_factory=list)
    waiting_patients: list[WaitingPatientItem] = Field(default_factory=list)
    active_consultations: list[ActiveConsultationItem] = Field(default_factory=list)
    overdue_appointments: list[OverdueAppointmentItem] = Field(default_factory=list)
    pending_bills: list[PendingBillItem] = Field(default_factory=list)
    incomplete_encounters: list[IncompleteEncounterItem] = Field(default_factory=list)
    low_stock_alerts: list[LowStockAlertItem] = Field(default_factory=list)


# ═════════════════════════════════════════════════════════════════════════════
# 2. OPERATIONAL TASK FOUNDATION
# ═════════════════════════════════════════════════════════════════════════════


class TaskPriority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class TaskCategory(str, enum.Enum):
    encounter = "encounter"
    billing = "billing"
    inventory = "inventory"
    follow_up = "follow_up"
    prescription = "prescription"
    queue = "queue"


class OperationalTaskItem(BaseModel):
    """A single operational task — computed, not stored."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # composite: "{category}-{entity_id}" for dedup
    category: TaskCategory
    priority: TaskPriority
    title: str
    description: str | None = None
    entity_id: UUID  # appointment_id, bill_id, po_id, etc.
    patient_name: str | None = None
    doctor_name: str | None = None
    action_label: str | None = None
    action_url: str | None = None
    created_at: datetime
    is_actionable: bool = True


class OperationalTaskList(BaseModel):
    """Tasks grouped by priority."""

    model_config = ConfigDict(from_attributes=True)

    high_priority: list[OperationalTaskItem] = Field(default_factory=list)
    medium_priority: list[OperationalTaskItem] = Field(default_factory=list)
    low_priority: list[OperationalTaskItem] = Field(default_factory=list)
    total_count: int = 0


# ═════════════════════════════════════════════════════════════════════════════
# 3. ACTIVITY STREAM FOUNDATION
# ═════════════════════════════════════════════════════════════════════════════


class ActivityType(str, enum.Enum):
    patient_arrived = "patient_arrived"
    patient_checked_in = "patient_checked_in"
    vitals_completed = "vitals_completed"
    consultation_started = "consultation_started"
    consultation_completed = "consultation_completed"
    bill_generated = "bill_generated"
    bill_paid = "bill_paid"
    inventory_received = "inventory_received"
    low_stock_alert = "low_stock_alert"
    stock_received = "stock_received"


class ActivityStreamItem(BaseModel):
    """A single activity event in the clinic timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    activity_type: ActivityType
    title: str
    description: str | None = None
    patient_name: str | None = None
    doctor_name: str | None = None
    entity_id: UUID | None = None
    created_at: datetime
    icon: str | None = None  # hint for frontend icon selection


class ActivityStreamResponse(BaseModel):
    """Paginated activity stream."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ActivityStreamItem] = Field(default_factory=list)
    total: int = 0
    skip: int = 0
    limit: int = 50


# ═════════════════════════════════════════════════════════════════════════════
# 4. OPERATIONAL ALERTS
# ═════════════════════════════════════════════════════════════════════════════


class AlertSeverity(str, enum.Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class AlertCategory(str, enum.Enum):
    low_stock = "low_stock"
    overdue_appointment = "overdue_appointment"
    pending_billing = "pending_billing"
    delayed_queue = "delayed_queue"
    missed_follow_up = "missed_follow_up"
    incomplete_encounter = "incomplete_encounter"


class OperationalAlertItem(BaseModel):
    """A single operational alert — computed, not stored."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    category: AlertCategory
    severity: AlertSeverity
    title: str
    description: str | None = None
    entity_id: UUID | None = None
    action_url: str | None = None
    created_at: datetime


class OperationalAlertList(BaseModel):
    """Alerts grouped by severity with counts."""

    model_config = ConfigDict(from_attributes=True)

    items: list[OperationalAlertItem] = Field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    total: int = 0


# ═════════════════════════════════════════════════════════════════════════════
# 5. DOCTOR OPERATIONAL VISIBILITY
# ═════════════════════════════════════════════════════════════════════════════


class DoctorQueueSlot(BaseModel):
    """A single queue slot in the doctor's view."""

    model_config = ConfigDict(from_attributes=True)

    queue_entry_id: UUID
    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    token_number: int = 0
    status: str = "waiting"
    wait_time_minutes: int = 0
    priority: int = 0
    has_vitals: bool = False
    is_ready: bool = False


class DoctorOperationAction(BaseModel):
    """A quick action available to the doctor."""

    model_config = ConfigDict(from_attributes=True)

    action: str  # 'start_consultation', 'mark_ready', 'call_next'
    appointment_id: UUID | None = None
    queue_entry_id: UUID | None = None
    label: str


class DoctorOperationsView(BaseModel):
    """Complete doctor operations view aggregate."""

    model_config = ConfigDict(from_attributes=True)

    doctor_id: UUID
    doctor_name: str
    waiting_patients_count: int = 0
    current_patient: ActiveConsultationItem | None = None
    queue: list[DoctorQueueSlot] = Field(default_factory=list)
    completed_today: int = 0
    quick_actions: list[DoctorOperationAction] = Field(default_factory=list)
