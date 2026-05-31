"""Align appointments.tenant_id with doctors.tenant_id (authoritative for visits).

Earlier migrations synced appointment tenant from the patient, which can differ
from the assigned doctor's clinic and breaks completion, inventory, and billing.

Revises: z1_full_tenant_cleanup
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "c9d0e1f2a3b4"
down_revision = "z1_full_tenant_cleanup"
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
              AND d.tenant_id IS NOT NULL
              AND a.tenant_id IS DISTINCT FROM d.tenant_id
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE billings AS b
            SET tenant_id = a.tenant_id
            FROM appointments AS a
            WHERE b.appointment_id = a.id
              AND a.tenant_id IS NOT NULL
              AND b.tenant_id IS DISTINCT FROM a.tenant_id
            """
        )
    )


def downgrade() -> None:
    pass
