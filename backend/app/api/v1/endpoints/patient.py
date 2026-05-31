import secrets
import string

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
from app.core.security import hash_password
from app.crud import crud_patient, crud_user
from app.models.user import User, UserRole
from app.schemas.patient import (
    PatientAutoCredentials,
    PatientCreate,
    PatientCreateResponse,
    PatientListRead,
    PatientMyDoctorRead,
    PatientRead,
    PatientUpdate,
)
from app.services import patient_service

router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    dependencies=[Depends(require_structured_profile_complete)],
)


def _generate_password(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.get("/me/doctors", response_model=list[PatientMyDoctorRead])
def read_my_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[PatientMyDoctorRead]:
    return patient_service.list_my_doctors(db, current_user)


@router.post("", response_model=PatientCreateResponse, status_code=201)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id_active),
    _verified: None = Depends(require_doctor_verification_approved),
) -> PatientCreateResponse:
    patient = patient_service.create_patient(
        db, payload, current_user, tenant_id
    )

    password = _generate_password()
    hashed = hash_password(password)
    username = payload.phone

    user_data = crud_user.create_user_tx(
        db,
        {
            "email": username,
            "hashed_password": hashed,
            "role": UserRole.patient,
            "force_password_reset": True,
        },
    )

    crud_patient.update_patient(
        db, patient, {"user_id": user_data.id}
    )
    db.refresh(patient)

    message = f"Welcome to Nevase Dental! Your patient portal login: Username: {username} Password: {password}"
    whatsapp_link = (
        f"https://wa.me/91{payload.phone}?text="
        f"Welcome%20to%20Nevase%20Dental!%20Your%20patient%20portal%20login:%20"
        f"Username:%20{username}%20Password:%20{password}%20"
        f"Login%20at:%20https://nevase-dental.vercel.app/login"
    )

    return PatientCreateResponse(
        **PatientRead.model_validate(patient).model_dump(),
        auto_credentials=PatientAutoCredentials(
            username=username,
            password=password,
            message=message,
            whatsapp_link=whatsapp_link,
        ),
    )


@router.get("", response_model=list[PatientListRead])
def read_patients(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
    _verified: None = Depends(require_doctor_verification_approved),
) -> list[PatientListRead]:
    return patient_service.get_patients(
        db,
        current_user,
        skip=skip,
        limit=limit,
        search=search,
        tenant_id=tenant_id,
        data_scope=data_scope,
    )


@router.get("/{patient_id}", response_model=PatientRead)
def read_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
    _verified: None = Depends(require_doctor_verification_approved),
) -> PatientRead:
    patient = patient_service.get_patient_or_404(db, patient_id)
    patient_service.authorize_patient_read(
        db,
        patient,
        current_user,
        tenant_id,
        rbac_action="read_patient",
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )
    return patient


@router.put("/{patient_id}", response_model=PatientRead)
def update_patient(
    patient_id: UUID,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
    _verified: None = Depends(require_doctor_verification_approved),
) -> PatientRead:
    return patient_service.update_patient(
        db,
        patient_id,
        payload,
        current_user,
        tenant_id,
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
    data_scope: ResolvedDataScope = Depends(get_resolved_data_scope),
    _verified: None = Depends(require_doctor_verification_approved),
) -> Response:
    patient_service.delete_patient(
        db,
        patient_id,
        current_user,
        tenant_id,
        restrict_to_doctor_id=restrict_doctor_id_for_detail(data_scope, current_user),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
