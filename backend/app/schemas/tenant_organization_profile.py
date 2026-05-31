"""
Tenant Organization Profile schemas — READ/WRITE models for tenant identity.

Phase 3C — Tenant Branding + Organization Profile Foundation.

All fields are optional for updates (patch-style).
Documents/rendering derive branding from these profiles, NOT hardcoded data.

TODO: Phase 4 — Object storage fields (logo_s3_key, logo_cdn_url)
TODO: Phase 4 — Signed upload URL support
TODO: Phase 4 — Image optimization metadata
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TenantOrganizationProfileRead(BaseModel):
    """Read model for tenant organization profile."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID

    # Identity
    organization_name: str | None = None
    legal_name: str | None = None
    logo_url: str | None = None

    # Contact
    phone: str | None = None
    email: str | None = None
    website: str | None = None

    # Address
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    # Compliance / Taxation
    gst_number: str | None = None
    registration_number: str | None = None

    # Regional defaults
    timezone: str | None = None
    currency: str | None = None

    # Document footers
    prescription_footer: str | None = None
    invoice_footer: str | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class TenantOrganizationProfileUpdate(BaseModel):
    """Update model — all fields optional for partial updates."""

    organization_name: str | None = Field(default=None, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=1024)

    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)

    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=100)

    gst_number: str | None = Field(default=None, max_length=50)
    registration_number: str | None = Field(default=None, max_length=100)

    timezone: str | None = Field(default=None, max_length=50)
    currency: str | None = Field(default=None, max_length=10)

    prescription_footer: str | None = None
    invoice_footer: str | None = None
