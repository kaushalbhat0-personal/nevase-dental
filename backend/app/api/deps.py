import logging
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

logger = logging.getLogger(__name__)

from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.http_exceptions import (
    inactive_user_exception,
    unauthorized_credentials_exception,
)
from app.core.data_scope import ResolvedDataScope, resolve_data_scope
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.tenant_context import MISSING_X_TENANT_ID_MSG, resolve_tenant_id_for_scoped_request
from app.core.workspace_context import (
    ActiveWorkspace,
    WorkspaceSlug,
    is_workspace_allowed_for_role,
)
from app.crud import crud_doctor, crud_doctor_profile, crud_user
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from app.services import doctor_service
from app.services.exceptions import ForbiddenError, ValidationError
from app.core.permissions import require_admin_or_owner

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/login",
    auto_error=False,
)


@dataclass
class TokenPayload:
    user_id: UUID
    role: str
    tenant_id: UUID | None


@dataclass(frozen=True)
class CurrentTenantContext:
    """Resolved RBAC tenant scope for the authenticated principal (see ``resolve_tenant_id_for_scoped_request``)."""

    user: User
    tenant_id: UUID | None


def _parse_access_token(token: str) -> TokenPayload:
    payload = decode_access_token(token)
    if payload is None:
        raise unauthorized_credentials_exception()
    if payload.get("type") != "access":
        raise unauthorized_credentials_exception()
    sub = payload.get("sub")
    if sub is None or not isinstance(sub, str):
        raise unauthorized_credentials_exception()
    try:
        user_id = UUID(sub)
    except ValueError:
        raise unauthorized_credentials_exception()

    # SECURITY INVARIANT: every token issued by this service contains an explicit
    # `role` claim written from user.role.value (a NOT-NULL DB column).  A missing
    # or malformed claim is therefore either a legacy pre-role token (which we
    # must NOT silently upgrade) or a tampered / externally-forged token.
    # Reject it unconditionally — never fall back to a privileged role.
    role = payload.get("role")
    if not role or not isinstance(role, str):
        raise unauthorized_credentials_exception()

    tenant_id = payload.get("tenant_id")
    if tenant_id and isinstance(tenant_id, str):
        try:
            tenant_id = UUID(tenant_id)
        except ValueError:
            tenant_id = None
    else:
        tenant_id = None

    return TokenPayload(user_id=user_id, role=role, tenant_id=tenant_id)


def _user_id_from_access_token(token: str) -> UUID:
    # Kept for backward compatibility with existing code
    return _parse_access_token(token).user_id


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    user_id = _user_id_from_access_token(token)
    user = crud_user.get_user(db, user_id)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = _user_id_from_access_token(token)
    user = crud_user.get_user(db, user_id)
    if user is None:
        raise unauthorized_credentials_exception()
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    logger.debug("[TRACE_MC] entered get_current_active_user: user=%s role=%s active=%s", current_user.id, current_user.role, current_user.is_active)
    if not current_user.is_active:
        raise inactive_user_exception()
    return current_user


def get_current_auth_context(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> TokenPayload:
    auth_ctx = _parse_access_token(token)
    user = crud_user.get_user(db, auth_ctx.user_id)
    if user is None:
        raise unauthorized_credentials_exception()
    if not user.is_active:
        raise inactive_user_exception()
    return auth_ctx


def get_linked_doctor_profile_optional(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Doctor | None:
    """Doctor row linked to this login (any role), for X-Data-Scope resolution."""
    result = crud_doctor.get_doctor_by_user_id(db, current_user.id)
    logger.debug("[TRACE_MC] get_linked_doctor_profile_optional: user=%s role=%s doctor=%s", current_user.id, current_user.role, result.id if result else None)
    return result


def get_resolved_data_scope(
    x_data_scope: str | None = Header(default=None, alias="X-Data-Scope"),
    current_user: User = Depends(get_current_user),
    linked_doctor: Doctor | None = Depends(get_linked_doctor_profile_optional),
) -> ResolvedDataScope:
    logger.debug("[TRACE_MC] get_resolved_data_scope: user=%s role=%s x_data_scope=%s linked_doctor=%s", current_user.id, current_user.role, x_data_scope, linked_doctor.id if linked_doctor else None)
    result = resolve_data_scope(
        x_data_scope, current_user=current_user, linked_doctor=linked_doctor
    )
    logger.debug("[TRACE_MC] get_resolved_data_scope result: kind=%s doctor_id=%s", result.kind.value, result.doctor_id)
    return result


def get_current_doctor(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Doctor:
    """Doctor profile for the current user; use on doctor-only routes."""
    return doctor_service.get_current_doctor(db, current_user)


def require_structured_profile_complete(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """No-op: profile completion is auto-approved for single-clinic mode."""



def require_doctor_verification_approved(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """No-op: verification is auto-approved for single-clinic mode."""


def get_current_users_doctor_for_structured_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Doctor:
    """
    Linked `Doctor` row for structured profile (GET/PUT) without requiring ``is_profile_complete``.
    """
    doctor = crud_doctor.get_doctor_by_user_id(db, current_user.id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No doctor record linked to this account",
        )
    if doctor.tenant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor tenant is not set",
        )
    return doctor


def get_optional_scoped_tenant_id(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-ID"),
) -> UUID | None:
    """Tenant scope for routes that patients may call with ``tenant_id=None`` (e.g. slot reads)."""
    return resolve_tenant_id_for_scoped_request(db, current_user, x_tenant_id)


def get_optional_scoped_tenant_id_optional_user(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-ID"),
) -> UUID | None:
    """Like ``get_optional_scoped_tenant_id`` but when there is no Bearer token (public slot reads)."""
    if current_user is None:
        return None
    return resolve_tenant_id_for_scoped_request(db, current_user, x_tenant_id)


def get_optional_scoped_tenant_id_active(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-ID"),
) -> UUID | None:
    """Like ``get_optional_scoped_tenant_id`` but requires an active user (mutations)."""
    logger.debug("[TRACE_MC] entered get_optional_scoped_tenant_id_active: user=%s role=%s x_tenant_id=%s", current_user.id, current_user.role, x_tenant_id)
    result = resolve_tenant_id_for_scoped_request(db, current_user, x_tenant_id)
    logger.debug("[TRACE_MC] get_optional_scoped_tenant_id_active result=%s", result)
    return result


def get_scoped_tenant_id(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-ID"),
) -> UUID:
    tid = resolve_tenant_id_for_scoped_request(db, current_user, x_tenant_id)
    if tid is None:
        raise ValidationError(MISSING_X_TENANT_ID_MSG)
    return tid


def get_scoped_tenant_id_active(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-ID"),
) -> UUID:
    tid = resolve_tenant_id_for_scoped_request(db, current_user, x_tenant_id)
    if tid is None:
        raise ValidationError(MISSING_X_TENANT_ID_MSG)
    return tid


def get_current_tenant_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-ID"),
) -> CurrentTenantContext:
    tenant_id = resolve_tenant_id_for_scoped_request(db, current_user, x_tenant_id)
    return CurrentTenantContext(user=current_user, tenant_id=tenant_id)


def get_current_tenant_context_active(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-ID"),
) -> CurrentTenantContext:
    tenant_id = resolve_tenant_id_for_scoped_request(db, current_user, x_tenant_id)
    return CurrentTenantContext(user=current_user, tenant_id=tenant_id)


def require_current_user_admin_or_owner(
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_scoped_tenant_id_active),
    current_user: User = Depends(get_current_active_user),
) -> User:
    """FastAPI guard: org admin, staff, super_admin, or practice owner in ``tenant_id``."""
    try:
        require_admin_or_owner(db, current_user, tenant_id)
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
        ) from e
    return current_user


# Alias for clinic_operations endpoint (maps to get_scoped_tenant_id)
get_current_tenant_id = get_scoped_tenant_id


def get_active_workspace(
    x_workspace: str | None = Header(default=None, alias="X-Workspace"),
    current_user: User = Depends(get_current_active_user),
) -> ActiveWorkspace | None:
    """Resolve the request-scoped active workspace from the ``X-Workspace`` header.

    Returns ``None`` when the header is absent (backward-compatible fallback).
    Returns ``None`` for invalid slugs (graceful fallback).
    Returns ``None`` for workspaces the user's role is not allowed to activate.

    DESIGN: Workspace is UI/operational context, NOT authorization authority.
    Authorization happens ONLY through:
      - capability checks (has_clinician_capability)
      - tenant/resource ownership (assert_authorized)
      - explicit service authorization (authorize_appointment_access)

    This is an **optional** dependency — endpoints that do not inject it
    behave exactly as before.
    """
    logger.debug("[TRACE_MC] entered get_active_workspace: user=%s role=%s x_workspace=%s", current_user.id, current_user.role, x_workspace)
    if x_workspace is None:
        logger.debug("[TRACE_MC] get_active_workspace: no header -> None")
        return None

    try:
        slug = WorkspaceSlug(x_workspace.strip().lower())
    except ValueError:
        logger.warning("[WORKSPACE] Invalid workspace slug: '%s' -> falling back to None", x_workspace)
        return None

    if not is_workspace_allowed_for_role(current_user.role, slug):
        logger.warning(
            "[WORKSPACE] Workspace '%s' not allowed for role '%s' -> falling back to None (not blocking)",
            slug.value,
            current_user.role,
        )
        return None

    logger.warning(
        "[WORKSPACE DEBUG] header=%s resolved=%s role=%s",
        x_workspace,
        slug.value,
        current_user.role,
    )
    return ActiveWorkspace(slug=slug)
