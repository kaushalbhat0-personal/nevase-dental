from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    get_current_user,
    get_optional_scoped_tenant_id,
    get_optional_scoped_tenant_id_active,
    get_resolved_data_scope,
    require_doctor_verification_approved,
    require_structured_profile_complete,
)
from app.core.data_scope import ResolvedDataScope, restrict_doctor_id_for_detail
from app.core.database import get_db
from app.models.billing import BillingStatus
from app.models.user import User
from app.schemas.billing import BillingCreate, BillingRead, BillingUpdate
from app.services import billing_service

router = APIRouter(
    prefix="/bills",
    tags=["bills"],
    dependencies=[Depends(require_structured_profile_complete)],
)


@router.post("", response_model=BillingRead, status_code=201)
def create_bill(
    payload: BillingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id_active),
    _verified: None = Depends(require_doctor_verification_approved),
) -> BillingRead:
    return billing_service.create_bill(
        db, payload, current_user, tenant_id
    )


@router.get("", response_model=list[BillingRead])
def read_bills(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    patient_id: UUID | None = None,
    appointment_id: UUID | None = None,
    status: BillingStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> list[BillingRead]:
    return billing_service.get_bills(
        db,
        current_user,
        skip=skip,
        limit=limit,
        patient_id=patient_id,
        appointment_id=appointment_id,
        status=status,
        tenant_id=tenant_id,
        data_scope=data_scope,
    )


@router.get("/{bill_id}", response_model=BillingRead)
def read_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> BillingRead:
    bill = billing_service.get_bill_or_404(db, bill_id)
    billing_service.authorize_bill_read(
        db,
        bill,
        current_user,
        tenant_id,
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )
    return bill


@router.put("/{bill_id}", response_model=BillingRead)
def update_bill(
    bill_id: UUID,
    payload: BillingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> BillingRead:
    return billing_service.update_bill(
        db,
        bill_id,
        payload,
        current_user,
        tenant_id,
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )


@router.get("/revenue/total", response_model=dict[str, float])
def get_total_revenue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> dict[str, float]:
    total = billing_service.get_total_revenue(db, tenant_id=tenant_id)
    return {"total_revenue": total}


@router.get("/revenue/today", response_model=dict[str, float])
def get_today_revenue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> dict[str, float]:
    today = billing_service.get_today_revenue(db, tenant_id=tenant_id)
    return {"today_revenue": today}


@router.get("/revenue/pending", response_model=dict[str, int | float])
def get_pending_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> dict[str, int | float]:
    return billing_service.get_pending_payments(db, tenant_id=tenant_id)


@router.post("/{bill_id}/pay", response_model=BillingRead)
def pay_bill(
    bill_id: UUID,
    payment_method: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> BillingRead:
    """Mark a bill as paid."""
    return billing_service.mark_bill_paid(
        db,
        bill_id,
        current_user,
        tenant_id,
        payment_method=payment_method,
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
) -> Response:
    """Soft delete a bill."""
    billing_service.soft_delete_bill(
        db,
        bill_id,
        current_user,
        tenant_id,
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
