"""Add outcome snapshot columns to appointment_completion_idempotency.

Revises: k1l2m3n4o5p7
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "m8n9o0p1q2r4"
down_revision = "k1l2m3n4o5p7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.add_column(
        "appointment_completion_idempotency",
        sa.Column("result_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "appointment_completion_idempotency",
        sa.Column(
            "billing_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_appt_completion_idempotency_billing_id",
        "appointment_completion_idempotency",
        "billings",
        ["billing_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_constraint(
        "fk_appt_completion_idempotency_billing_id",
        "appointment_completion_idempotency",
        type_="foreignkey",
    )
    op.drop_column("appointment_completion_idempotency", "billing_id")
    op.drop_column("appointment_completion_idempotency", "result_hash")
