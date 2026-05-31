from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_patients: int
    total_doctors: int
    today_appointments: int
    total_revenue: float


class AdminDashboardMetricsResponse(BaseModel):
    """GET /api/v1/admin/dashboard/metrics — tenant-scoped admin KPIs."""

    model_config = ConfigDict(from_attributes=True)

    total_revenue: float = Field(description="Sum of paid bill amounts in the last 7 days (since start of today − 7d)")
    revenue_today: float = Field(description="Sum of paid bill amounts with created_at on the current day (UTC)")
    appointments_today: int = Field(description="Count of appointments scheduled on the current day (UTC)")
    completed_appointments: int = Field(
        description="Count of completed appointments with appointment_time since start of today − 7d (UTC)"
    )
    pending_bills: float = Field(
        description="Sum of bill amounts in pending or failed status for the tenant (non-deleted)"
    )


class RevenueTrendItem(BaseModel):
    """One day of paid revenue in the admin 7-day UTC window."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    revenue: float


class DoctorPerformanceItem(BaseModel):
    """GET /api/v1/admin/dashboard/doctor-performance — one doctor in the 7-day UTC window."""

    model_config = ConfigDict(from_attributes=True)

    doctor_id: UUID
    doctor_name: str
    appointments_count: int
    completed_appointments: int
    total_revenue: float
