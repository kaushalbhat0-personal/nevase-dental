"""
Clinic Operations API endpoints — read-only operational visibility.

These endpoints wrap the existing clinic_operations_service aggregation layer.
NO new database models or schemas are created.
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.clinic_operations import (
    ActivityStreamResponse,
    ClinicOperationsDashboard,
    DoctorOperationsView,
    OperationalAlertList,
    OperationalTaskList,
)
from app.services import clinic_operations_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/dashboard", response_model=ClinicOperationsDashboard)
def get_operations_dashboard(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    tenant_id: UUID = Depends(deps.get_current_tenant_id),
) -> ClinicOperationsDashboard:
    """Get the complete clinic operations dashboard aggregate."""
    return clinic_operations_service.get_clinic_operations_dashboard(db, tenant_id)


@router.get("/tasks", response_model=OperationalTaskList)
def get_operations_tasks(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    tenant_id: UUID = Depends(deps.get_current_tenant_id),
) -> OperationalTaskList:
    """Get operational tasks grouped by priority."""
    return clinic_operations_service.get_operational_tasks(db, tenant_id)


@router.get("/activity-stream", response_model=ActivityStreamResponse)
def get_operations_activity_stream(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    tenant_id: UUID = Depends(deps.get_current_tenant_id),
) -> ActivityStreamResponse:
    """Get the clinic activity stream (paginated)."""
    return clinic_operations_service.get_activity_stream(db, tenant_id, skip=skip, limit=limit)


@router.get("/alerts", response_model=OperationalAlertList)
def get_operations_alerts(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    tenant_id: UUID = Depends(deps.get_current_tenant_id),
) -> OperationalAlertList:
    """Get operational alerts grouped by severity."""
    return clinic_operations_service.get_operational_alerts(db, tenant_id)


@router.get("/doctor-view", response_model=DoctorOperationsView)
def get_doctor_operations_view(
    doctor_id: UUID = Query(..., description="Doctor ID to get operations view for"),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    tenant_id: UUID = Depends(deps.get_current_tenant_id),
) -> DoctorOperationsView:
    """Get a doctor-specific operations view with queue and quick actions."""
    return clinic_operations_service.get_doctor_operations_view(db, tenant_id, doctor_id)
