"""Doctor patient visibility is derived from appointments (cohort), not from shared tenant alone."""

from __future__ import annotations

import uuid
from datetime import date, time
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.data_scope import resolve_data_scope
from app.crud import crud_doctor, crud_patient
from app.models.tenant import TenantType
from app.models.user import UserRole
from app.schemas.appointment import AppointmentCreate
from app.services import appointment_service, patient_service
from tests.factories import (
    add_weekly_availability,
    booking_slot_datetime_utc,
    create_doctor_profile,
    create_tenant,
    create_user,
)

_BOOKING_DAY_WEEKDAY = date(2035, 6, 15).weekday()


def _data_scope(db: Session, user, header: str = "doctor"):
    linked = crud_doctor.get_doctor_by_user_id(db, user.id)
    return resolve_data_scope(header, current_user=user, linked_doctor=linked)


def test_patient_books_appointment_appears_in_that_doctor_list(
    db_session: Session,
) -> None:
    """Appointment links patient to doctor; doctor did not create the patient record."""
    tenant = create_tenant(db_session, tenant_type=TenantType.organization)
    doc_user = create_user(
        db_session,
        email=f"doclink_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    doc = create_doctor_profile(
        db_session, tenant_id=tenant.id, user_id=doc_user.id, timezone_name="Asia/Kolkata"
    )
    add_weekly_availability(
        db_session,
        doctor_id=doc.id,
        tenant_id=tenant.id,
        day_of_week=_BOOKING_DAY_WEEKDAY,
        start=time(10, 0),
        end=time(12, 0),
        slot_duration=30,
    )
    pat_user = create_user(
        db_session,
        email=f"patlink_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    db_session.commit()
    # No Patient row until booking ensures one

    slot = booking_slot_datetime_utc()
    appt_in = AppointmentCreate(
        patient_id=UUID(int=0),  # Replaced by server for patient-role callers
        doctor_id=doc.id,
        appointment_time=slot,
    )
    appt, replay = appointment_service.create_appointment(
        db_session,
        appt_in,
        current_user=pat_user,
        tenant_id=None,
        idempotency_key=None,
    )
    assert replay is False
    assert appt.patient_id is not None
    assert appt.doctor_id == doc.id

    assert pat_user.id != doc_user.id
    out = patient_service.get_patients(
        db_session,
        doc_user,
        tenant_id=tenant.id,
        limit=50,
        data_scope=_data_scope(db_session, doc_user),
    )
    assert {p.id for p in out} == {appt.patient_id}

    p = crud_patient.get_patient(db_session, appt.patient_id)
    assert p is not None
    assert p.tenant_id is None
    assert appt.tenant_id == tenant.id


def test_two_doctors_same_tenant_patient_list_isolated(
    db_session: Session,
) -> None:
    tenant = create_tenant(db_session, tenant_type=TenantType.organization)
    doc_a_user = create_user(
        db_session,
        email=f"da_{uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    doc_b_user = create_user(
        db_session,
        email=f"db_{uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    doc_a = create_doctor_profile(
        db_session, tenant_id=tenant.id, user_id=doc_a_user.id, timezone_name="Asia/Kolkata"
    )
    doc_b = create_doctor_profile(
        db_session, tenant_id=tenant.id, user_id=doc_b_user.id, timezone_name="Asia/Kolkata"
    )
    for d in (doc_a, doc_b):
        add_weekly_availability(
            db_session,
            doctor_id=d.id,
            tenant_id=tenant.id,
            day_of_week=_BOOKING_DAY_WEEKDAY,
            start=time(10, 0),
            end=time(12, 0),
            slot_duration=30,
        )
    pat_user = create_user(
        db_session,
        email=f"pat2_{uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    db_session.commit()

    slot = booking_slot_datetime_utc()
    appt_in = AppointmentCreate(
        patient_id=UUID(int=0),
        doctor_id=doc_a.id,
        appointment_time=slot,
    )
    appt, _ = appointment_service.create_appointment(
        db_session, appt_in, pat_user, None, idempotency_key=None
    )

    a_list = {
        p.id
        for p in patient_service.get_patients(
            db_session,
            doc_a_user,
            tenant_id=tenant.id,
            limit=50,
            data_scope=_data_scope(db_session, doc_a_user),
        )
    }
    b_list = {
        p.id
        for p in patient_service.get_patients(
            db_session,
            doc_b_user,
            tenant_id=tenant.id,
            limit=50,
            data_scope=_data_scope(db_session, doc_b_user),
        )
    }
    assert appt.patient_id in a_list
    assert appt.patient_id not in b_list
