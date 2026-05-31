from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_scoped_tenant_id_active
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import OrganizationUserCreate, UserRead, UserRoleUpdate
from app.services import user_admin_service
from app.services.user_roles_service import user_read_with_roles

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserRead:
    return user_read_with_roles(db, current_user)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_organization_user(
    payload: OrganizationUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserRead:
    user = user_admin_service.provision_organization_user(db, current_user, payload)
    db.commit()
    db.refresh(user)
    return user_read_with_roles(db, user)


@router.patch("/users/{user_id}/role", response_model=UserRead)
def update_user_role_in_tenant(
    user_id: UUID,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id_active),
) -> UserRead:
    user = user_admin_service.update_user_role_in_tenant(
        db, current_user, user_id, tenant_id, payload
    )
    db.commit()
    db.refresh(user)
    return user_read_with_roles(db, user)
