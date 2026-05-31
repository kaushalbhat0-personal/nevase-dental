"""
Tenant Organization Profile + Branding Profile models.

Phase 3C — Tenant Branding + Organization Profile Foundation.

Architecture:
  - Branding is TENANT-SCOPED (1:1 with tenants table)
  - Branding is PRESENTATIONAL metadata — NOT mixed with billing/clinical logic
  - Independent doctors are also tenants and support branding
  - Future-safe for white-labeling, multilingual rendering, custom templates, mobile apps

TODO: Phase 4 — Multilingual template support
TODO: Phase 4 — Dark mode themes
TODO: Phase 4 — White-label domain mapping
TODO: Phase 4 — Custom typography (font families, sizes)
TODO: Phase 4 — Hospital chain / department-level branding overrides
TODO: Phase 4 — QR verification codes on documents
TODO: Phase 4 — NABH/JCI accreditation metadata
TODO: Phase 4 — Digital stamp / seal configuration
TODO: Phase 4 — Patient portal theming (portal_primary_color, portal_logo, etc.)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TenantOrganizationProfile(Base):
    """
    Canonical tenant identity — organization details, contact info, compliance fields.

    1:1 with tenants table. All fields optional initially.
    Documents/rendering derive branding from this profile, NOT hardcoded clinic data.
    """

    __tablename__ = "tenant_organization_profiles"
    __table_args__ = (
        Index("ix_org_profile_tenant_id", "tenant_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Identity
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Contact
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Address
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Compliance / Taxation
    gst_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Regional defaults
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Document footers
    prescription_footer: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_footer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship back to tenant
    tenant = relationship("Tenant", back_populates="organization_profile")


class TenantBrandingProfile(Base):
    """
    Visual branding configuration for a tenant.

    1:1 with tenants table. All fields optional with sensible defaults.
    Controls document rendering, colors, templates, and future theming.

    TODO: Phase 4 — Multilingual template selection (locale → template mapping)
    TODO: Phase 4 — Dark mode color overrides
    TODO: Phase 4 — White-label domain → branding profile mapping
    TODO: Phase 4 — Custom typography (heading_font, body_font, base_size)
    TODO: Phase 4 — Hospital chain / department-level branding overrides
    TODO: Phase 4 — QR verification code configuration
    """

    __tablename__ = "tenant_branding_profiles"
    __table_args__ = (
        Index("ix_branding_profile_tenant_id", "tenant_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Colors
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(7), nullable=True)

    # Document styling
    document_header_style: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="e.g. 'standard', 'compact', 'centered', 'minimal'",
    )
    watermark_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Template selection (future: reference to stored templates)
    prescription_template: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Template identifier for prescription rendering",
    )
    invoice_template: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Template identifier for invoice rendering",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship back to tenant
    tenant = relationship("Tenant", back_populates="branding_profile")
