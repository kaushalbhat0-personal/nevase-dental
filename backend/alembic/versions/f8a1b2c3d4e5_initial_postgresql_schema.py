"""Initial PostgreSQL schema (single squashed revision).

Tables are created in foreign-key order; indexes and partial unique indexes are
created afterward so PostgreSQL never references tables that do not exist yet.

Revision ID: f8a1b2c3d4e5
Revises:
Create Date: 2026-04-22

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a1b2c3d4e5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    userrole = postgresql.ENUM(
        "super_admin",
        "admin",
        "staff",
        "doctor",
        "patient",
        name="userrole",
        create_type=True,
    )
    userrole.create(bind, checkfirst=True)

    appointmentstatus = postgresql.ENUM(
        "scheduled",
        "completed",
        "cancelled",
        name="appointmentstatus",
        create_type=True,
    )
    appointmentstatus.create(bind, checkfirst=True)

    billingstatus = postgresql.ENUM(
        "pending",
        "paid",
        "failed",
        name="billingstatus",
        create_type=True,
    )
    billingstatus.create(bind, checkfirst=True)

    userrole_col = postgresql.ENUM(
        "super_admin",
        "admin",
        "staff",
        "doctor",
        "patient",
        name="userrole",
        create_type=False,
    )
    appointmentstatus_col = postgresql.ENUM(
        "scheduled",
        "completed",
        "cancelled",
        name="appointmentstatus",
        create_type=False,
    )
    billingstatus_col = postgresql.ENUM(
        "pending",
        "paid",
        "failed",
        name="billingstatus",
        create_type=False,
    )

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO tenants (id, name, type, is_active)
            VALUES (
                '00000000-0000-0000-0000-000000000001'::uuid,
                'Default',
                'hospital',
                true
            )
            ON CONFLICT (id) DO NOTHING
            """
        )
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", userrole_col, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "force_password_reset",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "doctors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("specialization", sa.String(length=255), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default=sa.text("'UTC'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("gender", sa.String(length=50), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_tenant",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", appointmentstatus_col, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "doctor_availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("slot_duration", sa.Integer(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "doctor_id",
            "day_of_week",
            "start_time",
            "end_time",
            name="uq_doctor_availability_window",
        ),
    )

    op.create_table(
        "doctor_time_off",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("off_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "off_date", name="uq_doctor_time_off_day"),
    )

    op.create_table(
        "appointment_creation_idempotency",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_appointment_idempotency_user_key"),
    )

    op.create_table(
        "billings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", billingstatus_col, nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_id", sa.String(length=255), nullable=True),
        sa.Column("payment_method", sa.String(length=50), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_billing_idempotency_key"),
    )

    op.create_table(
        "billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("billing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_metadata", sa.String(length=500), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["billing_id"], ["billings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Indexes (after all tables exist) ---
    op.create_index("ix_tenants_type", "tenants", ["type"], unique=False)

    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_index("ix_doctors_user_id", "doctors", ["user_id"], unique=True)

    op.create_index("ix_patients_user_id", "patients", ["user_id"], unique=True)

    op.create_index(
        "ix_appointments_tenant_patient_created",
        "appointments",
        ["tenant_id", "patient_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.create_index(
        "idx_user_doctor_time",
        "appointments",
        ["created_by", "doctor_id", "appointment_time"],
        unique=False,
    )

    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_appointments_doctor_time_active ON appointments "
            "(doctor_id, appointment_time) WHERE is_deleted = false "
            "AND status <> 'cancelled'::appointmentstatus"
        )
    )

    op.create_index(
        "ix_doctor_availability_doctor_id",
        "doctor_availability",
        ["doctor_id"],
        unique=False,
    )
    op.create_index(
        "ix_doctor_availability_tenant_id",
        "doctor_availability",
        ["tenant_id"],
        unique=False,
    )

    op.create_index(
        "ix_doctor_time_off_doctor_id",
        "doctor_time_off",
        ["doctor_id"],
        unique=False,
    )
    op.create_index(
        "ix_doctor_time_off_off_date",
        "doctor_time_off",
        ["off_date"],
        unique=False,
    )
    op.create_index(
        "ix_doctor_time_off_tenant_id",
        "doctor_time_off",
        ["tenant_id"],
        unique=False,
    )

    op.create_index(
        "ix_appointment_idempotency_created_at",
        "appointment_creation_idempotency",
        ["created_at"],
        unique=False,
    )

    op.create_index("idx_billing_created_by", "billings", ["created_by"], unique=False)
    op.create_index(
        "idx_billing_status_paid_at",
        "billings",
        ["status", "paid_at"],
        unique=False,
    )
    op.create_index("idx_billing_is_deleted", "billings", ["is_deleted"], unique=False)

    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_billing_active_appointment ON billings (appointment_id) "
            "WHERE appointment_id IS NOT NULL AND is_deleted = false"
        )
    )

    op.execute(
        sa.text("CREATE INDEX idx_paid_bills_only ON billings (paid_at) WHERE status = 'paid'")
    )

    op.create_index(
        "idx_billing_events_billing_id",
        "billing_events",
        ["billing_id"],
        unique=False,
    )
    op.create_index(
        "idx_billing_events_created_at",
        "billing_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("idx_billing_events_created_at", table_name="billing_events")
    op.drop_index("idx_billing_events_billing_id", table_name="billing_events")

    op.execute(sa.text("DROP INDEX IF EXISTS idx_paid_bills_only"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_billing_active_appointment"))

    op.drop_index("idx_billing_is_deleted", table_name="billings")
    op.drop_index("idx_billing_status_paid_at", table_name="billings")
    op.drop_index("idx_billing_created_by", table_name="billings")

    op.drop_index(
        "ix_appointment_idempotency_created_at",
        table_name="appointment_creation_idempotency",
    )

    op.drop_index("ix_doctor_time_off_tenant_id", table_name="doctor_time_off")
    op.drop_index("ix_doctor_time_off_off_date", table_name="doctor_time_off")
    op.drop_index("ix_doctor_time_off_doctor_id", table_name="doctor_time_off")

    op.drop_index("ix_doctor_availability_tenant_id", table_name="doctor_availability")
    op.drop_index("ix_doctor_availability_doctor_id", table_name="doctor_availability")

    op.execute(sa.text("DROP INDEX IF EXISTS uq_appointments_doctor_time_active"))
    op.drop_index("idx_user_doctor_time", table_name="appointments")
    op.drop_index("ix_appointments_tenant_patient_created", table_name="appointments")

    op.drop_index("ix_patients_user_id", table_name="patients")
    op.drop_index("ix_doctors_user_id", table_name="doctors")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_tenants_type", table_name="tenants")

    op.drop_table("billing_events")
    op.drop_table("billings")
    op.drop_table("appointment_creation_idempotency")
    op.drop_table("doctor_time_off")
    op.drop_table("doctor_availability")
    op.drop_table("appointments")
    op.drop_table("user_tenant")
    op.drop_table("patients")
    op.drop_table("doctors")
    op.drop_table("users")
    op.drop_table("tenants")

    billingstatus = postgresql.ENUM(name="billingstatus")
    billingstatus.drop(bind, checkfirst=True)

    appointmentstatus = postgresql.ENUM(name="appointmentstatus")
    appointmentstatus.drop(bind, checkfirst=True)

    userrole = postgresql.ENUM(name="userrole")
    userrole.drop(bind, checkfirst=True)
