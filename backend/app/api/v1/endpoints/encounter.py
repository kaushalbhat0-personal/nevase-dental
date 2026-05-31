"""
Encounter Aggregate API endpoint.

GET /encounters/{appointment_id} → EncounterDetailAggregate

This is the SINGLE canonical endpoint for encounter workspace rendering.
It replaces the previous pattern of assembling multiple requests client-side.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_optional_scoped_tenant_id,
    get_resolved_data_scope,
    require_structured_profile_complete,
)
from app.core.data_scope import ResolvedDataScope, restrict_doctor_id_for_detail
from app.core.database import get_db
from app.models.user import User
from app.schemas.encounter import EncounterDetailAggregate
from app.services import encounter_service

router = APIRouter(
    prefix="/encounters",
    tags=["encounters"],
    dependencies=[Depends(require_structured_profile_complete)],
)


@router.get("/{appointment_id}", response_model=EncounterDetailAggregate)
def get_encounter_detail(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
    include_timeline: bool = Query(
        default=True,
        description="Include lightweight patient history context",
    ),
) -> EncounterDetailAggregate:
    """
    Load the canonical EncounterDetailAggregate for the given appointment.

    This endpoint returns ALL encounter data in a single response:
    - appointment (encounter anchor)
    - patient
    - doctor
    - vitals
    - SOAP fields (subjective, objective, assessment, plan)
    - prescriptions
    - inventory usage
    - bill
    - timeline context (optional patient history)

    Authorization is capability-based (existing patterns):
    - assigned doctor
    - clinic admin/owner
    - super_admin
    - authorized patient (future-safe)

    Invariant violations are logged as structured warnings but do NOT block
    the response (fail-safe for reads).
    """
    return encounter_service.get_encounter_detail(
        db,
        appointment_id,
        current_user,
        tenant_id,
        include_timeline=include_timeline,
    )
