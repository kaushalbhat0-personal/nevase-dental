import logging
from sqlalchemy.orm import Session
from app.core.security import hash_password, verify_password
from app.crud import crud_patient, crud_tenant, crud_user
from app.models.tenant import TenantType
from app.models.user import User, UserRole
from app.schemas.user import SignupType, UserCreate
from app.services import doctor_service
from app.services.exceptions import AuthenticationError, ConflictError, ValidationError
from app.services.user_roles_service import roles_and_doctor_id_for_user

logger = logging.getLogger(__name__)


def _assert_registration_invariants(db: Session, user: User) -> None:
    if user.role == UserRole.patient:
        if user.tenant_id is not None:
            raise ValidationError("Patient account cannot have tenant_id")
        return
    if user.role == UserRole.doctor:
        _, did = roles_and_doctor_id_for_user(db, user)
        if user.tenant_id is None or did is None:
            raise ValidationError("Doctor account must have tenant_id and a doctor profile")
        return
    if user.role in (UserRole.admin, UserRole.staff):
        if user.tenant_id is None:
            raise ValidationError("Organization account must have tenant_id")
        return


def register_user(db: Session, user_in: UserCreate) -> User:
    hashed = hash_password(user_in.password)
    st = user_in.signup_type
    if st is None:
        raise ValidationError("signup_type is required")

    with db.begin():
        if crud_user.get_user_by_email(db, user_in.email):
            raise ConflictError("Email already registered")

        if st == SignupType.patient:
            user = crud_user.create_user_tx(
                db,
                {
                    "email": user_in.email,
                    "hashed_password": hashed,
                    "role": UserRole.patient,
                },
            )
            if user_in.patient_profile is None:
                raise ConflictError("Patient profile data required for patient role")
            patient_data = user_in.patient_profile.model_dump()
            patient_data["tenant_id"] = None
            patient_data["user_id"] = user.id
            patient_data["created_by"] = user.id
            crud_patient.create_patient_tx(db, patient_data)
            tenant_log = None

        elif st == SignupType.doctor:
            user = crud_user.create_user_tx(
                db,
                {
                    "email": user_in.email,
                    "hashed_password": hashed,
                    "role": UserRole.doctor,
                },
            )
            if user_in.doctor_profile is None:
                raise ConflictError("Doctor profile data required for doctor role")
            doctor_service.create_independent_doctor(
                db, user_in.doctor_profile, user.id, current_user=None
            )
            db.refresh(user)
            tenant_log = user.tenant_id

        elif st == SignupType.hospital:
            if not user_in.organization_name or not user_in.doctor_profile:
                raise ConflictError(
                    "organization_name and doctor_profile are required for hospital signup"
                )
            tenant = crud_tenant.create_tenant_tx(
                db,
                name=user_in.organization_name,
                type=TenantType.organization,
                is_active=True,
            )
            user = crud_user.create_user_tx(
                db,
                {
                    "email": user_in.email,
                    "hashed_password": hashed,
                    "role": UserRole.admin,
                    "is_owner": True,
                },
            )
            crud_tenant.create_user_tenant_tx(
                db,
                user_id=user.id,
                tenant_id=tenant.id,
                role="admin",
                is_primary=True,
            )
            doctor_service.create_doctor(
                db,
                user_in.doctor_profile,
                tenant_id=tenant.id,
                user_id=user.id,
                current_user=None,
            )
            db.refresh(user)
            tenant_log = tenant.id
        else:
            raise ValidationError("Unsupported signup type")

        _assert_registration_invariants(db, user)
        logger.info(
            "[AUTH_FLOW] signup_type=%s user_id=%s tenant_id=%s",
            st.value,
            user.id,
            tenant_log,
        )

    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    # Normalize email to lowercase for case-insensitive matching
    email_normalized = email.lower().strip()
    logger.info(f"[AUTH] Attempting login for: {email_normalized}")

    user = crud_user.get_user_by_email(db, email_normalized)
    if user is None:
        logger.warning(f"[AUTH] User not found: {email_normalized}")
        raise AuthenticationError("Incorrect email or password")

    logger.info(f"[AUTH] User found: {user.email}, active={user.is_active}")

    if not user.is_active:
        logger.warning(f"[AUTH] User inactive: {email_normalized}")
        raise AuthenticationError("Incorrect email or password")

    password_valid = verify_password(password, user.hashed_password)
    logger.info(f"[AUTH] Password verification: {password_valid}")

    if not password_valid:
        logger.warning(f"[AUTH] Invalid password for: {email_normalized}")
        raise AuthenticationError("Incorrect email or password")

    logger.info(f"[AUTH] Login successful: {email_normalized}")
    return user


def reset_password(db: Session, user: User, old_password: str, new_password: str) -> User:
    if not verify_password(old_password, user.hashed_password):
        raise ValidationError("Current password is incorrect")
    if verify_password(new_password, user.hashed_password):
        raise ValidationError("New password must be different from your current password")
    user.hashed_password = hash_password(new_password)
    user.force_password_reset = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
