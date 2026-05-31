"""Add doctor_profiles.verification_rejection_reason for rejected review flow."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "v1w2x3y4z5a6"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "doctor_profiles",
        sa.Column("verification_rejection_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("doctor_profiles", "verification_rejection_reason")
