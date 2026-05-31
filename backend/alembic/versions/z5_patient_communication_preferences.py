"""Add patient communication preferences table.

Phase P2 — Patient Communication Center.

Creates:
- patient_communication_preferences: Patient-level channel preference storage

Revision ID: z5_patient_communication_preferences
Revises: z4_notification_communication
Create Date: 2026-05-11 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z5_patient_communication_preferences"
down_revision: Union[str, None] = "z4_notification_communication"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table already exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = :table_name)"
        ),
        {"table_name": table_name},
    )
    return result.scalar() or False


def upgrade() -> None:
    """Create patient_communication_preferences table."""
    if table_exists("patient_communication_preferences"):
        return

    op.create_table(
        "patient_communication_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # ── Channel preferences ────────────────────────────────────────────
        sa.Column(
            "email_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "sms_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "whatsapp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "reminder_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        # ── Future-ready fields ────────────────────────────────────────────
        sa.Column(
            "quiet_hours_start",
            sa.String(5),
            nullable=True,
        ),
        sa.Column(
            "quiet_hours_end",
            sa.String(5),
            nullable=True,
        ),
        sa.Column(
            "locale",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'en'"),
        ),
        # ⚠️ CRITICAL: opt_out_all must NOT bypass critical notifications
        sa.Column(
            "opt_out_all",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        # ── Timestamps ─────────────────────────────────────────────────────
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
        # ── Constraints ────────────────────────────────────────────────────
        sa.UniqueConstraint(
            "patient_id",
            "tenant_id",
            name="uq_patient_comm_prefs_patient_tenant",
        ),
    )

    # Create indexes for efficient lookups
    op.create_index(
        "ix_patient_comm_prefs_patient_tenant",
        "patient_communication_preferences",
        ["patient_id", "tenant_id"],
        unique=True,
    )
    op.create_index(
        "ix_patient_comm_prefs_tenant_id",
        "patient_communication_preferences",
        ["tenant_id"],
    )


def downgrade() -> None:
    """Drop patient_communication_preferences table."""
    op.drop_index("ix_patient_comm_prefs_tenant_id")
    op.drop_index("ix_patient_comm_prefs_patient_tenant")
    op.drop_table("patient_communication_preferences")
