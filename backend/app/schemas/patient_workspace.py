"""
Patient Health Workspace Aggregate schema — READ-ONLY aggregate for the patient portal.

This is a **read model** that composes existing domain schemas.
It does NOT create a separate Encounter table.
Appointment remains the encounter anchor.

Patient workspace is READ-ORIENTED:
  Doctor workflows mutate.
  Patient workspace consumes aggregates.

CRITICAL:
  - Patient access is strictly scoped to their own data
  - SOAP internal sections are NEVER exposed
  - Doctor-only notes are NEVER exposed
  - Audit metadata is NEVER exposed
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ═════════════════════════════════════════════════════════════════════════════
# PATIENT PROFILE
# ═════════════════════════════════════════════════════════════════════════════


class PatientProfileRead(BaseModel):
    """Patient profile information for the workspace header."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    age: int | None = None
    gender: str | None = None
    phone: str | None = None

    # TODO: Phase 2 — Profile image
    # profile_image_url: str | None = None

    # TODO: Phase 2 — Blood group
    # blood_group: str | None = None

    # TODO: Phase 2 — Allergies
    # allergies: list[str] = Field(default_factory=list)

    # TODO: Phase 2 — Chronic conditions
    # chronic_conditions: list[str] = Field(default_factory=list)


# ═════════════════════════════════════════════════════════════════════════════
# ENCOUNTER CARD — patient-safe encounter summary for timeline
# ═════════════════════════════════════════════════════════════════════════════


class EncounterCard(BaseModel):
    """
    Patient-safe encounter summary for timeline rendering.

    CRITICAL: This is a READ-ONLY aggregate.
    SOAP internal sections are NEVER exposed.
    Doctor-only notes are NEVER exposed.
    """

    model_config = ConfigDict(from_attributes=True)

    # ── Core encounter anchor ──────────────────────────────────────────────
    appointment_id: UUID
    appointment_time: datetime
    status: str

    # ── Doctor & clinic ────────────────────────────────────────────────────
    doctor_id: UUID
    doctor_name: str
    doctor_specialization: str | None = None
    clinic_name: str | None = None

    # ── Clinical data (patient-safe) ───────────────────────────────────────
    diagnosis: str | None = None
    treatment_summary: str | None = None

    # ── Prescriptions summary ──────────────────────────────────────────────
    prescriptions_count: int = 0

    # ── Follow-up ──────────────────────────────────────────────────────────
    follow_up_date: datetime | None = None
    follow_up_notes: str | None = None

    # ── Documents availability ─────────────────────────────────────────────
    has_prescription: bool = False
    has_encounter_summary: bool = False

    # ── Encounter timing ───────────────────────────────────────────────────
    encounter_started_at: datetime | None = None
    encounter_completed_at: datetime | None = None

    # TODO: Phase 2 — AI health summary
    # ai_summary: str | None = None

    # TODO: Phase 2 — Attachments / lab reports
    # has_lab_reports: bool = False

    # TODO: Phase 2 — Vaccination administered
    # vaccination_administered: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# UPCOMING APPOINTMENT CARD
# ═════════════════════════════════════════════════════════════════════════════


class AppointmentCard(BaseModel):
    """Upcoming appointment card for the workspace."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    appointment_time: datetime
    status: str
    doctor_id: UUID
    doctor_name: str
    doctor_specialization: str | None = None
    clinic_name: str | None = None

    # TODO: Phase 2 — Telemedicine link
    # telemedicine_url: str | None = None

    # TODO: Phase 2 — Pre-visit instructions
    # pre_visit_instructions: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# VITALS SNAPSHOT — chronological vitals history
# ═════════════════════════════════════════════════════════════════════════════


class VitalsSnapshot(BaseModel):
    """Vitals captured during an appointment, for chronological history."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    appointment_time: datetime
    doctor_name: str | None = None

    temperature: float | None = None
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    pulse: int | None = None
    respiratory_rate: int | None = None
    spo2: int | None = None
    weight: float | None = None
    height: float | None = None
    bmi: float | None = None
    notes: str | None = None

    # TODO: Phase 2 — Blood glucose
    # blood_glucose: float | None = None

    # TODO: Phase 2 — Cholesterol
    # cholesterol_total: float | None = None
    # cholesterol_ldl: float | None = None
    # cholesterol_hdl: float | None = None

    # TODO: Phase 2 — Wearable integrations
    # steps: int | None = None
    # sleep_hours: float | None = None
    # heart_rate_variability: int | None = None


# ═════════════════════════════════════════════════════════════════════════════
# PRESCRIPTION SUMMARY
# ═════════════════════════════════════════════════════════════════════════════


class PrescriptionItemSummary(BaseModel):
    """Single prescribed medicine item."""

    model_config = ConfigDict(from_attributes=True)

    medicine_name: str
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    instructions: str | None = None


class PrescriptionSummary(BaseModel):
    """Prescription summary for patient display."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    appointment_id: UUID
    appointment_time: datetime | None = None
    doctor_name: str | None = None
    notes: str | None = None
    created_at: datetime
    items: list[PrescriptionItemSummary] = Field(default_factory=list)

    # TODO: Phase 2 — Medication reminders
    # reminder_enabled: bool = False
    # reminder_schedule: str | None = None

    # TODO: Phase 2 — Refill status
    # refills_remaining: int | None = None
    # refill_due_date: datetime | None = None


# ═════════════════════════════════════════════════════════════════════════════
# FOLLOW-UP SUMMARY
# ═════════════════════════════════════════════════════════════════════════════


class FollowUpItem(BaseModel):
    """Single follow-up recommendation."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    appointment_time: datetime
    doctor_id: UUID
    doctor_name: str
    doctor_specialization: str | None = None
    follow_up_date: datetime
    follow_up_notes: str | None = None
    is_overdue: bool = False

    # TODO: Phase 2 — Reminder automation
    # reminder_scheduled: bool = False
    # reminder_channel: str | None = None

    # TODO: Phase 2 — AI follow-up summary
    # ai_follow_up_summary: str | None = None

    # TODO: Phase 2 — Care plan reference
    # care_plan_id: UUID | None = None


class FollowUpSummary(BaseModel):
    """Aggregated follow-up information."""

    model_config = ConfigDict(from_attributes=True)

    upcoming: list[FollowUpItem] = Field(default_factory=list)
    overdue: list[FollowUpItem] = Field(default_factory=list)
    total_upcoming: int = 0
    total_overdue: int = 0

    # TODO: Phase 2 — Chronic disease tracking
    # chronic_condition_follow_ups: list[FollowUpItem] = Field(default_factory=list)

    # TODO: Phase 2 — Care plan adherence
    # care_plan_adherence_rate: float | None = None


# ═════════════════════════════════════════════════════════════════════════════
# BILLING SUMMARY
# ═════════════════════════════════════════════════════════════════════════════


class BillMini(BaseModel):
    """Minimal bill information for patient display."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    currency: str
    status: str
    description: str | None = None
    created_at: datetime
    paid_at: datetime | None = None


class BillingSummary(BaseModel):
    """Aggregated billing information for the patient."""

    model_config = ConfigDict(from_attributes=True)

    total_billed: Decimal = Decimal("0.00")
    total_paid: Decimal = Decimal("0.00")
    total_unpaid: Decimal = Decimal("0.00")
    recent_bills: list[BillMini] = Field(default_factory=list)

    # TODO: Phase 2 — Insurance information
    # insurance_provider: str | None = None
    # insurance_coverage: Decimal | None = None


# ═════════════════════════════════════════════════════════════════════════════
# DOCUMENT REFERENCE
# ═════════════════════════════════════════════════════════════════════════════


class DocumentRef(BaseModel):
    """Reference to a downloadable document."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    appointment_time: datetime | None = None
    doctor_name: str | None = None
    document_type: str  # "prescription" | "encounter_summary" | "invoice"
    download_url: str | None = None

    # TODO: Phase 2 — Lab reports
    # lab_report_url: str | None = None
    # lab_report_date: datetime | None = None


# ═════════════════════════════════════════════════════════════════════════════
# COMMUNICATION SUMMARY (future-ready)
# ═════════════════════════════════════════════════════════════════════════════


class CommunicationSummary(BaseModel):
    """Future-ready communication summary."""

    model_config = ConfigDict(from_attributes=True)

    unread_messages: int = 0
    last_message_at: datetime | None = None

    # TODO: Phase 2 — In-app messaging
    # recent_conversations: list[ConversationPreview] = Field(default_factory=list)

    # TODO: Phase 2 — Notification preferences
    # email_notifications: bool = True
    # sms_notifications: bool = True
    # push_notifications: bool = True


# ═════════════════════════════════════════════════════════════════════════════
# WORKSPACE AGGREGATE
# ═════════════════════════════════════════════════════════════════════════════


class PatientHealthWorkspaceAggregate(BaseModel):
    """
    Canonical READ-ONLY aggregate for the Patient Health Workspace.

    This is the SINGLE source of truth for:
    * Patient health timeline rendering
    * Encounter detail views
    * Vitals history
    * Follow-up tracking
    * Document downloads
    * Billing overview

    Appointment is the encounter anchor. No separate Encounter table exists.

    CRITICAL:
    - Patient access is strictly scoped to their own data
    - SOAP internal sections are NEVER exposed
    - Doctor-only notes are NEVER exposed
    - Audit metadata is NEVER exposed
    """

    model_config = ConfigDict(from_attributes=True)

    # ── Patient profile ────────────────────────────────────────────────────
    patient_profile: PatientProfileRead

    # ── Upcoming appointments ──────────────────────────────────────────────
    upcoming_appointments: list[AppointmentCard] = Field(default_factory=list)

    # ── Recent encounters (timeline) ───────────────────────────────────────
    recent_encounters: list[EncounterCard] = Field(default_factory=list)

    # ── Vitals history ─────────────────────────────────────────────────────
    vitals_history: list[VitalsSnapshot] = Field(default_factory=list)

    # ── Prescriptions history ──────────────────────────────────────────────
    prescriptions_history: list[PrescriptionSummary] = Field(default_factory=list)

    # ── Follow-up recommendations ──────────────────────────────────────────
    follow_ups: FollowUpSummary = Field(default_factory=FollowUpSummary)

    # ── Billing summary ────────────────────────────────────────────────────
    billing_summary: BillingSummary = Field(default_factory=BillingSummary)

    # ── Recent documents ───────────────────────────────────────────────────
    recent_documents: list[DocumentRef] = Field(default_factory=list)

    # ── Communication summary (future-ready) ───────────────────────────────
    communication_summary: CommunicationSummary = Field(
        default_factory=CommunicationSummary
    )

    # ══════════════════════════════════════════════════════════════════════
    # FUTURE EXTENSION HOOKS (Phase 2+)
    # ══════════════════════════════════════════════════════════════════════
    #
    # TODO: AI health summaries
    # ai_health_summary: str | None = None
    #
    # TODO: Medication reminders
    # active_reminders: list[MedicationReminder] = Field(default_factory=list)
    #
    # TODO: Wearable integrations
    # wearable_data: WearableSummary | None = None
    #
    # TODO: Lab reports
    # lab_reports: list[LabReportRef] = Field(default_factory=list)
    #
    # TODO: Family/dependent accounts
    # dependents: list[DependentProfile] = Field(default_factory=list)
    #
    # TODO: Vaccination history
    # vaccination_history: list[VaccinationRecord] = Field(default_factory=list)
    #
    # TODO: Chronic disease tracking
    # chronic_disease_status: list[ChronicConditionStatus] = Field(default_factory=list)
    #
    # TODO: Health score
    # health_score: HealthScore | None = None
    #
    # TODO: Multilingual patient summaries
    # locale: str = "en"
