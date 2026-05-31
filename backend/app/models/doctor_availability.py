import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DoctorAvailability(Base):
    """Weekly recurring availability: wall-clock times in the doctor's local timezone."""

    __tablename__ = "doctor_availability"
    __table_args__ = (
        UniqueConstraint("doctor_id", "day_of_week", "start_time", "end_time", name="uq_doctor_availability_window"),
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
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # Mon=0 .. Sun=6 (Python weekday)
    start_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    end_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    slot_duration: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    doctor = relationship("Doctor", back_populates="availability_windows")


class DoctorTimeOff(Base):
    """Calendar day off; optional start_time/end_time for a partial-day block (doctor local time)."""

    __tablename__ = "doctor_time_off"
    __table_args__ = (UniqueConstraint("doctor_id", "off_date", name="uq_doctor_time_off_day"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    off_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    doctor = relationship("Doctor", back_populates="time_off_days")
