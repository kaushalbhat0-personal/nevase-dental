"""
Add spo2 column to appointment_vitals.

Adds:
  - appointment_vitals.spo2 (nullable Integer)

This fixes the TypeError: 'spo2' is an invalid keyword argument for AppointmentVitals
that occurs when the frontend sends spo2 in vitals data during encounter completion.

Revision ID: z8_appointment_vitals_spo2
Revises: z7_procurement_foundation
Create Date: 2026-05-13 03:43:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "z8_appointment_vitals_spo2"
down_revision: str = "z7_procurement_foundation"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("appointment_vitals")]
    if "spo2" not in columns:
        op.add_column(
            "appointment_vitals",
            sa.Column("spo2", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("appointment_vitals")]
    if "spo2" in columns:
        op.drop_column("appointment_vitals", "spo2")
