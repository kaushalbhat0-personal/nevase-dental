"""Auth API: login force_password_reset flag and reset-password endpoint."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.tenant import TenantType
from app.models.user import User, UserRole
from tests.factories import create_tenant, create_user


@pytest.mark.asyncio
async def test_login_includes_force_password_reset_false(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name="t1")
    email = f"user_{uuid.uuid4().hex[:10]}@example.com"
    create_user(
        db,
        email=email,
        password="correct-horse-battery",
        role=UserRole.admin,
        tenant_id=tenant.id,
        force_password_reset=False,
    )
    db.commit()

    resp = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "correct-horse-battery"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("force_password_reset") is False
    assert "access_token" in body


@pytest.mark.asyncio
async def test_login_includes_force_password_reset_true(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name="t2")
    email = f"reset_{uuid.uuid4().hex[:10]}@example.com"
    create_user(
        db,
        email=email,
        password="InitialPass9",
        role=UserRole.doctor,
        tenant_id=tenant.id,
        force_password_reset=True,
    )
    db.commit()

    resp = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "InitialPass9"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("force_password_reset") is True
    assert body.get("access_token")


@pytest.mark.asyncio
async def test_reset_password_updates_hash_and_clears_flag(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name="t3")
    email = f"rp_{uuid.uuid4().hex[:10]}@example.com"
    user = create_user(
        db,
        email=email,
        password="OldPass123",
        role=UserRole.staff,
        tenant_id=tenant.id,
        force_password_reset=True,
    )
    uid = user.id
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "OldPass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    bad = await client.post(
        "/api/v1/auth/reset-password",
        json={"old_password": "wrong", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 400

    ok = await client.post(
        "/api/v1/auth/reset-password",
        json={"old_password": "OldPass123", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200

    u = db_session.get(User, uid)
    assert u is not None
    assert u.force_password_reset is False

    login2 = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "NewPass456"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login2.status_code == 200
    assert login2.json().get("force_password_reset") is False


@pytest.mark.asyncio
async def test_me_includes_tenant_id_and_type(client: AsyncClient, db_session: Session) -> None:
    db = db_session
    tenant = create_tenant(
        db, name=f"solo_{uuid.uuid4().hex[:8]}", tenant_type=TenantType.individual
    )
    email = f"me_{uuid.uuid4().hex[:10]}@example.com"
    create_user(
        db,
        email=email,
        password="SecretPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "SecretPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == str(tenant.id)
    assert data["tenant"] is not None
    assert data["tenant"]["id"] == str(tenant.id)
    assert data["tenant"]["type"] == "individual"
