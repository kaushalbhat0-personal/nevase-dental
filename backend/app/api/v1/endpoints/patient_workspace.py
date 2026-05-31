"""
Patient Health Workspace API endpoints — READ-ONLY aggregate for the patient portal.

These endpoints compose existing domain data into a patient-friendly workspace.
They enforce strict patient-scoped access and NEVER expose SOAP/doctor-only fields.

Architecture:
  - Appointment remains the encounter anchor
  - No separate Encounter table exists
  - Patient workspace is READ-ORIENTED (doctor workflows mutate)
  - Patient identity is resolved from current_user (never from request params)

Authorization:
  - Patient-only access (non-patients receive 403)
  - Tenant isolation via existing data_scope patterns
  - Encounter ownership validated by patient_id scoping
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_scoped_tenant_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.patient_workspace import (
    EncounterCard,
    FollowUpSummary,
    PatientHealthWorkspaceAggregate,
    VitalsSnapshot,
)
from app.services import patient_workspace_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/patient/workspace",
    tags=["patient-workspace"],
)


@router.get("", response_model=PatientHealthWorkspaceAggregate)
def get_patient_workspace(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> PatientHealthWorkspaceAggregate:
    """
    Get the full Patient Health Workspace aggregate for the authenticated patient.

    Returns a comprehensive workspace including:
    - Patient profile
    - Upcoming appointments
    - Recent encounters (timeline)
    - Vitals history
    - Prescriptions history
    - Follow-up recommendations
    - Billing summary
    - Recent documents
    - Communication summary (future-ready)

    CRITICAL:
    - Patient access is strictly scoped to their own data
    - SOAP internal sections are NEVER exposed
    - Doctor-only notes are NEVER exposed
    - Audit metadata is NEVER exposed
    """
    return patient_workspace_service.get_patient_workspace(db, current_user)


@router.get("/encounters", response_model=list[EncounterCard])
def get_patient_encounters(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> list[EncounterCard]:
    """
    Get paginated encounter cards for the patient timeline.

    Returns patient-safe encounter summaries (NO SOAP fields).
    Ordered by appointment time (newest first).
    """
    return patient_workspace_service.get_patient_encounters(
        db, current_user, skip=skip, limit=limit
    )


@router.get("/vitals", response_model=list[VitalsSnapshot])
def get_patient_vitals_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> list[VitalsSnapshot]:
    """
    Get chronological vitals history for the patient.

    Returns all vitals snapshots ordered by appointment time (newest first).
    Future-ready for chart/analytics integrations.
    """
    return patient_workspace_service.get_patient_vitals_history(db, current_user)


@router.get("/follow-ups", response_model=FollowUpSummary)
def get_patient_follow_ups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> FollowUpSummary:
    """
    Get follow-up summary for the patient.

    Returns upcoming and overdue follow-ups with doctor details.
    Future-ready for reminder automation and AI follow-up summaries.
    """
    return patient_workspace_service.get_patient_follow_ups(db, current_user)
