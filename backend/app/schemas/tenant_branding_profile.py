"""
Tenant Branding Profile schemas — READ/WRITE models for visual branding.

Phase 3C — Tenant Branding + Organization Profile Foundation.

All fields are optional for updates (patch-style).
Controls document rendering, colors, templates, and future theming.

TODO: Phase 4 — Multilingual template selection
TODO: Phase 4 — Dark mode color overrides
TODO: Phase 4 — White-label domain mapping
TODO: Phase 4 — Custom typography (heading_font, body_font, base_size)
TODO: Phase 4 — Hospital chain / department-level branding overrides
TODO: Phase 4 — QR verification code configuration
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TenantBrandingProfileRead(BaseModel):
    """Read model for tenant branding profile."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID

    # Colors
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None

    # Document styling
    document_header_style: str | None = None
    watermark_text: str | None = None

    # Template selection
    prescription_template: str | None = None
    invoice_template: str | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class TenantBrandingProfileCreate(BaseModel):
    """Create model — all fields optional for initial creation."""

    primary_color: str | None = Field(default=None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str | None = Field(default=None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str | None = Field(default=None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")

    document_header_style: str | None = Field(default=None, max_length=50)
    watermark_text: str | None = Field(default=None, max_length=255)

    prescription_template: str | None = Field(default=None, max_length=100)
    invoice_template: str | None = Field(default=None, max_length=100)


class TenantBrandingProfileUpdate(BaseModel):
    """Update model — all fields optional for partial updates."""

    primary_color: str | None = Field(default=None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str | None = Field(default=None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str | None = Field(default=None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")

    document_header_style: str | None = Field(default=None, max_length=50)
    watermark_text: str | None = Field(default=None, max_length=255)

    prescription_template: str | None = Field(default=None, max_length=100)
    invoice_template: str | None = Field(default=None, max_length=100)
