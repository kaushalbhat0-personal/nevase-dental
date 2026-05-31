"""change_billing_status_enum_to_unpaid_paid

Revision ID: 19677072c567
Revises: 0fe071b8e03e
Create Date: 2026-05-10 13:31:13.439435

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '19677072c567'
down_revision: Union[str, None] = '0fe071b8e03e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safe enum migration pattern for PostgreSQL
    # Temporarily convert to TEXT to remove enum dependency
    op.execute("ALTER TABLE billings ALTER COLUMN status DROP DEFAULT")
    op.execute("DROP INDEX IF EXISTS idx_paid_bills_only")
    op.execute("ALTER TYPE billingstatus RENAME TO billingstatus_old")
    op.execute("ALTER TABLE billings ALTER COLUMN status TYPE text USING status::text")
    op.execute("CREATE TYPE billingstatus AS ENUM ('unpaid', 'paid')")

    op.execute(
        """
        ALTER TABLE billings
        ALTER COLUMN status TYPE billingstatus
        USING (
            CASE
                WHEN status = 'pending' THEN 'unpaid'
                WHEN status = 'failed' THEN 'unpaid'
                WHEN status = 'paid' THEN 'paid'
            END
        )::billingstatus
        """
    )

    op.execute("ALTER TABLE billings ALTER COLUMN status SET DEFAULT 'unpaid'")
    op.execute("CREATE INDEX idx_paid_bills_only ON billings (paid_at) WHERE status = 'paid'")
    op.execute("DROP TYPE billingstatus_old")


def downgrade() -> None:
    # Safe downgrade path: rename current type, convert to text, recreate old type, migrate values back, then drop the renamed type.
    op.execute("ALTER TABLE billings ALTER COLUMN status DROP DEFAULT")
    op.execute("DROP INDEX IF EXISTS idx_paid_bills_only")
    op.execute("ALTER TYPE billingstatus RENAME TO billingstatus_new")
    op.execute("ALTER TABLE billings ALTER COLUMN status TYPE text USING status::text")
    op.execute("CREATE TYPE billingstatus AS ENUM ('pending', 'paid', 'failed')")

    op.execute(
        """
        ALTER TABLE billings
        ALTER COLUMN status TYPE billingstatus
        USING (
            CASE
                WHEN status = 'unpaid' THEN 'pending'
                WHEN status = 'paid' THEN 'paid'
            END
        )::billingstatus
        """
    )

    op.execute("ALTER TABLE billings ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("CREATE INDEX idx_paid_bills_only ON billings (paid_at) WHERE status = 'paid'")
    op.execute("DROP TYPE billingstatus_new")
