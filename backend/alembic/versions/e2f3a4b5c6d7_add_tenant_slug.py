"""Optional tenant slug (URL / SEO / marketplace).

Revision ID: e2f3a4b5c6d7
Revises: d4e5f6a7b8c9
Create Date: 2026-04-22

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("slug", sa.String(length=255), nullable=True))
    op.create_index("ux_tenants_slug", "tenants", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_tenants_slug", table_name="tenants")
    op.drop_column("tenants", "slug")
