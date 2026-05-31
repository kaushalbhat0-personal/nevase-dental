"""Doctor schedule helpers: day meta and next-available slot (single round-trip)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from tests.factories import BOOKING_ANCHOR_DATE_ISO, seed_bookable_doctor_and_patient


@pytest.mark.asyncio
async def test_day_meta_and_next_available(client: AsyncClient, db_session: Session) -> None:
    doc_email = f"doc_meta_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_meta_{uuid.uuid4().hex[:8]}@e2e.test"
    doctor, _patient, _slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password="DocPass123!",
        patient_email=pat_email,
        patient_password="PatPass123!",
    )
    doctor_id = str(doctor.id)

    login = await client.post(
        "/api/v1/login",
        data={"username": pat_email, "password": "PatPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    meta = await client.get(
        f"/api/v1/doctors/{doctor_id}/day-meta",
        params={"date": BOOKING_ANCHOR_DATE_ISO},
        headers=headers,
    )
    assert meta.status_code == 200, meta.text
    assert meta.json().get("full_day_time_off") is False

    nxt = await client.get(
        f"/api/v1/doctors/{doctor_id}/next-available",
        params={"from": BOOKING_ANCHOR_DATE_ISO},
        headers=headers,
    )
    assert nxt.status_code == 200, nxt.text
    body = nxt.json()
    assert body is not None
    assert body.get("available") is True
    assert "start" in body

    combo = await client.get(
        f"/api/v1/doctors/{doctor_id}/schedule/day",
        params={"date": BOOKING_ANCHOR_DATE_ISO, "from": BOOKING_ANCHOR_DATE_ISO},
        headers=headers,
    )
    assert combo.status_code == 200, combo.text
    payload = combo.json()
    assert isinstance(payload.get("slots"), list) and len(payload["slots"]) > 0
    assert payload.get("full_day_time_off") is False
    assert payload.get("next_available") is not None
    assert "start" in (payload.get("next_available") or {})
