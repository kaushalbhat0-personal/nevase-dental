"""Add users.is_owner for practice owner (solo doctor) admin equivalent.

Revises: f1a2b3c4d5e6
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "g2h3i4j5k6l7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Backfill: one active doctor (with login) per tenant.
    op.execute(
        """
        UPDATE users AS u
        SET is_owner = true
        FROM doctors AS d
        INNER JOIN (
            SELECT tenant_id
            FROM doctors
            WHERE is_deleted = false AND user_id IS NOT NULL
            GROUP BY tenant_id
            HAVING count(*) = 1
        ) AS sole ON d.tenant_id = sole.tenant_id
        WHERE u.id = d.user_id
          AND d.is_deleted = false
          AND d.user_id IS NOT NULL
        """
    )
    # Drop server default to match application default pattern (optional).
    op.alter_column("users", "is_owner", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "is_owner")
