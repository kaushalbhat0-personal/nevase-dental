"""
Procurement Foundation — suppliers, purchase orders, inventory movement extensions.

Creates:
  - suppliers table
  - purchase_orders table
  - purchase_order_items table

Alters:
  - inventory_movements (unit_cost, supplier_id, invoice_number already exist in model)

Adds enums:
  - purchaseorderstatus (draft, completed, cancelled)
  - paymentstatus (unpaid, paid, partial)

Architecture:
  Supplier is tenant-scoped vendor/supplier for procurement.
  PurchaseOrder is the canonical procurement document.
  PurchaseOrderItem are line items referencing inventory_items.
  InventoryMovement already has PROCUREMENT_IN type, unit_cost, supplier_id,
  and invoice_number columns defined in the model — this migration ensures
  the database schema matches.

Revision ID: z7_procurement_foundation
Revises: z6_patient_medication_schedules
Create Date: 2026-05-12 20:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z7_procurement_foundation"
down_revision: str | None = "z6_patient_medication_schedules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Enums ────────────────────────────────────────────────────────────────
    # PurchaseOrderStatus
    po_status_enum = postgresql.ENUM(
        "draft", "completed", "cancelled", name="purchaseorderstatus",
        create_type=True,
    )
    po_status_enum.create(op.get_bind(), checkfirst=True)

    po_status_col = postgresql.ENUM(
        "draft", "completed", "cancelled", name="purchaseorderstatus",
        create_type=False,
    )

    # PaymentStatus
    payment_status_enum = postgresql.ENUM(
        "unpaid", "paid", "partial", name="paymentstatus",
        create_type=True,
    )
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    payment_status_col = postgresql.ENUM(
        "unpaid", "paid", "partial", name="paymentstatus",
        create_type=False,
    )

    # ── suppliers table ──────────────────────────────────────────────────────
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("supplier_name", sa.String(255), nullable=False),
        sa.Column("contact_person", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("gst_number", sa.String(64), nullable=True),
        sa.Column("tax_id", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_suppliers_tenant_active",
        "suppliers",
        ["tenant_id", "is_active"],
    )
    op.create_index(
        "ix_suppliers_tenant_name",
        "suppliers",
        ["tenant_id", "supplier_name"],
    )

    # ── purchase_orders table ────────────────────────────────────────────────
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suppliers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("invoice_number", sa.String(128), nullable=True),
        sa.Column("invoice_date", sa.Date, nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column(
            "payment_status",
            payment_status_col,
            nullable=False,
            server_default="unpaid",
        ),
        sa.Column("payment_method", sa.String(64), nullable=True),
        sa.Column(
            "status",
            po_status_col,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_purchase_orders_tenant_status",
        "purchase_orders",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_purchase_orders_tenant_supplier",
        "purchase_orders",
        ["tenant_id", "supplier_id"],
    )
    op.create_index(
        "ix_purchase_orders_invoice",
        "purchase_orders",
        ["tenant_id", "invoice_number"],
    )

    # ── purchase_order_items table ───────────────────────────────────────────
    op.create_table(
        "purchase_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "purchase_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inventory_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("batch_number", sa.String(128), nullable=True),
        sa.Column("expiry_date", sa.Date, nullable=True),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )

    op.create_index(
        "ix_po_items_order",
        "purchase_order_items",
        ["purchase_order_id"],
    )
    op.create_index(
        "ix_po_items_item",
        "purchase_order_items",
        ["inventory_item_id"],
    )

    # ── inventory_movements — add procurement columns if not exist ───────────
    # The model already defines unit_cost, supplier_id, invoice_number.
    # Use batch operations with IF NOT EXISTS semantics via raw SQL checks.
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        # Check and add unit_cost column
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='inventory_movements' AND column_name='unit_cost'"
            )
        )
        if result.fetchone() is None:
            op.add_column(
                "inventory_movements",
                sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
            )

        # Check and add supplier_id column
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='inventory_movements' AND column_name='supplier_id'"
            )
        )
        if result.fetchone() is None:
            op.add_column(
                "inventory_movements",
                sa.Column(
                    "supplier_id",
                    postgresql.UUID(as_uuid=True),
                    sa.ForeignKey("suppliers.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )

        # Check and add invoice_number column
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='inventory_movements' AND column_name='invoice_number'"
            )
        )
        if result.fetchone() is None:
            op.add_column(
                "inventory_movements",
                sa.Column("invoice_number", sa.String(128), nullable=True),
            )

        # Ensure index on inventory_movements for procurement lookups
        op.create_index(
            "ix_inventory_movements_reference",
            "inventory_movements",
            ["reference_type", "reference_id"],
            if_not_exists=True,
        )
    else:
        # SQLite-compatible: add columns unconditionally (table recreated per test)
        # SQLite ignores IF NOT EXISTS for ALTER TABLE ADD COLUMN
        try:
            op.add_column(
                "inventory_movements",
                sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
            )
        except Exception:
            pass  # Column already exists

        try:
            op.add_column(
                "inventory_movements",
                sa.Column(
                    "supplier_id",
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )
        except Exception:
            pass

        try:
            op.add_column(
                "inventory_movements",
                sa.Column("invoice_number", sa.String(128), nullable=True),
            )
        except Exception:
            pass

        # SQLite-compatible index creation
        try:
            op.create_index(
                "ix_inventory_movements_reference",
                "inventory_movements",
                ["reference_type", "reference_id"],
            )
        except Exception:
            pass


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
    op.drop_table("suppliers")

    # Drop enums
    sa.Enum(name="purchaseorderstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="paymentstatus").drop(op.get_bind(), checkfirst=True)

    # Remove columns from inventory_movements (PostgreSQL only; SQLite needs table rebuild)
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        op.drop_index("ix_inventory_movements_reference", table_name="inventory_movements")
        op.drop_column("inventory_movements", "unit_cost")
        op.drop_column("inventory_movements", "supplier_id")
        op.drop_column("inventory_movements", "invoice_number")
