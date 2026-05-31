"""Doctor verification log: from_status, to_status, tenant_id; drop legacy status column."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "z1a2b3c4d5e6"
down_revision = "w2x3y4z5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "doctor_verification_logs",
        sa.Column("to_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "doctor_verification_logs",
        sa.Column("from_status", sa.String(length=32), nullable=True),
    )
    op.add_column("doctor_verification_logs", sa.Column("tenant_id", sa.UUID(), nullable=True))
    op.execute(sa.text("UPDATE doctor_verification_logs SET to_status = status WHERE to_status IS NULL"))
    op.alter_column("doctor_verification_logs", "to_status", nullable=False)
    op.drop_column("doctor_verification_logs", "status")
    op.create_foreign_key(
        "fk_doctor_verification_logs_tenant_id_tenants",
        "doctor_verification_logs",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_doctor_verification_logs_tenant_id",
        "doctor_verification_logs",
        ["tenant_id"],
    )
    bind = op.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        op.create_index(
            "ix_doctor_profiles_pending_partial",
            "doctor_profiles",
            ["verification_status"],
            postgresql_where=sa.text("verification_status = 'pending'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        op.drop_index("ix_doctor_profiles_pending_partial", table_name="doctor_profiles")
    op.drop_index("ix_doctor_verification_logs_tenant_id", table_name="doctor_verification_logs")
    op.drop_constraint(
        "fk_doctor_verification_logs_tenant_id_tenants",
        "doctor_verification_logs",
        type_="foreignkey",
    )
    op.drop_column("doctor_verification_logs", "tenant_id")
    op.add_column(
        "doctor_verification_logs",
        sa.Column("status", sa.String(length=32), nullable=True),
    )
    op.execute(sa.text("UPDATE doctor_verification_logs SET status = to_status WHERE status IS NULL"))
    op.alter_column("doctor_verification_logs", "status", nullable=False)
    op.drop_column("doctor_verification_logs", "from_status")
    op.drop_column("doctor_verification_logs", "to_status")
