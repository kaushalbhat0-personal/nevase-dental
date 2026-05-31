"""Backfill patients.tenant_id from appointments, then require NOT NULL.

Tenant is taken from ``doctors.tenant_id`` (appointments link to doctors), not from
``appointments`` — some databases have no ``appointments.tenant_id`` column.

Revises: h3i4j5k6l7m8
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

logger = logging.getLogger(__name__)

# Well-known default tenant (see app.core.tenancy.DEFAULT_TENANT_ID)
_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"

revision = "i4j5k6l7m8n9"
down_revision = "h3i4j5k6l7m8"
branch_labels = None
depends_on = None

# DISTINCT ON avoids MIN(uuid): PostgreSQL has no min() aggregate for uuid type.
_BACKFILL_PG = """
UPDATE patients p
SET tenant_id = sub.tenant_id
FROM (
    SELECT DISTINCT ON (a.patient_id) a.patient_id, d.tenant_id
    FROM appointments a
    INNER JOIN doctors d ON a.doctor_id = d.id
    WHERE a.is_deleted = false
      AND d.tenant_id IS NOT NULL
    ORDER BY a.patient_id, d.tenant_id
) sub
WHERE p.id = sub.patient_id
  AND p.tenant_id IS NULL
"""

_BACKFILL_SQLITE = """
UPDATE patients AS p
SET tenant_id = sub.tenant_id
FROM (
    SELECT a.patient_id, MIN(d.tenant_id) AS tenant_id
    FROM appointments a
    JOIN doctors d ON a.doctor_id = d.id
    WHERE a.is_deleted = 0
      AND d.tenant_id IS NOT NULL
    GROUP BY a.patient_id
) AS sub
WHERE p.id = sub.patient_id
  AND p.tenant_id IS NULL
"""


def _run_in_savepoint(connection, block_name: str, fn) -> None:
    """
    Run ``fn`` inside a SAVEPOINT so a SQL error is rolled back to the
    savepoint, not the whole migration transaction. Otherwise PostgreSQL
    leaves the connection in *aborted* state and the final ``alembic_version``
    update fails with InFailedSqlTransaction.
    """
    try:
        with connection.begin_nested():
            fn()
    except Exception as exc:
        logger.warning(
            "migration i4j5k6l7m8n9: %s failed: %s",
            block_name,
            exc,
            exc_info=True,
        )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)

    if not insp.has_table("patients"):
        logger.warning(
            "migration i4j5k6l7m8n9: patients table missing; skipping"
        )
        return
    patient_cols = {c["name"] for c in insp.get_columns("patients")}
    if "tenant_id" not in patient_cols:
        logger.warning(
            "migration i4j5k6l7m8n9: patients.tenant_id column missing; skipping"
        )
        return
    if not insp.has_table("appointments") or not insp.has_table("doctors"):
        logger.warning(
            "migration i4j5k6l7m8n9: appointments or doctors missing; skipping backfill"
        )
    else:
        def _backfill() -> None:
            try:
                if dialect == "postgresql":
                    op.execute(text(_BACKFILL_PG))
                else:
                    op.execute(text(_BACKFILL_SQLITE))
            except Exception:
                pass

        _run_in_savepoint(bind, "patient tenant_id backfill", _backfill)

    if dialect == "postgresql":

        def _insert_default_tenant() -> None:
            op.execute(
                text(
                    f"INSERT INTO tenants (id, name, type, is_active) VALUES "
                    f"('{_DEFAULT_TENANT}', 'Default', 'hospital', true) "
                    f"ON CONFLICT (id) DO NOTHING"
                )
            )

        _run_in_savepoint(bind, "default tenant insert", _insert_default_tenant)

    def _fill_orphan_patients() -> None:
        op.execute(
            text(
                f"UPDATE patients SET tenant_id = '{_DEFAULT_TENANT}' "
                f"WHERE tenant_id IS NULL"
            )
        )

    _run_in_savepoint(bind, "orphan patient tenant_id default", _fill_orphan_patients)

    if dialect != "postgresql":
        return

    def _not_null_and_fk() -> None:
        fk_insp = sa.inspect(bind)
        fk_name = None
        for fk in fk_insp.get_foreign_keys("patients"):
            cols = fk.get("constrained_columns") or []
            if "tenant_id" in cols:
                fk_name = fk.get("name")
                break
        if fk_name:
            op.drop_constraint(fk_name, "patients", type_="foreignkey")
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

    _run_in_savepoint(bind, "NOT NULL / patients_tenant_id FK", _not_null_and_fk)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    def _revert() -> None:
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
            ondelete="SET NULL",
        )

    _run_in_savepoint(bind, "i4j5k6l7m8n9 downgrade", _revert)
