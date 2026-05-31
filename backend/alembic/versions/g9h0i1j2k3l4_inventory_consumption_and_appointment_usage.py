"""Inventory consumption: appointment usage, movement references, completion notes, equipment type.

Revises: f7a8b9c0d1e2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "g9h0i1j2k3l4"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            DO $enum_add$ BEGIN
                ALTER TYPE inventoryitemtype ADD VALUE 'equipment';
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $enum_add$;
            """
        )
    )

    op.add_column(
        "appointments",
        sa.Column("completion_notes", sa.Text(), nullable=True),
    )

    op.add_column(
        "inventory_movements",
        sa.Column("reference_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "inventory_movements",
        sa.Column(
            "reference_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "inventory_movements",
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_inventory_movements_reference",
        "inventory_movements",
        ["reference_type", "reference_id"],
        unique=False,
    )

    op.create_table(
        "appointment_inventory_usage",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_appointment_inventory_usage_appointment",
        "appointment_inventory_usage",
        ["appointment_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index("ix_appointment_inventory_usage_appointment", table_name="appointment_inventory_usage")
    op.drop_table("appointment_inventory_usage")
    op.drop_index("ix_inventory_movements_reference", table_name="inventory_movements")
    op.drop_column("inventory_movements", "created_by")
    op.drop_column("inventory_movements", "reference_id")
    op.drop_column("inventory_movements", "reference_type")
    op.drop_column("appointments", "completion_notes")
