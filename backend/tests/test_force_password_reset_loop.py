"""End-to-end tests for force-password-reset flow.

Scenarios (RCCF):
  1. Create doctor → first login → reset password → success
  2. Create patient → first login → reset password → success
  3. Second login → no reset prompt
  4. Existing users → unaffected
  5. Password policy → still enforced
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from tests.factories import create_doctor_profile, create_tenant, create_user


@pytest.mark.asyncio
async def test_scenario1_doctor_creates_login_resets(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario 1: Create doctor via API → login → reset → login with new password."""
    db = db_session

    # Arrange: admin creates a doctor
    hospital = create_tenant(db, name=f"Hosp_{uuid.uuid4().hex[:6]}")
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
    admin_token = login.json()["access_token"]

    doc_email = f"dr_{uuid.uuid4().hex[:8]}@example.com"
    doc_pass = "TempPass123"

    create_resp = await client.post(
        "/api/v1/doctors",
        json={
            "name": "Dr ForceReset",
            "specialization": "General",
            "experience_years": 5,
            "account_email": doc_email,
            "account_password": doc_pass,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201, f"Doctor creation: {create_resp.text}"

    # Step 1: Doctor logs in with temp password → gets force_password_reset=True
    doc_login = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": doc_pass},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200, f"Doctor login: {doc_login.text}"
    doc_body = doc_login.json()
    assert doc_body["force_password_reset"] is True
    doc_token = doc_body["access_token"]

    # Step 2: Reset password
    new_pass = "NewSecurePass456"
    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"old_password": doc_pass, "new_password": new_pass},
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert reset_resp.status_code == 200, f"Reset: {reset_resp.text}"

    # Verify DB: force_password_reset cleared
    doc_user = db.execute(
        select(User).where(User.email == doc_email)
    ).scalar_one()
    assert doc_user.force_password_reset is False

    # Step 3: Login with new password → force_password_reset=False
    doc_login2 = await client.post(
        "/api/v1/login",
        data={"username": doc_email, "password": new_pass},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doc_login2.status_code == 200
    assert doc_login2.json()["force_password_reset"] is False


@pytest.mark.asyncio
async def test_scenario2_patient_created_login_resets(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario 2: Create patient via API → login → reset → login with new password."""
    db = db_session

    # Arrange: need a verified doctor with a profile to create the patient
    tenant = create_tenant(db, name=f"PatTenant_{uuid.uuid4().hex[:6]}")
    doc_user = create_user(
        db,
        email=f"doc_{uuid.uuid4().hex[:8]}@example.com",
        password="DocPass123!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    doc = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id, timezone_name="Asia/Kolkata")
    db.commit()

    # Login as doctor to get token (doctor can create patients)
    login = await client.post(
        "/api/v1/login",
        data={"username": doc_user.email, "password": "DocPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    doc_token = login.json()["access_token"]

    # Create patient (endpoint generates temp password)
    phone = f"99{uuid.uuid4().hex[:8]}"[:10]
    pat_resp = await client.post(
        "/api/v1/patients",
        json={
            "name": "Test Patient",
            "age": 30,
            "gender": "other",
            "phone": phone,
        },
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert pat_resp.status_code == 201, f"Patient creation: {pat_resp.text}"
    pat_data = pat_resp.json()
    temp_pass = pat_data["auto_credentials"]["password"]
    username = pat_data["auto_credentials"]["username"]
    assert username == phone

    # Step 1: Patient logs in with temp password → force_password_reset=True
    pat_login = await client.post(
        "/api/v1/login",
        data={"username": phone, "password": temp_pass},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert pat_login.status_code == 200, f"Patient login: {pat_login.text}"
    pat_body = pat_login.json()
    assert pat_body["force_password_reset"] is True
    pat_token = pat_body["access_token"]

    # Step 2: Reset password
    new_pass = "PatientNewPass789"
    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"old_password": temp_pass, "new_password": new_pass},
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert reset_resp.status_code == 200, f"Reset: {reset_resp.text}"

    # Verify DB: force_password_reset cleared
    pat_user = db.execute(
        select(User).where(User.email == phone)
    ).scalar_one()
    assert pat_user.force_password_reset is False

    # Step 3: Login with new password → force_password_reset=False
    pat_login2 = await client.post(
        "/api/v1/login",
        data={"username": phone, "password": new_pass},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert pat_login2.status_code == 200
    assert pat_login2.json()["force_password_reset"] is False


@pytest.mark.asyncio
async def test_scenario3_second_login_no_reset_prompt(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario 3: After successful reset, second login does NOT return force_password_reset=True."""
    db = db_session
    tenant = create_tenant(db, name=f"Reset_{uuid.uuid4().hex[:6]}")

    email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    user = create_user(
        db,
        email=email,
        password="InitialPass1",
        role=UserRole.staff,
        tenant_id=tenant.id,
        force_password_reset=True,
    )
    db.commit()

    # First login → force_password_reset=True
    r1 = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "InitialPass1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r1.status_code == 200
    assert r1.json()["force_password_reset"] is True
    token = r1.json()["access_token"]

    # Reset
    r_reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"old_password": "InitialPass1", "new_password": "AfterReset99"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_reset.status_code == 200

    # Second login with new password → force_password_reset MUST be False
    r2 = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "AfterReset99"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r2.status_code == 200
    assert r2.json()["force_password_reset"] is False


@pytest.mark.asyncio
async def test_scenario4_existing_users_unaffected(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario 4: Users without force_password_reset continue to work normally."""
    db = db_session
    tenant = create_tenant(db, name=f"Existing_{uuid.uuid4().hex[:6]}")
    email = f"existing_{uuid.uuid4().hex[:8]}@test.com"
    create_user(
        db,
        email=email,
        password="ExistingPass1",
        role=UserRole.staff,
        tenant_id=tenant.id,
        force_password_reset=False,
    )
    db.commit()

    # Login → force_password_reset=False
    r = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "ExistingPass1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    assert r.json()["force_password_reset"] is False


@pytest.mark.asyncio
async def test_scenario5_password_policy_enforced(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario 5: Password policy (min 8 chars) is enforced during reset."""
    db = db_session
    tenant = create_tenant(db, name=f"Policy_{uuid.uuid4().hex[:6]}")
    email = f"policy_{uuid.uuid4().hex[:8]}@test.com"
    user = create_user(
        db,
        email=email,
        password="OldPassLong1",
        role=UserRole.staff,
        tenant_id=tenant.id,
        force_password_reset=True,
    )
    db.commit()

    # Login
    r = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "OldPassLong1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    # Try new password < 8 chars → 422
    r_short = await client.post(
        "/api/v1/auth/reset-password",
        json={"old_password": "OldPassLong1", "new_password": "short"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_short.status_code == 422

    # Same as old password → 400
    r_same = await client.post(
        "/api/v1/auth/reset-password",
        json={"old_password": "OldPassLong1", "new_password": "OldPassLong1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_same.status_code == 400
    detail = (r_same.json().get("detail") or "").lower()
    assert "different" in detail

    # Wrong old password → 400
    r_wrong = await client.post(
        "/api/v1/auth/reset-password",
        json={"old_password": "WrongOldPass", "new_password": "ValidNewPass1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_wrong.status_code == 400
    detail = (r_wrong.json().get("detail") or "").lower()
    assert "incorrect" in detail
