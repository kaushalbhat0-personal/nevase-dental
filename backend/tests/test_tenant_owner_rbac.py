"""Practice owner (solo doctor) has admin-equivalent access; non-owner doctors do not."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.tenant import TenantType
from app.models.user import UserRole
from tests.factories import create_doctor_profile, create_tenant, create_user

METRICS = "/api/v1/admin/dashboard/metrics"


def _headers(token: str, tenant_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_owner_doctor_can_access_admin_metrics(client: AsyncClient, db_session: Session) -> None:
    tenant = create_tenant(db_session, name=f"own-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.organization)
    owner = create_user(
        db_session,
        email=f"owner_{uuid.uuid4().hex[:8]}@t.local",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
        is_owner=True,
    )
    create_doctor_profile(db_session, tenant_id=tenant.id, user_id=owner.id, timezone_name="UTC")
    db_session.commit()

    r = await client.post(
        "/api/v1/login",
        data={"username": owner.email, "password": "DocPass9!"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    m = await client.get(METRICS, headers=_headers(token, tenant.id))
    assert m.status_code == 200, m.text


@pytest.mark.asyncio
async def test_non_owner_doctor_cannot_access_admin_metrics(
    client: AsyncClient, db_session: Session
) -> None:
    tenant = create_tenant(db_session, name=f"no-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.organization)
    doc = create_user(
        db_session,
        email=f"doc_{uuid.uuid4().hex[:8]}@t.local",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
        is_owner=False,
    )
    create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc.id, timezone_name="UTC")
    db_session.commit()

    r = await client.post(
        "/api/v1/login",
        data={"username": doc.email, "password": "DocPass9!"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    m = await client.get(METRICS, headers=_headers(token, tenant.id))
    assert m.status_code == 403


@pytest.mark.asyncio
async def test_owner_retains_admin_access_after_second_doctor_added(
    client: AsyncClient, db_session: Session
) -> None:
    tenant = create_tenant(db_session, name=f"two-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.organization)
    owner = create_user(
        db_session,
        email=f"own2_{uuid.uuid4().hex[:8]}@t.local",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
        is_owner=True,
    )
    create_doctor_profile(db_session, tenant_id=tenant.id, user_id=owner.id, timezone_name="UTC")
    other = create_user(
        db_session,
        email=f"oth_{uuid.uuid4().hex[:8]}@t.local",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
        is_owner=False,
    )
    create_doctor_profile(db_session, tenant_id=tenant.id, user_id=other.id, timezone_name="UTC")
    db_session.commit()

    r = await client.post(
        "/api/v1/login",
        data={"username": owner.email, "password": "DocPass9!"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    m = await client.get(METRICS, headers=_headers(token, tenant.id))
    assert m.status_code == 200, m.text


@pytest.mark.asyncio
async def test_cannot_delete_practice_owner_doctor_profile(
    client: AsyncClient, db_session: Session
) -> None:
    tenant = create_tenant(db_session, name=f"del-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.organization)
    admin = create_user(
        db_session,
        email=f"adm_{uuid.uuid4().hex[:8]}@t.local",
        password="Adm1nPass!",
        role=UserRole.admin,
        tenant_id=tenant.id,
    )
    owner = create_user(
        db_session,
        email=f"ownd_{uuid.uuid4().hex[:8]}@t.local",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
        is_owner=True,
    )
    d = create_doctor_profile(db_session, tenant_id=tenant.id, user_id=owner.id, timezone_name="UTC")
    db_session.commit()

    r = await client.post(
        "/api/v1/login",
        data={"username": admin.email, "password": "Adm1nPass!"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    del_r = await client.delete(
        f"/api/v1/doctors/{d.id}",
        headers=_headers(token, tenant.id),
    )
    assert del_r.status_code == 403
    assert "owner" in del_r.json().get("detail", "").lower()
