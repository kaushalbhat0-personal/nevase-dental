"""Default doctor profile timezone to Asia/Kolkata (IST) for wall-clock availability.

Revision ID: d5e6f7a8b9c0
Revises: c5d6e7f8a9b0
Create Date: 2026-04-23

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Treat stored availability window times as wall clock in the doctor's zone; prior default UTC
    # made 09:00–17:00 UTC (shown as afternoon in IST) instead of local IST.
    op.execute("UPDATE doctors SET timezone = 'Asia/Kolkata' WHERE timezone = 'UTC'")
    op.alter_column(
        "doctors",
        "timezone",
        server_default=sa.text("'Asia/Kolkata'"),
        existing_type=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "doctors",
        "timezone",
        server_default=sa.text("'UTC'"),
        existing_type=sa.String(length=64),
        existing_nullable=False,
    )
