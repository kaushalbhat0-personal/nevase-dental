"""Align solo-doctor tenants to clinic; enforce doctors.tenant_id FK on delete.

Revision ID: f1a2b3c4d5e6
Revises: a9b8c7d6e5f4
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "a9b8c7d6e5f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE tenants SET type = 'clinic' WHERE type = 'independent_doctor'")
    )
    op.drop_constraint("doctors_tenant_id_fkey", "doctors", type_="foreignkey")
    op.create_foreign_key(
        "doctors_tenant_id_fkey",
        "doctors",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("doctors_tenant_id_fkey", "doctors", type_="foreignkey")
    op.create_foreign_key(
        "doctors_tenant_id_fkey",
        "doctors",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Cannot know which 'clinic' rows were former independent_doctor; no-op for type
