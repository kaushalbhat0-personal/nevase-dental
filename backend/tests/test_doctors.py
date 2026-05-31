"""POST /doctors: admin creates doctor with login (user + user_tenant + profile)."""

from __future__ import annotations

import asyncio
import uuid
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tenant import UserTenant
from app.models.user import User, UserRole
from tests.factories import create_tenant, create_user


@pytest.mark.asyncio
async def test_admin_creates_doctor_with_login(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    hospital = create_tenant(db, name=f"Hosp {uuid.uuid4().hex[:6]}")
    admin_email = f"adm_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=admin_email,
        password="AdminPass9!",
        role=UserRole.admin,
        tenant_id=hospital.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": admin_email, "password": "AdminPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    suffix = uuid.uuid4().hex[:8]
    mixed = f"New.Doc.{suffix}@Example.COM"
    expected = mixed.lower().strip()
    body = {
        "name": "Dr Smith",
        "specialization": "Cardiology",
        "experience_years": 7,
        "account_email": mixed,
        "account_password": "DocPass9!!",
    }
    r = await client.post("/api/v1/doctors", json=body, headers=auth)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "Dr Smith"
    assert data.get("linked_user_email") == expected
    did = UUID(data["id"])

    doc_user = db.scalars(
        select(User).where(User.email == expected, User.role == UserRole.doctor)
    ).first()
    assert doc_user is not None
    assert doc_user.role == UserRole.doctor
    assert doc_user.force_password_reset is True
    assert doc_user.is_active is True

    ut = db.scalars(
        select(UserTenant).where(
            UserTenant.user_id == doc_user.id,
            UserTenant.tenant_id == hospital.id,
        )
    ).one()
    assert ut.role == "doctor"
    assert ut.is_primary is True


@pytest.mark.asyncio
async def test_create_doctor_duplicate_email_400(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    hospital = create_tenant(db, name=f"Hosp2 {uuid.uuid4().hex[:6]}")
    admin_email = f"adm2_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=admin_email,
        password="AdminPass9!",
        role=UserRole.admin,
        tenant_id=hospital.id,
    )
    doc_email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=doc_email,
        password="DocPass9!!",
        role=UserRole.doctor,
        tenant_id=hospital.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": admin_email, "password": "AdminPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    body = {
        "name": "Dr Dup",
        "specialization": "ENT",
        "experience_years": 3,
        "account_email": doc_email,
        "account_password": "OtherPass9!",
    }
    r = await client.post("/api/v1/doctors", json=body, headers=auth)
    assert r.status_code == 400
    assert "email" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_doctor_idempotency_same_key_same_doctor(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    hospital = create_tenant(db, name=f"Hosp3 {uuid.uuid4().hex[:6]}")
    admin_email = f"adm3_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=admin_email,
        password="AdminPass9!",
        role=UserRole.admin,
        tenant_id=hospital.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": admin_email, "password": "AdminPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    key = f"idem-doc-{uuid.uuid4().hex[:8]}"
    auth = {"Authorization": f"Bearer {token}", "Idempotency-Key": key}
    body = {
        "name": "Idem Dr",
        "specialization": "GP",
        "experience_years": 2,
        "account_email": f"idem_{uuid.uuid4().hex[:8]}@example.com",
        "account_password": "DocPass9!!",
    }
    r1 = await client.post("/api/v1/doctors", json=body, headers=auth)
    r2 = await client.post("/api/v1/doctors", json=body, headers=auth)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_create_doctor_idempotency_key_conflict_different_body(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    hospital = create_tenant(db, name=f"Hosp4 {uuid.uuid4().hex[:6]}")
    admin_email = f"adm4_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=admin_email,
        password="AdminPass9!",
        role=UserRole.admin,
        tenant_id=hospital.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": admin_email, "password": "AdminPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    key = f"idem-bad-{uuid.uuid4().hex[:8]}"
    auth = {"Authorization": f"Bearer {token}", "Idempotency-Key": key}
    a = {
        "name": "A",
        "specialization": "X",
        "experience_years": 1,
        "account_email": f"a_{uuid.uuid4().hex[:8]}@example.com",
        "account_password": "DocPass9!!",
    }
    b = a.copy()
    b["name"] = "B"
    r1 = await client.post("/api/v1/doctors", json=a, headers=auth)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/doctors", json=b, headers=auth)
    assert r2.status_code == 400
    assert "idempotency" in r2.json()["detail"].lower()


@pytest.mark.postgres
@pytest.mark.asyncio
async def test_create_doctor_concurrent_same_email_one_wins(
    client: AsyncClient, db_session: Session
) -> None:
    """Optional: parallel POSTs with same new email; DB uniqueness yields one 201, rest 400."""
    db = db_session
    hospital = create_tenant(db, name=f"PGH {uuid.uuid4().hex[:6]}")
    admin_email = f"pg_adm_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=admin_email,
        password="AdminPass9!",
        role=UserRole.admin,
        tenant_id=hospital.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": admin_email, "password": "AdminPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    shared_email = f"race_{uuid.uuid4().hex}@example.com"
    body = {
        "name": "Race Dr",
        "specialization": "Race",
        "experience_years": 1,
        "account_email": shared_email,
        "account_password": "DocPass9!!",
    }
    auth = {"Authorization": f"Bearer {token}"}
    n = 5

    async def one():
        return await client.post("/api/v1/doctors", json=body, headers=auth)

    results = await asyncio.gather(*[one() for _ in range(n)])
    oks = [r for r in results if r.status_code == 201]
    bads = [r for r in results if r.status_code == 400]
    assert len(oks) == 1, [(r.status_code, r.text[:120]) for r in results]
    assert len(bads) == n - 1


@pytest.mark.asyncio
async def test_doctor_cannot_create_doctor(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    hospital = create_tenant(db, name=f"HospDoc {uuid.uuid4().hex[:6]}")
    existing_doc_email = f"doc_exist_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=existing_doc_email,
        password="DocPass9!!",
        role=UserRole.doctor,
        tenant_id=hospital.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": existing_doc_email, "password": "DocPass9!!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    body = {
        "name": "Dr Blocked",
        "specialization": "X",
        "experience_years": 1,
        "account_email": f"new_{uuid.uuid4().hex[:8]}@example.com",
        "account_password": "DocPass9!!",
    }
    r = await client.post("/api/v1/doctors", json=body, headers=auth)
    assert r.status_code == 403
    assert "doctor" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patient_cannot_create_doctor(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    hospital = create_tenant(db, name=f"HospPat {uuid.uuid4().hex[:6]}")
    patient_email = f"pat_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=patient_email,
        password="PatPass9!!",
        role=UserRole.patient,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": patient_email, "password": "PatPass9!!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    body = {
        "name": "Dr Blocked",
        "specialization": "X",
        "experience_years": 1,
        "account_email": f"new_{uuid.uuid4().hex[:8]}@example.com",
        "account_password": "DocPass9!!",
    }
    r = await client.post("/api/v1/doctors", json=body, headers=auth)
    assert r.status_code == 403
    assert "administrator" in r.json()["detail"].lower()
