"""
Explicit clinician capability helpers.

This module provides the canonical way to determine whether a user has
clinician capability — i.e., the authority to perform clinical actions
such as completing encounters, prescribing, and consuming visit inventory.

DESIGN PRINCIPLE
    Clinician capability is derived from the user's identity and data
    linkages, NOT from workspace context. A tenant doctor in the finance
    workspace is still a clinician. A pure admin (no Doctor record) in
    the doctor workspace is NOT a clinician.

CAPABILITY RULE
    A user has clinician capability if ANY of the following are true:
    1. current_user.role == doctor
    2. user has normalized role "doctor" (for dual-role users)
    3. user is linked to a Doctor record via user_id
    4. dual-role admin+doctor user

    A pure admin WITHOUT doctor linkage:
    - must NOT complete encounters
    - must NOT prescribe
    - must NOT consume clinical inventory

USAGE
    from app.core.clinical_capabilities import has_clinician_capability

    if not has_clinician_capability(db, current_user):
        raise ForbiddenError("Only clinicians can perform this action")
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User

logger = logging.getLogger(__name__)


def resolve_doctor_for_user(db: Session, current_user: User) -> object | None:
    """Look up a Doctor record linked to this user.

    Returns the Doctor ORM object if one exists, or ``None`` if the user
    has no linked doctor profile.

    This is a tenant-safe lookup — it does NOT bypass tenant isolation.
    The caller must still verify tenant alignment when using the result.
    """
    from app.crud.crud_doctor import get_doctor_by_user_id

    return get_doctor_by_user_id(db, current_user.id)


def has_clinician_capability(db: Session, current_user: User) -> bool:
    """Return ``True`` if *current_user* has clinician capability.

    This is the SINGLE source of truth for clinical authorization.
    It does NOT consider workspace context, admin elevation, or any
    other non-clinical factors.

    See module docstring for the full capability rule.
    """
    # 1. Direct role check — fastest path
    if current_user.role == "doctor":
        return True

    # 2. Normalized role check — handles dual-role users (admin+doctor)
    #    where the User model may have a `roles` attribute with "doctor"
    if hasattr(current_user, "roles") and isinstance(current_user.roles, list):
        if "doctor" in current_user.roles:
            return True

    # 3. Doctor record linkage — any user with a Doctor row via user_id
    #    This catches admin+doctor, staff+doctor, etc.
    doctor = resolve_doctor_for_user(db, current_user)
    if doctor is not None:
        return True

    return False
