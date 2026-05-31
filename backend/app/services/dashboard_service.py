from __future__ import annotations

import pytz
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Billing, BillingStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.core.permissions import has_tenant_admin_privileges
from app.services.exceptions import ForbiddenError, ValidationError


def get_dashboard_stats(db: Session) -> dict:
    total_patients = db.query(Patient).count()
    total_doctors = db.query(Doctor).count()

    # Use IST timezone for accurate "today" filtering
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    today_appointments = (
        db.query(Appointment)
        .filter(
            Appointment.appointment_time >= start,
            Appointment.appointment_time < end,
            Appointment.is_deleted == False,  # noqa: E712
        )
        .count()
    )

    total_revenue = (
        db.query(func.sum(Billing.amount))
        .filter(
            Billing.status == "paid",
            Billing.is_deleted == False,  # noqa: E712
        )
        .scalar()
        or 0
    )

    return {
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "today_appointments": today_appointments,
        "total_revenue": float(total_revenue),
    }


def get_dashboard_stats_for_tenant(
    db: Session,
    tenant_id: UUID,
    doctor_id: UUID | None = None,
) -> dict:
    """Staff dashboard KPIs scoped to a single tenant (matches GET /dashboard with X-Tenant-ID)."""
    if doctor_id is not None:
        doctor_row = db.get(Doctor, doctor_id)
        if doctor_row is None:
            raise ValidationError("Doctor not found")
        if doctor_row.tenant_id != tenant_id:
            raise ValidationError("Doctor does not belong to this organization")

        has_appt = exists().where(
            Appointment.patient_id == Patient.id,
            Appointment.doctor_id == doctor_id,
            Appointment.is_deleted == False,  # noqa: E712
        )
        total_patients = db.scalar(select(func.count(Patient.id)).where(has_appt)) or 0
        total_doctors = 1

        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        today_appointments = (
            db.scalar(
                select(func.count())
                .select_from(Appointment)
                .where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_time >= start,
                    Appointment.appointment_time < end,
                    Appointment.is_deleted == False,  # noqa: E712
                )
            )
            or 0
        )

        total_revenue = (
            db.scalar(
                select(func.coalesce(func.sum(Billing.amount), 0))
                .select_from(Billing)
                .join(Appointment, Billing.appointment_id == Appointment.id)
                .where(
                    Billing.tenant_id == tenant_id,
                    Billing.status == BillingStatus.paid,
                    Billing.is_deleted == False,  # noqa: E712
                    Appointment.doctor_id == doctor_id,
                )
            )
            or 0
        )

        return {
            "total_patients": int(total_patients),
            "total_doctors": int(total_doctors),
            "today_appointments": int(today_appointments),
            "total_revenue": float(total_revenue),
        }

    has_appt_in_tenant = exists().where(
        Appointment.patient_id == Patient.id,
        Appointment.tenant_id == tenant_id,
        Appointment.is_deleted == False,  # noqa: E712
    )
    total_patients = db.scalar(select(func.count(Patient.id)).where(has_appt_in_tenant)) or 0
    total_doctors = (
        db.query(Doctor)
        .filter(
            Doctor.tenant_id == tenant_id,
            Doctor.is_deleted == False,  # noqa: E712
        )
        .count()
    )

    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    today_appointments = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.appointment_time >= start,
            Appointment.appointment_time < end,
            Appointment.is_deleted == False,  # noqa: E712
        )
        .count()
    )

    total_revenue = (
        db.query(func.sum(Billing.amount))
        .filter(
            Billing.tenant_id == tenant_id,
            Billing.status == "paid",
            Billing.is_deleted == False,  # noqa: E712
        )
        .scalar()
        or 0
    )

    return {
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "today_appointments": today_appointments,
        "total_revenue": float(total_revenue),
    }


def authorize_admin_dashboard_access(current_user: User) -> None:
    if not has_tenant_admin_privileges(current_user):
        raise ForbiddenError("Admin access required")


def resolve_admin_metrics_tenant_id(
    db: Session,
    current_user: User,
    x_tenant_id: UUID,
) -> UUID:
    """
    Resolve tenant for admin metrics using the ``X-Tenant-ID`` header (required for these routes).

    - admin: header must match the user's primary tenant.
    - super_admin: uses the header as the selected tenant (no UserTenant row).
    """
    if current_user.role == UserRole.super_admin:
        row = db.get(Tenant, x_tenant_id)
        if row is None:
            raise ValidationError("Tenant not found")
        if not row.is_active:
            raise ValidationError("Tenant is not active")
        return x_tenant_id

    eff = get_current_tenant_id(current_user, db)
    if eff is None:
        raise ValidationError("Tenant context is not configured for this user")
    if x_tenant_id != eff:
        raise ForbiddenError("X-Tenant-ID does not match your organization")
    return eff


def get_admin_dashboard_metrics(
    db: Session,
    tenant_id: UUID,
    doctor_id: UUID | None = None,
) -> dict:
    """
    Aggregated admin metrics for a single tenant.
    * total_revenue: sum of paid bill amounts with created_at in [start_date, +inf)
    * start_date: start of (today UTC) minus 7 days
    * revenue_today: paid bills with created_at on the current UTC calendar day
    * appointments_today: appointments whose time falls on the current UTC day
    * completed_appointments: completed with appointment_time in [start_date, +inf)
    * pending_bills: sum of amount for non-deleted bills with status pending or failed
    """
    if doctor_id is not None:
        drow = db.get(Doctor, doctor_id)
        if drow is None or drow.tenant_id != tenant_id:
            raise ValidationError("Invalid doctor for this tenant")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    start_date = today_start - timedelta(days=7)

    base_bill = and_(
        Billing.tenant_id == tenant_id,
        Billing.is_deleted == False,  # noqa: E712
    )
    if doctor_id is not None:
        base_bill = and_(
            base_bill,
            Billing.appointment_id.in_(
                select(Appointment.id).where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.doctor_id == doctor_id,
                    Appointment.is_deleted == False,  # noqa: E712
                )
            ),
        )

    total_revenue = db.scalar(
        select(func.coalesce(func.sum(Billing.amount), 0))
        .select_from(Billing)
        .where(
            base_bill,
            Billing.status == BillingStatus.paid,
            Billing.created_at >= start_date,
        )
    )
    if total_revenue is None:
        total_revenue = 0

    revenue_today = db.scalar(
        select(func.coalesce(func.sum(Billing.amount), 0))
        .select_from(Billing)
        .where(
            base_bill,
            Billing.status == BillingStatus.paid,
            Billing.created_at >= today_start,
            Billing.created_at < today_end,
        )
    )
    if revenue_today is None:
        revenue_today = 0

    base_appt = and_(
        Appointment.tenant_id == tenant_id,
        Appointment.is_deleted == False,  # noqa: E712
    )
    if doctor_id is not None:
        base_appt = and_(base_appt, Appointment.doctor_id == doctor_id)

    appointments_today = db.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(
            base_appt,
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
        )
    ) or 0

    completed_appointments = db.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(
            base_appt,
            Appointment.status == AppointmentStatus.completed,
            Appointment.appointment_time >= start_date,
        )
    ) or 0

    pending_bills = db.scalar(
        select(func.coalesce(func.sum(Billing.amount), 0))
        .select_from(Billing)
        .where(
            base_bill,
            Billing.status == BillingStatus.unpaid,
        )
    )
    if pending_bills is None:
        pending_bills = 0

    return {
        "total_revenue": float(total_revenue),
        "revenue_today": float(revenue_today),
        "appointments_today": int(appointments_today),
        "completed_appointments": int(completed_appointments),
        "pending_bills": float(pending_bills),
    }


def _coerce_to_date(d: object) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return date.fromisoformat(d)
    raise TypeError(f"Unexpected calendar day from DB: {type(d)!r}")


def get_revenue_trend(
    db: Session,
    tenant_id: UUID,
    doctor_id: UUID | None = None,
) -> list[dict]:
    """
    Daily paid revenue for the last 7 UTC calendar days (inclusive of today), oldest first.
    Days with no paid bills show revenue 0.
    """
    if doctor_id is not None:
        drow = db.get(Doctor, doctor_id)
        if drow is None or drow.tenant_id != tenant_id:
            raise ValidationError("Invalid doctor for this tenant")

    now = datetime.now(timezone.utc)
    today: date = now.date()
    start_date: date = today - timedelta(days=6)
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_excl = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    # func.date is portable (SQLite/PostgreSQL) and avoids cast+Date issues on SQLite.
    day_col = func.date(Billing.created_at)
    base_bill = and_(
        Billing.tenant_id == tenant_id,
        Billing.is_deleted == False,  # noqa: E712
    )

    if doctor_id is not None:
        trend_select = (
            select(day_col, func.coalesce(func.sum(Billing.amount), 0.0))
            .select_from(Billing)
            .join(Appointment, Billing.appointment_id == Appointment.id)
            .where(
                base_bill,
                Billing.status == BillingStatus.paid,
                Billing.created_at >= start_dt,
                Billing.created_at < end_excl,
                Appointment.doctor_id == doctor_id,
            )
            .group_by(day_col)
        )
    else:
        trend_select = (
            select(day_col, func.coalesce(func.sum(Billing.amount), 0.0))
            .select_from(Billing)
            .where(
                base_bill,
                Billing.status == BillingStatus.paid,
                Billing.created_at >= start_dt,
                Billing.created_at < end_excl,
            )
            .group_by(day_col)
        )

    rows = db.execute(trend_select).all()

    by_day: dict[date, float] = {}
    for d, amount in rows:
        bd = _coerce_to_date(d)
        by_day[bd] = float(amount or 0)

    out: list[dict] = []
    cur = start_date
    one = timedelta(days=1)
    while cur <= today:
        out.append(
            {
                "date": cur,
                "revenue": float(by_day.get(cur, 0.0)),
            }
        )
        cur = cur + one
    return out


def get_doctor_performance(
    db: Session,
    tenant_id: UUID,
    doctor_id: UUID | None = None,
) -> list[dict]:
    """
    Per-doctor stats for the last 7 UTC calendar days (inclusive): ``today - 6`` through end of
    today, aligned with :func:`get_revenue_trend`.

    * Appointments: non-deleted, ``tenant_id`` match, ``appointment_time`` in the window.
    * Completed: same window and ``status == completed``.
    * Revenue: non-deleted paid bills with ``created_at`` in the window, joined to a non-deleted
      appointment in the tenant; amount attributed to that appointment's ``doctor_id``.
    * All non-deleted doctors in the tenant are included (zeros when no data).
    """
    if doctor_id is not None:
        drow = db.get(Doctor, doctor_id)
        if drow is None or drow.tenant_id != tenant_id:
            raise ValidationError("Invalid doctor for this tenant")

    now = datetime.now(timezone.utc)
    today: date = now.date()
    start_date: date = today - timedelta(days=6)
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_excl = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    base_appt = and_(
        Appointment.tenant_id == tenant_id,
        Appointment.is_deleted == False,  # noqa: E712
        Appointment.appointment_time >= start_dt,
        Appointment.appointment_time < end_excl,
    )
    if doctor_id is not None:
        base_appt = and_(base_appt, Appointment.doctor_id == doctor_id)

    appt_subq = (
        select(
            Appointment.doctor_id,
            func.count().label("appointments_count"),
            func.sum(
                case((Appointment.status == AppointmentStatus.completed, 1), else_=0)
            ).label("completed_appointments"),
        )
        .where(base_appt)
        .group_by(Appointment.doctor_id)
    ).subquery()

    base_bill_rev = and_(
        Billing.tenant_id == tenant_id,
        Billing.is_deleted == False,  # noqa: E712
        Billing.status == BillingStatus.paid,
        Billing.appointment_id.isnot(None),
        Billing.created_at >= start_dt,
        Billing.created_at < end_excl,
    )

    rev_join = [
        Billing.appointment_id == Appointment.id,
        Appointment.tenant_id == tenant_id,
        Appointment.is_deleted == False,  # noqa: E712
    ]
    if doctor_id is not None:
        rev_join.append(Appointment.doctor_id == doctor_id)

    rev_subq = (
        select(
            Appointment.doctor_id,
            func.coalesce(func.sum(Billing.amount), 0).label("total_revenue"),
        )
        .select_from(Billing)
        .join(Appointment, and_(*rev_join))
        .where(base_bill_rev)
        .group_by(Appointment.doctor_id)
    ).subquery()

    stmt = (
        select(
            Doctor.id,
            Doctor.name,
            func.coalesce(appt_subq.c.appointments_count, 0).label("appointments_count"),
            func.coalesce(appt_subq.c.completed_appointments, 0).label("completed_appointments"),
            func.coalesce(rev_subq.c.total_revenue, 0.0).label("total_revenue"),
        )
        .select_from(Doctor)
        .outerjoin(appt_subq, appt_subq.c.doctor_id == Doctor.id)
        .outerjoin(rev_subq, rev_subq.c.doctor_id == Doctor.id)
        .where(
            Doctor.tenant_id == tenant_id,
            Doctor.is_deleted == False,  # noqa: E712
        )
        .order_by(Doctor.name)
    )
    if doctor_id is not None:
        stmt = stmt.where(Doctor.id == doctor_id)

    rows = db.execute(stmt).all()
    out: list[dict] = []
    for row in rows:
        doc_id, name, n_appt, n_comp, rev = row
        out.append(
            {
                "doctor_id": doc_id,
                "doctor_name": name,
                "appointments_count": int(n_appt or 0),
                "completed_appointments": int(n_comp or 0),
                "total_revenue": float(rev or 0),
            }
        )
    return out
