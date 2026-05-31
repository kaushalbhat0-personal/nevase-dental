"""Tenant admin listing and doctor appointment cohort for patients."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.data_scope import ResolvedDataScope, resolve_data_scope
from app.crud import crud_doctor
from app.crud.crud_appointment import add_appointment
from app.models.appointment import AppointmentStatus
from app.models.patient import Patient
from app.models.tenant import TenantType
from app.models.user import UserRole
from app.services import patient_service
from app.services.exceptions import ForbiddenError
from tests.factories import create_doctor_profile, create_patient_profile, create_tenant, create_user


PATIENTS_URL = "/api/v1/patients"


def _scoped_headers(token: str, tenant_id, *, data_scope: str = "tenant") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Data-Scope": data_scope,
    }


def _data_scope_tenant(db: Session, user) -> ResolvedDataScope:
    linked = crud_doctor.get_doctor_by_user_id(db, user.id)
    return resolve_data_scope("tenant", current_user=user, linked_doctor=linked)


def _data_scope_doctor(db: Session, user) -> ResolvedDataScope:
    linked = crud_doctor.get_doctor_by_user_id(db, user.id)
    return resolve_data_scope("doctor", current_user=user, linked_doctor=linked)


def test_admin_sees_patient_after_booking_in_tenant_scope(
    db_session: Session,
) -> None:
    """Tenant admin lists a patient with ``tenant_id`` NULL once they have an appointment in that org."""
    tenant = create_tenant(db_session, tenant_type=TenantType.organization)
    admin = create_user(
        db_session,
        email=f"adm_tnull_{uuid.uuid4().hex[:8]}@test.local",
        password="AdmPass123!",
        role=UserRole.admin,
        tenant_id=tenant.id,
    )
    doc_user = create_user(
        db_session,
        email=f"doc_tnull_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    doc = create_doctor_profile(
        db_session, tenant_id=tenant.id, user_id=doc_user.id, timezone_name="UTC"
    )
    pat_user = create_user(
        db_session,
        email=f"pat_tnull_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p = create_patient_profile(
        db_session,
        tenant_id=tenant.id,
        user_id=pat_user.id,
        created_by=doc_user.id,
    )
    db_session.commit()
    db_session.execute(
        update(Patient).where(Patient.id == p.id).values(tenant_id=None)
    )
    db_session.commit()

    add_appointment(
        db_session,
        {
            "patient_id": p.id,
            "doctor_id": doc.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(hours=2),
            "status": AppointmentStatus.scheduled,
            "created_by": doc_user.id,
            "tenant_id": tenant.id,
        },
    )
    db_session.commit()

    admin_tenant_list = patient_service.get_patients(
        db_session,
        admin,
        tenant_id=tenant.id,
        limit=100,
        data_scope=_data_scope_tenant(db_session, admin),
    )
    assert p.id in {x.id for x in admin_tenant_list}
    before_row = next(x for x in admin_tenant_list if x.id == p.id)
    assert before_row.doctor_name == doc.name

    doc_listed_before = {
        x.id
        for x in patient_service.get_patients(
            db_session,
            doc_user,
            tenant_id=tenant.id,
            limit=100,
            data_scope=_data_scope_doctor(db_session, doc_user),
        )
    }
    assert p.id in doc_listed_before

    listed = {
        x.id
        for x in patient_service.get_patients(
            db_session,
            admin,
            tenant_id=tenant.id,
            limit=100,
            data_scope=_data_scope_tenant(db_session, admin),
        )
    }
    assert p.id in listed

    doc_listed = {
        x.id
        for x in patient_service.get_patients(
            db_session,
            doc_user,
            tenant_id=tenant.id,
            limit=100,
            data_scope=_data_scope_doctor(db_session, doc_user),
        )
    }
    assert p.id in doc_listed

    other = create_user(
        db_session,
        email=f"oth_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    _ = create_doctor_profile(
        db_session, tenant_id=tenant.id, user_id=other.id, timezone_name="UTC"
    )
    db_session.commit()
    peer = {
        x.id
        for x in patient_service.get_patients(
            db_session,
            other,
            tenant_id=tenant.id,
            limit=100,
            data_scope=_data_scope_doctor(db_session, other),
        )
    }
    assert p.id not in peer


def test_admin_sees_patient_with_foreign_tenant_id_when_appointment_in_tenant(
    db_session: Session,
) -> None:
    """Cross-clinic: admin lists by appointment tenant even when patient.tenant_id is another org."""
    tenant_home = create_tenant(db_session, tenant_type=TenantType.organization)
    tenant_visit = create_tenant(db_session, tenant_type=TenantType.organization)
    admin = create_user(
        db_session,
        email=f"adm_xc_{uuid.uuid4().hex[:8]}@test.local",
        password="AdmPass123!",
        role=UserRole.admin,
        tenant_id=tenant_visit.id,
    )
    doc_user = create_user(
        db_session,
        email=f"doc_xc_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant_visit.id,
    )
    doc = create_doctor_profile(
        db_session, tenant_id=tenant_visit.id, user_id=doc_user.id, timezone_name="UTC"
    )
    pat_user = create_user(
        db_session,
        email=f"pat_xc_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p = create_patient_profile(
        db_session,
        tenant_id=tenant_home.id,
        user_id=pat_user.id,
        created_by=doc_user.id,
    )
    db_session.commit()
    add_appointment(
        db_session,
        {
            "patient_id": p.id,
            "doctor_id": doc.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(hours=2),
            "status": AppointmentStatus.scheduled,
            "created_by": doc_user.id,
            "tenant_id": tenant_visit.id,
        },
    )
    db_session.commit()
    out = patient_service.get_patients(
        db_session,
        admin,
        tenant_id=tenant_visit.id,
        limit=100,
        data_scope=_data_scope_tenant(db_session, admin),
    )
    assert p.id in {x.id for x in out}
    row = next(x for x in out if x.id == p.id)
    assert row.doctor_name == doc.name


def test_doctor_read_requires_appointment_not_created_by(
    db_session: Session,
) -> None:
    """Doctor without an appointment to the patient is denied; creator-only is not enough."""
    tenant = create_tenant(db_session, tenant_type=TenantType.organization)
    doc_a = create_user(
        db_session,
        email=f"dca_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    _ = create_doctor_profile(
        db_session, tenant_id=tenant.id, user_id=doc_a.id, timezone_name="UTC"
    )
    doc_b = create_user(
        db_session,
        email=f"dcb_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    d_b = create_doctor_profile(
        db_session, tenant_id=tenant.id, user_id=doc_b.id, timezone_name="UTC"
    )
    pat_user = create_user(
        db_session,
        email=f"pu_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db_session,
        tenant_id=tenant.id,
        user_id=pat_user.id,
        created_by=doc_a.id,
    )
    add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": d_b.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(hours=3),
            "status": AppointmentStatus.scheduled,
            "created_by": pat_user.id,
            "tenant_id": tenant.id,
        },
    )
    db_session.commit()

    with pytest.raises(ForbiddenError, match="Not allowed to modify this patient"):
        patient_service.authorize_patient_read(
            db_session,
            patient,
            doc_a,
            tenant_id=tenant.id,
        )
    patient_service.authorize_patient_read(
        db_session,
        patient,
        doc_b,
        tenant_id=tenant.id,
    )


@pytest.mark.asyncio
async def test_admin_sees_all_patients_in_tenant(
    client: AsyncClient, db_session: Session
) -> None:
    """GET /patients with tenant scope lists patients with a non-deleted appointment in that org."""
    t1 = create_tenant(db_session, tenant_type=TenantType.organization)
    t_other = create_tenant(db_session, tenant_type=TenantType.organization)

    admin = create_user(
        db_session,
        email=f"adm_all_{uuid.uuid4().hex[:8]}@test.local",
        password="AdmPass123!",
        role=UserRole.admin,
        tenant_id=t1.id,
    )
    d1_user = create_user(
        db_session,
        email=f"d1_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=t1.id,
    )
    d2_user = create_user(
        db_session,
        email=f"d2_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=t1.id,
    )
    d1 = create_doctor_profile(
        db_session, tenant_id=t1.id, user_id=d1_user.id, timezone_name="UTC"
    )
    d2 = create_doctor_profile(
        db_session, tenant_id=t1.id, user_id=d2_user.id, timezone_name="UTC"
    )

    p1_user = create_user(
        db_session,
        email=f"p1_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p2_user = create_user(
        db_session,
        email=f"p2_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p1 = create_patient_profile(
        db_session,
        tenant_id=t1.id,
        user_id=p1_user.id,
        created_by=d1_user.id,
        name="Patient One",
    )
    p2 = create_patient_profile(
        db_session,
        tenant_id=t1.id,
        user_id=p2_user.id,
        created_by=d2_user.id,
        name="Patient Two",
    )
    db_session.commit()

    other_pat_user = create_user(
        db_session,
        email=f"p_other_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p_other = create_patient_profile(
        db_session,
        tenant_id=t_other.id,
        user_id=other_pat_user.id,
        created_by=other_pat_user.id,
        name="Other Tenant Patient",
    )
    db_session.commit()

    t0 = datetime.now(timezone.utc) + timedelta(hours=1)
    add_appointment(
        db_session,
        {
            "patient_id": p1.id,
            "doctor_id": d1.id,
            "appointment_time": t0,
            "status": AppointmentStatus.scheduled,
            "created_by": d1_user.id,
            "tenant_id": t1.id,
        },
    )
    add_appointment(
        db_session,
        {
            "patient_id": p2.id,
            "doctor_id": d2.id,
            "appointment_time": t0 + timedelta(hours=1),
            "status": AppointmentStatus.scheduled,
            "created_by": d2_user.id,
            "tenant_id": t1.id,
        },
    )
    db_session.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": admin.email, "password": "AdmPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    resp = await client.get(
        PATIENTS_URL,
        params={"limit": 100},
        headers=_scoped_headers(token, t1.id, data_scope="tenant"),
    )
    assert resp.status_code == 200, resp.text
    ids = {row["id"] for row in resp.json()}
    assert str(p1.id) in ids
    assert str(p2.id) in ids
    assert str(p_other.id) not in ids


@pytest.mark.asyncio
async def test_doctor_sees_only_own_patients(
    client: AsyncClient, db_session: Session
) -> None:
    """Practice-scoped listing includes only patients with an appointment to the logged-in doctor."""
    t1 = create_tenant(db_session, tenant_type=TenantType.organization)

    d1_user = create_user(
        db_session,
        email=f"doc1_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=t1.id,
    )
    d2_user = create_user(
        db_session,
        email=f"doc2_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=t1.id,
    )
    d1 = create_doctor_profile(
        db_session, tenant_id=t1.id, user_id=d1_user.id, timezone_name="UTC"
    )
    d2 = create_doctor_profile(
        db_session, tenant_id=t1.id, user_id=d2_user.id, timezone_name="UTC"
    )

    p1_user = create_user(
        db_session,
        email=f"dp1_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p2_user = create_user(
        db_session,
        email=f"dp2_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p1 = create_patient_profile(
        db_session,
        tenant_id=None,
        user_id=p1_user.id,
        created_by=d1_user.id,
        name="Cohort P1",
    )
    p2 = create_patient_profile(
        db_session,
        tenant_id=None,
        user_id=p2_user.id,
        created_by=d2_user.id,
        name="Cohort P2",
    )
    db_session.commit()

    t0 = datetime.now(timezone.utc) + timedelta(hours=2)
    add_appointment(
        db_session,
        {
            "patient_id": p1.id,
            "doctor_id": d1.id,
            "appointment_time": t0,
            "status": AppointmentStatus.scheduled,
            "created_by": d1_user.id,
            "tenant_id": t1.id,
        },
    )
    add_appointment(
        db_session,
        {
            "patient_id": p2.id,
            "doctor_id": d2.id,
            "appointment_time": t0 + timedelta(hours=1),
            "status": AppointmentStatus.scheduled,
            "created_by": d2_user.id,
            "tenant_id": t1.id,
        },
    )
    db_session.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": d1_user.email, "password": "DocPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    resp = await client.get(
        PATIENTS_URL,
        params={"limit": 100},
        headers=_scoped_headers(token, t1.id, data_scope="doctor"),
    )
    assert resp.status_code == 200, resp.text
    ids = {row["id"] for row in resp.json()}
    assert str(p1.id) in ids
    assert str(p2.id) not in ids


def test_patient_visible_after_booking(db_session: Session) -> None:
    """After an appointment exists, the doctor can list that patient in practice scope."""
    tenant = create_tenant(db_session, tenant_type=TenantType.organization)
    doc_user = create_user(
        db_session,
        email=f"doc_pb_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    doc = create_doctor_profile(
        db_session, tenant_id=tenant.id, user_id=doc_user.id, timezone_name="UTC"
    )
    pat_user = create_user(
        db_session,
        email=f"pat_pb_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p = create_patient_profile(
        db_session,
        tenant_id=tenant.id,
        user_id=pat_user.id,
        created_by=doc_user.id,
    )
    db_session.commit()
    add_appointment(
        db_session,
        {
            "patient_id": p.id,
            "doctor_id": doc.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(hours=4),
            "status": AppointmentStatus.scheduled,
            "created_by": doc_user.id,
            "tenant_id": tenant.id,
        },
    )
    db_session.commit()

    out = patient_service.get_patients(
        db_session,
        doc_user,
        tenant_id=tenant.id,
        limit=100,
        data_scope=_data_scope_doctor(db_session, doc_user),
    )
    assert p.id in {x.id for x in out}


def test_admin_sees_all_patients_with_appointments_in_tenant(db_session: Session) -> None:
    """Admin tenant scope lists patients that have at least one appointment in that org."""
    t1 = create_tenant(db_session, tenant_type=TenantType.organization)
    admin = create_user(
        db_session,
        email=f"adm_sa_{uuid.uuid4().hex[:8]}@test.local",
        password="AdmPass123!",
        role=UserRole.admin,
        tenant_id=t1.id,
    )
    d1 = create_user(
        db_session,
        email=f"d_sa1_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=t1.id,
    )
    d2 = create_user(
        db_session,
        email=f"d_sa2_{uuid.uuid4().hex[:8]}@test.local",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=t1.id,
    )
    doc1 = create_doctor_profile(
        db_session, tenant_id=t1.id, user_id=d1.id, timezone_name="UTC"
    )
    doc2 = create_doctor_profile(
        db_session, tenant_id=t1.id, user_id=d2.id, timezone_name="UTC"
    )
    p1u = create_user(
        db_session,
        email=f"p_sa1_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p2u = create_user(
        db_session,
        email=f"p_sa2_{uuid.uuid4().hex[:8]}@test.local",
        password="PatPass123!",
        role=UserRole.patient,
    )
    p1 = create_patient_profile(
        db_session,
        tenant_id=t1.id,
        user_id=p1u.id,
        created_by=d1.id,
        name="A",
    )
    p2 = create_patient_profile(
        db_session,
        tenant_id=t1.id,
        user_id=p2u.id,
        created_by=d2.id,
        name="B",
    )
    db_session.commit()

    t0 = datetime.now(timezone.utc) + timedelta(hours=5)
    add_appointment(
        db_session,
        {
            "patient_id": p1.id,
            "doctor_id": doc1.id,
            "appointment_time": t0,
            "status": AppointmentStatus.scheduled,
            "created_by": d1.id,
            "tenant_id": t1.id,
        },
    )
    add_appointment(
        db_session,
        {
            "patient_id": p2.id,
            "doctor_id": doc2.id,
            "appointment_time": t0 + timedelta(hours=1),
            "status": AppointmentStatus.scheduled,
            "created_by": d2.id,
            "tenant_id": t1.id,
        },
    )
    db_session.commit()

    listed = patient_service.get_patients(
        db_session,
        admin,
        tenant_id=t1.id,
        limit=100,
        data_scope=_data_scope_tenant(db_session, admin),
    )
    assert {p1.id, p2.id} <= {x.id for x in listed}
