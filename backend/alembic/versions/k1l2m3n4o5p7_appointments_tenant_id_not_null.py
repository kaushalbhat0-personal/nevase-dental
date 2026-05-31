"""Enforce appointments.tenant_id NOT NULL and RESTRICT FK.

Revises: c9d0e1f2a3b4
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "k1l2m3n4o5p7"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        text(
            """
            UPDATE appointments AS a
            SET tenant_id = d.tenant_id
            FROM doctors AS d
            WHERE a.doctor_id = d.id
              AND a.tenant_id IS NULL
              AND d.tenant_id IS NOT NULL
            """
        )
    )

    orphan = bind.execute(
        text(
            "SELECT COUNT(*) FROM appointments "
            "WHERE tenant_id IS NULL OR tenant_id = '00000000-0000-0000-0000-000000000000'::uuid"
        )
    ).scalar()
    if orphan and int(orphan) > 0:
        raise RuntimeError(
            "Cannot enforce NOT NULL: appointments still lack a valid tenant_id "
            "(assign doctor.tenant_id or delete orphan rows)"
        )

    op.drop_constraint(
        "appointments_tenant_id_fkey",
        "appointments",
        type_="foreignkey",
    )
    op.alter_column(
        "appointments",
        "tenant_id",
        nullable=False,
    )
    op.create_foreign_key(
        "appointments_tenant_id_fkey",
        "appointments",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_constraint(
        "appointments_tenant_id_fkey",
        "appointments",
        type_="foreignkey",
    )
    op.alter_column(
        "appointments",
        "tenant_id",
        nullable=True,
    )
    op.create_foreign_key(
        "appointments_tenant_id_fkey",
        "appointments",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )
