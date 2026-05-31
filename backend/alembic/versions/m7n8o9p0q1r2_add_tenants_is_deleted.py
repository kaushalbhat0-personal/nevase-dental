"""Add tenants.is_deleted for soft-deactivation (super-admin).

Revises: k6l7m8n9o0p2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m7n8o9p0q1r2"
down_revision = "k6l7m8n9o0p2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_tenants_is_deleted", "tenants", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_tenants_is_deleted", table_name="tenants")
    op.drop_column("tenants", "is_deleted")
