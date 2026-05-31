"""Placeholder revision: DBs were stamped with this id without a matching file.

Empty upgrade/downgrade so `alembic upgrade head` can continue to i1j2k3l4m5n6.

Revises: h0i1j2k3l4m5
"""

from __future__ import annotations

revision = "h1i2j3k4l5m6"
down_revision = "h0i1j2k3l4m5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
