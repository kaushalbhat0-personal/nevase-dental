"""Inventory items, stock, and movements (multi-tenant).

Revision ID: f0e1d2c3b4a5
Revises: d5e6f7a8b9c0
Create Date: 2026-04-23

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f0e1d2c3b4a5"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    inventoryitemtype = postgresql.ENUM(
        "medicine",
        "consumable",
        name="inventoryitemtype",
        create_type=True,
    )
    inventoryitemtype.create(bind, checkfirst=True)

    inventorymovementtype = postgresql.ENUM(
        "IN",
        "OUT",
        "ADJUST",
        name="inventorymovementtype",
        create_type=True,
    )
    inventorymovementtype.create(bind, checkfirst=True)

    itemtype_col = postgresql.ENUM(
        "medicine",
        "consumable",
        name="inventoryitemtype",
        create_type=False,
    )
    movementtype_col = postgresql.ENUM(
        "IN",
        "OUT",
        "ADJUST",
        name="inventorymovementtype",
        create_type=False,
    )

    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", itemtype_col, nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("cost_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("selling_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_items_tenant_active",
        "inventory_items",
        ["tenant_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_items_tenant_type",
        "inventory_items",
        ["tenant_id", "type"],
        unique=False,
    )

    op.create_table(
        "inventory_stock",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_stock_item_tenant_level",
        "inventory_stock",
        ["item_id"],
        unique=True,
        postgresql_where=sa.text("doctor_id IS NULL"),
        sqlite_where=sa.text("doctor_id IS NULL"),
    )
    op.create_index(
        "uq_inventory_stock_item_doctor",
        "inventory_stock",
        ["item_id", "doctor_id"],
        unique=True,
        postgresql_where=sa.text("doctor_id IS NOT NULL"),
        sqlite_where=sa.text("doctor_id IS NOT NULL"),
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", movementtype_col, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("billing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["billing_id"], ["billings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_movements_item_created",
        "inventory_movements",
        ["item_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_movements_item_created", table_name="inventory_movements")
    op.drop_table("inventory_movements")

    op.drop_index("uq_inventory_stock_item_doctor", table_name="inventory_stock")
    op.drop_index("uq_inventory_stock_item_tenant_level", table_name="inventory_stock")
    op.drop_table("inventory_stock")

    op.drop_index("ix_inventory_items_tenant_type", table_name="inventory_items")
    op.drop_index("ix_inventory_items_tenant_active", table_name="inventory_items")
    op.drop_table("inventory_items")

    bind = op.get_bind()
    inventorymovementtype = postgresql.ENUM(name="inventorymovementtype")
    inventorymovementtype.drop(bind, checkfirst=True)
    inventoryitemtype = postgresql.ENUM(name="inventoryitemtype")
    inventoryitemtype.drop(bind, checkfirst=True)
