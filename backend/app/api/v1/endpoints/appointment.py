import logging
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, Body, HTTPException, status

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from app.api.deps import (
    get_active_workspace,
    get_current_active_user,
    get_current_user,
    get_optional_scoped_tenant_id,
    get_optional_scoped_tenant_id_active,
    get_resolved_data_scope,
    require_doctor_verification_approved,
    require_structured_profile_complete,
)
from app.core.workspace_context import ActiveWorkspace
from app.core.config import settings
from app.core.data_scope import ResolvedDataScope, restrict_doctor_id_for_detail
from app.core.database import get_db
from app.models.appointment import AppointmentStatus
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    MarkAppointmentCompletedRequest,
)
from app.services import appointment_service


router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
    dependencies=[Depends(require_structured_profile_complete)],
)


class AppointmentListType(str, Enum):
    past = "past"
    upcoming = "upcoming"


@router.post("", response_model=AppointmentRead, status_code=201)
def create_appointment(
    response: Response,
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id_active),
    _verified: None = Depends(require_doctor_verification_approved),
) -> AppointmentRead:
    appt, idempotent_replay = appointment_service.create_appointment(
        db,
        payload,
        current_user,
        tenant_id,
        idempotency_key=idempotency_key,
    )
    if idempotent_replay:
        response.headers["X-Idempotent-Replay"] = "1"
    return appointment_service.appointment_to_read(db, appt)


@router.get("", response_model=list[AppointmentRead])
def read_appointments(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    doctor_id: UUID | None = None,
    patient_id: UUID | None = None,
    appt_type: AppointmentListType | None = Query(default=None, alias="type"),
    status: AppointmentStatus | None = Query(default=None, description="Filter by exact status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> list[AppointmentRead]:
    return appointment_service.get_appointments(
        db,
        current_user,
        skip=skip,
        limit=limit,
        doctor_id=doctor_id,
        patient_id=patient_id,
        tenant_id=tenant_id,
        list_type=appt_type.value if appt_type is not None else None,
        appt_status=status,
        data_scope=data_scope,
    )


@router.post("/{appointment_id}/mark-completed", response_model=AppointmentRead)
def mark_appointment_completed(
    appointment_id: UUID,
    response: Response,
    data: MarkAppointmentCompletedRequest | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id_active),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    active_workspace: ActiveWorkspace | None = Depends(get_active_workspace),
) -> AppointmentRead:
    logger.debug("[TRACE_MC] ENTERED endpoint handler")
    effective = data if data is not None else MarkAppointmentCompletedRequest()
    logger.warning(
        "[ENDPOINT DEBUG] active_workspace=%s slug=%s role=%s",
        active_workspace,
        active_workspace.slug.value if active_workspace else None,
        current_user.role,
    )
    try:
        appt, idempotent_replay = appointment_service.mark_appointment_completed(
            db,
            appointment_id,
            current_user,
            tenant_id,
            restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
            completion=effective,
            idempotency_key=idempotency_key,
            active_workspace=active_workspace,
        )
        if idempotent_replay:
            response.headers["X-Idempotent-Replay"] = "1"
        return appointment_service.appointment_to_read(db, appt)
    except Exception as e:
        logger.exception("[MARK_COMPLETED_EXCEPTION] type=%s msg=%s", type(e).__name__, str(e))
        raise


@router.get("/{appointment_id}", response_model=AppointmentRead)
def read_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> AppointmentRead:
    appointment = appointment_service.get_appointment_or_404(db, appointment_id)
    appointment_service.authorize_appointment_read(
        db,
        appointment,
        current_user,
        tenant_id,
        rbac_action="read_appointment",
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )
    return appointment_service.appointment_to_read(db, appointment)


@router.put("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: UUID,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> AppointmentRead:
    updated = appointment_service.update_appointment(
        db,
        appointment_id,
        payload,
        current_user,
        tenant_id,
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )
    return appointment_service.appointment_to_read(db, updated)


@router.delete("/{appointment_id}", response_model=AppointmentRead)
def delete_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> AppointmentRead:
    deleted = appointment_service.delete_appointment(
        db,
        appointment_id,
        current_user,
        tenant_id,
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )
    return appointment_service.appointment_to_read(db, deleted)
