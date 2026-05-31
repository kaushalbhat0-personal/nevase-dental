"""Add patient_id and patient index to prescriptions.

Revision ID: z2a3b4c5d6e7
Revises: p1q2r3s4t6
Create Date: 2026-05-10 12:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'z2a3b4c5d6e7'
down_revision: Union[str, None] = 'p1q2r3s4t6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add patient_id column to prescriptions.
    # Backfill from associated appointment records (appointment.patient_id).
    op.add_column(
        'prescriptions',
        sa.Column('patient_id', sa.UUID(), nullable=True),
    )

    # Backfill patient_id from appointment (with a temporary INNER JOIN approach).
    # Using raw SQL for maximum clarity in idempotent behavior.
    op.execute("""
        UPDATE prescriptions
        SET patient_id = appointments.patient_id
        FROM appointments
        WHERE prescriptions.appointment_id = appointments.id
        AND prescriptions.patient_id IS NULL;
    """)

    # Make patient_id NOT NULL after backfill.
    op.alter_column(
        'prescriptions',
        'patient_id',
        nullable=False,
        existing_type=sa.UUID(),
    )

    # Add foreign key constraint (RESTRICT to prevent accidental cascade).
    op.create_foreign_key(
        'fk_prescriptions_patient_id',
        'prescriptions',
        'patients',
        ['patient_id'],
        ['id'],
        ondelete='RESTRICT',
    )

    # Add index for efficient patient-scoped queries.
    op.create_index('ix_prescriptions_patient', 'prescriptions', ['patient_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_prescriptions_patient', table_name='prescriptions')
    op.drop_constraint('fk_prescriptions_patient_id', 'prescriptions', type_='foreignkey')
    op.drop_column('prescriptions', 'patient_id')
