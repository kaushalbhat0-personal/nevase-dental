"""Add encounter timestamps to appointments.

Revises: n9o0p1q2r3s4
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "o0p1q2r3s4t5"
down_revision = "n9o0p1q2r3s4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "appointments",
        sa.Column("encounter_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("encounter_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("appointments", "encounter_completed_at")
    op.drop_column("appointments", "encounter_started_at")
