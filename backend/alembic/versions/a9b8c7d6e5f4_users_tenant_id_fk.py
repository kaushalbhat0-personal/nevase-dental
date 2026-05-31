"""Add users.tenant_id for primary org (RBAC / tenant isolation).

Revision ID: a9b8c7d6e5f4
Revises: f0e1d2c3b4a5
Create Date: 2026-04-23

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "f0e1d2c3b4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users_tenant_id_tenants",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                """
                UPDATE users u SET tenant_id = sub.tid
                FROM (
                    SELECT DISTINCT ON (user_id) user_id, tenant_id AS tid
                    FROM user_tenant
                    WHERE is_primary = true
                    ORDER BY user_id, created_at
                ) sub
                WHERE u.id = sub.user_id AND u.role::text <> 'super_admin'
                """
            )
        )
        op.execute(
            text("UPDATE users SET tenant_id = NULL WHERE role::text = 'super_admin'")
        )


def downgrade() -> None:
    op.drop_constraint("fk_users_tenant_id_tenants", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")
