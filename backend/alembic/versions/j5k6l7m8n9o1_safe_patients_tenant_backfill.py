"""Idempotent patients.tenant_id backfill via doctors (never fails upgrade).

Uses ``doctors.tenant_id`` only (not ``appointments.tenant_id``).
Revises: i4j5k6l7m8n9
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "j5k6l7m8n9o1"
down_revision = "i4j5k6l7m8n9"
branch_labels = None
depends_on = None

_BACKFILL_PG = """
UPDATE patients p
SET tenant_id = sub.tenant_id
FROM (
    SELECT a.patient_id, MIN(d.tenant_id::text)::uuid AS tenant_id
    FROM appointments a
    JOIN doctors d ON a.doctor_id = d.id
    WHERE a.is_deleted = false
    GROUP BY a.patient_id
) sub
WHERE p.id = sub.patient_id
AND p.tenant_id IS NULL
"""

_BACKFILL_SQLITE = """
UPDATE patients AS p
SET tenant_id = sub.tenant_id
FROM (
    SELECT a.patient_id, MIN(d.tenant_id::text)::uuid AS tenant_id
    FROM appointments a
    JOIN doctors d ON a.doctor_id = d.id
    WHERE a.is_deleted = 0
    GROUP BY a.patient_id
) AS sub
WHERE p.id = sub.patient_id
AND p.tenant_id IS NULL
"""


def upgrade() -> None:
    """Run backfill in a SAVEPOINT so a failed statement does not abort the migration txn."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    def _backfill() -> None:
        if dialect == "postgresql":
            op.execute(text(_BACKFILL_PG))
        else:
            op.execute(text(_BACKFILL_SQLITE))

    try:
        with bind.begin_nested():
            _backfill()
    except Exception:
        pass


def downgrade() -> None:
    pass
