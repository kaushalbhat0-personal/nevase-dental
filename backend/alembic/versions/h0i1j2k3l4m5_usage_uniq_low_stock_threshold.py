"""Appointment usage dedupe, uniq constraint, low_stock_threshold; completion idempotency;
movement.created_by_role; Postgres tenant guard trigger on usage inserts.

Revises: g9h0i1j2k3l4

Previously split across ``h0`` + ``j2`` revisions — consolidated to reduce migration noise.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "h0i1j2k3l4m5"
down_revision = "g9h0i1j2k3l4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Dedupe existing rows before UNIQUE (Postgres has no MIN(uuid); order via text)
    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE appointment_inventory_usage u
                SET quantity = sub.t
                FROM (
                    SELECT
                        (MIN(id::text))::uuid AS kid,
                        SUM(quantity)::integer AS t
                    FROM appointment_inventory_usage
                    GROUP BY appointment_id, item_id
                ) sub
                WHERE u.id = sub.kid;

                DELETE FROM appointment_inventory_usage a
                WHERE EXISTS (
                    SELECT 1 FROM appointment_inventory_usage b
                    WHERE b.appointment_id = a.appointment_id
                      AND b.item_id = a.item_id
                      AND b.id < a.id
                );
                """
            )
        )

    op.create_unique_constraint(
        "uq_appointment_inventory_usage_appt_item",
        "appointment_inventory_usage",
        ["appointment_id", "item_id"],
    )

    op.add_column(
        "inventory_items",
        sa.Column("low_stock_threshold", sa.Integer(), nullable=True),
    )

    # --- former revision j2k3l4m5n6o7 ---
    op.create_table(
        "appointment_completion_idempotency",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "appointment_id",
            "user_id",
            "idempotency_key",
            name="uq_appt_completion_idempotency_appt_user_key",
        ),
    )
    op.create_index(
        "ix_appt_completion_idempotency_created_at",
        "appointment_completion_idempotency",
        ["created_at"],
    )

    op.add_column(
        "inventory_movements",
        sa.Column("created_by_role", sa.String(length=32), nullable=True),
    )

    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE OR REPLACE FUNCTION check_appointment_inventory_usage_tenant_match()
                RETURNS trigger AS $$
                DECLARE
                  item_tid UUID;
                  ap_tid UUID;
                BEGIN
                  SELECT tenant_id INTO item_tid FROM inventory_items WHERE id = NEW.item_id;
                  SELECT COALESCE(a.tenant_id, d.tenant_id) INTO ap_tid
                  FROM appointments a
                  JOIN doctors d ON d.id = a.doctor_id
                  WHERE a.id = NEW.appointment_id;

                  IF item_tid IS DISTINCT FROM ap_tid THEN
                    RAISE EXCEPTION 'Tenant mismatch for inventory usage';
                  END IF;
                  RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                DROP TRIGGER IF EXISTS trg_appointment_inventory_usage_tenant_match ON appointment_inventory_usage;
                CREATE TRIGGER trg_appointment_inventory_usage_tenant_match
                BEFORE INSERT ON appointment_inventory_usage
                FOR EACH ROW EXECUTE PROCEDURE check_appointment_inventory_usage_tenant_match();
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                DROP TRIGGER IF EXISTS trg_appointment_inventory_usage_tenant_match ON appointment_inventory_usage;
                DROP FUNCTION IF EXISTS check_appointment_inventory_usage_tenant_match();
                """
            )
        )

    op.drop_column("inventory_movements", "created_by_role")

    op.drop_index(
        "ix_appt_completion_idempotency_created_at",
        table_name="appointment_completion_idempotency",
    )
    op.drop_table("appointment_completion_idempotency")

    op.drop_column("inventory_items", "low_stock_threshold")

    op.drop_constraint(
        "uq_appointment_inventory_usage_appt_item",
        "appointment_inventory_usage",
        type_="unique",
    )
