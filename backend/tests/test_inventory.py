"""Inventory API: tenant scope, stock via movements, non-negative stock."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.crud.crud_appointment import add_appointment
from app.models.appointment import AppointmentStatus
from app.models.user import UserRole
from tests.factories import create_doctor_profile, create_tenant, create_user


@pytest.mark.asyncio
async def test_inventory_crud_and_stock_movements(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name="inv-tenant-a")
    email = f"inv_admin_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=email,
        password="InvPass9!",
        role=UserRole.admin,
        tenant_id=tenant.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "InvPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/inventory/items",
        json={
            "name": "Paracetamol 500mg",
            "type": "medicine",
            "unit": "strip",
            "cost_price": 20.0,
            "selling_price": 35.0,
            "is_active": True,
        },
        headers=auth,
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]
    assert create_resp.json()["tenant_id"] == str(tenant.id)

    list_resp = await client.get("/api/v1/inventory/items", headers=auth)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    add_resp = await client.post(
        "/api/v1/inventory/stock/add",
        json={"item_id": item_id, "quantity": 100, "doctor_id": None},
        headers=auth,
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["quantity"] == 100

    reduce_resp = await client.post(
        "/api/v1/inventory/stock/reduce",
        json={"item_id": item_id, "quantity": 30, "doctor_id": None},
        headers=auth,
    )
    assert reduce_resp.status_code == 200
    assert reduce_resp.json()["quantity"] == 70

    adj_resp = await client.post(
        "/api/v1/inventory/stock/adjust",
        json={"item_id": item_id, "quantity": -10, "doctor_id": None},
        headers=auth,
    )
    assert adj_resp.status_code == 200
    assert adj_resp.json()["quantity"] == 60

    bad = await client.post(
        "/api/v1/inventory/stock/reduce",
        json={"item_id": item_id, "quantity": 999, "doctor_id": None},
        headers=auth,
    )
    assert bad.status_code == 400
    detail = bad.json()["detail"].lower()
    assert "insufficient" in detail or "negative" in detail


@pytest.mark.asyncio
async def test_inventory_doctor_scoped_stock(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name="inv-tenant-doc")
    doc_email = f"inv_doc_{uuid.uuid4().hex[:8]}@example.com"
    doc_user = create_user(
        db,
        email=doc_email,
        password="InvPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": "InvPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/inventory/items",
        json={
            "name": "Gloves",
            "type": "consumable",
            "unit": "box",
            "cost_price": 200.0,
            "selling_price": 280.0,
        },
        headers=auth,
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    add_doc = await client.post(
        "/api/v1/inventory/stock/add",
        json={"item_id": item_id, "quantity": 5, "doctor_id": str(doctor.id)},
        headers=auth,
    )
    assert add_doc.status_code == 200
    assert add_doc.json()["quantity"] == 5

    # doctor_id null is resolved to the logged-in doctor; stock accumulates in one scope
    add_again = await client.post(
        "/api/v1/inventory/stock/add",
        json={"item_id": item_id, "quantity": 12, "doctor_id": None},
        headers=auth,
    )
    assert add_again.status_code == 200
    assert add_again.json()["quantity"] == 17


@pytest.mark.asyncio
async def test_inventory_cross_tenant_forbidden(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    ta = create_tenant(db, name="inv-ta")
    tb = create_tenant(db, name="inv-tb")
    email_a = f"inv_a_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=email_a,
        password="InvPass9!",
        role=UserRole.admin,
        tenant_id=ta.id,
    )
    email_b = f"inv_b_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=email_b,
        password="InvPass9!",
        role=UserRole.admin,
        tenant_id=tb.id,
    )
    db.commit()

    login_b = await client.post(
        "/api/v1/login",
        data={"username": email_b, "password": "InvPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_b = login_b.json()["access_token"]
    auth_b = {"Authorization": f"Bearer {token_b}"}

    item_b = await client.post(
        "/api/v1/inventory/items",
        json={
            "name": "Tenant B only",
            "type": "consumable",
            "unit": "each",
            "cost_price": 1.0,
            "selling_price": 2.0,
        },
        headers=auth_b,
    )
    item_id = item_b.json()["id"]

    login_a = await client.post(
        "/api/v1/login",
        data={"username": email_a, "password": "InvPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_a = login_a.json()["access_token"]
    auth_a = {"Authorization": f"Bearer {token_a}"}

    blocked = await client.post(
        "/api/v1/inventory/stock/add",
        json={"item_id": item_id, "quantity": 1, "doctor_id": None},
        headers=auth_a,
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_inventory_patient_forbidden(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name="inv-pat")
    pat_email = f"inv_pat_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=pat_email,
        password="InvPass9!",
        role=UserRole.patient,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": pat_email, "password": "InvPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    auth = {"Authorization": f"Bearer {login.json()['access_token']}"}

    for path in ("/api/v1/inventory/items", "/api/v1/inventory/stock?item_id=00000000-0000-0000-0000-000000000000"):
        resp = await client.get(path, headers=auth)
        assert resp.status_code == 403

    r_bulk = await client.get("/api/v1/inventory/stock/bulk", headers=auth)
    assert r_bulk.status_code == 403


@pytest.mark.asyncio
async def test_inventory_bulk_stock_merges_with_items_list(
    client: AsyncClient, db_session: Session
) -> None:
    """Three items, stock on two only — bulk returns all with missing stock as 0."""
    db = db_session
    tenant = create_tenant(db, name="inv-tenant-bulk")
    email = f"inv_bulk_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=email,
        password="InvPass9!",
        role=UserRole.admin,
        tenant_id=tenant.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "InvPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    created_ids: list[str] = []
    for i, name in enumerate(["Paracetamol", "Gloves", "Syringe"]):
        r = await client.post(
            "/api/v1/inventory/items",
            json={
                "name": name,
                "type": "medicine" if i == 0 else "consumable",
                "unit": "unit",
                "cost_price": 1.0,
                "selling_price": 2.0,
            },
            headers=auth,
        )
        assert r.status_code == 201
        created_ids.append(r.json()["id"])

    add1 = await client.post(
        "/api/v1/inventory/stock/add",
        json={"item_id": created_ids[0], "quantity": 120, "doctor_id": None},
        headers=auth,
    )
    assert add1.status_code == 200
    add2 = await client.post(
        "/api/v1/inventory/stock/add",
        json={"item_id": created_ids[1], "quantity": 45, "doctor_id": None},
        headers=auth,
    )
    assert add2.status_code == 200

    bulk = await client.get("/api/v1/inventory/stock/bulk", headers=auth)
    assert bulk.status_code == 200
    by_id = {row["item_id"]: row["quantity"] for row in bulk.json()}
    assert len(by_id) == 3
    assert by_id[created_ids[0]] == 120
    assert by_id[created_ids[1]] == 45
    assert by_id[created_ids[2]] == 0

    as_map = await client.get("/api/v1/inventory/stock/bulk?as_map=true", headers=auth)
    assert as_map.status_code == 200
    m = as_map.json()
    assert m[created_ids[0]] == 120
    assert m[created_ids[2]] == 0

    one = await client.get(
        f"/api/v1/inventory/stock?item_id={created_ids[0]}",
        headers=auth,
    )
    assert one.status_code == 200
    assert one.json() == {
        "item_id": created_ids[0],
        "doctor_id": None,
        "quantity": 120,
    }


@pytest.mark.asyncio
async def test_mark_completed_deducts_clinic_inventory(
    client: AsyncClient, db_session: Session,
) -> None:
    from tests.factories import create_user, seed_bookable_doctor_and_patient

    db = db_session
    doc_email = f"doc_{uuid.uuid4().hex[:8]}@e2e.test"
    pat_email = f"pat_{uuid.uuid4().hex[:8]}@e2e.test"
    doctor, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password="DocPass123!",
        patient_email=pat_email,
        patient_password="PatPass123!",
    )
    tenant_id = doctor.tenant_id
    assert tenant_id is not None
    adm_email = f"adm_{uuid.uuid4().hex[:8]}@e2e.test"
    create_user(
        db,
        email=adm_email,
        password="AdmPass9!",
        role=UserRole.admin,
        tenant_id=tenant_id,
    )
    db.commit()

    adm_login = await client.post(
        "/api/v1/login",
        data={"username": adm_email, "password": "AdmPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert adm_login.status_code == 200
    adm_h = {
        "Authorization": f"Bearer {adm_login.json()['access_token']}",
        "X-Tenant-ID": str(tenant_id),
    }

    item_r = await client.post(
        "/api/v1/inventory/items",
        json={
            "name": "Bandage roll",
            "type": "consumable",
            "unit": "roll",
            "cost_price": 10.0,
            "selling_price": 18.0,
        },
        headers=adm_h,
    )
    assert item_r.status_code == 201
    item_id = item_r.json()["id"]
    add_r = await client.post(
        "/api/v1/inventory/stock/add",
        json={"item_id": item_id, "quantity": 30, "doctor_id": None},
        headers=adm_h,
    )
    assert add_r.status_code == 200

    login_pat = await client.post(
        "/api/v1/login",
        data={"username": pat_email, "password": "PatPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_pat.status_code == 200
    pat_h = {"Authorization": f"Bearer {login_pat.json()['access_token']}"}
    appointment = add_appointment(
        db_session,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(minutes=10),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": tenant_id,
        },
    )
    db_session.commit()
    appt_id = str(appointment.id)

    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": "DocPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_h = {
        "Authorization": f"Bearer {doc_login.json()['access_token']}",
        "X-Tenant-ID": str(tenant_id),
    }
    ok = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json={
            "completion_notes": "Applied dressing.",
            "items": [{"item_id": item_id, "quantity": 8}],
        },
        headers={**doc_h, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "completed"

    bulk = await client.get(
        "/api/v1/inventory/stock/bulk",
        params={"as_map": "true", "tenant_stock_only": "true"},
        headers=adm_h,
    )
    assert bulk.status_code == 200
    assert bulk.json()[item_id] == 22

    again = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json={"completion_notes": None, "items": []},
        headers={**doc_h, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert again.status_code == 200
    assert again.json()["status"] == "completed"

    bulk2 = await client.get(
        "/api/v1/inventory/stock/bulk",
        params={"as_map": "true", "tenant_stock_only": "true"},
        headers=adm_h,
    )
    assert bulk2.status_code == 200
    assert bulk2.json()[item_id] == 22


@pytest.mark.asyncio
async def test_inventory_doctor_stock_adjust_forbidden(
    client: AsyncClient, db_session: Session,
) -> None:
    db = db_session
    tenant = create_tenant(db, name="inv-adj-doc")
    doc_email = f"inv_adj_{uuid.uuid4().hex[:8]}@example.com"
    doc_user = create_user(
        db,
        email=doc_email,
        password="InvPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": "InvPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    auth = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Tenant-ID": str(tenant.id),
    }

    create_item = await client.post(
        "/api/v1/inventory/items",
        json={
            "name": "Tape",
            "type": "consumable",
            "unit": "roll",
            "cost_price": 1.0,
            "selling_price": 3.0,
        },
        headers=auth,
    )
    assert create_item.status_code == 201
    item_id = create_item.json()["id"]
    await client.post(
        "/api/v1/inventory/stock/add",
        json={"item_id": item_id, "quantity": 10, "doctor_id": None},
        headers=auth,
    )
    bad = await client.post(
        "/api/v1/inventory/stock/adjust",
        json={"item_id": item_id, "quantity": 1, "doctor_id": None},
        headers=auth,
    )
    assert bad.status_code == 403
