import logging

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.schemas.auth import ResetPasswordRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.services import auth_service, doctor_profile_service
from app.services.user_roles_service import roles_and_doctor_id_for_user, user_response_with_roles

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


def _build_token_payload(user, db: Session) -> dict:
    """
    Build the JWT payload used by the frontend to determine:
    - **who** the user is (`sub`)
    - **what** the user can see (`role`, `roles`)
    - **which tenant** to scope requests to (`tenant_id`, when applicable)

    ``super_admin`` has no fixed tenant (client sends ``X-Tenant-ID`` per request).
    Otherwise we prefer ``users.tenant_id``, then legacy ``user_tenant`` primary row.
    """
    eff_roles, linked_doctor_id = roles_and_doctor_id_for_user(db, user)
    dpc = doctor_profile_service.doctor_profile_complete_for_user(db, user_id=user.id)
    payload = {
        "sub": str(user.id),
        "type": "access",
        "role": user.role.value,  # NOT NULL in DB — no fallback needed or permitted
        "roles": eff_roles,
        "tenant_id": None,
        "is_owner": user.is_owner,
        "doctor_id": str(linked_doctor_id) if linked_doctor_id is not None else None,
    }
    if dpc is not None:
        payload["doctor_profile_complete"] = dpc
    if user.role == UserRole.super_admin:
        return payload
    if user.tenant_id is not None:
        payload["tenant_id"] = str(user.tenant_id)
        return payload
    if user.tenant_associations:
        primary = next(
            (ta for ta in user.tenant_associations if ta.is_primary),
            user.tenant_associations[0],
        )
        payload["tenant_id"] = str(primary.tenant_id)
    return payload


@router.post("/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> Token:
    """Create a new user and return an access token for immediate sign-in."""
    user = auth_service.register_user(db, payload)
    access_token = create_access_token(_build_token_payload(user, db))
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response_with_roles(db, user),
    )


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 login endpoint.

    FastAPI's OAuth2PasswordRequestForm uses a `username` field even when the application
    authenticates by email. We treat `username` as the user's email address.
    """
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if user.force_password_reset:
        logger.warning("[PASSWORD RESET REQUIRED] user_id=%s", user.id)
    token_payload = _build_token_payload(user, db)
    access_token = create_access_token(token_payload)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": token_payload["role"],
        "roles": token_payload["roles"],
        "tenant_id": token_payload["tenant_id"],
        "doctor_id": token_payload.get("doctor_id"),
        "doctor_profile_complete": token_payload.get("doctor_profile_complete"),
        "is_owner": user.is_owner,
        "force_password_reset": user.force_password_reset,
    }


@router.post("/auth/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    """Authenticated password change (requires current password)."""
    auth_service.reset_password(db, current_user, body.old_password, body.new_password)
    return {"detail": "Password updated"}
