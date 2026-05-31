"""Merge Alembic heads.

This migration consolidates the two active migration heads into a single branch.

Revision ID: p1q2r3s4t6
Revises: 19677072c567, o0p1q2r3s4t5
Create Date: 2026-05-11 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision = "p1q2r3s4t6"
down_revision: Union[str, Sequence[str], None] = (
    "19677072c567",
    "o0p1q2r3s4t5",
)
branch_labels = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
