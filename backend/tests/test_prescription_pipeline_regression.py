"""
Regression tests for the encounter → prescription → medication schedule pipeline.

These protect recently stabilized clinical workflows from regressions without
refactoring application code or redesigning tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.crud import crud_appointment, crud_medication_schedule
from app.models.appointment import AppointmentStatus, Prescription, PrescriptionItem
from app.models.inventory import AppointmentInventoryUsage, InventoryItem, InventoryItemType
from app.models.patient_medication_schedule import PatientMedicationSchedule
from app.models.user import User, UserRole
from app.schemas.appointment import PrescriptionCreate, PrescriptionItemCreate
from app.services import appointment_service, encounter_service, patient_service
from app.services.exceptions import NotFoundError
from tests.factories import (
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

_PAST_TIME = datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)


def _setup_minimal(db: Session) -> tuple[User, User, UUID, UUID]:
    """Create tenant, doctor, patient. Returns (doc_user, pat_user, doctor_id, patient_id)."""
    tenant = create_tenant(db)
    doc_user = create_user(
        db, email="doc@regtest.test", password="TestPass9!",
        role=UserRole.doctor, tenant_id=tenant.id,
    )
    doctor = create_doctor_profile(db, tenant_id=tenant.id, user_id=doc_user.id)
    pat_user = create_user(
        db, email="pat@regtest.test", password="TestPass9!",
        role=UserRole.patient,
    )
    patient = create_patient_profile(
        db, tenant_id=tenant.id, user_id=pat_user.id, created_by=doc_user.id,
    )
    return doc_user, pat_user, doctor.id, patient.id


def _make_scheduled_appointment(
    db: Session, doctor_id: UUID, patient_id: UUID, doctor_user_id: UUID, tenant_id: UUID,
    *, appt_time: datetime | None = None,
) -> UUID:
    """Create a scheduled appointment (returns ID)."""
    appt = crud_appointment.add_appointment(db, {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": appt_time or _PAST_TIME,
        "status": AppointmentStatus.scheduled,
        "created_by": doctor_user_id,
        "tenant_id": tenant_id,
    })
    db.commit()
    return appt.id


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Encounter completion with structured prescription items
# ═══════════════════════════════════════════════════════════════════════════════


class TestStructuredPrescriptionPipeline:
    """Prescription → PrescriptionItem → PatientMedicationSchedule are all created."""

    def test_prescription_rows_created(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="Take with food",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        prescriptions = db_session.query(Prescription).filter(
            Prescription.appointment_id == appt_id,
        ).all()
        assert len(prescriptions) == 1
        assert prescriptions[0].notes == "Take with food"

    def test_prescription_item_rows_created(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="Take with food",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        items = db_session.query(PrescriptionItem).join(Prescription).filter(
            Prescription.appointment_id == appt_id,
        ).all()
        assert len(items) == 1
        assert items[0].medicine_name == "Paracetamol"
        assert items[0].dosage == "500mg"

    def test_medication_schedule_rows_created(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="Take with food",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        schedules = db_session.query(PatientMedicationSchedule).filter(
            PatientMedicationSchedule.patient_id == patient_id,
        ).all()
        assert len(schedules) == 1
        assert schedules[0].medicine_name == "Paracetamol"
        assert schedules[0].dosage == "500mg"
        assert schedules[0].frequency == "TDS"
        assert schedules[0].duration == "5 days"

    def test_patient_medicines_query_returns_schedules(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="Take with food",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        schedules, total = crud_medication_schedule.get_active_schedules_for_patient(
            db_session, patient_id, appt.tenant_id,
        )
        assert total == 1
        assert len(schedules) == 1
        assert schedules[0].medicine_name == "Paracetamol"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Notes-only prescription
# ═══════════════════════════════════════════════════════════════════════════════


class TestNotesOnlyPrescription:
    """Notes-only prescriptions create a Prescription row but no items or schedules."""

    def test_prescription_row_allowed(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(notes="Patient advised rest and hydration"),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        prescriptions = db_session.query(Prescription).filter(
            Prescription.appointment_id == appt_id,
        ).all()
        assert len(prescriptions) == 1
        assert prescriptions[0].notes == "Patient advised rest and hydration"

    def test_no_prescription_item_rows(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(notes="Patient advised rest and hydration"),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        items = db_session.query(PrescriptionItem).join(Prescription).filter(
            Prescription.appointment_id == appt_id,
        ).all()
        assert len(items) == 0

    def test_no_medication_schedules(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(notes="Patient advised rest and hydration"),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        schedules = db_session.query(PatientMedicationSchedule).filter(
            PatientMedicationSchedule.patient_id == patient_id,
        ).all()
        assert len(schedules) == 0

    def test_no_errors_thrown(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(notes="Patient advised rest and hydration"),
        ]
        try:
            appointment_service._create_appointment_prescriptions(
                db_session, appt, rx_data,
            )
            db_session.commit()
        except Exception as exc:
            pytest.fail(f"Notes-only prescription raised unexpected error: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. External pharmacy prescription (no inventory deduction)
# ═══════════════════════════════════════════════════════════════════════════════


class TestExternalPharmacyPrescription:
    """External pharmacy prescriptions create items and schedules but no inventory usage."""

    def test_prescription_items_created(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="External pharmacy",
                items=[PrescriptionItemCreate(
                    medicine_name="Amoxicillin", dosage="250mg",
                    frequency="TDS", duration="7 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        items = db_session.query(PrescriptionItem).join(Prescription).filter(
            Prescription.appointment_id == appt_id,
        ).all()
        assert len(items) == 1
        assert items[0].medicine_name == "Amoxicillin"

    def test_medication_schedules_created(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="External pharmacy",
                items=[PrescriptionItemCreate(
                    medicine_name="Amoxicillin", dosage="250mg",
                    frequency="TDS", duration="7 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        schedules = db_session.query(PatientMedicationSchedule).filter(
            PatientMedicationSchedule.patient_id == patient_id,
        ).all()
        assert len(schedules) == 1
        assert schedules[0].medicine_name == "Amoxicillin"

    def test_no_inventory_deduction(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="External pharmacy",
                items=[PrescriptionItemCreate(
                    medicine_name="Amoxicillin", dosage="250mg",
                    frequency="TDS", duration="7 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        db_session.commit()

        usage = db_session.query(AppointmentInventoryUsage).filter(
            AppointmentInventoryUsage.appointment_id == appt_id,
        ).all()
        assert len(usage) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Inventory-dispensed medicine
# ═══════════════════════════════════════════════════════════════════════════════


class TestInventoryDispensedMedicine:
    """Inventory-dispensed medicines have schedules AND inventory usage, independently."""

    def test_prescription_items_created(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="Dispensed from clinic",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="3 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        # Add inventory usage separately (independent of prescription pipeline)
        inv_item = InventoryItem(
            tenant_id=appt.tenant_id, name="Paracetamol 500mg",
            type=InventoryItemType.medicine, unit="tablet",
            cost_price=Decimal("1.00"), selling_price=Decimal("2.50"),
        )
        db_session.add(inv_item)
        db_session.flush()
        inv_usage = AppointmentInventoryUsage(
            appointment_id=appt.id, item_id=inv_item.id, quantity=10,
        )
        db_session.add(inv_usage)
        db_session.commit()

        items = db_session.query(PrescriptionItem).join(Prescription).filter(
            Prescription.appointment_id == appt_id,
        ).all()
        assert len(items) == 1

    def test_medication_schedules_created(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="Dispensed from clinic",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="3 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        inv_item = InventoryItem(
            tenant_id=appt.tenant_id, name="Paracetamol 500mg",
            type=InventoryItemType.medicine, unit="tablet",
            cost_price=Decimal("1.00"), selling_price=Decimal("2.50"),
        )
        db_session.add(inv_item)
        db_session.flush()
        inv_usage = AppointmentInventoryUsage(
            appointment_id=appt.id, item_id=inv_item.id, quantity=10,
        )
        db_session.add(inv_usage)
        db_session.commit()

        schedules = db_session.query(PatientMedicationSchedule).filter(
            PatientMedicationSchedule.patient_id == patient_id,
        ).all()
        assert len(schedules) == 1

    def test_inventory_usage_recorded_separately(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        rx_data = [
            PrescriptionCreate(
                notes="Dispensed from clinic",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="3 days",
                )],
            ),
        ]
        appointment_service._create_appointment_prescriptions(db_session, appt, rx_data)
        inv_item = InventoryItem(
            tenant_id=appt.tenant_id, name="Paracetamol 500mg",
            type=InventoryItemType.medicine, unit="tablet",
            cost_price=Decimal("1.00"), selling_price=Decimal("2.50"),
        )
        db_session.add(inv_item)
        db_session.flush()
        inv_usage = AppointmentInventoryUsage(
            appointment_id=appt.id, item_id=inv_item.id, quantity=10,
        )
        db_session.add(inv_usage)
        db_session.commit()

        usage = db_session.query(AppointmentInventoryUsage).filter(
            AppointmentInventoryUsage.appointment_id == appt_id,
        ).all()
        assert len(usage) == 1
        assert usage[0].quantity == 10

        # Inventory data is independent of prescription data
        schedule_names = [
            s.medicine_name
            for s in db_session.query(PatientMedicationSchedule).filter(
                PatientMedicationSchedule.patient_id == patient_id,
            ).all()
        ]
        assert "Paracetamol" in schedule_names


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Multiple encounters same patient
# ═══════════════════════════════════════════════════════════════════════════════


class TestMultipleEncountersSamePatient:
    """Medication schedules from multiple encounters aggregate correctly."""

    def test_schedules_aggregate_correctly(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_1_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
            appt_time=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_2_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
            appt_time=datetime(2024, 7, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_1 = crud_appointment.get_appointment(db_session, appt_1_id)
        appt_2 = crud_appointment.get_appointment(db_session, appt_2_id)
        tenant_id = doc_user.tenant_id

        appointment_service._create_appointment_prescriptions(db_session, appt_1, [
            PrescriptionCreate(
                notes="First visit",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ])
        appointment_service._create_appointment_prescriptions(db_session, appt_2, [
            PrescriptionCreate(
                notes="Second visit",
                items=[PrescriptionItemCreate(
                    medicine_name="Amoxicillin", dosage="250mg",
                    frequency="BD", duration="7 days",
                )],
            ),
        ])
        db_session.commit()

        schedules, total = crud_medication_schedule.get_active_schedules_for_patient(
            db_session, patient_id, tenant_id,
        )
        assert total == 2
        medicine_names = {s.medicine_name for s in schedules}
        assert medicine_names == {"Paracetamol", "Amoxicillin"}

    def test_no_duplicate_corruption(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_1_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
            appt_time=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_2_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
            appt_time=datetime(2024, 7, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_1 = crud_appointment.get_appointment(db_session, appt_1_id)
        appt_2 = crud_appointment.get_appointment(db_session, appt_2_id)
        tenant_id = doc_user.tenant_id

        appointment_service._create_appointment_prescriptions(db_session, appt_1, [
            PrescriptionCreate(
                notes="Same medicine",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ])
        appointment_service._create_appointment_prescriptions(db_session, appt_2, [
            PrescriptionCreate(
                notes="Same medicine again",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ])
        db_session.commit()

        schedules, total = crud_medication_schedule.get_active_schedules_for_patient(
            db_session, patient_id, tenant_id,
        )
        assert total == 2
        assert len(schedules) == 2
        # Verify distinct prescription_item_ids (no duplicate corruption)
        rx_item_ids = {s.prescription_item_id for s in schedules}
        assert len(rx_item_ids) == 2

    def test_patient_medication_history_stable(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_1_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
            appt_time=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_2_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
            appt_time=datetime(2024, 7, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_1 = crud_appointment.get_appointment(db_session, appt_1_id)
        appt_2 = crud_appointment.get_appointment(db_session, appt_2_id)

        appointment_service._create_appointment_prescriptions(db_session, appt_1, [
            PrescriptionCreate(
                notes="First visit",
                items=[PrescriptionItemCreate(
                    medicine_name="Medicine A", dosage="10mg",
                    frequency="OD", duration="30 days",
                )],
            ),
        ])
        appointment_service._create_appointment_prescriptions(db_session, appt_2, [
            PrescriptionCreate(
                notes="Second visit",
                items=[PrescriptionItemCreate(
                    medicine_name="Medicine B", dosage="20mg",
                    frequency="BD", duration="14 days",
                )],
            ),
        ])
        db_session.commit()

        # Encounters are still independently accessible
        enc_1 = encounter_service.get_encounter_detail(
            db_session, appt_1_id, doc_user, tenant_id=doc_user.tenant_id,
        )
        enc_2 = encounter_service.get_encounter_detail(
            db_session, appt_2_id, doc_user, tenant_id=doc_user.tenant_id,
        )
        assert len(enc_1.prescriptions) == 1
        assert len(enc_2.prescriptions) == 1
        assert enc_1.prescriptions[0].items[0].medicine_name == "Medicine A"
        assert enc_2.prescriptions[0].items[0].medicine_name == "Medicine B"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Multiple doctors same patient
# ═══════════════════════════════════════════════════════════════════════════════


class TestMultipleDoctorsSamePatient:
    """Medication schedules from different doctors for the same patient remain visible."""

    def test_schedules_remain_visible(self, db_session: Session) -> None:
        tenant = create_tenant(db_session)
        doc_1_user = create_user(
            db_session, email="doc1@regtest.test", password="TestPass9!",
            role=UserRole.doctor, tenant_id=tenant.id,
        )
        doc_1 = create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_1_user.id)
        doc_2_user = create_user(
            db_session, email="doc2@regtest.test", password="TestPass9!",
            role=UserRole.doctor, tenant_id=tenant.id,
        )
        doc_2 = create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_2_user.id)
        pat_user = create_user(
            db_session, email="pat@regtest.test", password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session, tenant_id=tenant.id, user_id=pat_user.id,
            created_by=doc_1_user.id,
        )

        appt_1_id = _make_scheduled_appointment(
            db_session, doc_1.id, patient.id, doc_1_user.id, tenant.id,
            appt_time=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_2_id = _make_scheduled_appointment(
            db_session, doc_2.id, patient.id, doc_2_user.id, tenant.id,
            appt_time=datetime(2024, 7, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_1 = crud_appointment.get_appointment(db_session, appt_1_id)
        appt_2 = crud_appointment.get_appointment(db_session, appt_2_id)

        appointment_service._create_appointment_prescriptions(db_session, appt_1, [
            PrescriptionCreate(
                notes="Dr 1 prescription",
                items=[PrescriptionItemCreate(
                    medicine_name="Medicine A", dosage="10mg",
                    frequency="OD", duration="30 days",
                )],
            ),
        ])
        appointment_service._create_appointment_prescriptions(db_session, appt_2, [
            PrescriptionCreate(
                notes="Dr 2 prescription",
                items=[PrescriptionItemCreate(
                    medicine_name="Medicine B", dosage="20mg",
                    frequency="BD", duration="14 days",
                )],
            ),
        ])
        db_session.commit()

        schedules, total = crud_medication_schedule.get_active_schedules_for_patient(
            db_session, patient.id, tenant.id,
        )
        assert total == 2
        medicine_names = {s.medicine_name for s in schedules}
        assert medicine_names == {"Medicine A", "Medicine B"}

    def test_attribution_preserved(self, db_session: Session) -> None:
        tenant = create_tenant(db_session)
        doc_1_user = create_user(
            db_session, email="doc1a@regtest.test", password="TestPass9!",
            role=UserRole.doctor, tenant_id=tenant.id,
        )
        doc_1 = create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_1_user.id)
        doc_2_user = create_user(
            db_session, email="doc2a@regtest.test", password="TestPass9!",
            role=UserRole.doctor, tenant_id=tenant.id,
        )
        doc_2 = create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_2_user.id)
        pat_user = create_user(
            db_session, email="pat2@regtest.test", password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session, tenant_id=tenant.id, user_id=pat_user.id,
            created_by=doc_1_user.id,
        )

        appt_1_id = _make_scheduled_appointment(
            db_session, doc_1.id, patient.id, doc_1_user.id, tenant.id,
            appt_time=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_2_id = _make_scheduled_appointment(
            db_session, doc_2.id, patient.id, doc_2_user.id, tenant.id,
            appt_time=datetime(2024, 7, 15, 10, 0, tzinfo=timezone.utc),
        )
        appt_1 = crud_appointment.get_appointment(db_session, appt_1_id)
        appt_2 = crud_appointment.get_appointment(db_session, appt_2_id)

        appointment_service._create_appointment_prescriptions(db_session, appt_1, [
            PrescriptionCreate(
                notes="Dr 1 Rx",
                items=[PrescriptionItemCreate(
                    medicine_name="Medicine A", dosage="10mg",
                    frequency="OD", duration="30 days",
                )],
            ),
        ])
        appointment_service._create_appointment_prescriptions(db_session, appt_2, [
            PrescriptionCreate(
                notes="Dr 2 Rx",
                items=[PrescriptionItemCreate(
                    medicine_name="Medicine B", dosage="20mg",
                    frequency="BD", duration="14 days",
                )],
            ),
        ])
        db_session.commit()

        rx_1 = db_session.query(Prescription).filter(
            Prescription.appointment_id == appt_1_id,
        ).first()
        rx_2 = db_session.query(Prescription).filter(
            Prescription.appointment_id == appt_2_id,
        ).first()
        assert rx_1.doctor_id == doc_1.id
        assert rx_2.doctor_id == doc_2.id


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Patient identity resolution
# ═══════════════════════════════════════════════════════════════════════════════


class TestPatientIdentityResolution:
    """User UUID != Patient UUID — patient medicine queries resolve correctly."""

    def test_user_uuid_differs_from_patient_uuid(self, db_session: Session) -> None:
        doc_user, pat_user, doctor_id, patient_id = _setup_minimal(db_session)
        assert pat_user.id != patient_id, (
            "User UUID must differ from Patient UUID for identity resolution test"
        )

    def test_patient_medication_query_by_patient_uuid(self, db_session: Session) -> None:
        doc_user, pat_user, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(
                notes="Test Rx",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ])
        db_session.commit()

        patient = patient_service.get_patient_by_user_id(db_session, pat_user.id)
        assert patient.id == patient_id
        schedules, total = crud_medication_schedule.get_active_schedules_for_patient(
            db_session, patient.id, appt.tenant_id,
        )
        assert total == 1
        assert schedules[0].medicine_name == "Paracetamol"

    def test_query_by_user_uuid_fails(self, db_session: Session) -> None:
        doc_user, pat_user, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(
                notes="Test Rx",
                items=[PrescriptionItemCreate(
                    medicine_name="Paracetamol", dosage="500mg",
                    frequency="TDS", duration="5 days",
                )],
            ),
        ])
        db_session.commit()

        # Querying with pat_user.id (User UUID) should return 0 schedules
        # because PatientMedicationSchedule is keyed on patient_id (Patient UUID)
        schedules, total = crud_medication_schedule.get_active_schedules_for_patient(
            db_session, pat_user.id, appt.tenant_id,
        )
        assert total == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Encounter aggregate serialization
# ═══════════════════════════════════════════════════════════════════════════════


class TestEncounterAggregateSerialization:
    """Encounter aggregate includes prescriptions with nested items per frontend contract."""

    def test_prescriptions_included_in_aggregate(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(
                notes="Test",
                items=[PrescriptionItemCreate(
                    medicine_name="Ibuprofen", dosage="400mg",
                    frequency="TDS", duration="5 days",
                    instructions="After meals",
                )],
            ),
        ])
        db_session.commit()
        # Mark as completed for encounter aggregate loading
        appt.status = AppointmentStatus.completed
        appt.encounter_completed_at = datetime.now(timezone.utc)
        db_session.commit()

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=doc_user.tenant_id,
        )
        assert len(aggregate.prescriptions) == 1
        assert aggregate.prescriptions[0].notes == "Test"

    def test_nested_items_included(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(
                notes="Test",
                items=[PrescriptionItemCreate(
                    medicine_name="Ibuprofen", dosage="400mg",
                    frequency="TDS", duration="5 days",
                    instructions="After meals",
                )],
            ),
        ])
        db_session.commit()
        appt.status = AppointmentStatus.completed
        appt.encounter_completed_at = datetime.now(timezone.utc)
        db_session.commit()

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=doc_user.tenant_id,
        )
        items = aggregate.prescriptions[0].items
        assert len(items) == 1
        assert items[0].medicine_name == "Ibuprofen"
        assert items[0].dosage == "400mg"
        assert items[0].frequency == "TDS"
        assert items[0].duration == "5 days"
        assert items[0].instructions == "After meals"

    def test_frontend_contract_preserved(self, db_session: Session) -> None:
        """Verify JSON serialization shape matches what the frontend expects."""
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(
                notes="Frontend contract test",
                items=[PrescriptionItemCreate(
                    medicine_name="Metformin", dosage="500mg",
                    frequency="BD", duration="30 days",
                )],
            ),
        ])
        db_session.commit()
        appt.status = AppointmentStatus.completed
        appt.encounter_completed_at = datetime.now(timezone.utc)
        db_session.commit()

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=doc_user.tenant_id,
        )
        data = aggregate.model_dump(mode="json")

        assert "prescriptions" in data
        assert isinstance(data["prescriptions"], list)
        assert len(data["prescriptions"]) == 1
        rx = data["prescriptions"][0]
        # PrescriptionRead contract
        assert "id" in rx
        assert "appointment_id" in rx
        assert "doctor_id" in rx
        assert "patient_id" in rx
        assert "tenant_id" in rx
        assert "notes" in rx
        assert "created_at" in rx
        assert "items" in rx
        assert isinstance(rx["items"], list)
        assert len(rx["items"]) == 1
        item = rx["items"][0]
        # PrescriptionItemRead contract
        assert item["medicine_name"] == "Metformin"
        assert item["dosage"] == "500mg"
        assert item["frequency"] == "BD"
        assert item["duration"] == "30 days"
        # Aggregate top-level contract
        assert "appointment" in data
        assert "patient" in data
        assert "doctor" in data
        assert "vitals" in data
        assert "inventory_usage" in data
        assert "bill" in data


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Notes-only UX safety
# ═══════════════════════════════════════════════════════════════════════════════


class TestNotesOnlyUXSafety:
    """Notes-only prescriptions are safe: the backend accepts them without error.

    No existing frontend test covers the notes-only UX warning for medicine-like
    notes without structured medicines. If such a frontend test is added in the
    future, it should verify:
      - a warning appears when medicine-like text exists in notes without items
      - the warning is non-blocking (form can still be submitted)
    """

    def test_notes_only_prescription_creates_prescription(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(notes="Paracetamol 500mg TDS x 5 days"),
        ])
        db_session.commit()

        rx_count = db_session.query(Prescription).filter(
            Prescription.appointment_id == appt_id,
        ).count()
        assert rx_count == 1

    def test_notes_only_does_not_create_items(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(notes="Paracetamol 500mg TDS x 5 days"),
        ])
        db_session.commit()

        item_count = db_session.query(PrescriptionItem).join(Prescription).filter(
            Prescription.appointment_id == appt_id,
        ).count()
        assert item_count == 0

    def test_notes_only_does_not_create_schedules(self, db_session: Session) -> None:
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        appointment_service._create_appointment_prescriptions(db_session, appt, [
            PrescriptionCreate(notes="Paracetamol 500mg TDS x 5 days"),
        ])
        db_session.commit()

        sched_count = db_session.query(PatientMedicationSchedule).filter(
            PatientMedicationSchedule.patient_id == patient_id,
        ).count()
        assert sched_count == 0

    def test_notes_only_safe_with_medicine_like_text(self, db_session: Session) -> None:
        """Notes containing medicine-like text do not error or create spurious items."""
        doc_user, _, doctor_id, patient_id = _setup_minimal(db_session)
        appt_id = _make_scheduled_appointment(
            db_session, doctor_id, patient_id, doc_user.id, doc_user.tenant_id,
        )
        appt = crud_appointment.get_appointment(db_session, appt_id)
        try:
            appointment_service._create_appointment_prescriptions(db_session, appt, [
                PrescriptionCreate(
                    notes="Amoxicillin 250mg TDS 7 days, Paracetamol 500mg SOS",
                ),
            ])
            db_session.commit()
        except Exception as exc:
            pytest.fail(f"Medicine-like notes raised unexpected error: {exc}")

        items = db_session.query(PrescriptionItem).join(Prescription).filter(
            Prescription.appointment_id == appt_id,
        ).all()
        assert len(items) == 0
