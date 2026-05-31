"""Case-insensitive unique index on users.email (LOWER).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-22

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_lower ON users (LOWER(email))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_users_email_lower")
