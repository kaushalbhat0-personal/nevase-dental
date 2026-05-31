"""Add tenant latitude/longitude for nearby-doctor search."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "p1q2r3s4t5u6"
down_revision = "n8o9p0q1r2s3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("tenants", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "longitude")
    op.drop_column("tenants", "latitude")
