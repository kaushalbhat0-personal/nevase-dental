"""Backfill patients.tenant_id when NULL or nil-UUID sentinel via appointment doctors.

Uses appointments -> doctors (same strategy as j5k6l7m8n9o1), then users.tenant_id for
patients with user_id still missing a tenant.

The raw ``UPDATE patients FROM doctors`` without a join is unsafe; this revision uses
deterministic subqueries.

Revises: h1i2j3k4l5m6
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "i1j2k3l4m5n6"
down_revision = "h1i2j3k4l5m6"
branch_labels = None
depends_on = None

_NIL = "00000000-0000-0000-0000-000000000000"

_BACKFILL_FROM_APPOINTMENTS = f"""
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
  AND (
    p.tenant_id IS NULL
    OR p.tenant_id = '{_NIL}'::uuid
  )
"""

_BACKFILL_FROM_USERS = f"""
UPDATE patients p
SET tenant_id = u.tenant_id
FROM users u
WHERE p.user_id = u.id
  AND u.tenant_id IS NOT NULL
  AND u.tenant_id != '{_NIL}'::uuid
  AND (
    p.tenant_id IS NULL
    OR p.tenant_id = '{_NIL}'::uuid
  )
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(text(_BACKFILL_FROM_APPOINTMENTS))
    op.execute(text(_BACKFILL_FROM_USERS))


def downgrade() -> None:
    # Data correction; no-op.
    pass
