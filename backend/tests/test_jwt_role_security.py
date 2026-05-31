"""JWT role-claim security tests.

Covers the vulnerability fixed in deps._parse_access_token:
  - A missing role claim MUST be rejected (was: silently upgraded to "admin")
  - A non-string / malformed role claim MUST be rejected
  - Valid role claims (patient, doctor, admin, super_admin, staff) MUST be accepted
  - Dual-role users (admin+doctor linkage) MUST be accepted and retain DB role
  - The _build_token_payload helper MUST always embed a role claim (no dead fallback)

No auth-system rewrite.  All tests operate at the HTTP layer (real ASGI transport)
or directly on _parse_access_token / _build_token_payload helpers.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.orm import Session

from app.api.deps import _parse_access_token
from app.api.http_exceptions import unauthorized_credentials_exception
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import UserRole
from tests.factories import create_tenant, create_user, create_doctor_profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_raw_token(payload: dict[str, Any]) -> str:
    """Sign a raw payload dict with the application secret (bypasses _build_token_payload)."""
    to_encode = {"type": "access", **payload}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Unit-level: _parse_access_token
# ---------------------------------------------------------------------------


class TestParseAccessTokenRoleValidation:
    """Unit tests for _parse_access_token — no DB, no HTTP."""

    def _make_sub(self) -> str:
        return str(uuid.uuid4())

    # --- MISSING ROLE CLAIM ---

    def test_missing_role_claim_raises_401(self) -> None:
        """A token with no 'role' key must be rejected — never silently promoted."""
        token = _build_raw_token({"sub": self._make_sub()})
        with pytest.raises(Exception) as exc_info:
            _parse_access_token(token)
        # unauthorized_credentials_exception returns HTTPException(401)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]

    def test_null_role_claim_raises_401(self) -> None:
        """role: null (None) must be rejected — not promoted to admin."""
        token = _build_raw_token({"sub": self._make_sub(), "role": None})
        with pytest.raises(Exception) as exc_info:
            _parse_access_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]

    def test_empty_string_role_claim_raises_401(self) -> None:
        """role: '' must be rejected — empty string is falsy."""
        token = _build_raw_token({"sub": self._make_sub(), "role": ""})
        with pytest.raises(Exception) as exc_info:
            _parse_access_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]

    # --- MALFORMED ROLE CLAIM ---

    def test_numeric_role_claim_raises_401(self) -> None:
        """role: 42 (non-string) must be rejected."""
        token = _build_raw_token({"sub": self._make_sub(), "role": 42})
        with pytest.raises(Exception) as exc_info:
            _parse_access_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]

    def test_list_role_claim_raises_401(self) -> None:
        """role: ['admin'] (list masquerading as role) must be rejected."""
        token = _build_raw_token({"sub": self._make_sub(), "role": ["admin"]})
        with pytest.raises(Exception) as exc_info:
            _parse_access_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]

    def test_boolean_role_claim_raises_401(self) -> None:
        """role: true (bool) — bools are not strings, must be rejected."""
        token = _build_raw_token({"sub": self._make_sub(), "role": True})
        with pytest.raises(Exception) as exc_info:
            _parse_access_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]

    def test_dict_role_claim_raises_401(self) -> None:
        """role: {} must be rejected."""
        token = _build_raw_token({"sub": self._make_sub(), "role": {}})
        with pytest.raises(Exception) as exc_info:
            _parse_access_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]

    # --- VALID ROLE CLAIMS — must parse successfully ---

    @pytest.mark.parametrize("role_value", ["admin", "doctor", "patient", "staff", "super_admin"])
    def test_valid_role_claim_accepted(self, role_value: str) -> None:
        """All known role strings must be accepted and returned verbatim."""
        sub = self._make_sub()
        token = _build_raw_token({"sub": sub, "role": role_value})
        payload = _parse_access_token(token)
        assert payload.role == role_value
        assert str(payload.user_id) == sub

    def test_unknown_role_string_is_accepted_as_string(self) -> None:
        """An unknown-but-string role is passed through (DB lookup will fail the user check later)."""
        token = _build_raw_token({"sub": self._make_sub(), "role": "wizard"})
        payload = _parse_access_token(token)
        assert payload.role == "wizard"

    # --- TENANT ID PASSTHROUGH ---

    def test_valid_tenant_id_is_parsed(self) -> None:
        tid = str(uuid.uuid4())
        token = _build_raw_token({"sub": self._make_sub(), "role": "admin", "tenant_id": tid})
        payload = _parse_access_token(token)
        assert str(payload.tenant_id) == tid

    def test_malformed_tenant_id_becomes_none(self) -> None:
        """A bad tenant_id UUID string must not crash — it silently becomes None."""
        token = _build_raw_token({"sub": self._make_sub(), "role": "admin", "tenant_id": "not-a-uuid"})
        payload = _parse_access_token(token)
        assert payload.tenant_id is None

    def test_missing_tenant_id_becomes_none(self) -> None:
        token = _build_raw_token({"sub": self._make_sub(), "role": "admin"})
        payload = _parse_access_token(token)
        assert payload.tenant_id is None


# ---------------------------------------------------------------------------
# HTTP-level: /api/v1/me — end-to-end role propagation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_role_claim_token_rejected_at_me_endpoint(
    client: AsyncClient, db_session: Session
) -> None:
    """A crafted token without a role claim is rejected before hitting the DB."""
    db = db_session
    tenant = create_tenant(db, name=f"sec_{uuid.uuid4().hex[:8]}")
    user = create_user(
        db,
        email=f"sec_{uuid.uuid4().hex[:8]}@example.com",
        password="Irrelevant9!",
        role=UserRole.admin,
        tenant_id=tenant.id,
    )
    db.commit()

    # Token is valid-signed but role claim is absent
    bad_token = _build_raw_token({"sub": str(user.id)})
    resp = await client.get("/api/v1/me", headers=_auth_header(bad_token))
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_null_role_claim_token_rejected_at_me_endpoint(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name=f"sec_{uuid.uuid4().hex[:8]}")
    user = create_user(
        db,
        email=f"sec_{uuid.uuid4().hex[:8]}@example.com",
        password="Irrelevant9!",
        role=UserRole.patient,
        tenant_id=None,  # patient has no tenant
    )
    db.commit()

    bad_token = _build_raw_token({"sub": str(user.id), "role": None})
    resp = await client.get("/api/v1/me", headers=_auth_header(bad_token))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_numeric_role_claim_token_rejected_at_me_endpoint(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name=f"sec_{uuid.uuid4().hex[:8]}")
    user = create_user(
        db,
        email=f"sec_{uuid.uuid4().hex[:8]}@example.com",
        password="Irrelevant9!",
        role=UserRole.staff,
        tenant_id=tenant.id,
    )
    db.commit()

    bad_token = _build_raw_token({"sub": str(user.id), "role": 1})
    resp = await client.get("/api/v1/me", headers=_auth_header(bad_token))
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# HTTP-level: Valid role claims — doctor, admin, patient, super_admin, staff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_doctor_role_token_accepted(
    client: AsyncClient, db_session: Session
) -> None:
    """A real doctor login produces a token that is accepted and role is preserved."""
    db = db_session
    tenant = create_tenant(db, name=f"doc_{uuid.uuid4().hex[:8]}")
    email = f"doc_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=email,
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "DocPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["role"] == "doctor"

    me = await client.get("/api/v1/me", headers=_auth_header(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "doctor"


@pytest.mark.asyncio
async def test_admin_role_token_accepted(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name=f"adm_{uuid.uuid4().hex[:8]}")
    email = f"adm_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=email,
        password="AdminPass9!",
        role=UserRole.admin,
        tenant_id=tenant.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "AdminPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["role"] == "admin"

    me = await client.get("/api/v1/me", headers=_auth_header(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_patient_role_token_accepted(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    email = f"pat_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=email,
        password="PatPass9!",
        role=UserRole.patient,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "PatPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["role"] == "patient"

    me = await client.get("/api/v1/me", headers=_auth_header(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "patient"


@pytest.mark.asyncio
async def test_staff_role_token_accepted(
    client: AsyncClient, db_session: Session
) -> None:
    db = db_session
    tenant = create_tenant(db, name=f"stf_{uuid.uuid4().hex[:8]}")
    email = f"stf_{uuid.uuid4().hex[:8]}@example.com"
    create_user(
        db,
        email=email,
        password="StaffPass9!",
        role=UserRole.staff,
        tenant_id=tenant.id,
    )
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "StaffPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["role"] == "staff"

    me = await client.get("/api/v1/me", headers=_auth_header(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "staff"


# ---------------------------------------------------------------------------
# Dual-role: admin user WITH a linked Doctor row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dual_role_admin_with_doctor_linkage_preserves_admin_role(
    client: AsyncClient, db_session: Session
) -> None:
    """
    An admin user that also has a linked Doctor row must:
      - Log in and get role='admin' in the token (NOT 'doctor')
      - Still be accepted by /api/v1/me
      - The DB role (admin) is authoritative, not any fallback
    """
    db = db_session
    tenant = create_tenant(db, name=f"dual_{uuid.uuid4().hex[:8]}")
    email = f"dual_{uuid.uuid4().hex[:8]}@example.com"
    user = create_user(
        db,
        email=email,
        password="DualPass9!",
        role=UserRole.admin,
        tenant_id=tenant.id,
    )
    # Link a Doctor row to this admin user (dual-role scenario)
    create_doctor_profile(db, tenant_id=tenant.id, user_id=user.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "DualPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    body = login.json()
    # Primary role remains 'admin' — no escalation
    assert body["role"] == "admin"

    me = await client.get("/api/v1/me", headers=_auth_header(body["access_token"]))
    assert me.status_code == 200
    me_data = me.json()
    assert me_data["role"] == "admin"


@pytest.mark.asyncio
async def test_dual_role_doctor_with_admin_token_role_is_doctor(
    client: AsyncClient, db_session: Session
) -> None:
    """A doctor user logs in and gets role='doctor'. No escalation to admin occurs."""
    db = db_session
    tenant = create_tenant(db, name=f"drdual_{uuid.uuid4().hex[:8]}")
    email = f"drdual_{uuid.uuid4().hex[:8]}@example.com"
    user = create_user(
        db,
        email=email,
        password="DrDual9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    create_doctor_profile(db, tenant_id=tenant.id, user_id=user.id)
    db.commit()

    login = await client.post(
        "/api/v1/login",
        data={"username": email, "password": "DrDual9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["role"] == "doctor"

    me = await client.get("/api/v1/me", headers=_auth_header(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "doctor"


# ---------------------------------------------------------------------------
# Regression: the old fallback must NOT work anymore
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_old_fallback_token_no_longer_grants_admin_access(
    client: AsyncClient, db_session: Session
) -> None:
    """
    A patient user forges a token with no role claim.
    Under the old code this would silently get role='admin'.
    Under the fixed code it must be rejected with 401.
    """
    db = db_session
    email = f"rogue_{uuid.uuid4().hex[:8]}@example.com"
    user = create_user(
        db,
        email=email,
        password="RoguePass9!",
        role=UserRole.patient,
    )
    db.commit()

    # Craft a token with no role claim — simulates old legacy or externally forged token
    forged_token = _build_raw_token({"sub": str(user.id)})

    # Must be rejected — not silently elevated to admin
    resp = await client.get("/api/v1/me", headers=_auth_header(forged_token))
    assert resp.status_code == 401, (
        f"SECURITY REGRESSION: token without role claim was NOT rejected. "
        f"Got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_empty_role_claim_no_longer_grants_admin_access(
    client: AsyncClient, db_session: Session
) -> None:
    """
    A token with role='' must be rejected — previously the empty-string check
    also fell through to role='admin' via the `not role` branch.
    """
    db = db_session
    email = f"empty_{uuid.uuid4().hex[:8]}@example.com"
    user = create_user(
        db,
        email=email,
        password="EmptyPass9!",
        role=UserRole.patient,
    )
    db.commit()

    forged_token = _build_raw_token({"sub": str(user.id), "role": ""})
    resp = await client.get("/api/v1/me", headers=_auth_header(forged_token))
    assert resp.status_code == 401, (
        f"SECURITY REGRESSION: token with empty role claim was NOT rejected. "
        f"Got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# _build_token_payload always emits a role claim (no None-user.role path)
# ---------------------------------------------------------------------------


def test_build_token_payload_always_includes_role(db_session: Session) -> None:
    """
    Verify that _build_token_payload always produces a non-null, non-empty
    role string so _parse_access_token will always accept the resulting token.
    """
    from app.api.v1.endpoints.auth import _build_token_payload

    db = db_session
    tenant = create_tenant(db, name=f"btp_{uuid.uuid4().hex[:8]}")

    for role in UserRole:
        if role == UserRole.super_admin:
            user = create_user(
                db,
                email=f"btp_sa_{uuid.uuid4().hex[:8]}@example.com",
                password="Pw9!",
                role=role,
            )
        elif role == UserRole.patient:
            user = create_user(
                db,
                email=f"btp_pt_{uuid.uuid4().hex[:8]}@example.com",
                password="Pw9!",
                role=role,
            )
        else:
            user = create_user(
                db,
                email=f"btp_{role.value}_{uuid.uuid4().hex[:8]}@example.com",
                password="Pw9!",
                role=role,
                tenant_id=tenant.id,
            )
        db.flush()

        payload = _build_token_payload(user, db)
        role_in_token = payload.get("role")
        assert role_in_token, (
            f"_build_token_payload produced missing/empty role for UserRole.{role.name}"
        )
        assert isinstance(role_in_token, str), (
            f"_build_token_payload produced non-string role for UserRole.{role.name}"
        )
        assert role_in_token == role.value, (
            f"role mismatch: token has '{role_in_token}', expected '{role.value}'"
        )

        # Round-trip: token must parse cleanly
        token = create_access_token(payload)
        parsed = _parse_access_token(token)
        assert parsed.role == role.value
