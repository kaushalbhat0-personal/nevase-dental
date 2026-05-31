import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TenantType(str, enum.Enum):
    """Solo practice vs multi-staff org; only these values are stored."""

    individual = "individual"
    organization = "organization"


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        Index("ix_tenants_type", "type"),
        Index("ix_tenants_is_deleted", "is_deleted"),
        Index("ux_tenants_name_lower", text("lower(name)"), unique=True),
        Index("ux_tenants_slug", "slug", unique=True),
        CheckConstraint(
            "phone IS NULL OR length(phone) <= 50",
            name="chk_tenants_phone_length",
        ),
        CheckConstraint(
            "type IN ('individual', 'organization')",
            name="chk_tenants_type_values",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TenantType.organization,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
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

    user_associations = relationship("UserTenant", back_populates="tenant")
    organization_profile = relationship(
        "TenantOrganizationProfile",
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )
    branding_profile = relationship(
        "TenantBrandingProfile",
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )


class TenantCreationIdempotency(Base):
    """Idempotency-Key + body hash for POST /tenants (hospital) deduplication."""

    __tablename__ = "tenant_creation_idempotency"

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_tenant_idempotency_user_key"),
        Index("ix_tenant_idempotency_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class UserTenant(Base):
    __tablename__ = "user_tenant"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant = relationship("Tenant", back_populates="user_associations")
    user = relationship("User", back_populates="tenant_associations")
