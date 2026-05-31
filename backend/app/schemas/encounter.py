"""
Encounter Aggregate schema — canonical READ-ONLY aggregate for the encounter workspace.

This is a **read model** that composes existing domain schemas.
It does NOT create a separate Encounter table.
Appointment remains the encounter anchor.

Future extension hooks are marked with TODO comments.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.appointment import (
    AppointmentInventoryUsageRead,
    AppointmentRead,
    DoctorMini,
    PatientMini,
    PrescriptionRead,
    VitalSignsRead,
)
from app.schemas.billing import BillingRead


class TimelineContext(BaseModel):
    """Lightweight patient history for encounter context (optional, read-only)."""

    model_config = ConfigDict(from_attributes=True)

    previous_visit_count: int = 0
    previous_appointment_ids: list[UUID] = Field(default_factory=list)


class EncounterDetailAggregate(BaseModel):
    """
    Canonical READ-ONLY aggregate for the encounter workspace.

    This is the SINGLE source of truth for:
    * Encounter Workspace rendering
    * AI clinical summaries (future)
    * PDF/export generation (future)
    * mobile sync (future)
    * analytics (future)
    * clinical integrations (future)

    Appointment is the encounter anchor. No separate Encounter table exists.
    """

    model_config = ConfigDict(from_attributes=True)

    # ── Core encounter anchor ──────────────────────────────────────────────
    appointment: AppointmentRead

    # ── Related domain entities ────────────────────────────────────────────
    patient: PatientMini
    doctor: DoctorMini

    # ── Clinical data ──────────────────────────────────────────────────────
    vitals: VitalSignsRead | None = None
    prescriptions: list[PrescriptionRead] = Field(default_factory=list)

    # ── Operational data ───────────────────────────────────────────────────
    inventory_usage: list[AppointmentInventoryUsageRead] = Field(default_factory=list)
    bill: BillingRead | None = None

    # ── Context ────────────────────────────────────────────────────────────
    timeline_context: TimelineContext | None = None

    # ══════════════════════════════════════════════════════════════════════
    # FUTURE EXTENSION HOOKS (Phase 2+)
    # ══════════════════════════════════════════════════════════════════════
    #
    # TODO: AI clinical summary (derived artifact, not source-of-truth)
    # ai_summary: AiEncounterSummary | None = None
    #
    # TODO: PDF encounter export
    # pdf_export_url: str | None = None
    #
    # TODO: ICD coding
    # icd_codes: list[IcdCodeAssignment] = Field(default_factory=list)
    #
    # TODO: Attachments / lab reports
    # attachments: list[AttachmentRef] = Field(default_factory=list)
    #
    # TODO: Referrals
    # referrals: list[ReferralRead] = Field(default_factory=list)
    #
    # TODO: E-prescription signatures
    # e_prescription_signed: bool = False
