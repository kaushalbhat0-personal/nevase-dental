from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_user_optional
from app.core.database import get_db
from app.crud import crud_tenant
from app.models.tenant import Tenant, TenantType
from app.models.user import User, UserRole
from app.schemas.tenant import (
    TenantCreate,
    TenantPublicRead,
    UpgradeToOrganizationRequest,
    UpgradeToOrganizationResponse,
)
from app.services import tenant_service
from app.services.exceptions import ForbiddenError, NotFoundError
from app.services.user_roles_service import roles_and_doctor_id_for_user

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "",
    response_model=TenantPublicRead,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> TenantPublicRead:
    tenant, admin_email = tenant_service.create_tenant(
        db, payload, current_user, idempotency_key=idempotency_key
    )
    return TenantPublicRead.model_validate(tenant).model_copy(update={"admin_email": admin_email})


@router.post(
    "/upgrade-to-organization",
    response_model=UpgradeToOrganizationResponse,
    status_code=status.HTTP_200_OK,
)
def upgrade_to_organization(
    payload: UpgradeToOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UpgradeToOrganizationResponse:
    """
    In-place upgrade: ``individual`` solo practice → ``organization``; caller becomes
    org admin/owner. Same ``tenant_id``; patients/appointments/billing rows are not migrated.
    """
    tenant, user = tenant_service.upgrade_individual_to_organization(
        db,
        current_user,
        payload.clinic_name,
    )
    admin_email = crud_tenant.get_primary_admin_email_for_tenant(db, tenant.id)
    eff_roles, _ = roles_and_doctor_id_for_user(db, user)
    return UpgradeToOrganizationResponse(
        tenant=TenantPublicRead.model_validate(tenant).model_copy(
            update={"admin_email": admin_email}
        ),
        roles=eff_roles,
    )


@router.get("", response_model=list[TenantPublicRead])
def read_tenants(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    include_deactivated: bool = Query(
        default=False,
        description="Super admins only: include soft-deleted (deactivated) organizations.",
    ),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[TenantPublicRead]:
    """
    Lists non-deleted tenants by default (``is_deleted = false``).
    Super admins may pass ``include_deactivated=true`` to list deactivated orgs for the control panel.
    Non-super users get active tenants of type organization or individual (e.g. marketplace).
    """
    exclude_deleted = True
    if (
        current_user is not None
        and current_user.is_active
        and current_user.role == UserRole.super_admin
        and include_deactivated
    ):
        exclude_deleted = False

    if (
        current_user is not None
        and current_user.is_active
        and current_user.role == UserRole.super_admin
    ):
        rows = crud_tenant.list_tenants(
            db,
            type=None,
            is_active=True,
            exclude_deleted=exclude_deleted,
            skip=skip,
            limit=limit,
        )
    else:
        rows = crud_tenant.list_tenants(
            db,
            type_in=(TenantType.organization.value, TenantType.individual.value),
            is_active=True,
            exclude_deleted=True,
            skip=skip,
            limit=limit,
        )
    return [TenantPublicRead.model_validate(t) for t in rows]


@router.post("/{tenant_id}/reactivate", response_model=TenantPublicRead)
def reactivate_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TenantPublicRead:
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super administrators can reactivate organizations",
        )
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found")
    tenant.is_deleted = False
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    admin_email = crud_tenant.get_primary_admin_email_for_tenant(db, tenant.id)
    return TenantPublicRead.model_validate(tenant).model_copy(
        update={"admin_email": admin_email}
    )


@router.get("/{tenant_id}", response_model=TenantPublicRead)
def read_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TenantPublicRead:
    if current_user.role != UserRole.super_admin:
        raise ForbiddenError("Only super administrators can load tenant details")
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found")
    admin_email = crud_tenant.get_primary_admin_email_for_tenant(db, tenant.id)
    return TenantPublicRead.model_validate(tenant).model_copy(
        update={"admin_email": admin_email}
    )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Soft-deactivate an organization (``is_deleted = true``). Super admin only."""
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super administrators can deactivate organizations",
        )
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found")
    tenant.is_deleted = True
    db.add(tenant)
    db.commit()
