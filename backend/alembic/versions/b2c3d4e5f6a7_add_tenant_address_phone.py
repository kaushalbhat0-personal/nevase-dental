"""Add optional address and phone to tenants.

Revision ID: b2c3d4e5f6a7
Revises: f8a1b2c3d4e5
Create Date: 2026-04-22

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f8a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("tenants", sa.Column("phone", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "phone")
    op.drop_column("tenants", "address")
