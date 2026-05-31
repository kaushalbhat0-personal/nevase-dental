"""Slots API reflects availability changes (including cache invalidation)."""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.models.doctor_availability import DoctorAvailability
from app.models.user import UserRole
from app.services.doctor_slot_service import invalidate_all_slots_cache_for_doctor
from tests.factories import (
    add_weekly_availability,
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)


@pytest.fixture
def doctor_factory(db_session: Session):
    def _make() -> Doctor:
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email=f"doc_{uuid.uuid4().hex[:8]}@slot-up.test",
            password="DocPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_user.id)
        db_session.commit()
        db_session.refresh(doctor)
        return doctor

    return _make


@pytest.fixture
def availability_factory(db_session: Session):
    def _make(
        *,
        doctor_id: UUID,
        day_of_week: int,
        start_time: str,
        end_time: str,
        slot_duration_minutes: int,
    ) -> None:
        doctor = db_session.get(Doctor, doctor_id)
        assert doctor is not None
        assert doctor.tenant_id is not None
        add_weekly_availability(
            db_session,
            doctor_id=doctor_id,
            tenant_id=doctor.tenant_id,
            day_of_week=day_of_week,
            start=time.fromisoformat(start_time),
            end=time.fromisoformat(end_time),
            slot_duration=slot_duration_minutes,
        )
        db_session.commit()

    return _make


@pytest.mark.asyncio
async def test_slots_update_after_availability_change(
    client: AsyncClient,
    db_session: Session,
    doctor_factory,
    availability_factory,
) -> None:
    doctor = doctor_factory()

    slot_date = date.today() + timedelta(days=14)
    availability_factory(
        doctor_id=doctor.id,
        day_of_week=slot_date.weekday(),
        start_time="09:00",
        end_time="17:00",
        slot_duration_minutes=30,
    )

    pat_email = f"pat_{uuid.uuid4().hex[:8]}@slot-up.test"
    pat_user = create_user(
        db_session,
        email=pat_email,
        password="PatPass9!",
        role=UserRole.patient,
    )
    create_patient_profile(
        db_session,
        tenant_id=doctor.tenant_id,
        user_id=pat_user.id,
        created_by=pat_user.id,
    )
    db_session.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": pat_email, "password": "PatPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    auth = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res1 = await client.get(
        f"/api/v1/doctors/{doctor.id}/slots?date={slot_date.isoformat()}",
        headers=auth,
    )
    assert res1.status_code == 200, res1.text
    slots1 = res1.json()
    assert len(slots1) > 0

    db_session.execute(
        update(DoctorAvailability)
        .where(DoctorAvailability.doctor_id == doctor.id)
        .values(slot_duration=15)
    )
    db_session.commit()

    invalidate_all_slots_cache_for_doctor(doctor.id)

    res2 = await client.get(
        f"/api/v1/doctors/{doctor.id}/slots?date={slot_date.isoformat()}",
        headers=auth,
    )
    assert res2.status_code == 200, res2.text
    slots2 = res2.json()

    assert len(slots2) > len(slots1)
