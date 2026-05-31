"""Restrict tenants.type to individual | organization; backfill legacy values.

Revises: j5k6l7m8n9o1
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "k6l7m8n9o0p2"
down_revision = "j5k6l7m8n9o1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            "UPDATE tenants SET type = 'organization' "
            "WHERE type IS NULL OR type NOT IN ('individual', 'organization')"
        )
    )
    op.create_check_constraint(
        "chk_tenants_type_values",
        "tenants",
        "type IN ('individual', 'organization')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_tenants_type_values", "tenants", type_="check")
