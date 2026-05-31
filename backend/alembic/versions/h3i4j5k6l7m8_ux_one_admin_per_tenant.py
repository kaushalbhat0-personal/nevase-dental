"""Partial unique index: at most one org admin (role admin) per users.tenant_id.

Also demote duplicate tenant admins to doctor (keep smallest ``users.id`` per tenant) and
align ``user_tenant.role`` to *doctor* for demoted users so the app stays consistent.

Revises: g2h3i4j5k6l7
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "h3i4j5k6l7m8"
down_revision = "g2h3i4j5k6l7"
branch_labels = None
depends_on = None

INDEX_NAME = "ux_users_one_admin_per_tenant"


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            """
            UPDATE users u
            SET
              role = 'doctor'::userrole,
              is_owner = false
            FROM (
              SELECT
                u2.tenant_id,
                (MIN(u2.id::text))::uuid AS keep_id
              FROM users u2
              WHERE u2.tenant_id IS NOT NULL
                AND u2.role = 'admin'::userrole
              GROUP BY u2.tenant_id
              HAVING COUNT(*) > 1
            ) s
            WHERE u.tenant_id = s.tenant_id
              AND u.role = 'admin'::userrole
              AND u.id <> s.keep_id
            """
        )
        op.execute(
            """
            UPDATE user_tenant ut
            SET role = 'doctor'
            FROM users u
            WHERE u.id = ut.user_id
              AND u.tenant_id = ut.tenant_id
              AND u.role = 'doctor'::userrole
              AND ut.role = 'admin'
            """
        )
        op.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
            ON users (tenant_id)
            WHERE role = 'admin'::userrole AND tenant_id IS NOT NULL
            """
        )
    else:
        op.execute(
            """
            UPDATE users
            SET role = 'doctor', is_owner = 0
            WHERE id IN (
              SELECT u2.id FROM users AS u2
              INNER JOIN (
                SELECT tenant_id, MIN(id) AS keep_id
                FROM users
                WHERE tenant_id IS NOT NULL AND role = 'admin'
                GROUP BY tenant_id
                HAVING COUNT(*) > 1
              ) AS s
                ON u2.tenant_id = s.tenant_id
                AND u2.id <> s.keep_id
              WHERE u2.role = 'admin'
            )
            """
        )
        op.execute(
            """
            UPDATE user_tenant
            SET role = 'doctor'
            WHERE role = 'admin'
              AND EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = user_tenant.user_id
                  AND u.tenant_id = user_tenant.tenant_id
                  AND u.role = 'doctor'
              )
            """
        )
        op.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
            ON users (tenant_id)
            WHERE role = 'admin' AND tenant_id IS NOT NULL
            """
        )


def downgrade() -> None:
    op.execute(sa.text(f"DROP INDEX IF EXISTS {INDEX_NAME}"))
