from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.organization_display import organization_label_from_active_doctor_count
from app.crud import crud_doctor, crud_tenant
from app.models.doctor import Doctor
from app.models.doctor_profile import DoctorProfile
from app.models.tenant import Tenant, TenantType
from app.schemas.public_discovery import (
    PublicDoctorProfile,
    PublicTenantDiscovery,
    PublicTenantDoctorBrief,
)
from app.services import doctor_profile_service, doctor_slot_service
from app.services.doctor_service import hydrate_doctor_availability_flags
from app.services.exceptions import NotFoundError

router = APIRouter(prefix="/public", tags=["public-discovery"])


def _load_doctor_with_tenant_and_profile(db: Session, doctor_id: UUID) -> Doctor | None:
    stmt = (
        select(Doctor)
        .options(joinedload(Doctor.tenant), joinedload(Doctor.structured_profile))
        .where(Doctor.id == doctor_id, Doctor.is_deleted == False)
    )
    return db.scalars(stmt).first()


@router.get("/tenants", response_model=list[PublicTenantDiscovery])
def list_public_tenants(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[PublicTenantDiscovery]:
    tenants = crud_tenant.list_tenants(
        db,
        type_in=(TenantType.organization.value, TenantType.individual.value),
        is_active=True,
        exclude_deleted=True,
        skip=skip,
        limit=limit,
    )
    if not tenants:
        return []

    tenant_ids = [t.id for t in tenants]
    counts = crud_doctor.count_active_doctors_by_tenant_ids(db, tenant_ids)

    result: list[PublicTenantDiscovery] = []
    for t in tenants:
        count = counts.get(t.id, 0)
        label = organization_label_from_active_doctor_count(count)
        sole_doctor: PublicTenantDoctorBrief | None = None
        if count == 1:
            docs = crud_doctor.get_doctors(db, tenant_id=t.id, limit=1, only_marketplace_verified=False)
            if docs:
                d = docs[0]
                hydrate_doctor_availability_flags(db, docs)
                sole_doctor = PublicTenantDoctorBrief(
                    id=d.id,
                    name=d.name,
                    specialization=d.specialization,
                    has_availability_windows=getattr(d, "has_availability_windows", False),
                )
        result.append(
            PublicTenantDiscovery(
                id=t.id,
                name=t.name,
                doctor_count=count,
                type=t.type,
                organization_label=label,
                sole_doctor=sole_doctor,
            )
        )
    return result


@router.get("/tenants/{tenant_id}/doctors", response_model=list[PublicTenantDoctorBrief])
def list_public_tenant_doctors(
    tenant_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[PublicTenantDoctorBrief]:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or tenant.is_deleted or not tenant.is_active:
        raise NotFoundError("Tenant not found")

    doctors = crud_doctor.get_doctors(db, tenant_id=tenant_id, skip=skip, limit=limit, only_marketplace_verified=False)
    hydrate_doctor_availability_flags(db, doctors)
    return [
        PublicTenantDoctorBrief(
            id=d.id,
            name=d.name,
            specialization=d.specialization,
            has_availability_windows=getattr(d, "has_availability_windows", False),
        )
        for d in doctors
    ]


@router.get("/doctors/{doctor_id}", response_model=PublicDoctorProfile)
def get_public_doctor(
    doctor_id: UUID,
    db: Session = Depends(get_db),
) -> PublicDoctorProfile:
    doctor = _load_doctor_with_tenant_and_profile(db, doctor_id)
    if doctor is None:
        raise NotFoundError("Doctor not found")

    profile = doctor.structured_profile
    if profile is None or profile.verification_status != doctor_profile_service.VERIFICATION_APPROVED:
        raise NotFoundError("Doctor profile not available")

    hydrate_doctor_availability_flags(db, [doctor])

    return PublicDoctorProfile(
        id=doctor.id,
        full_name=profile.full_name,
        specialization=profile.specialization or doctor.specialization,
        experience=profile.experience_years or doctor.experience_years,
        qualification=profile.qualification,
        clinic_name=profile.clinic_name,
        address=profile.address,
        city=profile.city,
        profile_image=profile.profile_image,
        verified=True,
        verification_status=profile.verification_status,
        timezone=doctor.timezone,
        has_availability_windows=getattr(doctor, "has_availability_windows", False),
    )
