"""Tenant API: hospital creation with admin user and user_tenant mapping."""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.tenant import Tenant, TenantType, UserTenant
from app.models.user import User, UserRole
from app.models.doctor import Doctor
from tests.factories import create_doctor_profile, create_patient_profile, create_tenant, create_user


@pytest.mark.asyncio
async def test_create_hospital_creates_admin_user_and_mapping(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    suffix = uuid.uuid4().hex[:8]
    admin_email_mixed = f"Admin.{suffix}@Hospital.ORG"
    expected_email = admin_email_mixed.lower().strip()
    hospital_name = f"Test Hospital {suffix}"

    resp = await client.post(
        "/api/v1/tenants",
        json={
            "name": hospital_name,
            "type": "organization",
            "admin": {"email": admin_email_mixed, "password": "Hospital9!"},
            "phone": "  +1 555 0100  ",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == hospital_name
    assert data["type"] == "organization"
    assert data["admin_email"] == expected_email
    assert data["phone"] == "+1 555 0100"

    tid = UUID(data["id"])
    tenant = db.get(Tenant, tid)
    assert tenant is not None
    assert tenant.name == hospital_name

    user = db.scalars(select(User).where(User.email == expected_email)).one()
    assert user.role == UserRole.admin
    assert user.force_password_reset is True
    assert user.tenant_id == tid

    ut = db.scalars(
        select(UserTenant).where(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tid,
        )
    ).one()
    assert ut.role == "admin"
    assert ut.is_primary is True


@pytest.mark.asyncio
async def test_create_hospital_duplicate_name_race(
    client: AsyncClient, db_session: Session
) -> None:
    """
    Only one tenant for a case-insensitively duplicate name. Concurrent POSTs
    are serialized by the unique index; this suite uses a shared in-memory
    SQLite connection, so we assert the same rule with two sequential requests
    (true parallel e2e is best validated against PostgreSQL).
    """
    db = db_session
    super_email = f"sa_race_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    suffix = uuid.uuid4().hex[:8]
    hospital_name = f"Race Hospital {suffix}"
    body_a = {
        "name": hospital_name,
        "type": "organization",
        "admin": {"email": f"admin_race_a_{suffix}@example.com", "password": "Hospital9!"},
    }
    body_b = {
        "name": hospital_name,
        "type": "organization",
        "admin": {"email": f"admin_race_b_{suffix}@example.com", "password": "Hospital9!"},
    }
    auth = {"Authorization": f"Bearer {token}"}

    r_ok = await client.post("/api/v1/tenants", json=body_a, headers=auth)
    assert r_ok.status_code == 201
    r_dup = await client.post("/api/v1/tenants", json=body_b, headers=auth)
    assert r_dup.status_code == 400
    assert "name" in r_dup.json()["detail"].lower() or "tenant" in r_dup.json()["detail"].lower()

    count = db.scalar(
        select(func.count(Tenant.id)).where(func.lower(Tenant.name) == hospital_name.lower())
    )
    assert count == 1


@pytest.mark.asyncio
async def test_create_hospital_idempotency_key_returns_same_tenant(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_idem_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    suffix = uuid.uuid4().hex[:8]
    hospital_name = f"Idem Hospital {suffix}"
    admin_email = f"admin_idem_{suffix}@example.com"
    body = {
        "name": hospital_name,
        "type": "organization",
        "admin": {"email": admin_email, "password": "Hospital9!"},
    }
    key = f"idem-{suffix}"
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": key}

    r1 = await client.post("/api/v1/tenants", json=body, headers=headers)
    r2 = await client.post("/api/v1/tenants", json=body, headers=headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    assert r1.json()["admin_email"] == r2.json()["admin_email"]


@pytest.mark.asyncio
async def test_create_org_minimal_clinic_no_admin(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_min_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    suffix = uuid.uuid4().hex[:8]
    clinic_name = f"Minimal Clinic {suffix}"
    resp = await client.post(
        "/api/v1/tenants",
        json={"name": clinic_name, "type": "organization"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == clinic_name
    assert data["type"] == "organization"
    assert data.get("admin_email") is None
    tid = UUID(data["id"])
    tenant = db.get(Tenant, tid)
    assert tenant is not None


@pytest.mark.asyncio
async def test_super_admin_list_includes_clinics(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_list_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    suffix = uuid.uuid4().hex[:8]
    create_tenant(db, name=f"List Clinic {suffix}", tenant_type=TenantType.organization)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/tenants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    types = {row["type"] for row in resp.json()}
    assert "organization" in types


@pytest.mark.asyncio
async def test_get_tenant_by_id_super_admin(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_get_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    suffix = uuid.uuid4().hex[:8]
    t = create_tenant(db, name=f"Detail Clinic {suffix}", tenant_type=TenantType.organization)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    resp = await client.get(
        f"/api/v1/tenants/{t.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(t.id)
    assert resp.json()["name"] == t.name


@pytest.mark.asyncio
async def test_super_admin_deactivate_tenant_soft_delete(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_del_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    t = create_tenant(db, name=f"Deactivate Me {uuid.uuid4().hex[:8]}")
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]

    r_del = await client.delete(
        f"/api/v1/tenants/{t.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_del.status_code == 204, r_del.text

    db.expire_all()
    row = db.get(Tenant, t.id)
    assert row is not None and row.is_deleted is True

    r_list = await client.get(
        "/api/v1/tenants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_list.status_code == 200
    ids = {row["id"] for row in r_list.json()}
    assert str(t.id) not in ids

    r_inc = await client.get(
        "/api/v1/tenants",
        params={"include_deactivated": "true"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_inc.status_code == 200
    found = next((x for x in r_inc.json() if x["id"] == str(t.id)), None)
    assert found is not None
    assert found.get("is_deleted") is True

    r_re = await client.post(
        f"/api/v1/tenants/{t.id}/reactivate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_re.status_code == 200, r_re.text
    assert r_re.json()["is_deleted"] is False
    db.expire_all()
    row2 = db.get(Tenant, t.id)
    assert row2 is not None and row2.is_deleted is False


@pytest.mark.asyncio
async def test_deactivate_tenant_forbidden_for_org_admin(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    t = create_tenant(db, name=f"Protected {uuid.uuid4().hex[:8]}")
    admin = create_user(
        db,
        email=f"adm_{uuid.uuid4().hex[:8]}@example.com",
        password="AdminPass9!",
        role=UserRole.admin,
        tenant_id=t.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": admin.email, "password": "AdminPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    r = await client.delete(
        f"/api/v1/tenants/{t.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_scoped_api_rejects_deactivated_tenant(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_scope_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    t = create_tenant(db, name=f"Offboarded {uuid.uuid4().hex[:8]}")
    t.is_deleted = True
    db.add(t)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    r = await client.get(
        "/api/v1/doctors",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(t.id),
        },
    )
    assert r.status_code == 400
    assert "deactivated" in r.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_super_admin_post_users_creates_tenant_admin(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_users_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    org = create_tenant(db, name=f"Org {uuid.uuid4().hex[:6]}")
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    new_admin_email = f"adm_{uuid.uuid4().hex[:8]}@Example.COM"
    r = await client.post(
        "/api/v1/users",
        json={
            "email": new_admin_email,
            "password": "AdminPass9!",
            "role": "admin",
            "tenant_id": str(org.id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == new_admin_email.lower().strip()
    u = db_session.get(User, UUID(body["id"]))
    assert u is not None
    assert u.tenant_id == org.id
    assert u.role == UserRole.admin


@pytest.mark.asyncio
async def test_upgrade_to_organization_preserves_data_and_enables_admin(
    client: AsyncClient, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """Individual-in-place upgrade: same ids, data retained, admin + doctor effective roles."""
    db = db_session
    suffix = uuid.uuid4().hex[:8]
    tenant = create_tenant(
        db, name=f"Solo Practice {suffix}", tenant_type=TenantType.individual
    )
    doc_user = create_user(
        db,
        email=f"solo_{suffix}@example.com",
        password="SoloDoc9!!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
        is_owner=True,
    )
    doc = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)
    pat_user = create_user(
        db,
        email=f"pat_{suffix}@example.com",
        password="PatPass9!!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db,
        tenant_id=tenant.id,
        user_id=pat_user.id,
        created_by=doc_user.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": f"solo_{suffix}@example.com", "password": "SoloDoc9!!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    pre_tid = str(tenant.id)
    pre_did = str(doc.id)
    pre_pid = str(patient.id)

    with caplog.at_level(logging.INFO, logger="app.services.tenant_service"):
        r = await client.post(
            "/api/v1/tenants/upgrade-to-organization",
            json={"clinic_name": f"Clinic Org {suffix}"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tenant"]["type"] == "organization"
    assert data["tenant"]["name"] == f"Clinic Org {suffix}"
    assert data["tenant"]["id"] == pre_tid
    assert set(data["roles"]) == {"admin", "doctor"}
    assert "[UPGRADE_FLOW]" in caplog.text
    assert f"user_id={doc_user.id}" in caplog.text
    assert f"tenant_id={tenant.id}" in caplog.text

    db.expire_all()
    t2 = db.get(Tenant, tenant.id)
    assert t2 is not None and t2.type == TenantType.organization.value
    u2 = db.get(User, doc_user.id)
    assert u2 is not None and u2.role == UserRole.admin and u2.is_owner is True
    ut = db.scalars(
        select(UserTenant).where(
            UserTenant.user_id == doc_user.id,
            UserTenant.tenant_id == tenant.id,
        )
    ).one()
    assert ut.role == "admin"
    p2 = db.get(Patient, patient.id)
    assert p2 is not None and p2.tenant_id is None
    d2 = db.get(Doctor, doc.id)
    assert d2 is not None
    assert str(d2.id) == pre_did and d2.tenant_id == tenant.id
    assert str(p2.id) == pre_pid

    admin_headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": pre_tid,
    }
    r_docs = await client.get("/api/v1/doctors", headers=admin_headers)
    assert r_docs.status_code == 200, r_docs.text


@pytest.mark.asyncio
async def test_create_tenant_rejects_legacy_type_value(client: AsyncClient, db_session: Session) -> None:
    db = db_session
    super_email = f"sa_badtype_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    db.commit()
    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    r = await client.post(
        "/api/v1/tenants",
        json={
            "name": f"Legacy {uuid.uuid4().hex[:8]}",
            "type": "hospital",
            "admin": {"email": f"adm_{uuid.uuid4().hex[:8]}@example.com", "password": "Hospital9!"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_tenant_rejects_individual_type(client: AsyncClient, db_session: Session) -> None:
    db = db_session
    super_email = f"sa_ind_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    db.commit()
    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    r = await client.post(
        "/api/v1/tenants",
        json={
            "name": f"Solo {uuid.uuid4().hex[:8]}",
            "type": "individual",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert "individual" in r.json()["detail"].lower()
