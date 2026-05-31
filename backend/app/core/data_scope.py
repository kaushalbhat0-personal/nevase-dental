"""Resolve X-Data-Scope with server-side enforcement (never trust the header alone)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal
from uuid import UUID

from sqlalchemy import exists, false
from sqlalchemy.sql import Select

from app.core.permissions import has_tenant_admin_privileges
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from app.services.exceptions import ForbiddenError


class DataScopeKind(str, Enum):
    doctor = "doctor"
    tenant = "tenant"


@dataclass(frozen=True)
class ResolvedDataScope:
    """Effective scope after RBAC."""

    kind: DataScopeKind
    doctor_id: UUID | None


def resolve_data_scope(
    header_value: str | None,
    *,
    current_user: User,
    linked_doctor: Doctor | None,
) -> ResolvedDataScope:
    raw = (header_value or "tenant").strip().lower()
    if raw not in ("doctor", "tenant"):
        raw = "tenant"
    requested = DataScopeKind(raw)

    if current_user.role == UserRole.patient:
        return ResolvedDataScope(kind=DataScopeKind.tenant, doctor_id=None)

    can_tenant = has_tenant_admin_privileges(current_user)
    doc_id: UUID | None = linked_doctor.id if linked_doctor is not None else None

    effective = requested
    if effective == DataScopeKind.tenant and not can_tenant:
        effective = DataScopeKind.doctor

    if effective == DataScopeKind.doctor and doc_id is None:
        if can_tenant:
            effective = DataScopeKind.tenant
        else:
            raise ForbiddenError("Doctor profile required for practice-scoped data")

    if effective == DataScopeKind.doctor:
        return ResolvedDataScope(kind=DataScopeKind.doctor, doctor_id=doc_id)
    return ResolvedDataScope(kind=DataScopeKind.tenant, doctor_id=None)


def restrict_doctor_id_for_detail(
    data_scope: ResolvedDataScope,
    current_user: User,
) -> UUID | None:
    """When set, single-resource reads/mutations must belong to this doctor cohort."""
    if data_scope.kind != DataScopeKind.doctor or data_scope.doctor_id is None:
        return None
    if current_user.role in (
        UserRole.admin,
        UserRole.staff,
        UserRole.super_admin,
    ):
        return data_scope.doctor_id
    if current_user.role == UserRole.doctor and current_user.is_owner:
        return data_scope.doctor_id
    return None


def apply_patient_scope(
    stmt: Select,
    user: User,
    *,
    data_scope_kind: Literal["doctor", "tenant"],
    doctor_id: UUID | None = None,
    tenant_id: UUID | None = None,
) -> Select:
    """
    Single source of truth for patient list visibility.

    - tenant scope: non-deleted appointment with ``Appointment.tenant_id == tenant_id``.
    - doctor scope: EXISTS active appointment for ``doctor_id`` (unchanged).
    """
    from app.models.appointment import Appointment
    from app.models.patient import Patient

    ex_appt = exists().where(
        Appointment.patient_id == Patient.id,
        Appointment.doctor_id == doctor_id,
        Appointment.is_deleted == False,  # noqa: E712
    )
    if data_scope_kind == "doctor":
        if doctor_id is None:
            return stmt.where(false())
        return stmt.where(ex_appt)
    if tenant_id is None:
        return stmt.where(false())
    has_appt_in_tenant = exists().where(
        Appointment.patient_id == Patient.id,
        Appointment.tenant_id == tenant_id,
        Appointment.is_deleted == False,  # noqa: E712
    )
    belongs_to_tenant = Patient.tenant_id == tenant_id
    if user.role in (UserRole.admin, UserRole.staff, UserRole.super_admin):
        return stmt.where(has_appt_in_tenant | belongs_to_tenant)
    if user.role == UserRole.doctor and user.is_owner:
        return stmt.where(has_appt_in_tenant | belongs_to_tenant)
    return stmt.where(false())
