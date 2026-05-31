"""Add doctor_verification_logs for verification audit trail."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "w2x3y4z5a6b7"
down_revision = "v1w2x3y4z5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctor_verification_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("doctor_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_doctor_verification_logs_doctor_id",
        "doctor_verification_logs",
        ["doctor_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_doctor_verification_logs_doctor_id", table_name="doctor_verification_logs")
    op.drop_table("doctor_verification_logs")
