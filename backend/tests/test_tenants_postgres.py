"""
Parallel hospital-creation stress (PostgreSQL only).

Uses concurrent HTTP requests so the DB enforces uniqueness under real pooling.
Default CI uses SQLite; these tests skip unless PYTEST_DATABASE_URL points at Postgres.

Example:
  set PYTEST_DATABASE_URL=postgresql+psycopg2://user:pass@127.0.0.1:5432/medical_test
  pytest -m postgres tests/test_tenants_postgres.py
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import UserRole
from tests.factories import create_tenant, create_user

pytestmark = pytest.mark.postgres


@pytest.mark.asyncio
async def test_create_hospital_concurrent_name_collision_single_201(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    super_email = f"sa_pg_conc_{uuid.uuid4().hex[:8]}@example.com"
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
    hospital_name = f"PG Concurrent {suffix}"
    auth = {"Authorization": f"Bearer {token}"}

    async def post_one(n: int):
        return await client.post(
            "/api/v1/tenants",
            json={
                "name": hospital_name,
                "type": "organization",
                "admin": {
                    "email": f"admin_pg_conc_{suffix}_{n}@example.com",
                    "password": "Hospital9!",
                },
            },
            headers=auth,
        )

    n_parallel = 8
    results = await asyncio.gather(*[post_one(i) for i in range(n_parallel)])
    assert sum(1 for r in results if r.status_code == 201) == 1, [
        (r.status_code, r.text[:200]) for r in results
    ]
    assert sum(1 for r in results if r.status_code == 400) == n_parallel - 1

    count = db.scalar(
        select(func.count(Tenant.id)).where(func.lower(Tenant.name) == hospital_name.lower())
    )
    assert count == 1
