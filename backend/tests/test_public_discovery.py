"""Public tenant/doctor discovery and patient my-doctors APIs."""

from __future__ import annotations

from datetime import datetime, time, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.crud.crud_appointment import add_appointment
from app.models.appointment import AppointmentStatus
from app.models.tenant import TenantType
from app.models.user import UserRole
from app.services import doctor_profile_service
from tests.factories import (
    add_weekly_availability,
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)


@pytest.mark.asyncio
async def test_public_tenants_counts_and_sole_doctor(client: AsyncClient, db_session: Session) -> None:
    clinic = create_tenant(db_session, name="Apollo Multi", tenant_type=TenantType.organization)
    create_doctor_profile(db_session, tenant_id=clinic.id)
    create_doctor_profile(db_session, tenant_id=clinic.id)

    solo_t = create_tenant(db_session, name="Solo Practice", tenant_type=TenantType.organization)
    d_solo = create_doctor_profile(db_session, tenant_id=solo_t.id)
    d_solo.name = "Dr Solo"
    db_session.flush()

    db_session.commit()

    r = await client.get("/api/v1/public/tenants")
    assert r.status_code == 200
    data = r.json()
    by_name = {row["name"]: row for row in data}
    assert by_name["Apollo Multi"]["doctor_count"] == 2
    assert by_name["Apollo Multi"]["organization_label"] == "Clinic/Hospital"
    assert by_name["Solo Practice"]["doctor_count"] == 1
    assert by_name["Solo Practice"]["organization_label"] == "Individual Doctor"
    assert by_name["Solo Practice"]["sole_doctor"]["name"] == "Dr Solo"

    r_docs = await client.get(f"/api/v1/public/tenants/{clinic.id}/doctors")
    assert r_docs.status_code == 200
    assert len(r_docs.json()) == 2


@pytest.mark.asyncio
async def test_patients_me_doctors_requires_patient_and_returns_booked(
    client: AsyncClient, db_session: Session
) -> None:
    tenant = create_tenant(db_session)
    _admin = create_user(
        db_session,
        email="admin-me-doc@t.test",
        password="x",
        role=UserRole.admin,
        tenant_id=tenant.id,
    )
    doc = create_doctor_profile(db_session, tenant_id=tenant.id)
    pat_user = create_user(
        db_session,
        email="pat-me-doc@t.test",
        password="x",
        role=UserRole.patient,
    )
    pat = create_patient_profile(
        db_session,
        tenant_id=tenant.id,
        user_id=pat_user.id,
        created_by=pat_user.id,
    )

    add_appointment(
        db_session,
        {
            "patient_id": pat.id,
            "doctor_id": doc.id,
            "appointment_time": datetime.now(timezone.utc),
            "status": AppointmentStatus.scheduled,
            "created_by": pat_user.id,
            "tenant_id": tenant.id,
        },
    )
    db_session.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": pat_user.email, "password": "x"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    r = await client.get("/api/v1/patients/me/doctors", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["id"] == str(doc.id)

    login_staff = await client.post(
        "/api/v1/login",
        data={"username": _admin.email, "password": "x"},
    )
    tok_staff = login_staff.json()["access_token"]
    r2 = await client.get(
        "/api/v1/patients/me/doctors",
        headers={"Authorization": f"Bearer {tok_staff}"},
    )
    assert r2.status_code == 403


@pytest.mark.asyncio
async def test_public_doctor_profile_approved_and_draft_404(
    client: AsyncClient, db_session: Session
) -> None:
    tenant = create_tenant(db_session, name="Clinic A", tenant_type=TenantType.organization)
    doc_ok = create_doctor_profile(db_session, tenant_id=tenant.id)
    doc_draft = create_doctor_profile(db_session, tenant_id=tenant.id)
    from app.crud import crud_doctor_profile

    prof = crud_doctor_profile.get_by_doctor_id(db_session, doc_draft.id)
    assert prof is not None
    prof.verification_status = doctor_profile_service.VERIFICATION_DRAFT
    db_session.commit()

    r_ok = await client.get(f"/api/v1/public/doctors/{doc_ok.id}")
    assert r_ok.status_code == 200
    body = r_ok.json()
    assert body["id"] == str(doc_ok.id)
    assert body["verified"] is True
    assert body["verification_status"] == "approved"
    assert "full_name" in body
    assert "next_available_slot" in body
    assert "available_today" in body
    assert "slots_today_count" in body
    assert "slots_tomorrow_count" in body
    assert "metrics_are_synthetic" in body
    assert body["rating_average"] == 4.8
    assert body["review_count"] == 124
    assert "distance_km" in body

    r_404 = await client.get(f"/api/v1/public/doctors/{doc_draft.id}")
    assert r_404.status_code == 404


@pytest.mark.asyncio
async def test_doctor_slots_unauthenticated_approved_only(
    client: AsyncClient, db_session: Session
) -> None:
    from datetime import date

    from zoneinfo import ZoneInfo

    tenant = create_tenant(db_session, name="Clinic B", tenant_type=TenantType.organization)
    doc = create_doctor_profile(db_session, tenant_id=tenant.id, timezone_name="Asia/Kolkata")
    add_weekly_availability(
        db_session,
        doctor_id=doc.id,
        tenant_id=tenant.id,
        day_of_week=date.today().weekday(),
        start=time(9, 0),
        end=time(12, 0),
        slot_duration=15,
    )
    db_session.commit()

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    r = await client.get(f"/api/v1/doctors/{doc.id}/slots", params={"date": today})
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    from app.crud import crud_doctor_profile

    prof = crud_doctor_profile.get_by_doctor_id(db_session, doc.id)
    assert prof is not None
    prof.verification_status = doctor_profile_service.VERIFICATION_DRAFT
    db_session.commit()

    r2 = await client.get(f"/api/v1/doctors/{doc.id}/slots", params={"date": today})
    assert r2.status_code == 404
