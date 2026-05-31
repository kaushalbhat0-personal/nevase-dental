"""Admin dashboard metrics API: RBAC, tenant isolation, and aggregation correctness."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.crud import crud_appointment
from app.models.appointment import AppointmentStatus
from app.models.billing import Billing, BillingStatus
from app.models.tenant import TenantType
from app.models.user import UserRole
from tests.factories import (
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)

METRICS_PATH = "/api/v1/admin/dashboard/metrics"
REVENUE_TREND_PATH = "/api/v1/admin/dashboard/revenue-trend"
DOCTOR_PERFORMANCE_PATH = "/api/v1/admin/dashboard/doctor-performance"


def _bearer_tenant(token: str, tenant_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


def _seed_tenant_a_metrics(
    db: Session,
) -> tuple[object, float, float, int, int, float, object, str, str]:
    """Returns (tenant, exp_total_rev, exp_rev_today, appts_today, completed, pending_sum, other_tenant, admin_email, admin_password)."""
    tenant_a = create_tenant(db, name="metrics-a", tenant_type=TenantType.organization)
    tenant_b = create_tenant(db, name="metrics-b", tenant_type=TenantType.organization)
    other = tenant_b

    admin = create_user(
        db,
        email=f"adm_{uuid.uuid4().hex[:10]}@test.local",
        password="Adm1nPass!",
        role=UserRole.admin,
        tenant_id=tenant_a.id,
    )
    doc_user = create_user(
        db,
        email=f"doc_{uuid.uuid4().hex[:10]}@test.local",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=tenant_a.id,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant_a.id, user_id=doc_user.id, timezone_name="UTC")

    pat_user = create_user(
        db,
        email=f"pat_{uuid.uuid4().hex[:10]}@test.local",
        password="PatPass9!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db, tenant_id=tenant_a.id, user_id=pat_user.id, created_by=admin.id, name="P Metrics"
    )

    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    start_date = today_start - timedelta(days=7)
    # Outside rolling window for total_revenue
    before_window = start_date - timedelta(seconds=1)

    # B other tenant: should not affect tenant A
    b_admin = create_user(
        db,
        email=f"badm_{uuid.uuid4().hex[:10]}@test.local",
        password="Adm1nPass!",
        role=UserRole.admin,
        tenant_id=tenant_b.id,
    )
    b_pat_user = create_user(
        db,
        email=f"bp_{uuid.uuid4().hex[:10]}@test.local",
        password="PatPass9!",
        role=UserRole.patient,
    )
    b_patient = create_patient_profile(
        db, tenant_id=tenant_b.id, user_id=b_pat_user.id, created_by=b_admin.id, name="B"
    )
    b_doc = create_doctor_profile(db, tenant_id=tenant_b.id, user_id=b_admin.id, timezone_name="UTC")
    crud_appointment.add_appointment(
        db,
        {
            "patient_id": b_patient.id,
            "doctor_id": b_doc.id,
            "appointment_time": today_start + timedelta(hours=1),
            "status": AppointmentStatus.completed,
            "created_by": b_admin.id,
            "tenant_id": tenant_b.id,
        },
    )
    db.add(
        Billing(
            patient_id=b_patient.id,
            appointment_id=None,
            tenant_id=tenant_b.id,
            amount=9999,
            status=BillingStatus.paid,
            created_by=b_admin.id,
        )
    )

    # A: paid in window
    t_ap = today_start
    a1 = crud_appointment.add_appointment(
        db,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": t_ap - timedelta(days=1) + timedelta(minutes=2),
            "status": AppointmentStatus.scheduled,
            "created_by": pat_user.id,
            "tenant_id": tenant_a.id,
        },
    )
    db.add(
        Billing(
            patient_id=patient.id,
            appointment_id=a1.id,
            tenant_id=tenant_a.id,
            amount=200,
            status=BillingStatus.paid,
            created_by=admin.id,
        )
    )
    b_old = crud_appointment.add_appointment(
        db,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": before_window + timedelta(minutes=5),
            "status": AppointmentStatus.scheduled,
            "created_by": pat_user.id,
            "tenant_id": tenant_a.id,
        },
    )
    b_revenue_ancient = Billing(
        patient_id=patient.id,
        appointment_id=b_old.id,
        tenant_id=tenant_a.id,
        amount=5000,
        status=BillingStatus.paid,
        created_by=admin.id,
    )
    db.add(b_revenue_ancient)
    db.flush()
    b_revenue_ancient.created_at = before_window

    # A: revenue_today
    a_today_apt = crud_appointment.add_appointment(
        db,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": t_ap + timedelta(hours=3),
            "status": AppointmentStatus.scheduled,
            "created_by": pat_user.id,
            "tenant_id": tenant_a.id,
        },
    )
    b_today = Billing(
        patient_id=patient.id,
        appointment_id=a_today_apt.id,
        tenant_id=tenant_a.id,
        amount=50,
        status=BillingStatus.paid,
        created_by=admin.id,
    )
    db.add(b_today)
    db.flush()
    b_today.created_at = today_start + timedelta(hours=1)

    # A: two appointments "today" (by appointment_time UTC)
    crud_appointment.add_appointment(
        db,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": t_ap + timedelta(hours=4, minutes=7),
            "status": AppointmentStatus.scheduled,
            "created_by": pat_user.id,
            "tenant_id": tenant_a.id,
        },
    )
    crud_appointment.add_appointment(
        db,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": t_ap + timedelta(hours=8, minutes=11),
            "status": AppointmentStatus.scheduled,
            "created_by": pat_user.id,
            "tenant_id": tenant_a.id,
        },
    )

    # A: completed in window
    for i in range(2):
        crud_appointment.add_appointment(
            db,
            {
                "patient_id": patient.id,
                "doctor_id": doctor.id,
                "appointment_time": t_ap - timedelta(days=1) + timedelta(minutes=20 + i * 3),
                "status": AppointmentStatus.completed,
                "created_by": pat_user.id,
                "tenant_id": tenant_a.id,
            },
        )

    # A: pending + failed
    db.add(
        Billing(
            patient_id=patient.id,
            appointment_id=None,
            tenant_id=tenant_a.id,
            amount=10,
            status=BillingStatus.unpaid,
            created_by=admin.id,
        )
    )
    db.add(
        Billing(
            patient_id=patient.id,
            appointment_id=None,
            tenant_id=tenant_a.id,
            amount=4.5,
            status=BillingStatus.unpaid,
            created_by=admin.id,
        )
    )

    db.commit()

    # Re-query sums from DB the same way the spec defines them
    from sqlalchemy import and_, func, or_, select

    from app.models.appointment import Appointment
    from app.models.billing import Billing as BillingModel

    total_rev = db.scalar(
        select(func.coalesce(func.sum(BillingModel.amount), 0))
        .select_from(BillingModel)
        .where(
            and_(
                BillingModel.tenant_id == tenant_a.id,
                BillingModel.is_deleted == False,  # noqa: E712
            ),
            BillingModel.status == BillingStatus.paid,
            BillingModel.created_at >= start_date,
        )
    )
    assert total_rev is not None
    rev_today = db.scalar(
        select(func.coalesce(func.sum(BillingModel.amount), 0))
        .select_from(BillingModel)
        .where(
            and_(
                BillingModel.tenant_id == tenant_a.id,
                BillingModel.is_deleted == False,  # noqa: E712
            ),
            BillingModel.status == BillingStatus.paid,
            BillingModel.created_at >= today_start,
            BillingModel.created_at < today_end,
        )
    )
    n_appt = db.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(
            and_(
                Appointment.tenant_id == tenant_a.id,
                Appointment.is_deleted == False,  # noqa: E712
            ),
            Appointment.appointment_time >= today_start,
            Appointment.appointment_time < today_end,
        )
    )
    n_comp = db.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(
            and_(
                Appointment.tenant_id == tenant_a.id,
                Appointment.is_deleted == False,  # noqa: E712
            ),
            Appointment.status == AppointmentStatus.completed,
            Appointment.appointment_time >= start_date,
        )
    )
    pend = db.scalar(
        select(func.coalesce(func.sum(BillingModel.amount), 0))
        .select_from(BillingModel)
        .where(
            and_(
                BillingModel.tenant_id == tenant_a.id,
                BillingModel.is_deleted == False,  # noqa: E712
            ),
            BillingModel.status == BillingStatus.unpaid,
        )
    )
    return (
        tenant_a,
        float(total_rev or 0),
        float(rev_today or 0),
        int(n_appt or 0),
        int(n_comp or 0),
        float(pend or 0),
        other,
        admin.email,
        "Adm1nPass!",
    )


@pytest.mark.asyncio
async def test_admin_can_read_dashboard_metrics(
    client: AsyncClient, db_session: Session
) -> None:
    _t, exp_total, exp_rtoday, exp_ap, exp_c, exp_p, _b, ad_email, ad_pw = _seed_tenant_a_metrics(
        db_session
    )
    login = await client.post(
        "/api/v1/login",
        data={"username": ad_email, "password": ad_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    r = await client.get(METRICS_PATH, headers=_bearer_tenant(token, _t.id))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_revenue"] == exp_total
    assert body["revenue_today"] == exp_rtoday
    assert body["appointments_today"] == exp_ap
    assert body["completed_appointments"] == exp_c
    assert body["pending_bills"] == exp_p

    for k in (
        "total_revenue",
        "revenue_today",
        "appointments_today",
        "completed_appointments",
        "pending_bills",
    ):
        assert k in body


@pytest.mark.asyncio
async def test_admin_dashboard_metrics_400_without_tenant_header(
    client: AsyncClient, db_session: Session
) -> None:
    t, _a, _b, _c, _d, _e, _f, ad_email, ad_pw = _seed_tenant_a_metrics(db_session)
    _ = t
    login = await client.post(
        "/api/v1/login",
        data={"username": ad_email, "password": ad_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    r = await client.get(METRICS_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_doctor_cannot_read_dashboard_metrics(
    client: AsyncClient, db_session: Session
) -> None:
    t, _a, _b, _c, _d, _e, _f, _g, _h = _seed_tenant_a_metrics(db_session)
    doc_email = f"docd_{uuid.uuid4().hex[:8]}@test.local"
    create_user(
        db_session,
        email=doc_email,
        password="Doc9Pass!",
        role=UserRole.doctor,
        tenant_id=t.id,
    )
    db_session.commit()
    login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": "Doc9Pass!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    r = await client.get(METRICS_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_metrics_respect_tenant_isolation(
    client: AsyncClient, db_session: Session
) -> None:
    t_a, exp_total, exp_rtoday, exp_ap, exp_c, exp_p, t_b, ad_email, ad_pw = _seed_tenant_a_metrics(
        db_session
    )
    _ = t_b  # noise tenant in seed; admin only for A
    token = (
        await client.post(
            "/api/v1/login",
            data={"username": ad_email, "password": ad_pw},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()["access_token"]
    r = await client.get(
        f"{METRICS_PATH}?tenant_id={t_b.id}",
        headers=_bearer_tenant(token, t_a.id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Query param must not let tenant A see tenant B: still scoped to admin's tenant
    assert body["total_revenue"] == exp_total
    assert body["revenue_today"] == exp_rtoday
    assert body["appointments_today"] == exp_ap
    assert body["completed_appointments"] == exp_c
    assert body["pending_bills"] == exp_p


def _seed_tenant_revenue_trend_minimal(
    db: Session,
) -> tuple[object, str, str, object, object]:
    """tenant_a, admin_email, admin_password, tenant_b, b_bill (for isolation check)."""
    tenant_a = create_tenant(db, name="rtrend-a", tenant_type=TenantType.organization)
    tenant_b = create_tenant(db, name="rtrend-b", tenant_type=TenantType.organization)
    admin = create_user(
        db,
        email=f"rt_ad_{uuid.uuid4().hex[:10]}@test.local",
        password="Adm1nPass!",
        role=UserRole.admin,
        tenant_id=tenant_a.id,
    )
    b_admin = create_user(
        db,
        email=f"rt_bad_{uuid.uuid4().hex[:10]}@test.local",
        password="Adm1nPass!",
        role=UserRole.admin,
        tenant_id=tenant_b.id,
    )
    b_pat = create_user(
        db,
        email=f"rt_bpat_{uuid.uuid4().hex[:8]}@test.local",
        password="Pat9!",
        role=UserRole.patient,
    )
    b_patient = create_patient_profile(
        db, tenant_id=tenant_b.id, user_id=b_pat.id, created_by=b_admin.id, name="RTB"
    )
    b_bill = Billing(
        patient_id=b_patient.id,
        appointment_id=None,
        tenant_id=tenant_b.id,
        amount=7777,
        status=BillingStatus.paid,
        created_by=b_admin.id,
    )
    db.add(b_bill)
    a_pat = create_user(
        db,
        email=f"rt_apat_{uuid.uuid4().hex[:8]}@test.local",
        password="Pat9!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db, tenant_id=tenant_a.id, user_id=a_pat.id, created_by=admin.id, name="RTA"
    )
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    a_bill = Billing(
        patient_id=patient.id,
        appointment_id=None,
        tenant_id=tenant_a.id,
        amount=123.45,
        status=BillingStatus.paid,
        created_by=admin.id,
    )
    db.add(a_bill)
    db.flush()
    a_bill.created_at = today_start + timedelta(hours=2)
    db.commit()
    return tenant_a, admin.email, "Adm1nPass!", tenant_b, b_bill


@pytest.mark.asyncio
async def test_admin_revenue_trend_seven_days_includes_zero_revenue_days(
    client: AsyncClient, db_session: Session
) -> None:
    t_a, ad_email, ad_pw, _b, _bb = _seed_tenant_revenue_trend_minimal(db_session)
    _ = t_a, _b, _bb
    login = await client.post(
        "/api/v1/login",
        data={"username": ad_email, "password": ad_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    r = await client.get(REVENUE_TREND_PATH, headers=_bearer_tenant(token, t_a.id))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 7
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=6)
    for i, row in enumerate(body):
        assert row["date"] == (start + timedelta(days=i)).isoformat()
    revenues = [row["revenue"] for row in body]
    assert sum(1 for x in revenues if x == 0) == 6
    assert abs(sum(revenues) - 123.45) < 0.01
    # Single paid bill "today" UTC — only the last day is non-zero
    assert revenues[-1] == pytest.approx(123.45)


@pytest.mark.asyncio
async def test_doctor_cannot_read_revenue_trend(client: AsyncClient, db_session: Session) -> None:
    t, _a, _b, _c, _d = _seed_tenant_revenue_trend_minimal(db_session)
    doc_email = f"rt_doc_{uuid.uuid4().hex[:8]}@test.local"
    create_user(
        db_session,
        email=doc_email,
        password="Doc9Pass!",
        role=UserRole.doctor,
        tenant_id=t.id,
    )
    db_session.commit()
    login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": "Doc9Pass!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    r = await client.get(
        REVENUE_TREND_PATH, headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_revenue_trend_respects_tenant_isolation(
    client: AsyncClient, db_session: Session
) -> None:
    t_a, ad_email, ad_pw, t_b, b_bill = _seed_tenant_revenue_trend_minimal(db_session)
    _ = t_a, t_b, b_bill
    token = (
        await client.post(
            "/api/v1/login",
            data={"username": ad_email, "password": ad_pw},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()["access_token"]
    r = await client.get(
        f"{REVENUE_TREND_PATH}?tenant_id={t_b.id}",
        headers=_bearer_tenant(token, t_a.id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Still tenant A only; 7777 (tenant B) must not appear in any day
    assert all(row["revenue"] < 1000 for row in body)
    assert abs(sum(row["revenue"] for row in body) - 123.45) < 0.01


def _seed_doctor_performance_tenant(
    db: Session,
) -> tuple[object, object, object, str, str, int, int, float]:
    """
    Returns (
      tenant_a,
      doctor_with_data,
      doctor_empty,
      admin_email,
      admin_password,
      exp_appt,
      exp_completed,
      exp_revenue,
    ).
    """
    tenant_a = create_tenant(db, name="dperf-a", tenant_type=TenantType.organization)
    tenant_b = create_tenant(db, name="dperf-b", tenant_type=TenantType.organization)

    admin = create_user(
        db,
        email=f"dperf_ad_{uuid.uuid4().hex[:10]}@test.local",
        password="Adm1nPass!",
        role=UserRole.admin,
        tenant_id=tenant_a.id,
    )
    b_admin = create_user(
        db,
        email=f"dperf_b_{uuid.uuid4().hex[:8]}@test.local",
        password="Adm1nPass!",
        role=UserRole.admin,
        tenant_id=tenant_b.id,
    )

    doc_u1 = create_user(
        db,
        email=f"dperf_d1_{uuid.uuid4().hex[:8]}@test.local",
        password="Doc9!",
        role=UserRole.doctor,
        tenant_id=tenant_a.id,
    )
    doc_u2 = create_user(
        db,
        email=f"dperf_d2_{uuid.uuid4().hex[:8]}@test.local",
        password="Doc9!",
        role=UserRole.doctor,
        tenant_id=tenant_a.id,
    )
    doctor_active = create_doctor_profile(
        db, tenant_id=tenant_a.id, user_id=doc_u1.id, timezone_name="UTC"
    )
    doctor_empty = create_doctor_profile(
        db, tenant_id=tenant_a.id, user_id=doc_u2.id, timezone_name="UTC"
    )
    b_doc = create_doctor_profile(
        db, tenant_id=tenant_b.id, user_id=b_admin.id, timezone_name="UTC"
    )

    pat_a = create_user(
        db,
        email=f"dperf_pa_{uuid.uuid4().hex[:8]}@test.local",
        password="Pat9!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db, tenant_id=tenant_a.id, user_id=pat_a.id, created_by=admin.id, name="DP Patient"
    )
    b_pat = create_user(
        db,
        email=f"dperf_pb_{uuid.uuid4().hex[:8]}@test.local",
        password="Pat9!",
        role=UserRole.patient,
    )
    b_patient = create_patient_profile(
        db, tenant_id=tenant_b.id, user_id=b_pat.id, created_by=b_admin.id, name="B"
    )

    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()
    start_date = today - timedelta(days=6)
    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_excl = datetime.combine(
        today + timedelta(days=1), time.min, tzinfo=timezone.utc
    )

    t_in = start_dt + timedelta(hours=2)
    a1 = crud_appointment.add_appointment(
        db,
        {
            "patient_id": patient.id,
            "doctor_id": doctor_active.id,
            "appointment_time": t_in,
            "status": AppointmentStatus.scheduled,
            "created_by": pat_a.id,
            "tenant_id": tenant_a.id,
        },
    )
    a2 = crud_appointment.add_appointment(
        db,
        {
            "patient_id": patient.id,
            "doctor_id": doctor_active.id,
            "appointment_time": t_in + timedelta(minutes=30),
            "status": AppointmentStatus.completed,
            "created_by": pat_a.id,
            "tenant_id": tenant_a.id,
        },
    )
    b1 = Billing(
        patient_id=patient.id,
        appointment_id=a1.id,
        tenant_id=tenant_a.id,
        amount=100.0,
        status=BillingStatus.paid,
        created_by=admin.id,
    )
    b2 = Billing(
        patient_id=patient.id,
        appointment_id=a2.id,
        tenant_id=tenant_a.id,
        amount=25.5,
        status=BillingStatus.paid,
        created_by=admin.id,
    )
    db.add(b1)
    db.add(b2)
    db.flush()
    b1.created_at = start_dt + timedelta(hours=1)
    b2.created_at = start_dt + timedelta(hours=2)

    # Tenant B: noise (must not affect tenant A)
    b_apt = crud_appointment.add_appointment(
        db,
        {
            "patient_id": b_patient.id,
            "doctor_id": b_doc.id,
            "appointment_time": t_in,
            "status": AppointmentStatus.completed,
            "created_by": b_pat.id,
            "tenant_id": tenant_b.id,
        },
    )
    db.add(
        Billing(
            patient_id=b_patient.id,
            appointment_id=b_apt.id,
            tenant_id=tenant_b.id,
            amount=50_000.0,
            status=BillingStatus.paid,
            created_by=b_admin.id,
        )
    )
    db.commit()

    return (
        tenant_a,
        doctor_active,
        doctor_empty,
        admin.email,
        "Adm1nPass!",
        2,
        1,
        125.5,
    )


@pytest.mark.asyncio
async def test_admin_gets_doctor_performance_including_empty_doctor(
    client: AsyncClient, db_session: Session
) -> None:
    _t, d_data, d_empty, ad_email, ad_pw, exp_n, exp_c, exp_rev = _seed_doctor_performance_tenant(
        db_session
    )
    login = await client.post(
        "/api/v1/login",
        data={"username": ad_email, "password": ad_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    r = await client.get(
        DOCTOR_PERFORMANCE_PATH, headers=_bearer_tenant(token, _t.id)
    )
    assert r.status_code == 200, r.text
    body = r.json()
    by_id = {x["doctor_id"]: x for x in body}
    row_data = by_id[str(d_data.id)]
    row_empty = by_id[str(d_empty.id)]
    assert row_data["appointments_count"] == exp_n
    assert row_data["completed_appointments"] == exp_c
    assert abs(row_data["total_revenue"] - exp_rev) < 0.01
    assert row_empty["appointments_count"] == 0
    assert row_empty["completed_appointments"] == 0
    assert row_empty["total_revenue"] == 0
    keys = (
        "doctor_id",
        "doctor_name",
        "appointments_count",
        "completed_appointments",
        "total_revenue",
    )
    for row in body:
        for k in keys:
            assert k in row


@pytest.mark.asyncio
async def test_doctor_cannot_read_doctor_performance(
    client: AsyncClient, db_session: Session
) -> None:
    t, _a, _b, ad_email, ad_pw, _e, _f, _g = _seed_doctor_performance_tenant(db_session)
    doc_email = f"dperf_doc_{uuid.uuid4().hex[:8]}@test.local"
    create_user(
        db_session,
        email=doc_email,
        password="Doc9Pass!",
        role=UserRole.doctor,
        tenant_id=t.id,
    )
    db_session.commit()
    login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": "Doc9Pass!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    r = await client.get(
        DOCTOR_PERFORMANCE_PATH,
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_doctor_performance_respects_tenant_isolation(
    client: AsyncClient, db_session: Session
) -> None:
    t_a, d_data, d_empty, ad_email, ad_pw, _n, _c, exp_rev = _seed_doctor_performance_tenant(
        db_session
    )
    t_b = create_tenant(db_session, name="dperf-iso", tenant_type=TenantType.organization)
    db_session.commit()
    token = (
        await client.post(
            "/api/v1/login",
            data={"username": ad_email, "password": ad_pw},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()["access_token"]
    r = await client.get(
        f"{DOCTOR_PERFORMANCE_PATH}?tenant_id={t_b.id}",
        headers=_bearer_tenant(token, t_a.id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Still tenant A: two doctors, revenue only from A
    assert len(body) == 2
    assert {str(d_data.id), str(d_empty.id)} == {x["doctor_id"] for x in body}
    assert sum(x["total_revenue"] for x in body) == pytest.approx(exp_rev, abs=0.01)
