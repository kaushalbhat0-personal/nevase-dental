"""Appointment API: slot double-book conflict."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.crud_appointment import add_appointment
from app.models.appointment import Appointment, AppointmentStatus, Prescription
from app.models.doctor import Doctor
from app.models.user import UserRole
from tests.factories import (
    BOOKING_ANCHOR_DATE_ISO,
    add_weekly_availability,
    create_doctor_profile,
    create_patient_profile,
    create_user,
    seed_bookable_doctor_and_patient,
)


@pytest.mark.asyncio
async def test_slot_conflict_second_booking_rejected(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )
    doctor_id = str(doctor.id)
    patient_id = str(patient.id)

    login = await client.post(
        "/api/v1/login",
        data={"username": pat_email, "password": pat_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": slot.isoformat(),
    }

    first = await client.post("/api/v1/appointments", json=payload, headers=headers)
    assert first.status_code == 201, first.text

    second = await client.post("/api/v1/appointments", json=payload, headers=headers)
    assert second.status_code == 400
    detail = (second.json().get("detail") or "").lower()
    # Same instant is rejected before exact-slot dedupe (30-minute doctor buffer) in create flow.
    assert "slot already booked" in detail or "30 minutes" in detail or "appointment within" in detail


@pytest.mark.asyncio
async def test_slot_conflict_second_patient_same_slot_rejected(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_a_email = f"pata_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_b_email = f"patb_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient_a, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_a_email,
        patient_password=pat_pw,
    )
    tenant_id = doctor.tenant_id
    assert tenant_id is not None

    pat_b_user = create_user(
        db_session,
        email=pat_b_email,
        password=pat_pw,
        role=UserRole.patient,
    )
    patient_b = create_patient_profile(
        db_session,
        tenant_id=tenant_id,
        user_id=pat_b_user.id,
        created_by=pat_b_user.id,
        name="Other Patient",
    )
    db_session.commit()

    login_a = await client.post(
        "/api/v1/login",
        data={"username": pat_a_email, "password": pat_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    login_b = await client.post(
        "/api/v1/login",
        data={"username": pat_b_email, "password": pat_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    payload_a = {
        "patient_id": str(patient_a.id),
        "doctor_id": str(doctor.id),
        "appointment_time": slot.isoformat(),
    }
    first = await client.post("/api/v1/appointments", json=payload_a, headers=headers_a)
    assert first.status_code == 201, first.text

    payload_b = {
        "patient_id": str(patient_b.id),
        "doctor_id": str(doctor.id),
        "appointment_time": slot.isoformat(),
    }
    second = await client.post("/api/v1/appointments", json=payload_b, headers=headers_b)
    assert second.status_code == 400
    detail = (second.json().get("detail") or "").lower()
    assert "slot already booked" in detail or "30 minutes" in detail or "appointment within" in detail


@pytest.mark.asyncio
async def test_patient_cannot_book_two_doctors_same_instant(
    client: AsyncClient, db_session: Session
) -> None:
    doc_a_email = f"doca_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_b_email = f"docb_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor_a, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_a_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )
    tenant_id = doctor_a.tenant_id
    assert tenant_id is not None

    doc_b_user = create_user(
        db_session,
        email=doc_b_email,
        password=doc_pw,
        role=UserRole.doctor,
        tenant_id=tenant_id,
    )
    doctor_b = create_doctor_profile(
        db_session,
        tenant_id=tenant_id,
        user_id=doc_b_user.id,
        timezone_name="Asia/Kolkata",
    )
    anchor = date.fromisoformat(BOOKING_ANCHOR_DATE_ISO)
    add_weekly_availability(
        db_session,
        doctor_id=doctor_b.id,
        tenant_id=tenant_id,
        day_of_week=anchor.weekday(),
        start=time(10, 0),
        end=time(12, 0),
        slot_duration=30,
    )
    db_session.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": pat_email, "password": pat_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": str(patient.id),
            "doctor_id": str(doctor_a.id),
            "appointment_time": slot.isoformat(),
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": str(patient.id),
            "doctor_id": str(doctor_b.id),
            "appointment_time": slot.isoformat(),
        },
        headers=headers,
    )
    assert second.status_code == 400
    assert "already have an appointment at this time" in (second.json().get("detail") or "").lower()


@pytest.mark.asyncio
async def test_get_appointments_includes_doctor_timezone(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )

    login = await client.post(
        "/api/v1/login",
        data={"username": pat_email, "password": pat_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "patient_id": str(patient.id),
        "doctor_id": str(doctor.id),
        "appointment_time": slot.isoformat(),
    }
    created = await client.post("/api/v1/appointments", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    assert created.json()["patient_id"] == str(patient.id)
    assert created.json()["doctor_id"] == str(doctor.id)
    appt_id = created.json()["id"]

    listed = await client.get("/api/v1/appointments", headers=headers)
    assert listed.status_code == 200
    rows = listed.json()
    match = next((r for r in rows if r["id"] == appt_id), None)
    assert match is not None
    assert match["patient_id"] == str(patient.id)
    assert match["doctor_id"] == str(doctor.id)
    doc_out = match["doctor"]
    assert doc_out["id"] == str(doctor.id)
    assert doc_out["name"] == doctor.name
    assert doc_out["timezone"] == doctor.timezone

    assert created.json()["doctor"]["timezone"] == doctor.timezone


@pytest.mark.asyncio
async def test_get_appointments_type_past_and_upcoming(
    client: AsyncClient, db_session: Session
) -> None:
    """GET ?type=past returns completed, cancelled, or overdue scheduled; ?type=upcoming returns future scheduled."""
    doc_email = f"doc_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )

    login_pat = await client.post(
        "/api/v1/login",
        data={"username": pat_email, "password": pat_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_pat.status_code == 200
    pat_headers = {"Authorization": f"Bearer {login_pat.json()['access_token']}"}
    create_payload = {
        "patient_id": str(patient.id),
        "doctor_id": str(doctor.id),
        "appointment_time": slot.isoformat(),
    }
    created = await client.post(
        "/api/v1/appointments", json=create_payload, headers=pat_headers
    )
    assert created.status_code == 201, created.text
    appt_id = created.json()["id"]

    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": doc_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_headers = {"Authorization": f"Bearer {doc_login.json()['access_token']}"}

    up = await client.get(
        "/api/v1/appointments", params={"type": "upcoming", "limit": 100}, headers=doc_headers
    )
    assert up.status_code == 200
    assert appt_id in {r["id"] for r in up.json()}

    pa = await client.get(
        "/api/v1/appointments", params={"type": "past", "limit": 100}, headers=doc_headers
    )
    assert pa.status_code == 200
    assert appt_id not in {r["id"] for r in pa.json()}

    # Simulate an accidental future-completed appointment and verify temporal grouping.
    future_completed = db_session.get(Appointment, uuid.UUID(appt_id))
    assert future_completed is not None
    future_completed.status = AppointmentStatus.completed
    future_completed.encounter_started_at = datetime.now(timezone.utc) - timedelta(minutes=45)
    future_completed.encounter_completed_at = datetime.now(timezone.utc) - timedelta(minutes=15)
    db_session.commit()

    up2 = await client.get(
        "/api/v1/appointments", params={"type": "upcoming", "limit": 100}, headers=doc_headers
    )
    assert up2.status_code == 200
    assert appt_id in {r["id"] for r in up2.json()}

    past2 = await client.get(
        "/api/v1/appointments", params={"type": "past", "limit": 100}, headers=doc_headers
    )
    assert past2.status_code == 200
    assert appt_id not in {r["id"] for r in past2.json()}


@pytest.mark.asyncio
async def test_mark_completed_fails_if_appointment_is_too_early(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_early_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_early_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, _slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )
    assert doctor.tenant_id is not None

    appointment = add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(minutes=20),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": doctor.tenant_id,
        },
    )
    db_session.commit()

    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": doc_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_headers = {
        "Authorization": f"Bearer {doc_login.json()['access_token']}",
        "X-Tenant-ID": str(doctor.tenant_id),
    }

    response = await client.post(
        f"/api/v1/appointments/{appointment.id}/mark-completed",
        headers={**doc_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 400
    assert "cannot be completed before scheduled time" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_mark_completed_within_grace_window_succeeds(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_grace_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_grace_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, _slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )
    assert doctor.tenant_id is not None

    appointment = add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(minutes=10),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": doctor.tenant_id,
        },
    )
    db_session.commit()

    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": doc_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_headers = {
        "Authorization": f"Bearer {doc_login.json()['access_token']}",
        "X-Tenant-ID": str(doctor.tenant_id),
    }

    response = await client.post(
        f"/api/v1/appointments/{appointment.id}/mark-completed",
        headers={**doc_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_mark_completed_sets_encounter_timestamps_on_completion(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_encounter_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_encounter_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, _slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )
    assert doctor.tenant_id is not None

    appointment = add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(minutes=10),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": doctor.tenant_id,
        },
    )
    db_session.commit()
    appt_id = str(appointment.id)

    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": doc_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_headers = {
        "Authorization": f"Bearer {doc_login.json()['access_token']}",
        "X-Tenant-ID": str(doctor.tenant_id),
    }

    ok = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        headers={**doc_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert ok.status_code == 200, ok.text

    body = ok.json()
    assert body["status"] == "completed"
    assert body["encounter_completed_at"] is not None
    assert body["encounter_started_at"] is not None

    db_session.expire_all()
    appointment_row = db_session.get(Appointment, appointment.id)
    assert appointment_row is not None
    assert appointment_row.encounter_completed_at is not None
    assert appointment_row.encounter_started_at is not None
    assert "+00:00" in body["encounter_started_at"] or body["encounter_started_at"].endswith("Z")
    assert "+00:00" in body["encounter_completed_at"] or body["encounter_completed_at"].endswith("Z")

    started = datetime.fromisoformat(body["encounter_started_at"].replace("Z", "+00:00"))
    completed = datetime.fromisoformat(body["encounter_completed_at"].replace("Z", "+00:00"))
    assert started.tzinfo is not None
    assert completed.tzinfo is not None
    assert completed >= started


@pytest.mark.asyncio
async def test_mark_completed_only_assigned_doctor(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )

    login_pat = await client.post(
        "/api/v1/login",
        data={"username": pat_email, "password": pat_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_pat.status_code == 200
    pat_headers = {"Authorization": f"Bearer {login_pat.json()['access_token']}"}

    appointment = add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(minutes=10),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": doctor.tenant_id,
        },
    )
    db_session.commit()
    appt_id = str(appointment.id)

    deny = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        headers={**pat_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert deny.status_code == 403

    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": doc_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_headers = {
        "Authorization": f"Bearer {doc_login.json()['access_token']}",
        "X-Tenant-ID": str(doctor.tenant_id),
    }
    ok = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        headers={**doc_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "completed"
    assert ok.json()["patient_id"] == str(patient.id)


@pytest.mark.asyncio
async def test_mark_completed_creates_prescriptions_with_patient_ids_and_no_inventory_deduction(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_rx_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_rx_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, _slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )
    assert doctor.tenant_id is not None

    appointment = add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(minutes=10),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": doctor.tenant_id,
        },
    )
    db_session.commit()
    appt_id = str(appointment.id)

    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": doc_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_headers = {
        "Authorization": f"Bearer {doc_login.json()['access_token']}",
        "X-Tenant-ID": str(doctor.tenant_id),
    }

    payload = {
        "clinical_notes": "Follow-up prescription",
        "prescriptions": [
            {
                "notes": "Prescribe only if symptomatic",
                "items": [
                    {
                        "medicine_name": "Paracetamol",
                        "dosage": "500 mg",
                        "frequency": "Thrice a day",
                        "duration": "5 days",
                        "instructions": "After meals",
                    }
                ],
            }
        ],
        "items": [],
    }

    ok = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["status"] == "completed"
    assert body["prescriptions"]
    assert body["prescriptions"][0]["patient_id"] == str(patient.id)
    assert body["prescriptions"][0]["items"][0]["medicine_name"] == "Paracetamol"
    assert body["inventory_usages"] == []

    prescription_rows = db_session.scalars(
        select(Prescription).where(Prescription.appointment_id == appointment.id)
    ).all()
    assert len(prescription_rows) == 1
    assert prescription_rows[0].patient_id == patient.id


@pytest.mark.asyncio
async def test_mark_completed_prescription_payload_is_idempotent_and_not_duplicated(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_rxid_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_rxid_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, _slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )
    assert doctor.tenant_id is not None

    appointment = add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(minutes=10),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": doctor.tenant_id,
        },
    )
    db_session.commit()
    appt_id = str(appointment.id)

    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": doc_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_headers = {
        "Authorization": f"Bearer {doc_login.json()['access_token']}",
        "X-Tenant-ID": str(doctor.tenant_id),
    }

    idempotency_key = str(uuid.uuid4())
    payload = {
        "clinical_notes": "Follow-up prescription",
        "prescriptions": [
            {
                "notes": "Take as directed",
                "items": [
                    {
                        "medicine_name": "Ibuprofen",
                        "dosage": "200 mg",
                        "frequency": "Twice a day",
                        "duration": "3 days",
                        "instructions": "With food",
                    }
                ],
            }
        ],
        "items": [],
    }

    first = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": idempotency_key},
    )
    assert first.status_code == 200, first.text
    assert len(first.json()["prescriptions"]) == 1

    second = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": idempotency_key},
    )
    assert second.status_code == 200, second.text
    assert len(second.json()["prescriptions"]) == 1
    assert second.json()["prescriptions"][0]["items"][0]["medicine_name"] == "Ibuprofen"

    prescription_rows = db_session.scalars(
        select(Prescription).where(Prescription.appointment_id == appointment.id)
    ).all()
    assert len(prescription_rows) == 1


@pytest.mark.asyncio
async def test_mark_completed_generate_bill_consultation_only(
    client: AsyncClient, db_session: Session
) -> None:
    doc_email = f"doc_gb_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_gb_{uuid.uuid4().hex[:8]}@e2e.test"
    doc_pw = "DocPass123!"
    pat_pw = "PatPass123!"

    doctor, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )
    assert doctor.tenant_id is not None

    appointment = add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(minutes=10),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": doctor.tenant_id,
        },
    )
    db_session.commit()
    appt_id = str(appointment.id)

    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": doc_pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_headers = {
        "Authorization": f"Bearer {doc_login.json()['access_token']}",
        "X-Tenant-ID": str(doctor.tenant_id),
    }

    bad = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json={"generate_bill": True, "bill_consultation_amount": "0", "items": []},
        headers=doc_headers,
    )
    assert bad.status_code == 400

    ok = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json={
            "generate_bill": True,
            "bill_consultation_amount": "250.50",
            "completion_notes": "Visit complete",
            "items": [],
        },
        headers={**doc_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "completed"

    bills = await client.get(
        "/api/v1/bills",
        params={"appointment_id": appt_id, "limit": 5},
        headers=doc_headers,
    )
    assert bills.status_code == 200
    rows = bills.json()
    assert len(rows) == 1
    assert float(rows[0]["amount"]) == pytest.approx(250.50)


def test_appointment_tenant_always_matches_doctor_invariant(
    db_session: Session,
) -> None:
    doc_email = f"doc_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_{uuid.uuid4().hex[:8]}@e2e.test"
    doctor, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password="DocPass123!",
        patient_email=pat_email,
        patient_password="PatPass123!",
    )
    tenant_id = doctor.tenant_id
    assert tenant_id is not None
    add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": slot + timedelta(hours=2),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": tenant_id,
        },
    )
    db_session.commit()

    for a in db_session.scalars(select(Appointment)).all():
        if a.patient_id and a.tenant_id and a.doctor_id:
            d = db_session.get(Doctor, a.doctor_id)
            assert d is not None
            assert a.tenant_id == d.tenant_id
