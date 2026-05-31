"""Completion idempotency: unique (appointment_id, idempotency_key); integrity_scan_state table.

Revises: m8n9o0p1q2r4
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
import sqlalchemy as sa


revision = "n9o0p1q2r3s4"
down_revision = "m8n9o0p1q2r4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                DELETE FROM appointment_completion_idempotency a
                WHERE EXISTS (
                    SELECT 1 FROM appointment_completion_idempotency b
                    WHERE b.appointment_id = a.appointment_id
                      AND b.idempotency_key = a.idempotency_key
                      AND b.id::text < a.id::text
                );
                """
            )
        )

    op.drop_constraint(
        "uq_appt_completion_idempotency_appt_user_key",
        "appointment_completion_idempotency",
        type_="unique",
    )
    op.create_index(
        "uq_completion_idempotency",
        "appointment_completion_idempotency",
        ["appointment_id", "idempotency_key"],
        unique=True,
    )

    op.create_table(
        "integrity_scan_state",
        sa.Column("scope_key", sa.String(length=96), nullable=False),
        sa.Column("last_successful_scan_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("scope_key", name="pk_integrity_scan_state"),
    )


def downgrade() -> None:
    op.drop_table("integrity_scan_state")
    op.drop_index(
        "uq_completion_idempotency",
        table_name="appointment_completion_idempotency",
    )
    op.create_unique_constraint(
        "uq_appt_completion_idempotency_appt_user_key",
        "appointment_completion_idempotency",
        ["appointment_id", "user_id", "idempotency_key"],
    )
