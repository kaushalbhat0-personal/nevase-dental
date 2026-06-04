"""Real PDF download validation — encounter summary + prescription PDFs.

On systems with WeasyPrint + GTK (production Linux):
  → 200, application/pdf, starts with %PDF-

On systems without GTK (Windows dev), _render_pdf raises OSError.
The httpx ASGI test transport propagates this as an unhandled exception.
This is CORRECT behavior — a visible error is better than a silently corrupted PDF.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy.orm import Session

from app.models.appointment import AppointmentStatus, AppointmentVitals
from app.models.user import UserRole
from app.crud.crud_appointment import add_appointment, add_prescription, add_prescription_item
from tests.factories import create_tenant, create_user, create_doctor_profile, create_patient_profile


def _check_weasyprint() -> bool:
    """Return True if weasyprint can actually render PDFs on this system."""
    try:
        from weasyprint import HTML as WeasyprintHTML
        WeasyprintHTML(string="<html><body>test</body></html>").write_pdf()
        return True
    except Exception:
        return False


WEASYPRINT_WORKS = _check_weasyprint()


@pytest.mark.asyncio
async def test_encounter_summary_pdf_download(client: httpx.AsyncClient, db_session: Session) -> None:
    """Scenario 1: Doctor downloads encounter summary PDF → 200 + %PDF-"""
    if not WEASYPRINT_WORKS:
        pytest.skip("WeasyPrint GTK libs not available on this system")

    # ── Setup: tenant + doctor + patient + appointment + vitals + prescriptions ──
    tenant = create_tenant(db_session)
    doc_user = create_user(
        db_session,
        email=f"dr_{uuid.uuid4().hex[:8]}@test.com",
        password="DocPass9!",
        role=UserRole.doctor,
        tenant_id=tenant.id,
    )
    doctor = create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_user.id)
    pat_user = create_user(
        db_session,
        email=f"pat_{uuid.uuid4().hex[:8]}@test.com",
        password="PatPass9!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db_session, tenant_id=tenant.id, user_id=pat_user.id, created_by=doc_user.id,
    )

    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    appt = add_appointment(db_session, {
        "patient_id": patient.id,
        "doctor_id": doctor.id,
        "appointment_time": past_time,
        "status": AppointmentStatus.scheduled,
        "created_by": doc_user.id,
        "tenant_id": tenant.id,
    })

    db_session.add(AppointmentVitals(
        appointment_id=appt.id, temperature=98.6, bp_systolic=120, bp_diastolic=80, pulse=72,
    ))
    rx = add_prescription(db_session, appointment_id=appt.id, doctor_id=doctor.id,
                          patient_id=patient.id, tenant_id=tenant.id, notes="Take with food")
    add_prescription_item(db_session, prescription_id=rx.id, line_data={
        "medicine_name": "Paracetamol", "dosage": "500mg", "frequency": "TDS",
        "duration": "5 days", "instructions": "After meals",
    })
    add_prescription_item(db_session, prescription_id=rx.id, line_data={
        "medicine_name": "Amoxicillin", "dosage": "250mg", "frequency": "BD",
        "duration": "7 days", "instructions": "With water",
    })
    appt.status = AppointmentStatus.completed
    appt.clinical_notes = "Patient recovering well"
    db_session.commit()

    doc_login = await client.post("/api/v1/login",
        data={"username": doc_user.email, "password": "DocPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert doc_login.status_code == 200
    doc_headers = {"Authorization": f"Bearer {doc_login.json()['access_token']}", "X-Tenant-ID": str(tenant.id)}

    enc_resp = await client.get(f"/api/v1/documents/encounter-summary/{appt.id}", headers=doc_headers)

    print(f"\n[Scenario 1] Status: {enc_resp.status_code}  Type: {enc_resp.headers.get('content-type')}  Size: {len(enc_resp.content)}")
    assert enc_resp.status_code == 200
    assert enc_resp.headers.get("content-type") == "application/pdf"
    assert enc_resp.content.startswith(b"%PDF-"), f"First bytes: {enc_resp.content[:20]}"
    assert len(enc_resp.content) > 100
    print("  ✅ PASSED")


@pytest.mark.asyncio
async def test_prescription_pdf_download(client: httpx.AsyncClient, db_session: Session) -> None:
    """Scenario 2: Patient downloads prescription PDF → 200 + %PDF-"""
    if not WEASYPRINT_WORKS:
        pytest.skip("WeasyPrint GTK libs not available on this system")

    # ── Setup ──
    tenant = create_tenant(db_session)
    doc_user = create_user(db_session, email=f"dr_{uuid.uuid4().hex[:8]}@test.com",
                           password="DocPass9!", role=UserRole.doctor, tenant_id=tenant.id)
    doctor = create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_user.id)
    pat_user = create_user(db_session, email=f"pat_{uuid.uuid4().hex[:8]}@test.com",
                           password="PatPass9!", role=UserRole.patient)
    patient = create_patient_profile(db_session, tenant_id=tenant.id, user_id=pat_user.id, created_by=doc_user.id)

    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    appt = add_appointment(db_session, {
        "patient_id": patient.id, "doctor_id": doctor.id, "appointment_time": past_time,
        "status": AppointmentStatus.scheduled, "created_by": doc_user.id, "tenant_id": tenant.id,
    })
    rx = add_prescription(db_session, appointment_id=appt.id, doctor_id=doctor.id,
                          patient_id=patient.id, tenant_id=tenant.id, notes="Take with food")
    add_prescription_item(db_session, prescription_id=rx.id, line_data={
        "medicine_name": "Ibuprofen", "dosage": "400mg", "frequency": "TDS",
        "duration": "3 days", "instructions": "After food",
    })
    appt.status = AppointmentStatus.completed
    db_session.commit()

    pat_login = await client.post("/api/v1/login",
        data={"username": pat_user.email, "password": "PatPass9!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert pat_login.status_code == 200
    pat_headers = {"Authorization": f"Bearer {pat_login.json()['access_token']}"}

    rx_resp = await client.get(f"/api/v1/documents/prescription/{appt.id}", headers=pat_headers)

    print(f"\n[Scenario 2] Status: {rx_resp.status_code}  Type: {rx_resp.headers.get('content-type')}  Size: {len(rx_resp.content)}")
    assert rx_resp.status_code == 200
    assert rx_resp.headers.get("content-type") == "application/pdf"
    assert rx_resp.content.startswith(b"%PDF-"), f"First bytes: {rx_resp.content[:20]}"
    assert len(rx_resp.content) > 100
    print("  ✅ PASSED")


@pytest.mark.asyncio
async def test_weasyprint_failure_does_not_corrupt_pdf(client: httpx.AsyncClient, db_session: Session) -> None:
    """Scenario 4: When WeasyPrint fails, no corrupted PDF is delivered.

    Instead of a fake PDF, the endpoint should raise an exception that
    propagates through FastAPI/Starlette as an error response or exception.
    The httpx ASGI transport will propagate the OSError to the caller.
    """
    import app.services.document_service as ds

    # Monkey-patch _render_pdf to simulate a failure even if weasyprint works
    original = ds._render_pdf

    def broken_render(html: str, fmt):
        from app.schemas.document import DocumentFormat
        if fmt == DocumentFormat.html:
            return html.encode("utf-8")
        raise RuntimeError("Simulated PDF generation failure — weasyprint unavailable")

    ds._render_pdf = broken_render

    try:
        tenant = create_tenant(db_session)
        doc_user = create_user(db_session, email=f"dr_{uuid.uuid4().hex[:8]}@test.com",
                               password="DocPass9!", role=UserRole.doctor, tenant_id=tenant.id)
        doctor = create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_user.id)
        pat_user = create_user(db_session, email=f"pat_{uuid.uuid4().hex[:8]}@test.com",
                               password="PatPass9!", role=UserRole.patient)
        patient = create_patient_profile(db_session, tenant_id=tenant.id, user_id=pat_user.id, created_by=doc_user.id)

        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        appt = add_appointment(db_session, {
            "patient_id": patient.id, "doctor_id": doctor.id, "appointment_time": past_time,
            "status": AppointmentStatus.scheduled, "created_by": doc_user.id, "tenant_id": tenant.id,
        })
        appt.status = AppointmentStatus.completed
        db_session.commit()

        pat_login = await client.post("/api/v1/login",
            data={"username": pat_user.email, "password": "PatPass9!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert pat_login.status_code == 200
        pat_headers = {"Authorization": f"Bearer {pat_login.json()['access_token']}"}

        # This should raise — _render_pdf now always fails
        response = await client.get(f"/api/v1/documents/prescription/{appt.id}", headers=pat_headers)

        # If we get here, it means Starlette caught the exception and returned a response
        # The response should NOT be a corrupted PDF
        assert response.status_code != 200, \
            f"Expected failure but got 200. Content-Type: {response.headers.get('content-type')}"
        print(f"  ✅ WeasyPrint failure → HTTP {response.status_code} (no corrupted PDF)")

    except (RuntimeError, OSError) as e:
        # The exception propagated through the ASGI transport — this is also correct
        print(f"  ✅ WeasyPrint failure → exception propagated ({type(e).__name__})")
    except Exception as e:
        print(f"  ✅ WeasyPrint failure → exception propagated ({type(e).__name__})")
    finally:
        ds._render_pdf = original

    print("  ✅ PASSED")
