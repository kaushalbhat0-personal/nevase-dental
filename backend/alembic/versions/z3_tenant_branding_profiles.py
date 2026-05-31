"""Add tenant organization profile and branding profile tables.

Phase 3C — Tenant Branding + Organization Profile Foundation.

Revision ID: z3_tenant_branding_profiles
Revises: z2_reporting_indexes
Create Date: 2026-05-11 08:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "z3_tenant_branding_profiles"
down_revision: Union[str, None] = "z2_reporting_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table already exists in the database."""
    bind = op.get_bind()
    result = bind.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.tables "
            "  WHERE table_name = :table_name"
            ")"
        ),
        {"table_name": table_name},
    ).scalar()
    return bool(result)


def index_exists(index_name: str) -> bool:
    """Check if an index already exists in the database."""
    bind = op.get_bind()
    result = bind.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT FROM pg_indexes "
            "  WHERE indexname = :index_name"
            ")"
        ),
        {"index_name": index_name},
    ).scalar()
    return bool(result)


def upgrade() -> None:
    # ── TenantOrganizationProfile ──────────────────────────────────────────
    if not table_exists("tenant_organization_profiles"):
        op.create_table(
            "tenant_organization_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            # NOTE: index=True is intentionally OMITTED from tenant_id column.
            # Explicit CREATE INDEX calls below use IF NOT EXISTS patterns.
            # Using index=True here would auto-generate ix_tenant_organization_profiles_tenant_id
            # which collides with the explicit ix_tenant_org_profiles_tenant_id index.
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("organization_name", sa.String(255), nullable=True),
            sa.Column("legal_name", sa.String(255), nullable=True),
            sa.Column("logo_url", sa.Text(), nullable=True),
            sa.Column("phone", sa.String(50), nullable=True),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("website", sa.String(255), nullable=True),
            sa.Column("address_line_1", sa.String(255), nullable=True),
            sa.Column("address_line_2", sa.String(255), nullable=True),
            sa.Column("city", sa.String(100), nullable=True),
            sa.Column("state", sa.String(100), nullable=True),
            sa.Column("postal_code", sa.String(20), nullable=True),
            sa.Column("country", sa.String(100), nullable=True),
            sa.Column("gst_number", sa.String(50), nullable=True),
            sa.Column("registration_number", sa.String(100), nullable=True),
            sa.Column("timezone", sa.String(50), nullable=True),
            sa.Column("currency", sa.String(10), nullable=True),
            sa.Column("prescription_footer", sa.Text(), nullable=True),
            sa.Column("invoice_footer", sa.Text(), nullable=True),
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
        )
    else:
        op.execute(text("SELECT 1 -- tenant_organization_profiles already exists, skipping CREATE TABLE"))

    # ── TenantBrandingProfile ──────────────────────────────────────────────
    if not table_exists("tenant_branding_profiles"):
        op.create_table(
            "tenant_branding_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            # NOTE: index=True is intentionally OMITTED from tenant_id column.
            # Explicit CREATE INDEX calls below use IF NOT EXISTS patterns.
            # Using index=True here would auto-generate ix_tenant_branding_profiles_tenant_id
            # which collides with the explicit CREATE INDEX call of the same name.
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("primary_color", sa.String(7), nullable=True, comment="Hex color e.g. #2563eb"),
            sa.Column("secondary_color", sa.String(7), nullable=True, comment="Hex color e.g. #64748b"),
            sa.Column("accent_color", sa.String(7), nullable=True, comment="Hex color e.g. #f59e0b"),
            sa.Column("document_header_style", sa.String(50), nullable=True, comment="e.g. default, minimal, branded"),
            sa.Column("watermark_text", sa.String(255), nullable=True),
            sa.Column("prescription_template", sa.String(100), nullable=True, comment="Template identifier for prescriptions"),
            sa.Column("invoice_template", sa.String(100), nullable=True, comment="Template identifier for invoices"),
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
        )
    else:
        op.execute(text("SELECT 1 -- tenant_branding_profiles already exists, skipping CREATE TABLE"))

    # ── Indexes — use PostgreSQL IF NOT EXISTS for bulletproof retry safety ─
    # Using raw SQL CREATE UNIQUE INDEX IF NOT EXISTS guarantees idempotency
    # even across partial migration failures / Render retries.
    # This is safer than op.create_index() + existence checks because:
    #   - op.create_index() does not support IF NOT EXISTS for unique indexes
    #   - Raw SQL is atomic and survives transaction boundary issues
    #   - PostgreSQL 9.5+ guarantees IF NOT EXISTS is idempotent

    op.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_tenant_org_profiles_tenant_id "
        "ON tenant_organization_profiles (tenant_id)"
    ))

    op.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_tenant_branding_profiles_tenant_id "
        "ON tenant_branding_profiles (tenant_id)"
    ))

    # ── Cleanup orphaned auto-generated indexes from prior partial runs ─────
    # If a previous partial execution created the table with index=True,
    # PostgreSQL auto-generated ix_tenant_organization_profiles_tenant_id.
    # This is a DUPLICATE of ix_tenant_org_profiles_tenant_id (different name,
    # same column). Drop it silently if it exists.
    op.execute(text(
        "DROP INDEX IF EXISTS ix_tenant_organization_profiles_tenant_id"
    ))


def downgrade() -> None:
    op.drop_table("tenant_branding_profiles")
    op.drop_table("tenant_organization_profiles")
