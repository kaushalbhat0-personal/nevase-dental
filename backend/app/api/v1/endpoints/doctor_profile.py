from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_users_doctor_for_structured_profile
from app.core.database import get_db
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor_profile import (
    DoctorProfileRead,
    DoctorProfileUpdate,
    DoctorProfileWrite,
)
from app.services import doctor_profile_service

router = APIRouter(prefix="/doctor", tags=["doctor-profile"])


@router.get("/profile", response_model=DoctorProfileRead)
def get_structured_profile(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
    doctor: Doctor = Depends(get_current_users_doctor_for_structured_profile),
) -> DoctorProfileRead:
    row = doctor_profile_service.ensure_profile_for_doctor(db, doctor)
    return DoctorProfileRead.model_validate(row)


@router.post("/profile", response_model=DoctorProfileRead, status_code=status.HTTP_200_OK)
def post_structured_profile(
    payload: DoctorProfileWrite,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
    doctor: Doctor = Depends(get_current_users_doctor_for_structured_profile),
) -> DoctorProfileRead:
    row = doctor_profile_service.upsert_profile_from_write(db, doctor, payload)
    db.commit()
    db.refresh(row)
    return DoctorProfileRead.model_validate(row)


@router.put("/profile", response_model=DoctorProfileRead)
def put_structured_profile(
    payload: DoctorProfileWrite,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
    doctor: Doctor = Depends(get_current_users_doctor_for_structured_profile),
) -> DoctorProfileRead:
    row = doctor_profile_service.upsert_profile_from_write(db, doctor, payload)
    db.commit()
    db.refresh(row)
    return DoctorProfileRead.model_validate(row)


@router.patch("/profile", response_model=DoctorProfileRead)
def patch_structured_profile(
    payload: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
    doctor: Doctor = Depends(get_current_users_doctor_for_structured_profile),
) -> DoctorProfileRead:
    row = doctor_profile_service.patch_profile(db, doctor, payload)
    db.commit()
    db.refresh(row)
    return DoctorProfileRead.model_validate(row)


@router.post(
    "/profile/submit-for-verification",
    response_model=DoctorProfileRead,
    status_code=status.HTTP_200_OK,
)
def submit_structured_profile_for_verification(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
    doctor: Doctor = Depends(get_current_users_doctor_for_structured_profile),
) -> DoctorProfileRead:
    row = doctor_profile_service.submit_profile_for_verification(db, doctor)
    db.commit()
    db.refresh(row)
    return DoctorProfileRead.model_validate(row)
