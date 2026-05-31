"""Drop redundant patient_id CHECK; named patient FK with RESTRICT; patient+tenant index.

Revises: c5d6e7f8a9b2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d6e7f8a9b0c3"
down_revision = "c5d6e7f8a9b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS fk_patient_not_null"))

    insp = sa.inspect(bind)
    for fk in insp.get_foreign_keys("appointments"):
        if fk.get("referred_table") == "patients" and fk.get("constrained_columns") == ["patient_id"]:
            op.drop_constraint(fk["name"], "appointments", type_="foreignkey")
            break

    op.create_foreign_key(
        "fk_appointments_patient",
        "appointments",
        "patients",
        ["patient_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "idx_appointments_patient_tenant",
        "appointments",
        ["patient_id", "tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index("idx_appointments_patient_tenant", table_name="appointments")

    op.drop_constraint("fk_appointments_patient", "appointments", type_="foreignkey")

    op.create_foreign_key(
        "appointments_patient_id_fkey",
        "appointments",
        "patients",
        ["patient_id"],
        ["id"],
        ondelete="CASCADE",
    )
