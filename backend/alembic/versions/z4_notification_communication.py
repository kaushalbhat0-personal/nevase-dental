"""Add notification and communication infrastructure tables.

Phase 3D — Notification + Communication Foundation.

Creates:
- notification_events: Canonical event records derived from business actions
- notification_deliveries: Per-channel delivery tracking
- communication_templates: Tenant-scoped message templates

Revision ID: z4_notification_communication
Revises: z3_tenant_branding_profiles
Create Date: 2026-05-11 08:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "z4_notification_communication"
down_revision: Union[str, None] = "z3_tenant_branding_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table already exists in the database."""
    bind = op.get_bind()
    result = bind.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.tables "
            "  WHERE table_name = :table_name"
            ")"
        ),
        {"table_name": table_name},
    )
    return result.scalar() is True


def upgrade() -> None:
    """Create notification and communication tables."""

    bind = op.get_bind()

    # ── Enum Types ──────────────────────────────────────────────────────
    # Create enums with checkfirst=True for retry safety (idempotent).
    # This follows the established project pattern from f8a1b2c3d4e5 and
    # f0e1d2c3b4a5 — define ENUM with create_type=True, create with
    # checkfirst=True, then use create_type=False variants in table columns
    # to prevent automatic re-creation during create_table().

    notification_event_type = postgresql.ENUM(
        "appointment_booked",
        "appointment_reminder",
        "appointment_completed",
        "prescription_ready",
        "bill_generated",
        "payment_received",
        "follow_up_reminder",
        name="notificationeventtype",
        create_type=True,
    )
    notification_event_type.create(bind, checkfirst=True)

    notification_channel = postgresql.ENUM(
        "email",
        "sms",
        "whatsapp",
        "in_app",
        name="notificationchannel",
        create_type=True,
    )
    notification_channel.create(bind, checkfirst=True)

    notification_delivery_status = postgresql.ENUM(
        "pending",
        "sent",
        "delivered",
        "read",
        "failed",
        name="notificationdeliverystatus",
        create_type=True,
    )
    notification_delivery_status.create(bind, checkfirst=True)

    # ── Non-creating column variants ────────────────────────────────────
    # These reference the already-created enum types but do NOT emit
    # CREATE TYPE when used inside op.create_table().

    notification_event_type_col = postgresql.ENUM(
        "appointment_booked",
        "appointment_reminder",
        "appointment_completed",
        "prescription_ready",
        "bill_generated",
        "payment_received",
        "follow_up_reminder",
        name="notificationeventtype",
        create_type=False,
    )

    notification_channel_col = postgresql.ENUM(
        "email",
        "sms",
        "whatsapp",
        "in_app",
        name="notificationchannel",
        create_type=False,
    )

    notification_delivery_status_col = postgresql.ENUM(
        "pending",
        "sent",
        "delivered",
        "read",
        "failed",
        name="notificationdeliverystatus",
        create_type=False,
    )

    # ── notification_events ─────────────────────────────────────────────

    if not table_exists("notification_events"):
        op.create_table(
            "notification_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "event_type",
                notification_event_type_col,
                nullable=False,
            ),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "patient_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("patients.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "doctor_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("doctors.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "appointment_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("appointments.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "bill_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("billings.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("payload", postgresql.JSONB, nullable=True),

            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "is_deleted",
                sa.Boolean,
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

        # Indexes (guarded with IF NOT EXISTS for deploy retry safety)
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_notification_events_tenant_created "
            "ON notification_events (tenant_id, created_at)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_notification_events_patient "
            "ON notification_events (patient_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_notification_events_type_created "
            "ON notification_events (event_type, created_at)"
        )


    # ── notification_deliveries ──────────────────────────────────────────

    if not table_exists("notification_deliveries"):
        op.create_table(
            "notification_deliveries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "notification_event_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("notification_events.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "channel",
                notification_channel_col,
                nullable=False,
            ),
            sa.Column(
                "status",
                notification_delivery_status_col,
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column(
                "recipient",
                sa.String(320),
                nullable=False,
            ),
            sa.Column(
                "sent_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "failed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column("provider_response", postgresql.JSONB, nullable=True),

            sa.Column(
                "retry_count",
                sa.Integer,
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("error_message", sa.Text, nullable=True),
            sa.Column(
                "next_retry_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

        # Indexes (guarded with IF NOT EXISTS for deploy retry safety)
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_notification_delivery_status "
            "ON notification_deliveries (status)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_notification_delivery_event "
            "ON notification_deliveries (notification_event_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_notification_delivery_retry "
            "ON notification_deliveries (next_retry_at)"
        )


    # ── communication_templates ─────────────────────────────────────────

    if not table_exists("communication_templates"):
        op.create_table(
            "communication_templates",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "template_type",
                notification_event_type_col,
                nullable=False,
            ),
            sa.Column(
                "channel",
                notification_channel_col,
                nullable=False,
            ),
            sa.Column("subject", sa.String(255), nullable=True),
            sa.Column("body", sa.Text, nullable=False),
            sa.Column(
                "locale",
                sa.String(10),
                nullable=False,
                server_default=sa.text("'en'"),
            ),
            sa.Column(
                "is_active",
                sa.Boolean,
                nullable=False,
                server_default=sa.text("true"),
            ),
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
        )

        # Unique constraint (guarded against partial-deploy duplicate failures)
        op.execute(
            "DO $$ "
            "BEGIN "
            "  ALTER TABLE communication_templates "
            "    ADD CONSTRAINT uq_template_tenant_type_channel_locale "
            "    UNIQUE (tenant_id, template_type, channel, locale); "
            "EXCEPTION "
            "  WHEN duplicate_object THEN NULL; "
            "END $$;"
        )

        # Indexes (guarded with IF NOT EXISTS for deploy retry safety)
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_communication_templates_tenant "
            "ON communication_templates (tenant_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_communication_templates_type "
            "ON communication_templates (template_type)"
        )

    # Ensure alembic_version can hold long revision IDs
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(256)")


def downgrade() -> None:
    """Drop notification and communication tables."""
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)")

    # Drop tables (order matters for FK constraints)
    op.drop_table("communication_templates")
    op.drop_table("notification_deliveries")
    op.drop_table("notification_events")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS notificationdeliverystatus")
    op.execute("DROP TYPE IF EXISTS notificationchannel")
    op.execute("DROP TYPE IF EXISTS notificationeventtype")
