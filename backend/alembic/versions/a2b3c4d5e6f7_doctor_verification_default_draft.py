"""Doctor profile verification: default draft; backfill mistaken pending rows."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a2b3c4d5e6f7"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE doctor_profiles
            SET verification_status = 'draft'
            WHERE verification_status = 'pending'
            AND (
                full_name IS NULL OR
                specialization IS NULL OR
                registration_number IS NULL OR
                phone IS NULL
            );
            """
        )
    )
    op.alter_column(
        "doctor_profiles",
        "verification_status",
        server_default=sa.text("'draft'"),
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "doctor_profiles",
        "verification_status",
        server_default=sa.text("'pending'"),
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )
