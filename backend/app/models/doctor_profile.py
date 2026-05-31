import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DoctorProfile(Base):
    """Structured identity + verification data for a doctor (separate from auth `User` and roster `Doctor`)."""

    __tablename__ = "doctor_profiles"
    __table_args__ = (
        Index("idx_doctor_profiles_verification_status", "verification_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    specialization: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    qualification: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_council: Mapped[str | None] = mapped_column(Text, nullable=True)

    clinic_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)

    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_image: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_profile_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    verification_rejection_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )

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

    doctor = relationship("Doctor", back_populates="structured_profile")
