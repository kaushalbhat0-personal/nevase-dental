"""RBAC and transitions for admin doctor marketplace verification."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.tenant import TenantType
from app.models.user import UserRole
from app.services import doctor_profile_service as dps
from tests.factories import create_doctor_profile, create_tenant, create_user

VERIFY = "/api/v1/admin/doctor-profiles/{doctor_id}/verification"


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post(
        "/api/v1/login",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _pending_profile(db: Session, doctor_id) -> None:
    from app.crud import crud_doctor

    d = crud_doctor.get_doctor(db, doctor_id)
    assert d is not None
    p = dps.ensure_profile_for_doctor(db, d)
    dps.recompute_is_complete(p)
    p.registration_number = p.registration_number or "R1"
    p.phone = p.phone or "9000000000"
    p.qualification = p.qualification or "MBBS"
    p.verification_status = dps.VERIFICATION_PENDING
    db.add(p)
    db.flush()


@pytest.mark.asyncio
async def test_individual_tenant_org_admin_403_super_admin_200(
    client: AsyncClient, db_session: Session
) -> None:
    ind = create_tenant(
        db_session, name=f"ind-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.individual
    )
    org = create_tenant(
        db_session, name=f"org-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.organization
    )
    other_admin = create_user(
        db_session,
        email=f"a_{uuid.uuid4().hex[:8]}@t.local",
        password="XyzPass9!!",
        role=UserRole.admin,
        tenant_id=org.id,
    )
    doc = create_doctor_profile(db_session, tenant_id=ind.id)
    _pending_profile(db_session, doc.id)
    db_session.commit()

    tok = await _login(client, other_admin.email, "XyzPass9!!")
    r = await client.patch(
        VERIFY.format(doctor_id=doc.id),
        headers={
            "Authorization": f"Bearer {tok}",
            "X-Tenant-ID": str(org.id),
        },
        json={"status": "approved"},
    )
    assert r.status_code == 403, r.text

    sa = create_user(
        db_session,
        email=f"sa_{uuid.uuid4().hex[:8]}@t.local",
        password="SaPass9!!",
        role=UserRole.super_admin,
    )
    doc2 = create_doctor_profile(db_session, tenant_id=ind.id)
    _pending_profile(db_session, doc2.id)
    db_session.commit()

    tok_sa = await _login(client, sa.email, "SaPass9!!")
    r2 = await client.patch(
        VERIFY.format(doctor_id=doc2.id),
        headers={"Authorization": f"Bearer {tok_sa}"},
        json={"status": "approved"},
    )
    assert r2.status_code == 200, r2.text


@pytest.mark.asyncio
async def test_org_same_tenant_admin_200(client: AsyncClient, db_session: Session) -> None:
    org = create_tenant(
        db_session, name=f"o-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.organization
    )
    admin = create_user(
        db_session,
        email=f"adm_{uuid.uuid4().hex[:8]}@t.local",
        password="AdPass9!!",
        role=UserRole.admin,
        tenant_id=org.id,
    )
    doc = create_doctor_profile(db_session, tenant_id=org.id)
    _pending_profile(db_session, doc.id)
    db_session.commit()

    tok = await _login(client, admin.email, "AdPass9!!")
    r = await client.patch(
        VERIFY.format(doctor_id=doc.id),
        headers={
            "Authorization": f"Bearer {tok}",
            "X-Tenant-ID": str(org.id),
        },
        json={"status": "approved"},
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_org_cross_tenant_admin_403(client: AsyncClient, db_session: Session) -> None:
    ta = create_tenant(db_session, name=f"a-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.organization)
    tb = create_tenant(db_session, name=f"b-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.organization)
    admin_a = create_user(
        db_session,
        email=f"aa_{uuid.uuid4().hex[:8]}@t.local",
        password="AaPass9!!",
        role=UserRole.admin,
        tenant_id=ta.id,
    )
    doc_b = create_doctor_profile(db_session, tenant_id=tb.id)
    _pending_profile(db_session, doc_b.id)
    db_session.commit()

    tok = await _login(client, admin_a.email, "AaPass9!!")
    r = await client.patch(
        VERIFY.format(doctor_id=doc_b.id),
        headers={
            "Authorization": f"Bearer {tok}",
            "X-Tenant-ID": str(ta.id),
        },
        json={"status": "approved"},
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_transition_approved_to_rejected_non_super_403(
    client: AsyncClient, db_session: Session
) -> None:
    org = create_tenant(
        db_session, name=f"x-{uuid.uuid4().hex[:6]}", tenant_type=TenantType.organization
    )
    admin = create_user(
        db_session,
        email=f"ad2_{uuid.uuid4().hex[:8]}@t.local",
        password="Ad2Pass9!",
        role=UserRole.admin,
        tenant_id=org.id,
    )
    doc = create_doctor_profile(db_session, tenant_id=org.id)
    p = dps.ensure_profile_for_doctor(db_session, doc)
    dps.recompute_is_complete(p)
    p.registration_number = p.registration_number or "R1"
    p.phone = p.phone or "9000000001"
    p.qualification = p.qualification or "MBBS"
    p.verification_status = dps.VERIFICATION_APPROVED
    db_session.add(p)
    db_session.flush()
    db_session.commit()

    tok = await _login(client, admin.email, "Ad2Pass9!")
    r = await client.patch(
        VERIFY.format(doctor_id=doc.id),
        headers={
            "Authorization": f"Bearer {tok}",
            "X-Tenant-ID": str(org.id),
        },
        json={"status": "rejected", "reason": "not good enough"},
    )
    assert r.status_code == 403, r.text
