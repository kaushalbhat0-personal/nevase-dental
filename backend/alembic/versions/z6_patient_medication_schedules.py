"""
Patient Medication Schedules — adherence tracking foundation.

Creates:
  - patient_medication_schedules (derived from prescriptions)
  - medication_adherence_logs (audit trail for patient actions)

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

Revision ID: z6_patient_medication_schedules
Revises: z5_patient_communication_preferences
Create Date: 2026-05-12 01:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z6_patient_medication_schedules"
down_revision: str | None = "z5_patient_communication_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Medication Schedule Status enum ────────────────────────────────────
    # Create with checkfirst=True for idempotent retry safety.
    # Then use create_type=False variants in table columns to prevent
    # automatic re-creation during create_table().
    med_schedule_status_enum = postgresql.ENUM(
        "active", "completed", "paused", name="medicationschedulestatus",
        create_type=True,
    )
    med_schedule_status_enum.create(op.get_bind(), checkfirst=True)

    # Non-creating column variant
    med_schedule_status_col = postgresql.ENUM(
        "active", "completed", "paused", name="medicationschedulestatus",
        create_type=False,
    )

    # ── Medication Schedule Adherence Action enum ──────────────────────────
    med_adherence_action_enum = postgresql.ENUM(
        "taken", "skipped", "snoozed", name="medicationscheduleadherenceaction",
        create_type=True,
    )
    med_adherence_action_enum.create(op.get_bind(), checkfirst=True)

    # Non-creating column variant
    med_adherence_action_col = postgresql.ENUM(
        "taken", "skipped", "snoozed", name="medicationscheduleadherenceaction",
        create_type=False,
    )

    # ── patient_medication_schedules table ─────────────────────────────────
    op.create_table(
        "patient_medication_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "prescription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prescriptions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "prescription_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prescription_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Snapshot of prescription data (read-only after creation)
        sa.Column("medicine_name", sa.String(255), nullable=False),
        sa.Column("dosage", sa.String(128), nullable=True),
        sa.Column("frequency", sa.String(128), nullable=True),
        sa.Column("duration", sa.String(128), nullable=True),
        sa.Column("instructions", sa.Text, nullable=True),
        # Schedule
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reminder_times",
            postgresql.JSONB,
            nullable=True,
            server_default="[]",
            comment="Array of HH:MM strings for reminder scheduling",
        ),
        # Adherence tracking
        sa.Column("taken_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "total_doses",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Expected doses in this schedule period",
        ),
        # State
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "status",
            med_schedule_status_col,
            nullable=False,
            server_default="active",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Constraints
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_med_schedule_date_range",
        ),
    )

    # Indexes
    op.create_index(
        "ix_med_schedule_patient_active",
        "patient_medication_schedules",
        ["patient_id", "is_active"],
    )
    op.create_index(
        "ix_med_schedule_prescription_item",
        "patient_medication_schedules",
        ["prescription_item_id"],
    )
    op.create_index(
        "ix_med_schedule_tenant",
        "patient_medication_schedules",
        ["tenant_id"],
    )

    # ── medication_adherence_logs table ────────────────────────────────────
    op.create_table(
        "medication_adherence_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "medication_schedule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "patient_medication_schedules.id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "action",
            med_adherence_action_col,
            nullable=False,
        ),
        sa.Column(
            "actioned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "scheduled_time",
            sa.String(5),
            nullable=True,
            comment="Which reminder slot this corresponds to (HH:MM format)",
        ),
    )

    # Indexes
    op.create_index(
        "ix_adherence_log_schedule",
        "medication_adherence_logs",
        ["medication_schedule_id"],
    )
    op.create_index(
        "ix_adherence_log_patient_date",
        "medication_adherence_logs",
        ["patient_id", "actioned_at"],
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table("medication_adherence_logs")
    op.drop_table("patient_medication_schedules")

    # Drop enums
    sa.Enum(name="medicationscheduleadherenceaction").drop(op.get_bind())
    sa.Enum(name="medicationschedulestatus").drop(op.get_bind())
