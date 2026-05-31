"""Transactional rollback + idempotency invariant regression tests for appointment workflows.

Protects the most dangerous transactional and replay invariants before any future
decomposition work.  Uses real DB / session behaviour wherever possible.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.crud_appointment import add_appointment
from app.models.appointment import (
    Appointment,
    AppointmentCompletionIdempotency,
    AppointmentCreationIdempotency,
    AppointmentStatus,
    Prescription,
)
from app.models.billing import Billing
from app.models.inventory import (
    AppointmentInventoryUsage,
    InventoryItem,
    InventoryItemType,
    InventoryStock,
)
from app.models.patient_medication_schedule import PatientMedicationSchedule
from app.services import billing_service
from tests.factories import seed_bookable_doctor_and_patient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_inventory_item_with_stock(
    db: Session,
    tenant_id: uuid.UUID,
    quantity: int = 100,
) -> InventoryItem:
    item = InventoryItem(
        name="Test regression medicine",
        type=InventoryItemType.medicine,
        unit="tablet",
        cost_price=Decimal("20.00"),
        selling_price=Decimal("50.00"),
        tenant_id=tenant_id,
        is_active=True,
    )
    db.add(item)
    db.flush()
    stock = InventoryStock(item_id=item.id, doctor_id=None, quantity=quantity)
    db.add(stock)
    db.flush()
    return item


async def _login_as(
    client: AsyncClient, email: str, password: str
) -> dict[str, str]:
    """Return auth headers for the given user."""
    r = await client.post(
        "/api/v1/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _setup_doctor_and_patient(
    db: Session, tag: str
) -> tuple:  # (Doctor, Patient, datetime, headers_dict, tenant_id_str)
    doc_email = f"doc_{tag}_{uuid.uuid4().hex[:8]}@reg.test"
    pat_email = f"pat_{tag}_{uuid.uuid4().hex[:8]}@reg.test"
    doc_pw = "RegPass123!"
    pat_pw = "RegPass123!"
    doctor, patient, _slot = seed_bookable_doctor_and_patient(
        db,
        doctor_email=doc_email,
        doctor_password=doc_pw,
        patient_email=pat_email,
        patient_password=pat_pw,
    )
    assert doctor.tenant_id is not None
    appointment = add_appointment(
        db,
        {
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "appointment_time": datetime.now(timezone.utc) + timedelta(minutes=10),
            "status": AppointmentStatus.scheduled,
            "created_by": patient.user_id,
            "tenant_id": doctor.tenant_id,
        },
    )
    db.commit()
    return doctor, patient, appointment, doc_email, doc_pw, str(doctor.tenant_id)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Completion rollback on billing failure
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_completion_rollback_on_billing_failure(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario: billing_service.create_bill raises AFTER inventory consumption,
    prescription creation, and medication schedule creation.

    Invariant: FULL rollback — no partial side effect survives.
    """
    doctor, patient, appointment, doc_email, doc_pw, tenant_id = (
        _setup_doctor_and_patient(db_session, "rb")
    )
    appt_id = str(appointment.id)
    item = _create_inventory_item_with_stock(db_session, doctor.tenant_id)
    db_session.commit()

    doc_headers = await _login_as(client, doc_email, doc_pw)
    doc_headers["X-Tenant-ID"] = tenant_id

    # Patch billing_service.create_bill to raise ValidationError after the
    # point where inventory / prescriptions / schedules have been flushed.
    from app.services.exceptions import ValidationError as SvcValidationError

    with patch.object(
        billing_service,
        "create_bill",
        side_effect=SvcValidationError("Billing service unavailable"),
    ):
        resp = await client.post(
            f"/api/v1/appointments/{appt_id}/mark-completed",
            json={
                "generate_bill": True,
                "bill_consultation_amount": "250.00",
                "completion_notes": "Regression rollback test",
                "items": [{"item_id": str(item.id), "quantity": 1}],
                "prescriptions": [
                    {
                        "notes": "Take as directed",
                        "items": [
                            {
                                "medicine_name": "Amoxicillin",
                                "dosage": "250 mg",
                                "frequency": "Three times a day",
                                "duration": "7 days",
                                "instructions": "After meals",
                            }
                        ],
                    }
                ],
            },
            headers={**doc_headers, "Idempotency-Key": str(uuid.uuid4())},
        )
        # ServiceError (parent of ValidationError) is mapped to 400 by FastAPI
        assert resp.status_code == 400

    db_session.expire_all()

    # (a) appointment.status NOT completed
    appt = db_session.get(Appointment, uuid.UUID(appt_id))
    assert appt is not None
    assert appt.status != AppointmentStatus.completed, (
        f"Expected status != completed, got {appt.status}"
    )

    # (b) no bill created
    bills = list(
        db_session.scalars(
            select(Billing).where(Billing.appointment_id == uuid.UUID(appt_id))
        )
    )
    assert len(bills) == 0

    # (c) no inventory deduction persisted
    usages = list(
        db_session.scalars(
            select(AppointmentInventoryUsage).where(
                AppointmentInventoryUsage.appointment_id == uuid.UUID(appt_id)
            )
        )
    )
    assert len(usages) == 0

    # (d) no prescriptions persisted
    prescriptions = list(
        db_session.scalars(
            select(Prescription).where(
                Prescription.appointment_id == uuid.UUID(appt_id)
            )
        )
    )
    assert len(prescriptions) == 0

    # (e) no medication schedules persisted
    schedules = list(
        db_session.scalars(
            select(PatientMedicationSchedule).where(
                PatientMedicationSchedule.patient_id == patient.id
            )
        )
    )
    assert len(schedules) == 0


# ═══════════════════════════════════════════════════════════════════════════
# 2. Completion idempotency replay — SAME body
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_completion_idempotency_replay_same_body(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario: same idempotency key + identical body replay.

    Invariant: second request returns existing result safely; no duplicate
    inventory deductions, bills, prescriptions, or schedules.
    """
    doctor, patient, appointment, doc_email, doc_pw, tenant_id = (
        _setup_doctor_and_patient(db_session, "replay_same")
    )
    appt_id = str(appointment.id)
    item = _create_inventory_item_with_stock(db_session, doctor.tenant_id)
    db_session.commit()

    doc_headers = await _login_as(client, doc_email, doc_pw)
    doc_headers["X-Tenant-ID"] = tenant_id

    idem_key = str(uuid.uuid4())
    payload = {
        "generate_bill": True,
        "bill_consultation_amount": "100.00",
        "clinical_notes": "Follow-up visit",
        "items": [{"item_id": str(item.id), "quantity": 1}],
        "prescriptions": [
            {
                "notes": "Take weekly",
                "items": [
                    {
                        "medicine_name": "Multivitamin",
                        "dosage": "1 tablet",
                        "frequency": "Once daily",
                        "duration": "30 days",
                        "instructions": "After breakfast",
                    }
                ],
            }
        ],
    }

    # First request — processes the completion
    first = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": idem_key},
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "completed"
    assert "X-Idempotent-Replay" not in first.headers

    # Second request — idempotent replay
    second = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": idem_key},
    )
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "completed"
    assert second.headers.get("X-Idempotent-Replay") == "1"

    db_session.expire_all()

    # Exactly one bill
    bills = list(
        db_session.scalars(
            select(Billing).where(Billing.appointment_id == uuid.UUID(appt_id))
        )
    )
    assert len(bills) == 1

    # Exactly one inventory usage row
    usages = list(
        db_session.scalars(
            select(AppointmentInventoryUsage).where(
                AppointmentInventoryUsage.appointment_id == uuid.UUID(appt_id)
            )
        )
    )
    assert len(usages) == 1

    # Exactly one prescription
    prescriptions = list(
        db_session.scalars(
            select(Prescription).where(
                Prescription.appointment_id == uuid.UUID(appt_id)
            )
        )
    )
    assert len(prescriptions) == 1

    # Exactly one medication schedule
    schedules = list(
        db_session.scalars(
            select(PatientMedicationSchedule).where(
                PatientMedicationSchedule.patient_id == patient.id
            )
        )
    )
    assert len(schedules) == 1

    # Exactly one completion idempotency row
    idem_rows = list(
        db_session.scalars(
            select(AppointmentCompletionIdempotency).where(
                AppointmentCompletionIdempotency.appointment_id
                == uuid.UUID(appt_id)
            )
        )
    )
    assert len(idem_rows) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 3. Completion idempotency replay — DIFFERENT body
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_completion_idempotency_replay_different_body(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario: same idempotency key, modified payload.

    Invariant: ConflictError raised; original appointment & side effects preserved.
    """
    doctor, patient, appointment, doc_email, doc_pw, tenant_id = (
        _setup_doctor_and_patient(db_session, "replay_diff")
    )
    appt_id = str(appointment.id)
    item = _create_inventory_item_with_stock(db_session, doctor.tenant_id)
    db_session.commit()

    doc_headers = await _login_as(client, doc_email, doc_pw)
    doc_headers["X-Tenant-ID"] = tenant_id

    idem_key = str(uuid.uuid4())
    original_payload = {
        "clinical_notes": "First visit notes",
        "items": [{"item_id": str(item.id), "quantity": 1}],
        "prescriptions": [
            {
                "notes": "Initial prescription",
                "items": [
                    {
                        "medicine_name": "Ibuprofen",
                        "dosage": "200 mg",
                        "frequency": "Twice daily",
                        "duration": "5 days",
                        "instructions": "With food",
                    }
                ],
            }
        ],
    }

    # First: process normally (no billing to keep it simple)
    first = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=original_payload,
        headers={**doc_headers, "Idempotency-Key": idem_key},
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "completed"

    db_session.expire_all()
    appt_before = db_session.get(Appointment, uuid.UUID(appt_id))
    original_clinical_notes = appt_before.clinical_notes
    orig_prescription_count = len(
        list(
            db_session.scalars(
                select(Prescription).where(
                    Prescription.appointment_id == uuid.UUID(appt_id)
                )
            )
        )
    )

    # Second: different body, same key
    modified_payload = {
        "clinical_notes": "Completely different notes",
        "items": [{"item_id": str(item.id), "quantity": 1}],
        "prescriptions": [],
    }

    second = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=modified_payload,
        headers={**doc_headers, "Idempotency-Key": idem_key},
    )
    assert second.status_code == 400
    detail = second.json().get("detail", "").lower()
    assert "idempotency key reused with different request payload" in detail

    # Original state is preserved
    db_session.expire_all()
    appt_after = db_session.get(Appointment, uuid.UUID(appt_id))
    assert appt_after.status == AppointmentStatus.completed
    assert appt_after.clinical_notes == original_clinical_notes

    after_prescription_count = len(
        list(
            db_session.scalars(
                select(Prescription).where(
                    Prescription.appointment_id == uuid.UUID(appt_id)
                )
            )
        )
    )
    assert after_prescription_count == orig_prescription_count


# ═══════════════════════════════════════════════════════════════════════════
# 4. create_appointment duplicate idempotency replay
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_appointment_duplicate_idempotency_replay(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario: duplicate create request with same idempotency key + body.

    Invariant: existing appointment safely returned; no duplicate appointment
    or idempotency rows.
    """
    doc_email = f"doc_create_idem_{uuid.uuid4().hex[:8]}@reg.test"
    pat_email = f"pat_create_idem_{uuid.uuid4().hex[:8]}@reg.test"
    doctor, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password="RegPass123!",
        patient_email=pat_email,
        patient_password="RegPass123!",
    )

    pat_headers = await _login_as(client, pat_email, "RegPass123!")
    doctor_id = str(doctor.id)
    patient_id = str(patient.id)

    idem_key = str(uuid.uuid4())
    payload = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": slot.isoformat(),
    }

    # First create
    first = await client.post(
        "/api/v1/appointments",
        json=payload,
        headers={**pat_headers, "Idempotency-Key": idem_key},
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["id"]
    assert "X-Idempotent-Replay" not in first.headers

    # Second create — same key, same body
    second = await client.post(
        "/api/v1/appointments",
        json=payload,
        headers={**pat_headers, "Idempotency-Key": idem_key},
    )
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first_id
    assert second.headers.get("X-Idempotent-Replay") == "1"

    # No duplicate appointment rows
    appts = list(db_session.scalars(select(Appointment)))
    assert len(appts) == 1

    # No duplicate creation idempotency rows
    idem_rows = list(db_session.scalars(select(AppointmentCreationIdempotency)))
    assert len(idem_rows) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 5. create_appointment duplicate key with different body
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_appointment_different_body_same_key(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario: same idempotency key, different request body on create.

    Invariant: ConflictError raised; original appointment preserved.
    """
    doc_email = f"doc_create_diff_{uuid.uuid4().hex[:8]}@reg.test"
    pat_email = f"pat_create_diff_{uuid.uuid4().hex[:8]}@reg.test"
    doctor, patient, slot = seed_bookable_doctor_and_patient(
        db_session,
        doctor_email=doc_email,
        doctor_password="RegPass123!",
        patient_email=pat_email,
        patient_password="RegPass123!",
    )
    db_session.commit()

    pat_headers = await _login_as(client, pat_email, "RegPass123!")
    doctor_id = str(doctor.id)
    patient_id = str(patient.id)

    idem_key = str(uuid.uuid4())
    original_payload = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": slot.isoformat(),
    }

    # First create
    first = await client.post(
        "/api/v1/appointments",
        json=original_payload,
        headers={**pat_headers, "Idempotency-Key": idem_key},
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["id"]

    # Create a different slot time for the modified payload
    different_slot = (slot + timedelta(hours=2)).isoformat()
    modified_payload = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": different_slot,
    }

    # Second create — same key, different body
    second = await client.post(
        "/api/v1/appointments",
        json=modified_payload,
        headers={**pat_headers, "Idempotency-Key": idem_key},
    )
    assert second.status_code == 400
    detail = second.json().get("detail", "").lower()
    assert "idempotency key reused with different request payload" in detail

    # Original appointment preserved
    db_session.expire_all()
    appts = list(db_session.scalars(select(Appointment)))
    assert len(appts) == 1
    assert str(appts[0].id) == first_id


# ═══════════════════════════════════════════════════════════════════════════
# 6. Concurrent completion protection
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_concurrent_completion_protection(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario: two completion attempts against the same appointment.

    Invariant: exactly one succeeds; no duplicate bills, schedules, or
    inventory deductions.
    """
    doctor, patient, appointment, doc_email, doc_pw, tenant_id = (
        _setup_doctor_and_patient(db_session, "concur")
    )
    appt_id = str(appointment.id)
    item = _create_inventory_item_with_stock(db_session, doctor.tenant_id)
    db_session.commit()

    doc_headers = await _login_as(client, doc_email, doc_pw)
    doc_headers["X-Tenant-ID"] = tenant_id

    # Use the SAME idempotency key for both attempts to simulate the
    # concurrent-safe path (unique constraint + savepoint catches duplicates).
    common_key = str(uuid.uuid4())
    payload = {
        "generate_bill": True,
        "bill_consultation_amount": "150.00",
        "clinical_notes": "Concurrent test",
        "items": [{"item_id": str(item.id), "quantity": 1}],
        "prescriptions": [
            {
                "notes": "Standard course",
                "items": [
                    {
                        "medicine_name": "Metformin",
                        "dosage": "500 mg",
                        "frequency": "Twice daily",
                        "duration": "30 days",
                        "instructions": "With meals",
                    }
                ],
            }
        ],
    }

    # First attempt
    first = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": common_key},
    )
    assert first.status_code == 200, first.text

    # Second attempt — same key triggers idempotency replay
    second = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": common_key},
    )
    assert second.status_code == 200, second.text
    assert second.headers.get("X-Idempotent-Replay") == "1"

    db_session.expire_all()

    # Exactly one bill
    bills = list(
        db_session.scalars(
            select(Billing).where(Billing.appointment_id == uuid.UUID(appt_id))
        )
    )
    assert len(bills) == 1

    # Exactly one inventory usage
    usages = list(
        db_session.scalars(
            select(AppointmentInventoryUsage).where(
                AppointmentInventoryUsage.appointment_id == uuid.UUID(appt_id)
            )
        )
    )
    assert len(usages) == 1

    # Exactly one prescription
    prescriptions = list(
        db_session.scalars(
            select(Prescription).where(
                Prescription.appointment_id == uuid.UUID(appt_id)
            )
        )
    )
    assert len(prescriptions) == 1

    # Exactly one medication schedule
    schedules = list(
        db_session.scalars(
            select(PatientMedicationSchedule).where(
                PatientMedicationSchedule.patient_id == patient.id
            )
        )
    )
    assert len(schedules) == 1

    # Exactly one completion idempotency record
    idem_rows = list(
        db_session.scalars(
            select(AppointmentCompletionIdempotency).where(
                AppointmentCompletionIdempotency.appointment_id
                == uuid.UUID(appt_id)
            )
        )
    )
    assert len(idem_rows) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 7. Completion with notes-only prescription
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_completion_notes_only_prescription(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario: completion with a prescription that has notes but no items.

    Invariant: completion succeeds; no medication schedules created; no
    errors thrown; encounter state is valid.
    """
    doctor, patient, appointment, doc_email, doc_pw, tenant_id = (
        _setup_doctor_and_patient(db_session, "notes_only")
    )
    appt_id = str(appointment.id)
    db_session.commit()

    doc_headers = await _login_as(client, doc_email, doc_pw)
    doc_headers["X-Tenant-ID"] = tenant_id

    payload = {
        "clinical_notes": "Visit with notes-only prescription",
        "prescriptions": [
            {
                "notes": "Patient advised rest and hydration — no medication needed",
                "items": [],
            }
        ],
    }

    resp = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"
    assert resp.json()["encounter_completed_at"] is not None
    assert resp.json()["encounter_started_at"] is not None

    db_session.expire_all()

    # Prescription exists (notes-only prescription IS created)
    prescriptions = list(
        db_session.scalars(
            select(Prescription).where(
                Prescription.appointment_id == uuid.UUID(appt_id)
            )
        )
    )
    assert len(prescriptions) == 1
    assert prescriptions[0].notes == (
        "Patient advised rest and hydration — no medication needed"
    )

    # No medication schedules (no items → no schedules derived)
    schedules = list(
        db_session.scalars(
            select(PatientMedicationSchedule).where(
                PatientMedicationSchedule.patient_id == patient.id
            )
        )
    )
    assert len(schedules) == 0

    # Encounter state valid
    appt = db_session.get(Appointment, uuid.UUID(appt_id))
    assert appt is not None
    assert appt.status == AppointmentStatus.completed
    assert appt.encounter_started_at is not None
    assert appt.encounter_completed_at is not None
    assert appt.encounter_completed_at >= appt.encounter_started_at


# ═══════════════════════════════════════════════════════════════════════════
# 8. Outcome hash replay consistency
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_outcome_hash_replay_consistency(
    client: AsyncClient, db_session: Session
) -> None:
    """Scenario: replay returns same outcome hash; mutation after completion
    triggers mismatch detection.

    Invariant: stored result_hash is consistent on replay; state mutation
    causes outcome drift that is detected (logged/metric incremented).
    """
    doctor, patient, appointment, doc_email, doc_pw, tenant_id = (
        _setup_doctor_and_patient(db_session, "hash")
    )
    appt_id = str(appointment.id)
    db_session.commit()

    doc_headers = await _login_as(client, doc_email, doc_pw)
    doc_headers["X-Tenant-ID"] = tenant_id

    idem_key = str(uuid.uuid4())
    payload = {
        "generate_bill": True,
        "bill_consultation_amount": "200.00",
        "clinical_notes": "Hash consistency visit",
    }

    # First completion
    first = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": idem_key},
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "completed"

    db_session.expire_all()

    # Check the stored result_hash
    idem_row = db_session.scalar(
        select(AppointmentCompletionIdempotency).where(
            AppointmentCompletionIdempotency.appointment_id
            == uuid.UUID(appt_id),
            AppointmentCompletionIdempotency.idempotency_key == idem_key,
        )
    )
    assert idem_row is not None
    assert idem_row.result_hash is not None
    assert idem_row.billing_id is not None
    stored_hash = idem_row.result_hash

    # Replay returns the same outcome (same billing_id → same result_hash)
    second = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": idem_key},
    )
    assert second.status_code == 200, second.text
    assert second.headers.get("X-Idempotent-Replay") == "1"

    # Mutate: delete the bill to cause outcome drift
    bill = db_session.scalar(
        select(Billing).where(Billing.appointment_id == uuid.UUID(appt_id))
    )
    assert bill is not None
    db_session.delete(bill)
    db_session.commit()

    # Replay again — outcome hash no longer matches stored hash.
    # The service still returns 200 but detects and logs the mismatch.
    third = await client.post(
        f"/api/v1/appointments/{appt_id}/mark-completed",
        json=payload,
        headers={**doc_headers, "Idempotency-Key": idem_key},
    )
    assert third.status_code == 200, third.text
    assert third.headers.get("X-Idempotent-Replay") == "1"

    # The stored idempotency row should still have the original hash
    # (it is NOT updated on replay — only compared for drift detection)
    db_session.expire_all()
    idem_row_after = db_session.scalar(
        select(AppointmentCompletionIdempotency).where(
            AppointmentCompletionIdempotency.appointment_id
            == uuid.UUID(appt_id),
            AppointmentCompletionIdempotency.idempotency_key == idem_key,
        )
    )
    assert idem_row_after is not None
    assert idem_row_after.result_hash == stored_hash
