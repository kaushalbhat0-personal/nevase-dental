"""Add SOAP notes and extended vitals fields for Phase 2C

Revision ID: ecc6aa611584
Revises: z2a3b4c5d6e7
Create Date: 2026-05-11 05:14:46.631195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecc6aa611584'
down_revision: Union[str, None] = 'z2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add extended vitals fields to appointment_vitals
    op.add_column('appointment_vitals', sa.Column('respiratory_rate', sa.Integer(), nullable=True))
    op.add_column('appointment_vitals', sa.Column('height', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('appointment_vitals', sa.Column('bmi', sa.Numeric(precision=4, scale=1), nullable=True))
    op.add_column('appointment_vitals', sa.Column('notes', sa.Text(), nullable=True))

    # Add SOAP notes fields to appointments
    op.add_column('appointments', sa.Column('subjective_notes', sa.Text(), nullable=True))
    op.add_column('appointments', sa.Column('objective_notes', sa.Text(), nullable=True))
    op.add_column('appointments', sa.Column('assessment_notes', sa.Text(), nullable=True))
    op.add_column('appointments', sa.Column('plan_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove SOAP notes fields from appointments
    op.drop_column('appointments', 'plan_notes')
    op.drop_column('appointments', 'assessment_notes')
    op.drop_column('appointments', 'objective_notes')
    op.drop_column('appointments', 'subjective_notes')

    # Remove extended vitals fields from appointment_vitals
    op.drop_column('appointment_vitals', 'notes')
    op.drop_column('appointment_vitals', 'bmi')
    op.drop_column('appointment_vitals', 'height')
    op.drop_column('appointment_vitals', 'respiratory_rate')
