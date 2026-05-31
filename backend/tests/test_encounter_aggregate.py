"""
Tests for the Encounter Aggregate API.

Covers:
- Full aggregate loads correctly with all sub-entities
- Tenant isolation (cross-tenant access blocked)
- Doctor authorization (assigned doctor can read)
- Invariant enforcement (prescription tenant/patient mismatch logs warnings)
- Aggregate includes vitals, prescriptions, billing, inventory usage, SOAP fields
- No N+1 query explosion (query count assertion)
"""

from __future__ import annotations

import uuid
from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.crud.crud_appointment import add_appointment, add_prescription, add_prescription_item
from app.models.appointment import AppointmentStatus, AppointmentVitals
from app.models.billing import Billing, BillingStatus
from app.models.inventory import AppointmentInventoryUsage, InventoryItem, InventoryItemType
from app.models.patient import Patient
from app.models.tenant import Tenant, TenantType
from app.models.user import User, UserRole
from app.schemas.encounter import EncounterDetailAggregate
from app.services import encounter_service
from app.services.exceptions import NotFoundError
from tests.factories import (
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
    link_user_tenant,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _auth_header(user: User) -> dict[str, str]:
    """Create an Authorization header for the given user."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "type": "access",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _seed_completed_appointment(
    db: Session,
    *,
    tenant_id: UUID,
    doctor_user_id: UUID,
    doctor_id: UUID,
    patient_id: UUID,
    appointment_time: datetime | None = None,
) -> UUID:
    """Seed a completed appointment with vitals, prescriptions, inventory usage, and a bill."""
    if appointment_time is None:
        appointment_time = datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)

    appt = add_appointment(
        db,
        {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_time": appointment_time,
            "status": AppointmentStatus.completed,
            "created_by": doctor_user_id,
            "tenant_id": tenant_id,
            "clinical_notes": "Patient presented with fever",
            "diagnosis": "Viral fever",
            "treatment_summary": "Prescribed paracetamol",
            "subjective_notes": "Patient reports headache and body ache",
            "objective_notes": "Temperature 101°F, BP 120/80",
            "assessment_notes": "Viral infection suspected",
            "plan_notes": "Rest, hydration, paracetamol 500mg TDS",
            "encounter_started_at": appointment_time,
            "encounter_completed_at": appointment_time,
        },
    )
    db.flush()

    # Vitals
    vitals = AppointmentVitals(
        appointment_id=appt.id,
        temperature=38.5,
        bp_systolic=120,
        bp_diastolic=80,
        pulse=78,
        weight=70.0,
        height=170.0,
        bmi=24.2,
    )
    db.add(vitals)

    # Prescription
    rx = add_prescription(
        db,
        appointment_id=appt.id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        tenant_id=tenant_id,
        notes="Take with food",
    )
    add_prescription_item(
        db,
        prescription_id=rx.id,
        line_data={
            "medicine_name": "Paracetamol",
            "dosage": "500mg",
            "frequency": "TDS",
            "duration": "5 days",
            "instructions": "After meals",
        },
    )

    # Inventory item + usage
    inv_item = InventoryItem(
        tenant_id=tenant_id,
        name="Paracetamol 500mg",
        type=InventoryItemType.medicine,
        unit="tablet",
        cost_price=Decimal("1.00"),
        selling_price=Decimal("2.50"),
    )
    db.add(inv_item)
    db.flush()

    inv_usage = AppointmentInventoryUsage(
        appointment_id=appt.id,
        item_id=inv_item.id,
        quantity=10,
    )
    db.add(inv_usage)

    # Bill
    bill = Billing(
        patient_id=patient_id,
        appointment_id=appt.id,
        tenant_id=tenant_id,
        amount=Decimal("500.00"),
        currency="INR",
        status=BillingStatus.unpaid,
        created_by=doctor_user_id,
    )
    db.add(bill)

    db.commit()
    return appt.id


# ── Tests ──────────────────────────────────────────────────────────────────


class TestEncounterAggregateLoads:
    """Verify the aggregate loads correctly with all sub-entities."""

    def test_encounter_aggregate_loads_correctly(
        self,
        db_session: Session,
    ) -> None:
        """Full aggregate with all sub-entities loads correctly."""
        # Arrange
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        # Act
        aggregate = encounter_service.get_encounter_detail(
            db_session,
            appt_id,
            doc_user,
            tenant_id=tenant.id,
        )

        # Assert
        assert aggregate is not None
        assert aggregate.appointment.id == appt_id
        assert aggregate.appointment.status == AppointmentStatus.completed
        assert aggregate.patient.id == patient.id
        assert aggregate.doctor.id == doctor.id

        # Vitals
        assert aggregate.vitals is not None
        assert aggregate.vitals.temperature == 38.5
        assert aggregate.vitals.bp_systolic == 120

        # SOAP fields
        assert aggregate.appointment.subjective_notes == "Patient reports headache and body ache"
        assert aggregate.appointment.objective_notes == "Temperature 101°F, BP 120/80"
        assert aggregate.appointment.assessment_notes == "Viral infection suspected"
        assert aggregate.appointment.plan_notes == "Rest, hydration, paracetamol 500mg TDS"

        # Prescriptions
        assert len(aggregate.prescriptions) == 1
        assert aggregate.prescriptions[0].notes == "Take with food"
        assert len(aggregate.prescriptions[0].items) == 1
        assert aggregate.prescriptions[0].items[0].medicine_name == "Paracetamol"

        # Inventory usage
        assert len(aggregate.inventory_usage) == 1
        assert aggregate.inventory_usage[0].quantity == 10
        assert aggregate.inventory_usage[0].item_name == "Paracetamol 500mg"

        # Bill
        assert aggregate.bill is not None
        assert aggregate.bill.amount == Decimal("500.00")
        assert aggregate.bill.appointment_id == appt_id

        # Timeline context
        assert aggregate.timeline_context is not None
        assert aggregate.timeline_context.previous_visit_count == 0

    def test_encounter_aggregate_includes_vitals(
        self,
        db_session: Session,
    ) -> None:
        """Vitals are included in the aggregate."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor2@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient2@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=tenant.id
        )

        assert aggregate.vitals is not None
        assert aggregate.vitals.temperature == 38.5
        assert aggregate.vitals.bp_systolic == 120

    def test_encounter_aggregate_includes_prescriptions(
        self,
        db_session: Session,
    ) -> None:
        """Prescriptions are included in the aggregate."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor3@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient3@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=tenant.id
        )

        assert len(aggregate.prescriptions) == 1
        assert aggregate.prescriptions[0].notes == "Take with food"

    def test_encounter_aggregate_includes_billing(
        self,
        db_session: Session,
    ) -> None:
        """Billing is included in the aggregate."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor4@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient4@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=tenant.id
        )

        assert aggregate.bill is not None
        assert aggregate.bill.amount == Decimal("500.00")

    def test_encounter_aggregate_includes_inventory_usage(
        self,
        db_session: Session,
    ) -> None:
        """Inventory usage is included in the aggregate."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor5@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient5@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=tenant.id
        )

        assert len(aggregate.inventory_usage) == 1
        assert aggregate.inventory_usage[0].quantity == 10

    def test_encounter_aggregate_includes_soap_fields(
        self,
        db_session: Session,
    ) -> None:
        """SOAP fields are included in the aggregate."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor6@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient6@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=tenant.id
        )

        assert aggregate.appointment.subjective_notes is not None
        assert aggregate.appointment.objective_notes is not None
        assert aggregate.appointment.assessment_notes is not None
        assert aggregate.appointment.plan_notes is not None


class TestEncounterAuthorization:
    """Verify authorization rules for the encounter aggregate."""

    def test_tenant_isolation(
        self,
        db_session: Session,
    ) -> None:
        """Cross-tenant access is blocked."""
        # Arrange — tenant A
        tenant_a = create_tenant(db_session, name="Tenant A")
        doc_user_a = create_user(
            db_session,
            email="doctor_a@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant_a.id,
        )
        doctor_a = create_doctor_profile(
            db_session, tenant_id=tenant_a.id, user_id=doc_user_a.id
        )
        pat_user_a = create_user(
            db_session,
            email="patient_a@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient_a = create_patient_profile(
            db_session,
            tenant_id=tenant_a.id,
            user_id=pat_user_a.id,
            created_by=doc_user_a.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant_a.id,
            doctor_user_id=doc_user_a.id,
            doctor_id=doctor_a.id,
            patient_id=patient_a.id,
        )

        # Arrange — tenant B (different tenant)
        tenant_b = create_tenant(db_session, name="Tenant B")
        doc_user_b = create_user(
            db_session,
            email="doctor_b@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant_b.id,
        )
        create_doctor_profile(db_session, tenant_id=tenant_b.id, user_id=doc_user_b.id)

        # Act & Assert — doctor from tenant B cannot access tenant A's encounter
        from app.services.exceptions import ForbiddenError

        with pytest.raises(ForbiddenError):
            encounter_service.get_encounter_detail(
                db_session,
                appt_id,
                doc_user_b,
                tenant_id=tenant_b.id,
            )

    def test_doctor_authorization_assigned_doctor(
        self,
        db_session: Session,
    ) -> None:
        """Assigned doctor can read the encounter."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor_assigned@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient_assigned@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, doc_user, tenant_id=tenant.id
        )

        assert aggregate is not None
        assert aggregate.appointment.id == appt_id

    def test_super_admin_can_read_any_encounter(
        self,
        db_session: Session,
    ) -> None:
        """Super admin can read any encounter."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor_sa@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient_sa@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        super_admin = create_user(
            db_session,
            email="superadmin@test.com",
            password="TestPass9!",
            role=UserRole.super_admin,
        )

        aggregate = encounter_service.get_encounter_detail(
            db_session, appt_id, super_admin, tenant_id=None
        )

        assert aggregate is not None
        assert aggregate.appointment.id == appt_id

    def test_not_found_for_nonexistent_appointment(
        self,
        db_session: Session,
    ) -> None:
        """Non-existent appointment raises NotFoundError."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor_nf@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )

        fake_id = uuid.uuid4()
        with pytest.raises(NotFoundError):
            encounter_service.get_encounter_detail(
                db_session, fake_id, doc_user, tenant_id=tenant.id
            )


class TestEncounterInvariants:
    """Verify invariant enforcement (fail-safe — logs warnings, does not raise)."""

    def test_invariant_prescription_tenant_mismatch_logs_warning(
        self,
        db_session: Session,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Prescription tenant mismatch logs a warning but does not raise."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor_inv@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient_inv@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )

        appt_time = datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)
        appt = add_appointment(
            db_session,
            {
                "patient_id": patient.id,
                "doctor_id": doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.completed,
                "created_by": doc_user.id,
                "tenant_id": tenant.id,
            },
        )
        db_session.flush()

        # Create prescription with WRONG tenant_id
        wrong_tenant_id = uuid.uuid4()
        rx = add_prescription(
            db_session,
            appointment_id=appt.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
            tenant_id=wrong_tenant_id,  # Mismatch!
        )
        add_prescription_item(
            db_session,
            prescription_id=rx.id,
            line_data={"medicine_name": "Test Drug", "dosage": "10mg"},
        )
        db_session.commit()

        with caplog.at_level("WARNING"):
            aggregate = encounter_service.get_encounter_detail(
                db_session, appt.id, doc_user, tenant_id=tenant.id
            )

        # Assert — aggregate still loads (fail-safe)
        assert aggregate is not None
        assert aggregate.appointment.id == appt.id
        # Assert — warning was logged
        assert any(
            "prescription.tenant_id != appointment.tenant_id" in msg
            for msg in caplog.messages
        )

    def test_invariant_prescription_patient_mismatch_logs_warning(
        self,
        db_session: Session,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Prescription patient mismatch logs a warning but does not raise."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor_inv2@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient_inv2@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )

        appt_time = datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)
        appt = add_appointment(
            db_session,
            {
                "patient_id": patient.id,
                "doctor_id": doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.completed,
                "created_by": doc_user.id,
                "tenant_id": tenant.id,
            },
        )
        db_session.flush()

        # Create prescription with WRONG patient_id
        wrong_patient_id = uuid.uuid4()
        rx = add_prescription(
            db_session,
            appointment_id=appt.id,
            doctor_id=doctor.id,
            patient_id=wrong_patient_id,  # Mismatch!
            tenant_id=tenant.id,
        )
        add_prescription_item(
            db_session,
            prescription_id=rx.id,
            line_data={"medicine_name": "Test Drug", "dosage": "10mg"},
        )
        db_session.commit()

        with caplog.at_level("WARNING"):
            aggregate = encounter_service.get_encounter_detail(
                db_session, appt.id, doc_user, tenant_id=tenant.id
            )

        assert aggregate is not None
        assert any(
            "prescription.patient_id != appointment.patient_id" in msg
            for msg in caplog.messages
        )

    def test_invariant_bill_tenant_mismatch_logs_warning(
        self,
        db_session: Session,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Bill tenant_id mismatch logs a warning but does not raise."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor_inv3@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient_inv3@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )

        appt_time = datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)
        appt = add_appointment(
            db_session,
            {
                "patient_id": patient.id,
                "doctor_id": doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.completed,
                "created_by": doc_user.id,
                "tenant_id": tenant.id,
            },
        )
        db_session.flush()

        # Create bill with correct appointment_id but WRONG tenant_id
        wrong_tenant_id = uuid.uuid4()
        bill = Billing(
            patient_id=patient.id,
            appointment_id=appt.id,  # Correct appointment_id
            tenant_id=wrong_tenant_id,  # Tenant mismatch!
            amount=Decimal("100.00"),
            currency="INR",
            status=BillingStatus.unpaid,
            created_by=doc_user.id,
        )
        db_session.add(bill)
        db_session.commit()

        with caplog.at_level("WARNING"):
            aggregate = encounter_service.get_encounter_detail(
                db_session, appt.id, doc_user, tenant_id=tenant.id
            )

        assert aggregate is not None
        assert any(
            "bill.tenant_id != appointment.tenant_id" in msg
            for msg in caplog.messages
        )


class TestEncounterQueryPerformance:
    """Verify no N+1 query explosion."""

    def test_encounter_no_n_plus_one(
        self,
        db_session: Session,
    ) -> None:
        """The aggregate loads in a small number of queries (no N+1)."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor_perf@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient_perf@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        # Count queries
        from sqlalchemy import event

        query_count = [0]

        @event.listens_for(db_session.bind, "before_cursor_execute")
        def _count_queries(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
            query_count[0] += 1

        try:
            aggregate = encounter_service.get_encounter_detail(
                db_session, appt_id, doc_user, tenant_id=tenant.id
            )
        finally:
            event.remove(db_session.bind, "before_cursor_execute", _count_queries)

        assert aggregate is not None
        # Expected queries:
        # 1. Main appointment query (joinedload patient, doctor)
        # 2. selectinload vitals
        # 3. selectinload prescriptions
        # 4. selectinload prescription items
        # 5. selectinload inventory_usages
        # 6. joinedload inventory_usages.item
        # 7. appointment_inventory_materials_selling_total (in appointment_to_read)
        # 8. Bill query
        # 9. Timeline context query
        # 10-12. Authorization checks (doctor profile lookup, tenant verification)
        # Total should be <= 12 (selectinload emits separate queries per collection)
        assert query_count[0] <= 12, (
            f"Expected <= 12 queries, got {query_count[0]}. "
            "This may indicate an N+1 problem."
        )


class TestEncounterAPIEndpoint:
    """Integration tests for the GET /encounters/{appointment_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_encounter_detail_endpoint(
        self,
        db_session: Session,
        client: AsyncClient,
    ) -> None:
        """GET /encounters/{appointment_id} returns the full aggregate."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor_api@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        doctor = create_doctor_profile(
            db_session, tenant_id=tenant.id, user_id=doc_user.id
        )
        pat_user = create_user(
            db_session,
            email="patient_api@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient = create_patient_profile(
            db_session,
            tenant_id=tenant.id,
            user_id=pat_user.id,
            created_by=doc_user.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant.id,
            doctor_user_id=doc_user.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )

        headers = _auth_header(doc_user)
        headers["X-Tenant-ID"] = str(tenant.id)

        response = await client.get(
            f"/api/v1/encounters/{appt_id}",
            headers=headers,
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify structure
        assert "appointment" in data
        assert "patient" in data
        assert "doctor" in data
        assert "vitals" in data
        assert "prescriptions" in data
        assert "inventory_usage" in data
        assert "bill" in data
        assert "timeline_context" in data

        # Verify content
        assert data["appointment"]["id"] == str(appt_id)
        assert data["patient"]["id"] == str(patient.id)
        assert data["doctor"]["id"] == str(doctor.id)
        assert data["vitals"]["temperature"] == 38.5
        assert len(data["prescriptions"]) == 1
        assert len(data["inventory_usage"]) == 1
        assert data["bill"]["amount"] == "500.00"

    @pytest.mark.asyncio
    async def test_get_encounter_detail_unauthorized(
        self,
        db_session: Session,
        client: AsyncClient,
    ) -> None:
        """Cross-tenant access returns 403."""
        tenant_a = create_tenant(db_session, name="Tenant A")
        doc_user_a = create_user(
            db_session,
            email="doctor_api_a@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant_a.id,
        )
        doctor_a = create_doctor_profile(
            db_session, tenant_id=tenant_a.id, user_id=doc_user_a.id
        )
        pat_user_a = create_user(
            db_session,
            email="patient_api_a@test.com",
            password="TestPass9!",
            role=UserRole.patient,
        )
        patient_a = create_patient_profile(
            db_session,
            tenant_id=tenant_a.id,
            user_id=pat_user_a.id,
            created_by=doc_user_a.id,
        )
        appt_id = _seed_completed_appointment(
            db_session,
            tenant_id=tenant_a.id,
            doctor_user_id=doc_user_a.id,
            doctor_id=doctor_a.id,
            patient_id=patient_a.id,
        )

        # Tenant B user tries to access Tenant A's encounter
        tenant_b = create_tenant(db_session, name="Tenant B")
        doc_user_b = create_user(
            db_session,
            email="doctor_api_b@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant_b.id,
        )
        create_doctor_profile(db_session, tenant_id=tenant_b.id, user_id=doc_user_b.id)

        headers = _auth_header(doc_user_b)
        headers["X-Tenant-ID"] = str(tenant_b.id)

        response = await client.get(
            f"/api/v1/encounters/{appt_id}",
            headers=headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_encounter_detail_not_found(
        self,
        db_session: Session,
        client: AsyncClient,
    ) -> None:
        """Non-existent appointment returns 404."""
        tenant = create_tenant(db_session)
        doc_user = create_user(
            db_session,
            email="doctor_nf_api@test.com",
            password="TestPass9!",
            role=UserRole.doctor,
            tenant_id=tenant.id,
        )
        create_doctor_profile(db_session, tenant_id=tenant.id, user_id=doc_user.id)

        headers = _auth_header(doc_user)
        headers["X-Tenant-ID"] = str(tenant.id)

        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/encounters/{fake_id}",
            headers=headers,
        )

        assert response.status_code == 404
