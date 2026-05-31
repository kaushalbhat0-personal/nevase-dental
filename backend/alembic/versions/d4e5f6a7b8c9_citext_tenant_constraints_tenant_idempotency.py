"""CITEXT email, tenant name uniqueness, phone check, tenant idempotency table.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-22

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("DROP INDEX IF EXISTS ux_users_email_lower")
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    # CITEXT enforces case-insensitive uniqueness: fail fast if varchar rows differ only by case.
    op.execute(
        r"""
        DO $citext_email_dup_check$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM users a
                INNER JOIN users b
                    ON a.id < b.id AND lower(a.email::text) = lower(b.email::text)
            ) THEN
                RAISE EXCEPTION
                    'CITEXT migration blocked: case-insensitive duplicate user emails exist. '
                    'Resolve or merge those rows before re-running. '
                    'Do not rely on blind DELETE; inspect: '
                    'SELECT a.id, a.email, b.id, b.email FROM users a '
                    'INNER JOIN users b ON a.id < b.id AND lower(a.email::text) = lower(b.email::text)';
            END IF;
        END
        $citext_email_dup_check$;
        """
    )
    op.execute("ALTER TABLE users ALTER COLUMN email TYPE citext USING email::citext")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_ci ON users (email)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tenants_name_lower ON tenants (lower(name))"
    )
    op.execute(
        "ALTER TABLE tenants ADD CONSTRAINT chk_tenants_phone_length "
        "CHECK (phone IS NULL OR char_length(phone) <= 50)"
    )
    op.create_table(
        "tenant_creation_idempotency",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_tenant_idempotency_user_key"
        ),
    )
    op.create_index(
        "ix_tenant_idempotency_created_at",
        "tenant_creation_idempotency",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index(
        "ix_tenant_idempotency_created_at", table_name="tenant_creation_idempotency"
    )
    op.drop_table("tenant_creation_idempotency")
    op.execute("ALTER TABLE tenants DROP CONSTRAINT IF EXISTS chk_tenants_phone_length")
    op.execute("DROP INDEX IF EXISTS ux_tenants_name_lower")
    op.execute("DROP INDEX IF EXISTS ux_users_email_ci")
    op.execute("ALTER TABLE users ALTER COLUMN email TYPE varchar(320) USING email::varchar")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_lower ON users (lower(email))"
    )
