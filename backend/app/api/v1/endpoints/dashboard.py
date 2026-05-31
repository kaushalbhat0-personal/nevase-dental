import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_resolved_data_scope,
    get_scoped_tenant_id,
    require_structured_profile_complete,
)
from app.core.data_scope import DataScopeKind, ResolvedDataScope
from app.core.database import get_db
from app.core.metrics import get_counters_snapshot
from app.core.permissions import has_tenant_admin_privileges
from app.core.tenant_context import MISSING_X_TENANT_ID_MSG
from app.models.user import User
from app.schemas.dashboard import (
    AdminDashboardMetricsResponse,
    DashboardResponse,
    DoctorPerformanceItem,
    RevenueTrendItem,
)
from app.services import dashboard_service

router = APIRouter(dependencies=[Depends(require_structured_profile_complete)])
admin_router = APIRouter(
    tags=["admin", "dashboard"],
    dependencies=[Depends(require_structured_profile_complete)],
)
logger = logging.getLogger(__name__)


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> DashboardResponse:
    """
    Get dashboard statistics including:
    - Total patients count
    - Total doctors count
    - Today's appointments count
    - Total revenue (sum of paid bills)
    """
    logger.info("Dashboard endpoint hit - fetching stats")

    doc_id = (
        data_scope.doctor_id
        if data_scope.kind == DataScopeKind.doctor
        else None
    )
    stats = dashboard_service.get_dashboard_stats_for_tenant(
        db, tenant_id, doctor_id=doc_id
    )

    logger.info(
        "Dashboard stats returned - patients: %s, doctors: %s, today_appointments: %s, revenue: %s",
        stats["total_patients"],
        stats["total_doctors"],
        stats["today_appointments"],
        stats["total_revenue"],
    )

    return DashboardResponse(**stats)


@admin_router.get("/dashboard/metrics", response_model=AdminDashboardMetricsResponse)
def get_admin_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
    x_tenant_id: UUID | None = Header(
        default=None,
        alias="X-Tenant-ID",
        description="Tenant to scope admin dashboard metrics (required)",
    ),
    _legacy_tenant_id: UUID | None = Query(
        default=None,
        alias="tenant_id",
        description="Deprecated; use X-Tenant-ID. Ignored.",
    ),
) -> AdminDashboardMetricsResponse:
    dashboard_service.authorize_admin_dashboard_access(current_user)
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail=MISSING_X_TENANT_ID_MSG)
    tenant_id = dashboard_service.resolve_admin_metrics_tenant_id(db, current_user, x_tenant_id)
    logger.info("TENANT ID: %s", tenant_id)
    doc_id = (
        data_scope.doctor_id
        if data_scope.kind == DataScopeKind.doctor
        else None
    )
    metrics = dashboard_service.get_admin_dashboard_metrics(
        db, tenant_id, doctor_id=doc_id
    )
    return AdminDashboardMetricsResponse.model_validate(metrics)


@admin_router.get("/dashboard/revenue-trend", response_model=list[RevenueTrendItem])
def get_admin_revenue_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
    x_tenant_id: UUID | None = Header(
        default=None,
        alias="X-Tenant-ID",
    ),
    _legacy_tenant_id: UUID | None = Query(
        default=None,
        alias="tenant_id",
        description="Deprecated; use X-Tenant-ID. Ignored.",
    ),
) -> list[RevenueTrendItem]:
    dashboard_service.authorize_admin_dashboard_access(current_user)
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail=MISSING_X_TENANT_ID_MSG)
    tenant_id = dashboard_service.resolve_admin_metrics_tenant_id(db, current_user, x_tenant_id)
    logger.info("TENANT ID: %s", tenant_id)
    doc_id = (
        data_scope.doctor_id
        if data_scope.kind == DataScopeKind.doctor
        else None
    )
    rows = dashboard_service.get_revenue_trend(db, tenant_id, doctor_id=doc_id)
    return [RevenueTrendItem.model_validate(x) for x in rows]


@admin_router.get(
    "/dashboard/doctor-performance",
    response_model=list[DoctorPerformanceItem],
)
def get_admin_doctor_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
    x_tenant_id: UUID | None = Header(
        default=None,
        alias="X-Tenant-ID",
    ),
    _legacy_tenant_id: UUID | None = Query(
        default=None,
        alias="tenant_id",
        description="Deprecated; use X-Tenant-ID. Ignored.",
    ),
) -> list[DoctorPerformanceItem]:
    dashboard_service.authorize_admin_dashboard_access(current_user)
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail=MISSING_X_TENANT_ID_MSG)
    tenant_id = dashboard_service.resolve_admin_metrics_tenant_id(db, current_user, x_tenant_id)
    logger.info("TENANT ID: %s", tenant_id)
    doc_id = (
        data_scope.doctor_id
        if data_scope.kind == DataScopeKind.doctor
        else None
    )
    rows = dashboard_service.get_doctor_performance(db, tenant_id, doctor_id=doc_id)
    return [DoctorPerformanceItem.model_validate(x) for x in rows]


@admin_router.get("/observability/metrics")
def get_observability_metrics(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Process-local counters (appointments completed, inventory deductions, idempotency, RBAC)."""
    if not has_tenant_admin_privileges(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return {"counters": get_counters_snapshot()}



