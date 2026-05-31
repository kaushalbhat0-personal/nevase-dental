"""Full tenant cleanup: nil-UUID to NULL, backfill tenant links, CHECKs, indexes.

Revises: i1j2k3l4m5n6
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "z1_full_tenant_cleanup"
down_revision = "i1j2k3l4m5n6"
branch_labels = None
depends_on = None

NIL_UUID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Replace legacy CHECK on appointments (disallows nil UUID only) with explicit NULL-or-real.
    op.execute(text("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS tenant_not_zero"))

    # -------------------------------
    # 1. CLEAN NIL UUID → NULL
    # -------------------------------
    op.execute(
        text(
            f"""
        UPDATE patients
        SET tenant_id = NULL
        WHERE tenant_id = '{NIL_UUID}'::uuid
    """
        )
    )

    op.execute(
        text(
            f"""
        UPDATE appointments
        SET tenant_id = NULL
        WHERE tenant_id = '{NIL_UUID}'::uuid
    """
        )
    )

    op.execute(
        text(
            f"""
        UPDATE billings
        SET tenant_id = NULL
        WHERE tenant_id = '{NIL_UUID}'::uuid
    """
        )
    )

    # -------------------------------
    # 2. FIX PATIENT TENANT FROM DOCTOR
    # -------------------------------
    op.execute(
        text(
            """
        UPDATE patients p
        SET tenant_id = d.tenant_id
        FROM doctors d
        WHERE p.created_by = d.user_id
          AND p.tenant_id IS NULL
          AND d.tenant_id IS NOT NULL
    """
        )
    )

    op.execute(
        text(
            """
        UPDATE patients p
        SET tenant_id = a.tenant_id
        FROM appointments a
        WHERE a.patient_id = p.id
          AND p.tenant_id IS NULL
          AND a.tenant_id IS NOT NULL
    """
        )
    )

    # -------------------------------
    # 3. FIX APPOINTMENT TENANT FROM PATIENT
    # -------------------------------
    op.execute(
        text(
            """
        UPDATE appointments a
        SET tenant_id = p.tenant_id
        FROM patients p
        WHERE a.patient_id = p.id
          AND (a.tenant_id IS NULL OR a.tenant_id IS DISTINCT FROM p.tenant_id)
          AND p.tenant_id IS NOT NULL
    """
        )
    )

    # -------------------------------
    # 4. FINAL FALLBACK: FROM DOCTOR
    # -------------------------------
    op.execute(
        text(
            """
        UPDATE appointments a
        SET tenant_id = d.tenant_id
        FROM doctors d
        WHERE a.doctor_id = d.id
          AND a.tenant_id IS NULL
          AND d.tenant_id IS NOT NULL
    """
        )
    )

    # -------------------------------
    # 5. FIX BILLINGS FROM APPOINTMENTS
    # -------------------------------
    op.execute(
        text(
            """
        UPDATE billings b
        SET tenant_id = a.tenant_id
        FROM appointments a
        WHERE b.appointment_id = a.id
          AND (b.tenant_id IS NULL OR b.tenant_id IS DISTINCT FROM a.tenant_id)
          AND a.tenant_id IS NOT NULL
    """
        )
    )

    # -------------------------------
    # 6. HARD CONSTRAINTS (SAFETY)
    # -------------------------------
    op.execute(
        text(
            f"""
        ALTER TABLE patients
        ADD CONSTRAINT ck_patients_tenant_not_nil
        CHECK (tenant_id IS NULL OR tenant_id != '{NIL_UUID}'::uuid)
    """
        )
    )

    op.execute(
        text(
            f"""
        ALTER TABLE appointments
        ADD CONSTRAINT ck_appointments_tenant_not_nil
        CHECK (tenant_id IS NULL OR tenant_id != '{NIL_UUID}'::uuid)
    """
        )
    )

    op.execute(
        text(
            f"""
        ALTER TABLE billings
        ADD CONSTRAINT ck_billings_tenant_not_nil
        CHECK (tenant_id IS NULL OR tenant_id != '{NIL_UUID}'::uuid)
    """
        )
    )

    # -------------------------------
    # 7. ADD INDEXES (PERFORMANCE + SAFETY)
    # -------------------------------
    op.execute(text("CREATE INDEX IF NOT EXISTS idx_patients_tenant ON patients (tenant_id)"))
    op.execute(
        text("CREATE INDEX IF NOT EXISTS idx_appointments_tenant ON appointments (tenant_id)")
    )
    op.execute(text("CREATE INDEX IF NOT EXISTS idx_billings_tenant ON billings (tenant_id)"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(text("DROP INDEX IF EXISTS idx_patients_tenant"))
    op.execute(text("DROP INDEX IF EXISTS idx_appointments_tenant"))
    op.execute(text("DROP INDEX IF EXISTS idx_billings_tenant"))

    op.execute(text("ALTER TABLE patients DROP CONSTRAINT IF EXISTS ck_patients_tenant_not_nil"))
    op.execute(text("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS ck_appointments_tenant_not_nil"))
    op.execute(text("ALTER TABLE billings DROP CONSTRAINT IF EXISTS ck_billings_tenant_not_nil"))

    op.execute(
        text(
            """
        ALTER TABLE appointments
        ADD CONSTRAINT tenant_not_zero
        CHECK (tenant_id != '00000000-0000-0000-0000-000000000000'::uuid)
    """
        )
    )
