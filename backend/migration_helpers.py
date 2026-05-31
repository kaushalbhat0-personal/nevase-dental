"""PostgreSQL introspection helpers for idempotent Alembic migrations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


def pg_column_exists(table_name: str, column_name: str, *, schema: str = "public") -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = :table
                      AND column_name = :column
                )
                """
            ),
            {"schema": schema, "table": table_name, "column": column_name},
        ).scalar()
    )


def pg_table_exists(table_name: str, *, schema: str = "public") -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = :schema AND table_name = :table
                )
                """
            ),
            {"schema": schema, "table": table_name},
        ).scalar()
    )


def pg_index_exists(index_name: str, *, schema: str = "public") -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE schemaname = :schema AND indexname = :name
                )
                """
            ),
            {"schema": schema, "name": index_name},
        ).scalar()
    )


def pg_constraint_exists(
    constraint_name: str,
    *,
    table_name: str | None = None,
    schema: str = "public",
) -> bool:
    bind = op.get_bind()
    if table_name is None:
        return bool(
            bind.execute(
                sa.text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_constraint c
                        JOIN pg_namespace n ON n.oid = c.connamespace
                        WHERE n.nspname = :schema AND c.conname = :name
                    )
                    """
                ),
                {"schema": schema, "name": constraint_name},
            ).scalar()
        )
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_constraint c
                    JOIN pg_namespace n ON n.oid = c.connamespace
                    JOIN pg_class cl ON cl.oid = c.conrelid
                    WHERE n.nspname = :schema AND c.conname = :name AND cl.relname = :table
                )
                """
            ),
            {"schema": schema, "name": constraint_name, "table": table_name},
        ).scalar()
    )
