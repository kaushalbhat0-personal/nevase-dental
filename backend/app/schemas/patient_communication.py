"""
Patient Communication Aggregate schema — Phase P2 Patient Communication Center.

Architecture:
  This is a READ-ONLY aggregate that composes existing notification data.
  It does NOT create duplicate storage or shadow inbox systems.
  
  NotificationEvent remains the source-of-truth.
  Communication delivery remains infrastructure-level.
  Patient UI CONSUMES communication aggregates — it does not own delivery workflows.

CRITICAL:
  - Patient access is strictly scoped to their own data
  - Provider delivery internals are NEVER exposed
  - Audit metadata is NEVER exposed
  - Internal notification payloads are NEVER exposed
  - Other patients' communications are NEVER exposed

TODO: Phase 3 — AI health assistant integration
TODO: Phase 3 — Conversational chat
TODO: Phase 3 — Care-plan nudges
TODO: Phase 3 — Medication adherence tracking
TODO: Phase 3 — Voice reminders
TODO: Phase 3 — Push notifications
TODO: Phase 3 — Family/dependent notifications
TODO: Phase 3 — Multilingual templates
TODO: Phase 3 — Patient-provider messaging
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ═════════════════════════════════════════════════════════════════════════════
# COMMUNICATION CARD — patient-safe notification display
# ═════════════════════════════════════════════════════════════════════════════


class CTA_ACTION(str):
    """Canonical CTA action types for communication cards."""

    VIEW_DETAILS = "view_details"
    RESCHEDULE = "reschedule"
    PAY_NOW = "pay_now"
    VIEW_INVOICE = "view_invoice"
    VIEW_PRESCRIPTION = "view_prescription"
    SCHEDULE_NOW = "schedule_now"
    DOWNLOAD_DOCUMENT = "download_document"
    VIEW_ENCOUNTER = "view_encounter"


class CommunicationCard(BaseModel):
    """
    Patient-safe communication card for timeline/inbox display.

    CRITICAL: Only exposes patient-safe fields.
    - NO delivery internal metadata (provider_response, error_message, retry_count)
    - NO audit data
    - NO other patients' data
    - NO internal notification payloads
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    title: str = ""  # Rendered from template
    summary: str = ""  # Rendered from template
    created_at: datetime
    is_read: bool = False
    is_urgent: bool = False

    # ── Related entities (patient-safe) ────────────────────────────────────
    doctor_name: str | None = None
    clinic_name: str | None = None
    linked_appointment_id: UUID | None = None
    linked_bill_id: UUID | None = None

    # ── Document links ─────────────────────────────────────────────────────
    linked_documents: list[DocumentLink] = Field(default_factory=list)

    # ── CTA actions ────────────────────────────────────────────────────────
    cta_actions: list[str] = Field(default_factory=list)

    # TODO: Phase 3 — AI health assistant context
    # ai_context: str | None = None

    # TODO: Phase 3 — Conversational chat thread
    # thread_id: UUID | None = None


class DocumentLink(BaseModel):
    """Reference to a downloadable document from a communication."""

    model_config = ConfigDict(from_attributes=True)

    document_type: str  # "prescription" | "encounter_summary" | "invoice"
    download_url: str | None = None
    appointment_id: UUID | None = None

    # TODO: Phase 3 — Lab reports
    # lab_report_url: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# REMINDER CARD — patient-safe reminder display
# ═════════════════════════════════════════════════════════════════════════════


class ReminderCard(BaseModel):
    """
    Patient-safe reminder display.

    Visual hierarchy:
    - urgent: overdue follow-ups, unpaid bills past due
    - upcoming: tomorrow's appointments, upcoming follow-ups
    - completed: past visits, paid bills
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    title: str = ""
    reminder_date: datetime
    urgency: str = "upcoming"  # "urgent" | "upcoming" | "completed"
    doctor_name: str | None = None
    clinic_name: str | None = None
    linked_appointment_id: UUID | None = None
    linked_bill_id: UUID | None = None
    cta_actions: list[str] = Field(default_factory=list)

    # TODO: Phase 3 — AI reminder prioritization score
    # ai_priority_score: float | None = None

    # TODO: Phase 3 — Smart nudge timing
    # next_nudge_at: datetime | None = None

    # TODO: Phase 3 — Medication adherence
    # medication_name: str | None = None
    # adherence_rate: float | None = None


# ═════════════════════════════════════════════════════════════════════════════
# COMMUNICATION PREFERENCES
# ═════════════════════════════════════════════════════════════════════════════


class CommunicationPreferencesRead(BaseModel):
    """Patient communication preferences — read model."""

    model_config = ConfigDict(from_attributes=True)

    email_enabled: bool = True
    sms_enabled: bool = True
    whatsapp_enabled: bool = False
    reminder_enabled: bool = True

    # Future-ready fields
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    locale: str = "en"
    opt_out_all: bool = False

    # TODO: Phase 3 — Quiet hours enforcement
    # TODO: Phase 3 — Multilingual communication
    # TODO: Phase 3 — Consent management / GDPR
    # TODO: Phase 3 — Opt-out audit trail


class CommunicationPreferencesUpdate(BaseModel):
    """Patient communication preferences — update model."""

    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    whatsapp_enabled: bool | None = None
    reminder_enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    locale: str | None = None
    opt_out_all: bool | None = None

    # TODO: Phase 3 — Consent management fields
    # consent_granted_at: datetime | None = None
    # consent_revoked_at: datetime | None = None


# ═════════════════════════════════════════════════════════════════════════════
# PATIENT COMMUNICATION AGGREGATE
# ═════════════════════════════════════════════════════════════════════════════


class PatientCommunicationAggregate(BaseModel):
    """
    Canonical READ-ONLY aggregate for patient communications.

    Composes existing NotificationEvent data into a patient-friendly view.
    NotificationEvent remains the source-of-truth.

    CRITICAL:
    - Patient access is strictly scoped to their own data
    - Provider delivery internals are NEVER exposed
    - Audit metadata is NEVER exposed
    - Internal notification payloads are NEVER exposed
    """

    model_config = ConfigDict(from_attributes=True)

    # ── Recent notifications (timeline) ────────────────────────────────────
    recent_notifications: list[CommunicationCard] = Field(default_factory=list)

    # ── Unread count ───────────────────────────────────────────────────────
    unread_count: int = 0

    # ── Reminders by urgency ───────────────────────────────────────────────
    reminders_by_urgency: dict[str, list[ReminderCard]] = Field(
        default_factory=lambda: {"urgent": [], "upcoming": [], "completed": []}
    )

    # ── Communication preferences ──────────────────────────────────────────
    preferences: CommunicationPreferencesRead = Field(
        default_factory=CommunicationPreferencesRead
    )

    # ── Linked documents ───────────────────────────────────────────────────
    linked_documents: list[DocumentLink] = Field(default_factory=list)

    # ══════════════════════════════════════════════════════════════════════
    # FUTURE EXTENSION HOOKS (Phase 3+)
    # ══════════════════════════════════════════════════════════════════════
    #
    # TODO: AI health assistant
    # ai_assistant_summary: str | None = None
    #
    # TODO: Conversational chat
    # recent_conversations: list[ConversationPreview] = Field(default_factory=list)
    #
    # TODO: Care-plan nudges
    # care_plan_nudges: list[CarePlanNudge] = Field(default_factory=list)
    #
    # TODO: Medication adherence
    # medication_adherence: list[MedicationAdherence] = Field(default_factory=list)
    #
    # TODO: Voice reminders
    # voice_reminder_enabled: bool = False
    #
    # TODO: Push notification tokens
    # push_tokens: list[str] = Field(default_factory=list)
    #
    # TODO: Family/dependent notifications
    # dependent_notifications: list[DependentNotification] = Field(default_factory=list)
    #
    # TODO: Patient-provider messaging
    # unread_provider_messages: int = 0


# ═════════════════════════════════════════════════════════════════════════════
# PAGINATED RESPONSES
# ═════════════════════════════════════════════════════════════════════════════


class CommunicationTimelineResponse(BaseModel):
    """Paginated communication timeline."""

    items: list[CommunicationCard]
    total: int
    skip: int
    limit: int


class ReminderListResponse(BaseModel):
    """Reminders grouped by urgency."""

    reminders_by_urgency: dict[str, list[ReminderCard]] = Field(
        default_factory=lambda: {"urgent": [], "upcoming": [], "completed": []}
    )
    total_urgent: int = 0
    total_upcoming: int = 0
    total_completed: int = 0
