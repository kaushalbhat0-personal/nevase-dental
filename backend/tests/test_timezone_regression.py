"""Regression: naive appointment_time interpreted as doctor local timezone, not UTC.

Doctor availability: 09:00-13:00 IST (Asia/Kolkata, UTC+5:30)
The frontend sends wall-clock times as naive datetime strings.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from tests.factories import (
    BOOKING_ANCHOR_DATE_ISO,
    add_weekly_availability,
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)

_IST = ZoneInfo("Asia/Kolkata")
_FUTURE = date(2035, 6, 15)

# Availability window (wall-clock IST)
AVAIL_START = time(9, 0)
AVAIL_END = time(13, 0)


def _naive_ist(d: date, t: time) -> str:
    """Return ISO string of a *naive* datetime representing wall-clock IST."""
    return datetime.combine(d, t).isoformat()


def _utc_aware_ist(d: date, t: time) -> str:
    """Return ISO string of the UTC equivalent of an IST wall-clock time (tz-aware)."""
    aware_local = datetime.combine(d, t, tzinfo=_IST)
    return aware_local.astimezone(timezone.utc).isoformat()


def _seed_doctor(db: Session, availability_end: time | None = None) -> tuple:
    """Create tenant + doctor (Asia/Kolkata) with 09:00-13:00 IST availability.

    Returns (Doctor, Patient, doc_user, pat_user).
    """
    tenant = create_tenant(db)
    doc_user = create_user(
        db,
        email=f"tzdoc_{uuid.uuid4().hex[:8]}@test",
        password="Pass1234!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    doc = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id, timezone_name="Asia/Kolkata")
    add_weekly_availability(
        db,
        doctor_id=doc.id,
        tenant_id=tenant.id,
        day_of_week=_FUTURE.weekday(),
        start=AVAIL_START,
        end=availability_end or AVAIL_END,
        slot_duration=30,
    )
    pat_user = create_user(
        db,
        email=f"tzpat_{uuid.uuid4().hex[:8]}@test",
        password="Pass1234!",
        role=UserRole.patient,
    )
    pat = create_patient_profile(db, tenant_id=tenant.id, user_id=pat_user.id, created_by=pat_user.id)
    db.commit()
    return doc, pat, doc_user, pat_user


@pytest.mark.asyncio
async def test_scenario_A_book_within_availability_naive(client: AsyncClient, db_session: Session) -> None:
    """Scenario A: Book 10:00 IST (naive) → appointment created."""
    doc, pat, doc_user, _ = _seed_doctor(db_session)
    login = await client.post(
        "/api/v1/login",
        data={"username": doc_user.email, "password": "Pass1234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "patient_id": str(pat.id),
        "doctor_id": str(doc.id),
        "appointment_time": _naive_ist(_FUTURE, time(10, 0)),
    }
    resp = await client.post(
        "/api/v1/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"A - expected 201 got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_scenario_B_book_outside_availability_naive(client: AsyncClient, db_session: Session) -> None:
    """Scenario B: Book 14:00 IST (naive, outside 09-13) → rejected."""
    doc, pat, doc_user, _ = _seed_doctor(db_session)
    login = await client.post(
        "/api/v1/login",
        data={"username": doc_user.email, "password": "Pass1234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "patient_id": str(pat.id),
        "doctor_id": str(doc.id),
        "appointment_time": _naive_ist(_FUTURE, time(14, 0)),
    }
    resp = await client.post(
        "/api/v1/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400, f"B - expected 400 got {resp.status_code}: {resp.text}"
    detail = (resp.json().get("detail") or "").lower()
    assert "slot" in detail or "availability" in detail or "scheduled" in detail, f"unexpected detail: {detail}"


@pytest.mark.asyncio
async def test_scenario_C_reschedule_naive(client: AsyncClient, db_session: Session) -> None:
    """Scenario C: Create at 10:00 IST (naive), reschedule to 11:00 IST (naive) → success."""
    doc, pat, doc_user, _ = _seed_doctor(db_session)
    login = await client.post(
        "/api/v1/login",
        data={"username": doc_user.email, "password": "Pass1234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    # Create
    create_payload = {
        "patient_id": str(pat.id),
        "doctor_id": str(doc.id),
        "appointment_time": _naive_ist(_FUTURE, time(10, 0)),
    }
    created = await client.post(
        "/api/v1/appointments",
        json=create_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201, f"C-create: {created.text}"
    appt_id = created.json()["id"]

    # Reschedule
    update_payload = {
        "appointment_time": _naive_ist(_FUTURE, time(11, 0)),
    }
    updated = await client.put(
        f"/api/v1/appointments/{appt_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert updated.status_code == 200, f"C-reschedule: {updated.text}"


@pytest.mark.asyncio
async def test_scenario_D_patient_booking_naive(client: AsyncClient, db_session: Session) -> None:
    """Scenario D: Patient books their own slot with naive datetime → success."""
    doc, pat, _, pat_user = _seed_doctor(db_session)
    login = await client.post(
        "/api/v1/login",
        data={"username": pat_user.email, "password": "Pass1234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "patient_id": str(pat.id),
        "doctor_id": str(doc.id),
        "appointment_time": _naive_ist(_FUTURE, time(10, 30)),
    }
    resp = await client.post(
        "/api/v1/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"D: {resp.text}"


@pytest.mark.asyncio
async def test_scenario_E_admin_booking_naive(client: AsyncClient, db_session: Session) -> None:
    """Scenario E: Admin/receptionist creates appointment with naive datetime → success."""
    doc, pat, doc_user, _ = _seed_doctor(db_session)
    admin_user = create_user(
        db_session,
        email=f"tzadmin_{uuid.uuid4().hex[:8]}@test",
        password="AdminPass1!",
        role=UserRole.admin,
        tenant_id=doc.tenant_id,
    )
    db_session.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": admin_user.email, "password": "AdminPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "patient_id": str(pat.id),
        "doctor_id": str(doc.id),
        "appointment_time": _naive_ist(_FUTURE, time(9, 30)),
    }
    resp = await client.post(
        "/api/v1/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"E: {resp.text}"


@pytest.mark.asyncio
async def test_existing_tz_aware_still_works(client: AsyncClient, db_session: Session) -> None:
    """Existing tz-aware UTC callers must not break."""
    doc, pat, doc_user, _ = _seed_doctor(db_session)
    login = await client.post(
        "/api/v1/login",
        data={"username": doc_user.email, "password": "Pass1234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "patient_id": str(pat.id),
        "doctor_id": str(doc.id),
        "appointment_time": _utc_aware_ist(_FUTURE, time(10, 0)),
    }
    resp = await client.post(
        "/api/v1/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"tz-aware UTC: {resp.text}"


@pytest.mark.asyncio
async def test_double_book_still_rejected_naive(client: AsyncClient, db_session: Session) -> None:
    """Two bookings at same naive time → first succeeds, second is rejected."""
    doc, pat, _, pat_user = _seed_doctor(db_session)
    login = await client.post(
        "/api/v1/login",
        data={"username": pat_user.email, "password": "Pass1234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "patient_id": str(pat.id),
        "doctor_id": str(doc.id),
        "appointment_time": _naive_ist(_FUTURE, time(10, 0)),
    }
    first = await client.post(
        "/api/v1/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 201

    # Second booking at same time → double-book protection
    second = await client.post(
        "/api/v1/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 400, f"double-book: {second.text}"
