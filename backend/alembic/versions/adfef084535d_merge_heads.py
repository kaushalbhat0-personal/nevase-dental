"""merge_heads

Revision ID: adfef084535d
Revises: 5a93cca8f072
Create Date: 2026-05-08 20:52:30.809862

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adfef084535d'
down_revision: Union[str, None] = '5a93cca8f072'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
