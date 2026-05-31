"""PATCH /users/{id}/role — super admin promotes a tenant doctor to admin."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from tests.factories import create_doctor_profile, create_tenant, create_user


@pytest.mark.asyncio
async def test_super_admin_promotes_doctor_to_admin(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_promo_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    org = create_tenant(db, name=f"PromoOrg {uuid.uuid4().hex[:6]}")
    doc_user = create_user(
        db,
        email=f"docp_{uuid.uuid4().hex[:8]}@example.com",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=org.id,
    )
    create_doctor_profile(db, tenant_id=org.id, user_id=doc_user.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    r = await client.patch(
        f"/api/v1/users/{doc_user.id}/role",
        json={"role": "admin"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(org.id),
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "admin"
    db.expire_all()
    reloaded = db.get(User, doc_user.id)
    assert reloaded is not None
    assert reloaded.role == UserRole.admin
    assert reloaded.is_owner is True


@pytest.mark.asyncio
async def test_cannot_promote_doctor_from_other_tenant(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_x_{uuid.uuid4().hex[:8]}@example.com"
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
        email=f"docb_{uuid.uuid4().hex[:8]}@example.com",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=org_b.id,
    )
    create_doctor_profile(db, tenant_id=org_b.id, user_id=doc_user.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]

    r = await client.patch(
        f"/api/v1/users/{doc_user.id}/role",
        json={"role": "admin"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(org_a.id),
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_post_users_create_admin_still_works(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_new_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    org = create_tenant(db, name=f"NewAdm {uuid.uuid4().hex[:6]}")
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    new_email = f"adm_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/users",
        json={
            "email": new_email,
            "password": "AdminPass9!",
            "role": "admin",
            "tenant_id": str(org.id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == new_email.lower()
    assert r.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_create_org_admin_demotes_existing_admin(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_swap_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=super_email,
        password="SuperAdmin9!",
        role=UserRole.super_admin,
    )
    org = create_tenant(db, name=f"Swap {uuid.uuid4().hex[:6]}")
    old = create_user(
        db,
        email=f"old_{uuid.uuid4().hex[:8]}@example.com",
        password="Old9Pass!!",
        role=UserRole.admin,
        tenant_id=org.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": super_email, "password": "SuperAdmin9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    new_email = f"new_adm_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/users",
        json={
            "email": new_email,
            "password": "AdminPass9!",
            "role": "admin",
            "tenant_id": str(org.id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    db.expire_all()
    reloaded_old = db.get(User, old.id)
    assert reloaded_old is not None
    assert reloaded_old.role == UserRole.doctor
    n = db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.tenant_id == org.id, User.role == UserRole.admin)
    )
    assert n == 1
