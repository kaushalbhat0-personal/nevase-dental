import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.data_scope import DataScopeKind, ResolvedDataScope
from app.core.tenancy import non_nil_tenant_id
from app.crud import crud_patient
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.services import doctor_service
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.patient import (
    PatientCreate,
    PatientListRead,
    PatientMyDoctorRead,
    PatientRead,
    PatientUpdate,
)
from app.services.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.services.security_audit import (
    assert_authorized,
    log_audit_mutation,
    log_rbac_mutation_violation,
)

logger = logging.getLogger(__name__)


def patient_is_in_doctor_cohort(
    db: Session,
    patient: Patient,
    doctor_id: UUID,
) -> bool:
    return crud_patient.patient_has_appointment_with_doctor(
        db, patient.id, doctor_id
    )


def _validate_age(age: int | None) -> None:
    if age is not None and age < 0:
        raise ValidationError("Age must be greater than or equal to 0")


def _tenant_scope_for_patient_create_assert(
    db: Session,
    current_user: User,
    request_tenant_id: UUID | None,
) -> UUID:
    req = non_nil_tenant_id(request_tenant_id)
    if req is not None:
        return req
    if current_user.role == UserRole.doctor:
        doc = doctor_service.get_current_doctor(db, current_user)
        doc_tid = non_nil_tenant_id(doc.tenant_id)
        if doc_tid is not None:
            return doc_tid
    user_tid = non_nil_tenant_id(current_user.tenant_id)
    if user_tid is not None:
        return user_tid
    raise ValidationError("Tenant scope is required to create a patient")


def authorize_patient_create(
    db: Session,
    current_user: User,
    tenant_id: UUID | None,
) -> None:
    if current_user.role == UserRole.patient:
        log_rbac_mutation_violation(
            current_user, "patient", action="create_patient"
        )
        raise ForbiddenError("Cannot create another patient record")
    if current_user.role == UserRole.super_admin:
        return
    if current_user.role in (UserRole.admin, UserRole.staff):
        return
    if current_user.role == UserRole.doctor:
        try:
            _ = doctor_service.get_current_doctor(db, current_user)
        except ForbiddenError:
            log_rbac_mutation_violation(
                current_user, "patient", action="create_patient"
            )
            raise
        return
    log_rbac_mutation_violation(current_user, "patient", action="create_patient")
    raise ForbiddenError("Not allowed to create patients")


def create_patient(
    db: Session,
    patient_in: PatientCreate,
    current_user: User,
    tenant_id: UUID | None,
) -> Patient:
    _validate_age(patient_in.age)
    logger.info(f"[RBAC] role={current_user.role}, user={current_user.id}")
    authorize_patient_create(
        db, current_user, tenant_id
    )
    audit_tenant = _tenant_scope_for_patient_create_assert(
        db, current_user, tenant_id
    )
    if current_user.role != UserRole.super_admin:
        assert_authorized(
            "create",
            "patient",
            current_user,
            audit_tenant,
            resource_tenant_id=audit_tenant,
        )
    patient_data = patient_in.model_dump()
    patient_data.pop("created_by", None)
    patient_data["created_by"] = current_user.id
    patient_data["tenant_id"] = None
    patient = crud_patient.create_patient(db, patient_data)
    log_audit_mutation(
        "create",
        current_user,
        "patient",
        patient.id,
        audit_tenant,
    )
    return patient


def get_patient_or_404(db: Session, patient_id: UUID) -> Patient:
    patient = crud_patient.get_patient(db, patient_id)
    if patient is None:
        raise NotFoundError("Patient not found")
    return patient


def get_patient_by_user_id(db: Session, user_id: UUID) -> Patient:
    patient = crud_patient.get_patient_by_user_id(db, user_id)
    if patient is None:
        raise NotFoundError("Patient profile not found for this user")
    return patient


def ensure_patient_profile_for_user_tx(db: Session, current_user: User) -> Patient:
    """
    App users (patient role) need a row in ``patients`` to book. Creates a minimal
    profile in the current transaction if missing.
    """
    if current_user.role != UserRole.patient:
        raise ValidationError("Only patient accounts can own a patient profile")
    existing = crud_patient.get_patient_by_user_id(db, current_user.id)
    if existing is not None:
        return existing
    local = (current_user.email or "patient").split("@", 1)[0].strip() or "Patient"
    name = (local[:255]) if local else "Patient"
    return crud_patient.create_patient_tx(
        db,
        {
            "name": name,
            "age": 0,
            "gender": "other",
            "phone": "0000000000",
            "user_id": current_user.id,
            "created_by": current_user.id,
            "tenant_id": None,
        },
    )


def list_my_doctors(db: Session, current_user: User) -> list[PatientMyDoctorRead]:
    if current_user.role != UserRole.patient:
        raise ForbiddenError("Only patients can list their doctors")
    patient = crud_patient.get_patient_by_user_id(db, current_user.id)
    if patient is None:
        return []
    appt_doctor_ids = (
        select(Appointment.doctor_id)
        .where(
            Appointment.patient_id == patient.id,
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.status != AppointmentStatus.cancelled,
        )
        .distinct()
    )
    stmt = (
        select(Doctor)
        .where(
            Doctor.id.in_(appt_doctor_ids),
            Doctor.is_active == True,  # noqa: E712
            Doctor.is_deleted == False,  # noqa: E712
        )
        .order_by(Doctor.name.asc())
    )
    doctors = list(db.scalars(stmt).all())
    return [PatientMyDoctorRead.model_validate(d) for d in doctors]


def authorize_patient_access(
    db: Session,
    patient: Patient,
    current_user: User,
    tenant_id: UUID | None,
    *,
    rbac_action: str = "patient_access",
    restrict_to_doctor_id: UUID | None = None,
) -> None:
    if current_user.role == UserRole.super_admin:
        if restrict_to_doctor_id is not None and not patient_is_in_doctor_cohort(
            db, patient, restrict_to_doctor_id
        ):
            log_rbac_mutation_violation(
                current_user, "patient", action=rbac_action
            )
            raise ForbiddenError("Not allowed to access this patient")
        return

    if current_user.role == UserRole.patient:
        if patient.user_id != current_user.id:
            log_rbac_mutation_violation(
                current_user, "patient", action=rbac_action
            )
            raise ForbiddenError("Not allowed to modify this patient")
        return

    if tenant_id is None:
        log_rbac_mutation_violation(current_user, "patient", action=rbac_action)
        raise ForbiddenError("Tenant context required")

    if not crud_patient.patient_has_active_appointment_in_tenant(
        db, patient.id, tenant_id
    ):
        log_rbac_mutation_violation(
            current_user, "patient", action=rbac_action
        )
        raise ForbiddenError("Patient is not in your tenant")
    assert_authorized(
        "access",
        "patient",
        current_user,
        tenant_id,
        resource_tenant_id=tenant_id,
    )

    if current_user.role in (UserRole.admin, UserRole.staff):
        if restrict_to_doctor_id is not None and not patient_is_in_doctor_cohort(
            db, patient, restrict_to_doctor_id
        ):
            log_rbac_mutation_violation(
                current_user, "patient", action=rbac_action
            )
            raise ForbiddenError("Not allowed to access this patient")
        return

    if current_user.role == UserRole.doctor and current_user.is_owner:
        if restrict_to_doctor_id is None:
            return
        if patient_is_in_doctor_cohort(db, patient, restrict_to_doctor_id):
            return
        log_rbac_mutation_violation(
            current_user, "patient", action=rbac_action
        )
        raise ForbiddenError("Not allowed to access this patient")

    if current_user.role == UserRole.doctor:
        doc = doctor_service.get_current_doctor(
            db, current_user
        )
        if not crud_patient.patient_has_appointment_with_doctor(
            db, patient.id, doc.id
        ):
            log_rbac_mutation_violation(
                current_user,
                "patient",
                action=rbac_action,
            )
            raise ForbiddenError("Not allowed to modify this patient")
        return

    log_rbac_mutation_violation(current_user, "patient", action=rbac_action)
    raise ForbiddenError("Not allowed to modify this patient")


authorize_patient_read = authorize_patient_access
authorize_patient_update = authorize_patient_access
authorize_patient_delete = authorize_patient_access


def get_patients(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    tenant_id: UUID | None = None,
    *,
    data_scope: ResolvedDataScope,
) -> list[PatientListRead]:
    logger.info(f"[RBAC] role={current_user.role}, user={current_user.id}")
    user_id: UUID | None = None
    effective_tenant_id = tenant_id

    linked_doctor_id: UUID | None = None
    if current_user.role == UserRole.doctor and current_user.is_owner:
        if data_scope.kind == DataScopeKind.doctor:
            doc = doctor_service.get_current_doctor(
                db, current_user
            )
            effective_tenant_id = doc.tenant_id
            linked_doctor_id = doc.id
    elif current_user.role == UserRole.doctor:
        doc = doctor_service.get_current_doctor(
            db, current_user
        )
        effective_tenant_id = doc.tenant_id
        linked_doctor_id = doc.id
    elif current_user.role == UserRole.patient:
        user_id = current_user.id
        # Own profile is keyed by user_id; patient rows may not carry tenant_id
        effective_tenant_id = None
    elif current_user.role in (UserRole.admin, UserRole.super_admin, UserRole.staff):
        if (
            data_scope.kind == DataScopeKind.doctor
            and data_scope.doctor_id is not None
        ):
            linked_doctor_id = data_scope.doctor_id

    scope_kind = data_scope.kind.value

    rows = crud_patient.get_patients(
        db,
        current_user,
        skip=skip,
        limit=limit,
        search=search,
        tenant_id=effective_tenant_id,
        user_id=user_id,
        linked_doctor_id=linked_doctor_id,
        data_scope_kind=scope_kind,
    )

    if (
        current_user.role in (UserRole.admin, UserRole.staff, UserRole.super_admin)
        and data_scope.kind == DataScopeKind.tenant
        and effective_tenant_id is not None
    ):
        logger.info(
            "[PATIENT_SCOPE_ADMIN] tenant_id=%s count=%d source=appointment_based",
            effective_tenant_id,
            len(rows),
        )
    logger.info(
        "[PATIENT_SCOPE] scope=%s doctor_id=%s tenant_id=%s user=%s returned=%d",
        scope_kind,
        linked_doctor_id,
        effective_tenant_id,
        current_user.id,
        len(rows),
    )

    doctor_label: str | None = None
    if (
        data_scope.kind == DataScopeKind.doctor
        and linked_doctor_id is not None
    ):
        d = db.get(Doctor, linked_doctor_id)
        doctor_label = d.name if d is not None else None

    out: list[PatientListRead] = []
    for patient, crud_name in rows:
        name_out = crud_name
        if doctor_label is not None:
            name_out = doctor_label
        pr = PatientRead.model_validate(patient)
        out.append(
            PatientListRead(**pr.model_dump(), doctor_name=name_out)
        )
    return out


def update_patient(
    db: Session,
    patient_id: UUID,
    patient_in: PatientUpdate,
    current_user: User,
    tenant_id: UUID | None,
    *,
    restrict_to_doctor_id: UUID | None = None,
) -> Patient:
    _validate_age(patient_in.age)
    patient = get_patient_or_404(db, patient_id)
    authorize_patient_update(
        db,
        patient,
        current_user,
        tenant_id,
        rbac_action="update_patient",
        restrict_to_doctor_id=restrict_to_doctor_id,
    )
    update_data = patient_in.model_dump(exclude_unset=True)
    if not update_data:
        return patient
    updated = crud_patient.update_patient(db, patient, update_data)
    log_audit_mutation(
        "update",
        current_user,
        "patient",
        updated.id,
        updated.tenant_id,
    )
    return updated


def delete_patient(
    db: Session,
    patient_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    *,
    restrict_to_doctor_id: UUID | None = None,
) -> None:
    patient = get_patient_or_404(db, patient_id)
    authorize_patient_delete(
        db,
        patient,
        current_user,
        tenant_id,
        rbac_action="delete_patient",
        restrict_to_doctor_id=restrict_to_doctor_id,
    )
    log_audit_mutation(
        "delete",
        current_user,
        "patient",
        patient.id,
        patient.tenant_id,
    )
    crud_patient.delete_patient(db, patient)
