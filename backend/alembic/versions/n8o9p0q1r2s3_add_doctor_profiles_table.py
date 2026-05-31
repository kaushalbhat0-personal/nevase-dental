"""Add doctor_profiles structured identity + verification layer.

Revises: m7n8o9p0q1r2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "n8o9p0q1r2s3"
down_revision = "m7n8o9p0q1r2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("specialization", sa.Text(), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("qualification", sa.Text(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("registration_council", sa.Text(), nullable=True),
        sa.Column("clinic_name", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("profile_image", sa.Text(), nullable=True),
        sa.Column(
            "is_profile_complete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "verification_status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", name="uq_doctor_profiles_doctor_id"),
    )
    op.create_index("ix_doctor_profiles_doctor_id", "doctor_profiles", ["doctor_id"], unique=True)

    op.execute(
        """
        INSERT INTO doctor_profiles (
            id, doctor_id, full_name, specialization, experience_years,
            verification_status, is_profile_complete, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            d.id,
            d.name,
            d.specialization,
            d.experience_years,
            'pending',
            false,
            now(),
            now()
        FROM doctors d
        WHERE d.is_deleted = false
          AND NOT EXISTS (
              SELECT 1 FROM doctor_profiles p WHERE p.doctor_id = d.id
          );
        """
    )


def downgrade() -> None:
    op.drop_index("ix_doctor_profiles_doctor_id", table_name="doctor_profiles")
    op.drop_table("doctor_profiles")
