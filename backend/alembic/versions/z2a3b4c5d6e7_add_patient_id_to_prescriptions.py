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
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Add patient_id column if it doesn't already exist (0fe071b8e03e may have
    # already created it as part of the prescriptions table).
    columns = [col['name'] for col in inspector.get_columns('prescriptions')]
    if 'patient_id' not in columns:
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

    # Create index only if it doesn't already exist (0fe071b8e03e may have
    # already created it).
    indexes = [idx['name'] for idx in inspector.get_indexes('prescriptions')]
    if 'ix_prescriptions_patient' not in indexes:
        op.create_index('ix_prescriptions_patient', 'prescriptions', ['patient_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    indexes = [idx['name'] for idx in inspector.get_indexes('prescriptions')]
    if 'ix_prescriptions_patient' in indexes:
        op.drop_index('ix_prescriptions_patient', table_name='prescriptions')

    # Only drop constraint if it exists and column still exists (don't touch the
    # inline FK from the original CREATE TABLE if any).
    columns = [col['name'] for col in inspector.get_columns('prescriptions')]
    if 'patient_id' in columns:
        try:
            op.drop_constraint('fk_prescriptions_patient_id', 'prescriptions', type_='foreignkey')
        except Exception:
            pass

        op.drop_column('prescriptions', 'patient_id')
