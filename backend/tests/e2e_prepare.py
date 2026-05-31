"""
Seed SQLite DB and credentials for Playwright e2e.

Run from backend root: python -m tests.e2e_prepare
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_ROOT = _BACKEND_ROOT / "frontend"
_CRED_PATH = _FRONTEND_ROOT / "e2e" / ".e2e-credentials.json"
_DB_PATH = _BACKEND_ROOT / ".playwright_e2e.sqlite3"


def main() -> None:
    if _DB_PATH.exists():
        _DB_PATH.unlink()

    # Seed DB is SQLite; ensure Settings() does not apply production PostgreSQL-only rules.
    os.environ["ENVIRONMENT"] = "development"
    db_url = f"sqlite+pysqlite:///{_DB_PATH.as_posix()}"
    os.environ["DATABASE_URL"] = db_url
    os.environ.setdefault("SECRET_KEY", "playwright-e2e-secret-key-0000000001")
    os.environ.setdefault("ALLOWED_ORIGINS", "http://127.0.0.1:5173")

    # Import after env
    import app.models  # noqa: F401
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base
    from tests.factories import (
        BOOKING_ANCHOR_DATE_ISO,
        extend_playwright_e2e_seed,
        seed_bookable_doctor_and_patient,
        seed_doctor_password_reset_only,
        seed_e2e_doctor_other_tenant,
        seed_e2e_hospital_doctor,
    )

    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        doctor, patient, _slot = seed_bookable_doctor_and_patient(
            db,
            doctor_email="e2e-doctor@local.test",
            doctor_password="TempPass9!",
            patient_email="e2e-patient@local.test",
            patient_password="TempPass9!",
            doctor_force_password_reset=False,
        )
        extras = extend_playwright_e2e_seed(db, doctor_a=doctor, patient_a=patient)
        other_tenant = seed_e2e_doctor_other_tenant(db)
        hospital_doc = seed_e2e_hospital_doctor(db)
        seed_doctor_password_reset_only(
            db,
            email="e2e-doctor-reset@local.test",
            password="TempPass9!",
        )
        data = {
            "apiBaseUrl": "http://127.0.0.1:9777/api/v1",
            "bookingDate": BOOKING_ANCHOR_DATE_ISO,
            "doctorEmail": "e2e-doctor@local.test",
            "doctorPassword": "TempPass9!",
            "newDoctorPassword": "NewPass4567",
            "resetDoctorEmail": "e2e-doctor-reset@local.test",
            "resetDoctorPassword": "TempPass9!",
            "patientEmail": "e2e-patient@local.test",
            "patientPassword": "TempPass9!",
            "patientBEmail": "e2e-patient-b@local.test",
            "patientBPassword": "TempPass9!",
            "doctorDisplayName": doctor.name,
            "doctorBEmail": "e2e-doctor-b@local.test",
            "doctorBPassword": "TempPass9!",
            "doctorBDisplayName": extras["doctor_b_display_name"],
            "patientOnlyDoctorBName": extras["patient_only_doctor_b_name"],
            "doctorLinkedPatientId": extras["doctor_a_patient_id"],
            "doctorLinkedAppointmentId": extras["doctor_a_appointment_id"],
            "doctorOtherTenantEmail": other_tenant["doctor_other_tenant_email"],
            "doctorOtherTenantPassword": other_tenant["doctor_other_tenant_password"],
            "doctorOtherTenantDisplayName": other_tenant["doctor_other_tenant_display_name"],
            "hospitalDoctorEmail": hospital_doc["hospital_doctor_email"],
            "hospitalDoctorPassword": hospital_doc["hospital_doctor_password"],
            "hospitalDoctorDisplayName": hospital_doc["hospital_doctor_display_name"],
        }
    finally:
        db.close()
        engine.dispose()

    _FRONTEND_ROOT.mkdir(parents=True, exist_ok=True)
    (_FRONTEND_ROOT / "e2e").mkdir(parents=True, exist_ok=True)
    _CRED_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {_CRED_PATH}")


if __name__ == "__main__":
    main()
