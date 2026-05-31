"""Align appointment tenant_id with the linked patient (data fix).

Revises: a3b4c5d6e7f8
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "b4c5d6e7f8a1"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Match each appointment to its patient's org; fixes NULLs and doctor-only mismatches.
    op.execute(
        text(
            """
            UPDATE appointments AS a
            SET tenant_id = p.tenant_id
            FROM patients AS p
            WHERE p.id = a.patient_id
              AND (
                a.tenant_id IS NULL
                OR a.tenant_id IS DISTINCT FROM p.tenant_id
              )
            """
        )
    )


def downgrade() -> None:
    # Irreversible data correction; no-op.
    pass
