import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InventoryItemType(str, enum.Enum):
    medicine = "medicine"
    consumable = "consumable"
    equipment = "equipment"


class InventoryReferenceType(str, enum.Enum):
    """Who/what triggered the movement (extensible for billing, manual)."""

    APPOINTMENT = "APPOINTMENT"
    BILL = "BILL"
    MANUAL = "MANUAL"


class InventoryMovementType(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"
    PROCUREMENT_IN = "PROCUREMENT_IN"


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    __table_args__ = (
        Index("ix_inventory_items_tenant_active", "tenant_id", "is_active"),
        Index("ix_inventory_items_tenant_type", "tenant_id", "type"),
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
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[InventoryItemType] = mapped_column(
        Enum(InventoryItemType, name="inventoryitemtype", native_enum=True),
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    low_stock_threshold: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant = relationship("Tenant")
    stock_rows = relationship(
        "InventoryStock",
        back_populates="item",
        cascade="all, delete-orphan",
    )
    movements = relationship("InventoryMovement", back_populates="item")


class InventoryStock(Base):
    __tablename__ = "inventory_stock"

    __table_args__ = (
        Index(
            "uq_inventory_stock_item_tenant_level",
            "item_id",
            unique=True,
            sqlite_where=text("doctor_id IS NULL"),
            postgresql_where=text("doctor_id IS NULL"),
        ),
        Index(
            "uq_inventory_stock_item_doctor",
            "item_id",
            "doctor_id",
            unique=True,
            sqlite_where=text("doctor_id IS NOT NULL"),
            postgresql_where=text("doctor_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    item = relationship("InventoryItem", back_populates="stock_rows")
    doctor = relationship("Doctor")


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    __table_args__ = (Index("ix_inventory_movements_item_created", "item_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[InventoryMovementType] = mapped_column(
        Enum(InventoryMovementType, name="inventorymovementtype", native_enum=True),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    billing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billings.id", ondelete="SET NULL"),
        nullable=True,
    )
    reference_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    # Procurement snapshot fields
    unit_cost: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)

    item = relationship("InventoryItem", back_populates="movements")
    doctor = relationship("Doctor")
    billing = relationship("Billing")
    actor = relationship("User", foreign_keys=[created_by])



class AppointmentInventoryUsage(Base):
    """Per-visit line items tying clinic stock consumption to an appointment."""

    __tablename__ = "appointment_inventory_usage"

    __table_args__ = (
        Index("ix_appointment_inventory_usage_appointment", "appointment_id"),
        UniqueConstraint("appointment_id", "item_id", name="uq_appointment_inventory_usage_appt_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    appointment = relationship("Appointment", back_populates="inventory_usages")
    item = relationship("InventoryItem")
