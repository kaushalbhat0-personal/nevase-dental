"""
Request-scoped active workspace context.

This module provides the ``ActiveWorkspace`` dataclass and validation helpers
for the X-Workspace header propagation system.

DESIGN PRINCIPLE
    Workspace = UX/Operational Context (what screen the user is looking at)
    Role      = Identity (who the user is, unchanged)
    Capabilities = Authorization (checked via service-layer guards)

CRITICAL: Workspace is NOT an authorization authority.
Authorization happens ONLY through:
  - capability checks (has_clinician_capability)
  - tenant/resource ownership (assert_authorized)
  - explicit service authorization (authorize_appointment_access)

There is NO ``effective_role`` mapping. An admin in the doctor workspace
is still an admin — they just get scoped elevation at specific bottleneck
checks (doctor-record requirement, inventory doctor-scope, etc.).

SECURITY
    - ``ROLE_ALLOWED_WORKSPACES`` is an informational whitelist per role.
    - Workspace mismatch does NOT block operations — it falls back gracefully.
    - Tenant isolation is preserved by upstream ``assert_authorized()`` calls.
    - Audit logs remain truthful: ``role=admin workspace=doctor``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.models.user import User, UserRole


class WorkspaceSlug(Enum):
    """Canonical workspace slugs. These match the frontend workspace registry keys."""

    frontdesk = "frontdesk"
    doctor = "doctor"
    nurse = "nurse"
    operations = "operations"
    procurement = "procurement"
    finance = "finance"
    admin = "admin"
    patient = "patient"


# Explicit whitelist per role — no blanket defaults.
# Each role can only activate certain workspaces.
# Adding a new workspace requires explicit addition here.
ROLE_ALLOWED_WORKSPACES: dict[UserRole, list[WorkspaceSlug]] = {
    UserRole.super_admin: [
        WorkspaceSlug.admin,
        WorkspaceSlug.doctor,
        WorkspaceSlug.nurse,
        WorkspaceSlug.frontdesk,
        WorkspaceSlug.operations,
        WorkspaceSlug.procurement,
        WorkspaceSlug.finance,
        WorkspaceSlug.patient,
    ],
    UserRole.admin: [
        WorkspaceSlug.admin,
        WorkspaceSlug.doctor,
        WorkspaceSlug.frontdesk,
        WorkspaceSlug.operations,
        WorkspaceSlug.procurement,
        WorkspaceSlug.finance,
    ],
    UserRole.staff: [
        WorkspaceSlug.frontdesk,
        WorkspaceSlug.operations,
    ],
    UserRole.doctor: [
        WorkspaceSlug.doctor,
    ],
    UserRole.patient: [
        WorkspaceSlug.patient,
    ],
}


@dataclass(frozen=True)
class ActiveWorkspace:
    """Request-scoped workspace context.

    This is operational context only — it does NOT change the user's role.
    Authorization decisions should check ``current_user.role`` AND
    ``active_workspace.slug`` together.
    """

    slug: WorkspaceSlug


def is_workspace_allowed_for_role(
    role: UserRole,
    slug: WorkspaceSlug,
) -> bool:
    """Check whether *role* is permitted to activate *slug*.

    Returns ``True`` if the role is in the explicit whitelist for this slug.
    """
    allowed = ROLE_ALLOWED_WORKSPACES.get(role, [])
    return slug in allowed


def is_elevated_workspace_access(
    current_user: User,
    active_workspace: ActiveWorkspace | None,
    *,
    target_slug: WorkspaceSlug = WorkspaceSlug.doctor,
) -> bool:
    """Check if the user has elevated access through a workspace context.

    Returns ``True`` when:
    - The user is admin or super_admin
    - AND the active workspace matches *target_slug*

    This is the canonical pattern for scoped elevation checks.
    """
    if active_workspace is None:
        return False
    if current_user.role not in (UserRole.admin, UserRole.super_admin):
        return False
    return active_workspace.slug == target_slug
