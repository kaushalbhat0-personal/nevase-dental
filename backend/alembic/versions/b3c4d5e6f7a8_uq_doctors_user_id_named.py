"""Named UNIQUE on doctors.user_id (replaces ix_doctors_user_id index).

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-22

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_doctors_user_id", table_name="doctors")
    op.create_unique_constraint("uq_doctors_user_id", "doctors", ["user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_doctors_user_id", "doctors", type_="unique")
    op.create_index("ix_doctors_user_id", "doctors", ["user_id"], unique=True)
