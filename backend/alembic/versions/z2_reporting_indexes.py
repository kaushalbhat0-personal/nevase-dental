"""Add performance indexes for reporting queries.

Adds composite indexes on billings for date-range + tenant filtering,
and on inventory_movements for efficient ledger queries.

Merge of heads: z1_full_tenant_cleanup, z1a2b3c4d5e6, ecc6aa611584
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision = "z2_reporting_indexes"
down_revision: Union[str, Sequence[str], None] = (
    "z1_full_tenant_cleanup",
    "z1a2b3c4d5e6",
    "ecc6aa611584",
)

branch_labels = None
depends_on = None



def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # ── Billing indexes ──────────────────────────────────────────────────
    # Composite index for date-range + tenant filtering (billing report)
    op.create_index(
        "ix_billing_tenant_created_at",
        "billings",
        ["tenant_id", "created_at"],
        postgresql_where=text("is_deleted = false"),
        if_not_exists=True,
    )

    # Composite index for status + tenant filtering
    op.create_index(
        "ix_billing_tenant_status",
        "billings",
        ["tenant_id", "status"],
        postgresql_where=text("is_deleted = false"),
        if_not_exists=True,
    )

    # Composite index for patient + tenant filtering (patient financial ledger)
    op.create_index(
        "ix_billing_tenant_patient",
        "billings",
        ["tenant_id", "patient_id"],
        postgresql_where=text("is_deleted = false"),
        if_not_exists=True,
    )

    # ── Inventory movement indexes ───────────────────────────────────────
    # Composite index for date-range filtering on inventory ledger
    op.create_index(
        "ix_inventory_movements_created_at",
        "inventory_movements",
        ["created_at"],
        if_not_exists=True,
    )

    # Composite index for movement type filtering
    op.create_index(
        "ix_inventory_movements_type_created",
        "inventory_movements",
        ["type", "created_at"],
        if_not_exists=True,
    )

    # ── Appointment indexes ──────────────────────────────────────────────
    # Composite index for patient encounter lookups (patient financial ledger)
    op.create_index(
        "ix_appointments_patient_tenant",
        "appointments",
        ["patient_id", "tenant_id"],
        postgresql_where=text("is_deleted = false"),
        if_not_exists=True,
    )

    # ── Inventory items indexes ──────────────────────────────────────────
    # Index for tenant-scoped item lookups in inventory ledger
    op.create_index(
        "ix_inventory_items_tenant_name",
        "inventory_items",
        ["tenant_id", "name"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_billing_tenant_created_at", table_name="billings", if_exists=True)
    op.drop_index("ix_billing_tenant_status", table_name="billings", if_exists=True)
    op.drop_index("ix_billing_tenant_patient", table_name="billings", if_exists=True)
    op.drop_index("ix_inventory_movements_created_at", table_name="inventory_movements", if_exists=True)
    op.drop_index("ix_inventory_movements_type_created", table_name="inventory_movements", if_exists=True)
    op.drop_index("ix_appointments_patient_tenant", table_name="appointments", if_exists=True)
    op.drop_index("ix_inventory_items_tenant_name", table_name="inventory_items", if_exists=True)
