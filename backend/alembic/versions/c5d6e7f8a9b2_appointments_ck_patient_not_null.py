"""Explicit CHECK that appointments.patient_id is never null (documents invariant).

Column is already NOT NULL; this adds a named constraint as requested.

Revises: b4c5d6e7f8a1
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "c5d6e7f8a9b2"
down_revision = "b4c5d6e7f8a1"
branch_labels = None
depends_on = None

_CONSTRAINT = "fk_patient_not_null"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        text(
            f"""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{_CONSTRAINT}'
              ) THEN
                ALTER TABLE appointments
                ADD CONSTRAINT {_CONSTRAINT}
                CHECK (patient_id IS NOT NULL);
              END IF;
            END$$;
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(text(f"ALTER TABLE appointments DROP CONSTRAINT IF EXISTS {_CONSTRAINT}"))
