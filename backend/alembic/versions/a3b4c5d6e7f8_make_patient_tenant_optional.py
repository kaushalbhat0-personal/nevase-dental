"""Make patients.tenant_id optional (set at first booking, not signup).

Revises: a2b3c4d5e6f7
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "a3b4c5d6e7f8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None

# Same as migration i4j5k6l7m8n9 — required before NOT NULL in downgrade
_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_constraint("patients_tenant_id_fkey", "patients", type_="foreignkey")
    op.alter_column(
        "patients",
        "tenant_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        "patients_tenant_id_fkey",
        "patients",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        text(
            f"INSERT INTO tenants (id, name, type, is_active) VALUES "
            f"('{_DEFAULT_TENANT}', 'Default', 'hospital', true) "
            f"ON CONFLICT (id) DO NOTHING"
        )
    )
    op.execute(
        text(
            f"UPDATE patients SET tenant_id = '{_DEFAULT_TENANT}' "
            f"WHERE tenant_id IS NULL"
        )
    )

    op.drop_constraint("patients_tenant_id_fkey", "patients", type_="foreignkey")
    op.alter_column(
        "patients",
        "tenant_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        "patients_tenant_id_fkey",
        "patients",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
