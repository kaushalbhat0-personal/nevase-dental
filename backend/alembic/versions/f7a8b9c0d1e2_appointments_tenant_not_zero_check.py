"""Reject Nil-UUID sentinel on appointments.tenant_id.

Revises: d6e7f8a9b0c3
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "f7a8b9c0d1e2"
down_revision = "d6e7f8a9b0c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        text(
            """
            ALTER TABLE appointments
            ADD CONSTRAINT tenant_not_zero
            CHECK (tenant_id != '00000000-0000-0000-0000-000000000000'::uuid)
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint(
        "tenant_not_zero",
        "appointments",
        type_="check",
    )
