"""PATCH /doctors/{id}/promote — update existing user to admin (no new user row)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from tests.factories import create_doctor_profile, create_tenant, create_user

pytestmark = pytest.mark.asyncio


async def test_super_admin_promotes_doctor_via_doctor_id(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_docpr_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    org = create_tenant(db, name=f"DocPromo {uuid.uuid4().hex[:6]}")
    doc_user = create_user(
        db,
        email=f"doc_pr_{uuid.uuid4().hex[:8]}@example.com",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=org.id,
    )
    doctor = create_doctor_profile(db, tenant_id=org.id, user_id=doc_user.id)
    db.commit()

    user_count_before = db.scalar(select(func.count()).select_from(User))

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    r = await client.patch(
        f"/api/v1/doctors/{doctor.id}/promote",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(org.id),
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == str(doc_user.id)
    assert body["role"] == "admin"
    user_count_after = db.scalar(select(func.count()).select_from(User))
    assert user_count_after == user_count_before
    db.expire_all()
    reloaded = db.get(User, doc_user.id)
    assert reloaded is not None
    assert reloaded.role == UserRole.admin
    assert reloaded.is_owner is True


async def test_org_admin_can_promote_doctor(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    org = create_tenant(db, name=f"AdmPr {uuid.uuid4().hex[:6]}")
    admin_email = f"adm_pr_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=admin_email,
        password="Adm9Pass!!",
        role=UserRole.admin,
        tenant_id=org.id,
    )
    doc_user = create_user(
        db,
        email=f"doc_ad_{uuid.uuid4().hex[:8]}@example.com",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=org.id,
    )
    doctor = create_doctor_profile(db, tenant_id=org.id, user_id=doc_user.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": admin_email, "password": "Adm9Pass!!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    r = await client.patch(
        f"/api/v1/doctors/{doctor.id}/promote",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(org.id),
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "admin"


async def test_non_privileged_doctor_cannot_promote(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    org = create_tenant(db, name=f"NoPriv {uuid.uuid4().hex[:6]}")
    d1 = create_user(
        db,
        email=f"dr1_{uuid.uuid4().hex[:8]}@example.com",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=org.id,
    )
    d2 = create_user(
        db,
        email=f"dr2_{uuid.uuid4().hex[:8]}@example.com",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=org.id,
    )
    create_doctor_profile(db, tenant_id=org.id, user_id=d1.id)
    doc2 = create_doctor_profile(db, tenant_id=org.id, user_id=d2.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": d1.email, "password": "DocPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    r = await client.patch(
        f"/api/v1/doctors/{doc2.id}/promote",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(org.id),
        },
    )
    assert r.status_code == 403


async def test_promote_fails_for_doctor_in_other_tenant(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_xd_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    org_a = create_tenant(db, name="OrgA")
    org_b = create_tenant(db, name="OrgB")
    doc_user = create_user(
        db,
        email=f"doc_b_{uuid.uuid4().hex[:8]}@example.com",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=org_b.id,
    )
    doctor = create_doctor_profile(db, tenant_id=org_b.id, user_id=doc_user.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]

    r = await client.patch(
        f"/api/v1/doctors/{doctor.id}/promote",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(org_a.id),
        },
    )
    assert r.status_code == 404


async def test_promote_demotes_previous_admin(
    client: AsyncClient, db_session: Session
) -> None:
    """Only one org admin: promoting doctor B demotes the prior admin to doctor."""
    db = db_session
    org = create_tenant(db, name=f"OneAdm {uuid.uuid4().hex[:6]}")
    old_admin = create_user(
        db,
        email=f"old_adm_{uuid.uuid4().hex[:8]}@example.com",
        password="Adm9Pass!!",
        role=UserRole.admin,
        tenant_id=org.id,
    )
    doc_b = create_user(
        db,
        email=f"doc_b_{uuid.uuid4().hex[:8]}@example.com",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=org.id,
    )
    _ = create_doctor_profile(db, tenant_id=org.id, user_id=old_admin.id)
    doctor_b = create_doctor_profile(db, tenant_id=org.id, user_id=doc_b.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": old_admin.email, "password": "Adm9Pass!!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    r = await client.patch(
        f"/api/v1/doctors/{doctor_b.id}/promote",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(org.id),
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["id"] == str(doc_b.id)
    assert r.json()["role"] == "admin"

    db.expire_all()
    reloaded_old = db.get(User, old_admin.id)
    reloaded_b = db.get(User, doc_b.id)
    assert reloaded_old is not None
    assert reloaded_b is not None
    assert reloaded_old.role == UserRole.doctor
    assert reloaded_b.role == UserRole.admin
    assert reloaded_b.is_owner is True
    assert reloaded_old.is_owner is False

    admin_count = db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.tenant_id == org.id,
            User.role == UserRole.admin,
        )
    )
    assert admin_count == 1
