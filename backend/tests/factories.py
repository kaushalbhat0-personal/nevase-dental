"""Test data builders for API tests and Playwright e2e seeding.

When seeding with literal UUID strings and a SQLAlchemy session, prefer
``app.utils.db_uuids.as_db_uuid`` so SQLite and PostgreSQL both bind correctly.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crud.crud_appointment import add_appointment
from app.models.doctor import Doctor
from app.models.doctor_availability import DoctorAvailability
from app.models.appointment import AppointmentStatus
from app.models.billing import Billing, BillingStatus
from app.models.patient import Patient
from app.models.tenant import Tenant, TenantType, UserTenant
from app.models.user import User, UserRole
from app.utils.appointment_datetime import normalize_appointment_time_utc

# Product default; availability `time` fields are wall clock in the doctor's IANA zone.
_IST = ZoneInfo("Asia/Kolkata")


def _wall_clock_to_utc_appointment(d: date, t: time, zone: ZoneInfo) -> datetime:
    return normalize_appointment_time_utc(datetime.combine(d, t, tzinfo=zone).astimezone(timezone.utc))


def create_tenant(db: Session, *, name: str | None = None, tenant_type: TenantType = TenantType.organization) -> Tenant:
    t = Tenant(name=name or f"Test Tenant {uuid.uuid4().hex[:8]}", type=tenant_type.value)
    db.add(t)
    db.flush()
    return t


def link_user_tenant(
    db: Session,
    *,
    user_id: UUID,
    tenant_id: UUID,
    is_primary: bool = True,
    role: str = "admin",
) -> UserTenant:
    ut = UserTenant(user_id=user_id, tenant_id=tenant_id, is_primary=is_primary, role=role)
    db.add(ut)
    db.flush()
    return ut


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: UserRole,
    tenant_id: UUID | None = None,
    force_password_reset: bool = False,
    is_owner: bool = False,
) -> User:
    if role == UserRole.super_admin:
        u = User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
            force_password_reset=force_password_reset,
            is_owner=is_owner,
            tenant_id=None,
        )
        db.add(u)
        db.flush()
        return u
    if role == UserRole.patient:
        if tenant_id is not None:
            raise ValueError("patient test users must not have tenant_id; omit the argument")
        u = User(
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.patient,
            is_active=True,
            force_password_reset=force_password_reset,
            is_owner=False,
            tenant_id=None,
        )
        db.add(u)
        db.flush()
        return u
    if tenant_id is None:
        raise ValueError("tenant_id is required for non-super_admin, non-patient users")
    u = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        force_password_reset=force_password_reset,
        is_owner=is_owner,
        tenant_id=tenant_id,
    )
    db.add(u)
    db.flush()
    link_user_tenant(db, user_id=u.id, tenant_id=tenant_id, is_primary=True, role=role.value)
    return u


def create_doctor_profile(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID | None = None,
    timezone_name: str = "Asia/Kolkata",
) -> Doctor:
    d = Doctor(
        name=f"Dr Test {uuid.uuid4().hex[:6]}",
        specialization="General",
        experience_years=5,
        tenant_id=tenant_id,
        user_id=user_id,
        timezone=timezone_name,
    )
    db.add(d)
    db.flush()
    _ensure_structured_doctor_profile_complete(db, d)
    return d


def _ensure_structured_doctor_profile_complete(db: Session, d: Doctor) -> None:
    """Seed `doctor_profiles` with mandatory fields so doctor-scoped APIs pass RBAC in tests."""
    from app.services import doctor_profile_service

    p = doctor_profile_service.ensure_profile_for_doctor(db, d)
    p.registration_number = p.registration_number or "TEST-REG-NUM"
    p.phone = p.phone or "9876543210"
    p.qualification = p.qualification or "MBBS"
    p.verification_status = doctor_profile_service.VERIFICATION_APPROVED
    p.verification_rejection_reason = None
    doctor_profile_service.recompute_is_complete(p)
    db.add(p)
    db.flush()


def add_weekly_availability(
    db: Session,
    *,
    doctor_id: UUID,
    tenant_id: UUID,
    day_of_week: int,
    start: time,
    end: time,
    slot_duration: int = 30,
) -> DoctorAvailability:
    w = DoctorAvailability(
        doctor_id=doctor_id,
        tenant_id=tenant_id,
        day_of_week=day_of_week,
        start_time=start,
        end_time=end,
        slot_duration=slot_duration,
    )
    db.add(w)
    db.flush()
    return w


def create_patient_profile(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    user_id: UUID,
    created_by: UUID,
    name: str = "E2E Patient",
) -> Patient:
    p = Patient(
        name=name,
        age=30,
        gender="other",
        phone="555-0100",
        user_id=user_id,
        created_by=created_by,
        tenant_id=tenant_id,
    )
    db.add(p)
    db.flush()
    return p


# Fixed future calendar day for stable slot math (Python: Monday=0 .. Sunday=6).
_BOOKING_ANCHOR_DATE = date(2035, 6, 15)  # Friday; availability uses this weekday
BOOKING_ANCHOR_DATE_ISO: str = _BOOKING_ANCHOR_DATE.isoformat()


def booking_slot_datetime_utc() -> datetime:
    """UTC instant for first 30m slot of seeded availability on BOOKING_ANCHOR_DATE (wall times in IST)."""
    return _wall_clock_to_utc_appointment(_BOOKING_ANCHOR_DATE, time(10, 0), _IST)


def seed_bookable_doctor_and_patient(
    db: Session,
    *,
    doctor_email: str,
    doctor_password: str,
    patient_email: str,
    patient_password: str,
    doctor_force_password_reset: bool = False,
) -> tuple[Doctor, Patient, datetime]:
    tenant = create_tenant(db, tenant_type=TenantType.organization)
    doc_user = create_user(
        db,
        email=doctor_email,
        password=doctor_password,
        role=UserRole.doctor,
        tenant_id=tenant.id,
        force_password_reset=doctor_force_password_reset,
    )
    doc = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id, timezone_name="Asia/Kolkata")
    assert doc.timezone == "Asia/Kolkata"
    add_weekly_availability(
        db,
        doctor_id=doc.id,
        tenant_id=tenant.id,
        day_of_week=_BOOKING_ANCHOR_DATE.weekday(),
        start=time(10, 0),
        end=time(12, 0),
        slot_duration=30,
    )
    pat_user = create_user(
        db,
        email=patient_email,
        password=patient_password,
        role=UserRole.patient,
    )
    pat = create_patient_profile(
        db,
        tenant_id=tenant.id,
        user_id=pat_user.id,
        created_by=pat_user.id,
    )
    db.commit()
    slot = booking_slot_datetime_utc()
    return doc, pat, slot


def seed_doctor_password_reset_only(
    db: Session,
    *,
    email: str,
    password: str,
) -> None:
    """Separate tenant + doctor for the forced password-reset Playwright flow."""
    tenant = create_tenant(db, name="E2E Password Reset Tenant")
    doc_user = create_user(
        db,
        email=email,
        password=password,
        role=UserRole.doctor,
        tenant_id=tenant.id,
        force_password_reset=True,
    )
    create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id, timezone_name="UTC")
    db.commit()


def extend_playwright_e2e_seed(
    db: Session,
    *,
    doctor_a: Doctor,
    patient_a: Patient,
) -> dict[str, str]:
    """
    Same-tenant extras: second patient (conflict), doctor B, patient visible only to doctor B,
    and two appointments (A+A patient, B+B-only patient) at distinct instants.
    """
    tenant_id = doctor_a.tenant_id
    if tenant_id is None:
        raise ValueError("doctor_a.tenant_id is required")

    pat_b_user = create_user(
        db,
        email="e2e-patient-b@local.test",
        password="TempPass9!",
        role=UserRole.patient,
    )
    _patient_b = create_patient_profile(
        db,
        tenant_id=tenant_id,
        user_id=pat_b_user.id,
        created_by=pat_b_user.id,
        name="E2E Patient B",
    )

    doc_b_user = create_user(
        db,
        email="e2e-doctor-b@local.test",
        password="TempPass9!",
        role=UserRole.doctor,
        tenant_id=tenant_id,
        force_password_reset=False,
    )
    doctor_b = create_doctor_profile(db, tenant_id=tenant_id, user_id=doc_b_user.id, timezone_name="UTC")
    add_weekly_availability(
        db,
        doctor_id=doctor_b.id,
        tenant_id=tenant_id,
        day_of_week=_BOOKING_ANCHOR_DATE.weekday(),
        start=time(10, 0),
        end=time(12, 0),
        slot_duration=30,
    )

    only_b_user = create_user(
        db,
        email="e2e-patient-only-b@local.test",
        password="TempPass9!",
        role=UserRole.patient,
    )
    patient_only_b = create_patient_profile(
        db,
        tenant_id=tenant_id,
        user_id=only_b_user.id,
        created_by=only_b_user.id,
        name="E2E Only Doctor B Patient",
    )

    # After 10:00 IST so first bookable slot (10:00) stays valid for double-book e2e (30-minute buffer).
    appt_a_time = _wall_clock_to_utc_appointment(_BOOKING_ANCHOR_DATE, time(11, 30), _IST)
    appt_a = add_appointment(
        db,
        {
            "patient_id": patient_a.id,
            "doctor_id": doctor_a.id,
            "appointment_time": appt_a_time,
            "status": AppointmentStatus.scheduled,
            "created_by": patient_a.user_id,
            "tenant_id": tenant_id,
        },
    )
    e2e_bill = Billing(
        patient_id=patient_a.id,
        appointment_id=appt_a.id,
        tenant_id=tenant_id,
        amount=500,
        currency="INR",
        status=BillingStatus.paid,
        description="E2E seed bill",
        idempotency_key="e2e-seed-bill-001",
        created_by=doctor_a.user_id,
    )
    db.add(e2e_bill)

    appt_b_time = normalize_appointment_time_utc(
        datetime.combine(_BOOKING_ANCHOR_DATE, time(11, 0), tzinfo=timezone.utc)
    )
    add_appointment(
        db,
        {
            "patient_id": patient_only_b.id,
            "doctor_id": doctor_b.id,
            "appointment_time": appt_b_time,
            "status": AppointmentStatus.scheduled,
            "created_by": only_b_user.id,
            "tenant_id": tenant_id,
        },
    )

    db.commit()
    return {
        "doctor_b_display_name": doctor_b.name,
        "patient_only_doctor_b_name": patient_only_b.name,
        "doctor_a_patient_id": str(patient_a.id),
        "doctor_a_appointment_id": str(appt_a.id),
    }


def seed_e2e_hospital_doctor(db: Session) -> dict[str, str]:
    """Organization-managed (hospital) doctor for read-only schedule UI E2E."""
    tenant = create_tenant(db, name="E2E Hospital Tenant", tenant_type=TenantType.organization)
    doc_user = create_user(
        db,
        email="e2e-hospital-doctor@local.test",
        password="TempPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
        force_password_reset=False,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id, timezone_name="Asia/Kolkata")
    add_weekly_availability(
        db,
        doctor_id=doctor.id,
        tenant_id=tenant.id,
        day_of_week=_BOOKING_ANCHOR_DATE.weekday(),
        start=time(10, 0),
        end=time(12, 0),
        slot_duration=30,
    )
    db.commit()
    return {
        "hospital_doctor_email": doc_user.email,
        "hospital_doctor_password": "TempPass9!",
        "hospital_doctor_display_name": doctor.name,
    }


def seed_e2e_doctor_other_tenant(db: Session) -> dict[str, str]:
    """Second-tenant doctor for Playwright SaaS isolation checks (never visible to tenant A doctors)."""
    tenant = create_tenant(db, name="E2E Isolation Tenant B")
    doc_user = create_user(
        db,
        email="e2e-doctor-other-tenant@local.test",
        password="TempPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
        force_password_reset=False,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id, timezone_name="UTC")
    db.commit()
    return {
        "doctor_other_tenant_email": doc_user.email,
        "doctor_other_tenant_password": "TempPass9!",
        "doctor_other_tenant_display_name": doctor.name,
    }
