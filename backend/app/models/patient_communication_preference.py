"""
Patient Communication Preference Model — Phase P2 Patient Communication Center.

Architecture:
  This is the ONE new table introduced by Phase P2.
  It stores patient-level communication channel preferences.
  
  CRITICAL:
  - opt_out_all must NOT bypass critical healthcare notifications
  - Preferences are patient-scoped + tenant-scoped
  - Source-of-truth for communication remains NotificationEvent

  TODO: Phase 3 — Quiet hours enforcement
  TODO: Phase 3 — Multilingual communication (locale switching)
  TODO: Phase 3 — Consent management / GDPR compliance
  TODO: Phase 3 — Family/dependent notification preferences
  TODO: Phase 3 — Medication adherence reminder preferences
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PatientCommunicationPreference(Base):
    """
    Patient-level communication channel preferences.

    Each patient has exactly one preference record per tenant.
    Preferences control which channels are used for non-critical communications.
    
    CRITICAL HEALTHCARE NOTIFICATIONS are NEVER bypassed:
    - Appointment reminders
    - Urgent medical results
    - Prescription readiness
    - Follow-up reminders

    TODO: Phase 3 — Quiet hours (start_time / end_time)
    TODO: Phase 3 — Multilingual locale switching
    TODO: Phase 3 — Consent management timestamps
    TODO: Phase 3 — Opt-out audit trail
    """

    __tablename__ = "patient_communication_preferences"

    __table_args__ = (
        UniqueConstraint(
            "patient_id",
            "tenant_id",
            name="uq_patient_comm_prefs_patient_tenant",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Channel preferences ──────────────────────────────────────────────
    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    sms_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    whatsapp_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # ── Future-ready fields ──────────────────────────────────────────────
    quiet_hours_start: Mapped[str | None] = mapped_column(
        String(5),  # "HH:MM" format
        nullable=True,
    )
    quiet_hours_end: Mapped[str | None] = mapped_column(
        String(5),  # "HH:MM" format
        nullable=True,
    )
    locale: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        server_default="en",
    )

    # ⚠️ CRITICAL: opt_out_all must NOT bypass critical notifications
    # Critical notifications (appointment reminders, urgent results)
    # are ALWAYS sent regardless of this flag.
    opt_out_all: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
