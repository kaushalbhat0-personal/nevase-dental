import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.request_context import get_request_id
from app.models.user import User
from app.services.exceptions import ForbiddenError

logger = logging.getLogger(__name__)


def log_rbac_mutation_violation(
    current_user: User,
    resource: str,
    *,
    action: str | None = None,
    tenant_type: str | None = None,
) -> None:
    logger.warning(
        "[RBAC] denied user=%s role=%s resource=%s action=%s tenant_type=%s",
        current_user.id,
        current_user.role,
        resource,
        action if action is not None else "-",
        tenant_type if tenant_type is not None else "-",
    )


def enforce_tenant_match(
    resource_tenant_id: UUID | None,
    tenant_id: UUID | None,
    current_user: User,
    resource: str,
) -> None:
    if tenant_id is None:
        log_rbac_mutation_violation(current_user, resource)
        raise ForbiddenError("Tenant context required")
    if resource_tenant_id is None:
        log_rbac_mutation_violation(current_user, resource)
        raise ForbiddenError("Resource tenant is not set")
    if resource_tenant_id != tenant_id:
        log_rbac_mutation_violation(current_user, resource)
        raise ForbiddenError("Resource is not in your tenant")


def assert_authorized(
    action: str,
    resource: str,
    current_user: User,
    tenant_id: UUID | None,
    *,
    resource_tenant_id: UUID | None,
) -> None:
    """Tenant isolation: request scope and resource tenant must both be present and equal."""
    enforce_tenant_match(resource_tenant_id, tenant_id, current_user, resource)


def log_audit_mutation(
    action: str,
    current_user: User,
    resource: str,
    resource_id: Any,
    tenant_id: UUID | None,
    *,
    status: str = "success",
    extra: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    rid = request_id if request_id is not None else get_request_id()
    payload: dict[str, Any] = {
        "action": action,
        "resource": resource,
        "resource_id": str(resource_id) if resource_id is not None else None,
        "tenant_id": str(tenant_id) if tenant_id is not None else None,
        "actor_id": str(current_user.id),
        "actor_user_id": str(current_user.id),
        "actor_role": (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else str(current_user.role)
        ),
        "ts": ts,
        "timestamp": ts,
        "status": status,
    }
    if rid:
        payload["request_id"] = rid
    if extra:
        for k, v in extra.items():
            if v is not None:
                payload[k] = v
    logger.info("[AUDIT] %s", json.dumps(payload, default=str))


def log_structured_audit_event(
    *,
    event: str,
    tenant_id: UUID | None,
    resource_id: str | None,
    actor_id: str,
    status: str = "success",
    request_id: str | None = None,
    ts: datetime | None = None,
    **fields: Any,
) -> None:
    """Stable JSON envelope for downstream log analytics."""
    t = ts or datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "event": event,
        "tenant_id": str(tenant_id) if tenant_id is not None else None,
        "resource_id": resource_id,
        "actor_id": actor_id,
        "status": status,
        "ts": t.isoformat(),
    }
    rid = request_id if request_id is not None else get_request_id()
    if rid:
        payload["request_id"] = rid
    for k, v in fields.items():
        if v is not None:
            payload[k] = v
    logger.info("[AUDIT] %s", json.dumps(payload, default=str))
