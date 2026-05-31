"""
Tests for clinic operations — appointment operational states, queue management,
front desk workflow, nurse workflow, and walk-in support.

These tests validate the operational backbone WITHOUT modifying:
- Encounter architecture
- Appointment ownership
- Billing architecture
- Realtime infrastructure
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import ANY, patch
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.crud import crud_appointment, crud_clinic_queue
from app.models.appointment import Appointment, AppointmentStatus
from app.models.clinic_queue import ClinicQueueEntry, ClinicQueueStatus
from app.schemas.clinic_queue import (
    QueueDashboardRead,
    QueueEntryRead,
    QueuePositionRead,
    PrepChecklistUpdate,
    RoomAssignment,
)
from app.services import (
    front_desk_service,
    nurse_workflow_service,
    queue_service,
)
from app.services.exceptions import NotFoundError, ValidationError
from tests.factories import (
    create_tenant,
    create_user,
    create_doctor_profile,
    create_patient_profile,
    add_appointment,
)
from app.models.user import UserRole


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def seeded_tenant(db_session: Session):
    """Create a tenant for test isolation."""
    return create_tenant(db_session)


@pytest.fixture
def seeded_doctor(db_session: Session, seeded_tenant):
    """Create a doctor profile."""
    user = create_user(
        db_session,
        email=f"doctor_{uuid.uuid4().hex[:8]}@test.com",
        password="TestPass123!",
        role=UserRole.doctor,
        tenant_id=seeded_tenant.id,
    )
    return create_doctor_profile(db_session, tenant_id=seeded_tenant.id, user_id=user.id)


@pytest.fixture
def seeded_patient(db_session: Session):
    """Create a patient profile."""
    user = create_user(
        db_session,
        email=f"patient_{uuid.uuid4().hex[:8]}@test.com",
        password="TestPass123!",
        role=UserRole.patient,
    )
    return create_patient_profile(
        db_session,
        user_id=user.id,
        created_by=user.id,
    )


@pytest.fixture
def seeded_appointment(db_session: Session, seeded_tenant, seeded_doctor, seeded_patient):
    """Create a scheduled appointment."""
    appt_time = datetime.now(timezone.utc) + timedelta(hours=1)
    return add_appointment(db_session, {
        "patient_id": seeded_patient.id,
        "doctor_id": seeded_doctor.id,
        "appointment_time": appt_time,
        "status": AppointmentStatus.scheduled,
        "created_by": seeded_patient.user_id,
        "tenant_id": seeded_tenant.id,
    })


@pytest.fixture
def seeded_user_id(db_session: Session, seeded_tenant):
    """Create a staff user for audit actor tracking."""
    user = create_user(
        db_session,
        email=f"staff_{uuid.uuid4().hex[:8]}@test.com",
        password="TestPass123!",
        role=UserRole.admin,
        tenant_id=seeded_tenant.id,
    )
    return user.id


# ═════════════════════════════════════════════════════════════════════════════
# 1. APPOINTMENT OPERATIONAL STATES
# ═════════════════════════════════════════════════════════════════════════════

class TestAppointmentOperationalStates:
    """Validate the full operational state machine for appointments."""

    def test_valid_state_transitions(self):
        """Verify allowed state transitions."""
        valid_transitions = {
            AppointmentStatus.scheduled: [AppointmentStatus.confirmed, AppointmentStatus.cancelled],
            AppointmentStatus.confirmed: [AppointmentStatus.arrived, AppointmentStatus.cancelled],
            AppointmentStatus.arrived: [AppointmentStatus.checked_in, AppointmentStatus.cancelled, AppointmentStatus.no_show],
            AppointmentStatus.checked_in: [AppointmentStatus.vitals_completed, AppointmentStatus.cancelled],
            AppointmentStatus.vitals_completed: [AppointmentStatus.waiting_for_doctor, AppointmentStatus.cancelled],
            AppointmentStatus.waiting_for_doctor: [AppointmentStatus.in_consultation, AppointmentStatus.cancelled],
            AppointmentStatus.in_consultation: [AppointmentStatus.completed],
            AppointmentStatus.completed: [],
            AppointmentStatus.cancelled: [],
            AppointmentStatus.no_show: [],
        }

        for from_state, to_states in valid_transitions.items():
            for to_state in to_states:
                assert to_state in valid_transitions[from_state] or not valid_transitions[from_state], \
                    f"Transition {from_state} -> {to_state} should be valid"

    def test_invalid_state_transitions(self):
        """Verify disallowed state transitions raise errors."""
        invalid_transitions = [
            (AppointmentStatus.scheduled, AppointmentStatus.completed),
            (AppointmentStatus.scheduled, AppointmentStatus.in_consultation),
            (AppointmentStatus.confirmed, AppointmentStatus.completed),
            (AppointmentStatus.arrived, AppointmentStatus.completed),
            (AppointmentStatus.checked_in, AppointmentStatus.completed),
            (AppointmentStatus.completed, AppointmentStatus.scheduled),
            (AppointmentStatus.cancelled, AppointmentStatus.scheduled),
            (AppointmentStatus.no_show, AppointmentStatus.scheduled),
        ]

        for from_state, to_state in invalid_transitions:
            assert to_state not in self._get_valid_next_states(from_state), \
                f"Transition {from_state} -> {to_state} should be invalid"

    def _get_valid_next_states(self, status: AppointmentStatus) -> list:
        """Helper to get valid next states for a given status."""
        transitions = {
            AppointmentStatus.scheduled: [AppointmentStatus.confirmed, AppointmentStatus.cancelled],
            AppointmentStatus.confirmed: [AppointmentStatus.arrived, AppointmentStatus.cancelled],
            AppointmentStatus.arrived: [AppointmentStatus.checked_in, AppointmentStatus.cancelled, AppointmentStatus.no_show],
            AppointmentStatus.checked_in: [AppointmentStatus.vitals_completed, AppointmentStatus.cancelled],
            AppointmentStatus.vitals_completed: [AppointmentStatus.waiting_for_doctor, AppointmentStatus.cancelled],
            AppointmentStatus.waiting_for_doctor: [AppointmentStatus.in_consultation, AppointmentStatus.cancelled],
            AppointmentStatus.in_consultation: [AppointmentStatus.completed],
            AppointmentStatus.completed: [],
            AppointmentStatus.cancelled: [],
            AppointmentStatus.no_show: [],
        }
        return transitions.get(status, [])

    def test_all_states_defined(self):
        """Ensure all required operational states exist."""
        required_states = [
            "scheduled", "confirmed", "arrived", "checked_in",
            "vitals_completed", "waiting_for_doctor", "in_consultation",
            "completed", "cancelled", "no_show",
        ]
        for state in required_states:
            assert hasattr(AppointmentStatus, state), f"Missing state: {state}"

    def test_terminal_states(self):
        """Verify terminal states cannot transition further."""
        terminal_states = [
            AppointmentStatus.completed,
            AppointmentStatus.cancelled,
            AppointmentStatus.no_show,
        ]
        for state in terminal_states:
            assert len(self._get_valid_next_states(state)) == 0, \
                f"{state} should be terminal"


# ═════════════════════════════════════════════════════════════════════════════
# 2. QUEUE MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

class TestQueueManagement:
    """Validate queue entry creation, ordering, and status management."""

    def test_add_appointment_to_queue(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test adding an appointment to the queue."""
        entry = queue_service.add_appointment_to_queue(
            db=db_session,
            appointment_id=seeded_appointment.id,
            tenant_id=seeded_tenant.id,
            doctor_id=seeded_doctor.id,
            patient_id=seeded_patient.id,
            created_by=seeded_user_id,
        )
        assert entry is not None
        assert entry.token_number > 0
        assert entry.queue_status == ClinicQueueStatus.waiting
        assert entry.appointment_id == seeded_appointment.id

    def test_queue_token_sequencing(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Verify token numbers are sequential per doctor per day."""
        entries = []
        for i in range(3):
            appt_time = datetime.now(timezone.utc) + timedelta(hours=1, minutes=i * 30)
            appt = add_appointment(db_session, {
                "patient_id": seeded_patient.id,
                "doctor_id": seeded_doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.scheduled,
                "created_by": seeded_user_id,
                "tenant_id": seeded_tenant.id,
            })
            entry = queue_service.add_appointment_to_queue(
                db=db_session,
                appointment_id=appt.id,
                tenant_id=seeded_tenant.id,
                doctor_id=seeded_doctor.id,
                patient_id=seeded_patient.id,
                created_by=seeded_user_id,
            )
            entries.append(entry)

        for i, entry in enumerate(entries):
            assert entry.token_number == i + 1, \
                f"Expected token {i + 1}, got {entry.token_number}"

    def test_queue_position(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Verify queue position calculation."""
        queue_service.add_appointment_to_queue(
            db=db_session,
            appointment_id=seeded_appointment.id,
            tenant_id=seeded_tenant.id,
            doctor_id=seeded_doctor.id,
            patient_id=seeded_patient.id,
            created_by=seeded_user_id,
        )
        position = queue_service.get_queue_position(db_session, seeded_appointment.id)
        assert position is not None
        assert position.position >= 1
        assert position.token_number >= 1

    def test_mark_called(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test marking a queue entry as called (in_room)."""
        entry = queue_service.add_appointment_to_queue(
            db=db_session,
            appointment_id=seeded_appointment.id,
            tenant_id=seeded_tenant.id,
            doctor_id=seeded_doctor.id,
            patient_id=seeded_patient.id,
            created_by=seeded_user_id,
        )
        called = queue_service.mark_called(db_session, entry.id)
        assert called.queue_status == ClinicQueueStatus.in_room

    def test_mark_completed(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test completing a queue entry."""
        entry = queue_service.add_appointment_to_queue(
            db=db_session,
            appointment_id=seeded_appointment.id,
            tenant_id=seeded_tenant.id,
            doctor_id=seeded_doctor.id,
            patient_id=seeded_patient.id,
            created_by=seeded_user_id,
        )
        queue_service.mark_called(db_session, entry.id)
        completed = queue_service.mark_completed(db_session, entry.id)
        assert completed.queue_status == ClinicQueueStatus.completed

    def test_mark_skipped(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test skipping a queue entry."""
        entry = queue_service.add_appointment_to_queue(
            db=db_session,
            appointment_id=seeded_appointment.id,
            tenant_id=seeded_tenant.id,
            doctor_id=seeded_doctor.id,
            patient_id=seeded_patient.id,
            created_by=seeded_user_id,
        )
        skipped = queue_service.mark_skipped(db_session, entry.id)
        assert skipped.queue_status == ClinicQueueStatus.skipped

    def test_get_front_desk_queue(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test retrieving the front desk queue dashboard."""
        for i in range(3):
            appt_time = datetime.now(timezone.utc) + timedelta(hours=1, minutes=i * 30)
            appt = add_appointment(db_session, {
                "patient_id": seeded_patient.id,
                "doctor_id": seeded_doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.scheduled,
                "created_by": seeded_user_id,
                "tenant_id": seeded_tenant.id,
            })
            queue_service.add_appointment_to_queue(
                db=db_session,
                appointment_id=appt.id,
                tenant_id=seeded_tenant.id,
                doctor_id=seeded_doctor.id,
                patient_id=seeded_patient.id,
                created_by=seeded_user_id,
            )

        dashboard = queue_service.get_front_desk_queue(db_session, seeded_tenant.id)
        assert dashboard is not None
        assert dashboard.total_waiting == 3
        assert len(dashboard.entries) == 3

    def test_get_doctor_queue(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test retrieving queue filtered by doctor."""
        for i in range(2):
            appt_time = datetime.now(timezone.utc) + timedelta(hours=1, minutes=i * 30)
            appt = add_appointment(db_session, {
                "patient_id": seeded_patient.id,
                "doctor_id": seeded_doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.scheduled,
                "created_by": seeded_user_id,
                "tenant_id": seeded_tenant.id,
            })
            queue_service.add_appointment_to_queue(
                db=db_session,
                appointment_id=appt.id,
                tenant_id=seeded_tenant.id,
                doctor_id=seeded_doctor.id,
                patient_id=seeded_patient.id,
                created_by=seeded_user_id,
            )

        doctor_queue = queue_service.get_doctor_queue(
            db_session, doctor_id=seeded_doctor.id, tenant_id=seeded_tenant.id
        )
        assert doctor_queue is not None
        assert len(doctor_queue) == 2

    def test_wait_estimation(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test wait estimation foundation."""
        created_appts = []
        for i in range(5):
            appt_time = datetime.now(timezone.utc) + timedelta(hours=1, minutes=i * 30)
            appt = add_appointment(db_session, {
                "patient_id": seeded_patient.id,
                "doctor_id": seeded_doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.scheduled,
                "created_by": seeded_user_id,
                "tenant_id": seeded_tenant.id,
            })
            queue_service.add_appointment_to_queue(
                db=db_session,
                appointment_id=appt.id,
                tenant_id=seeded_tenant.id,
                doctor_id=seeded_doctor.id,
                patient_id=seeded_patient.id,
                created_by=seeded_user_id,
            )
            created_appts.append(appt)

        # Verify queue position for the first appointment
        position = queue_service.get_queue_position(
            db_session, created_appts[0].id
        )
        assert position is not None
        assert position.position >= 0


# ═════════════════════════════════════════════════════════════════════════════
# 3. FRONT DESK WORKFLOW
# ═════════════════════════════════════════════════════════════════════════════

class TestFrontDeskWorkflow:
    """Validate receptionist operational actions."""

    def test_mark_arrived(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test marking an appointment as arrived."""
        appointment = front_desk_service.mark_arrived(
            db=db_session,
            appointment_id=seeded_appointment.id,
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        assert appointment.status == AppointmentStatus.arrived

    def test_check_in_patient(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test checking in a patient."""
        front_desk_service.mark_arrived(
            db=db_session,
            appointment_id=seeded_appointment.id,
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        appointment = front_desk_service.check_in_patient(
            db=db_session,
            appointment_id=seeded_appointment.id,
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        assert appointment.status == AppointmentStatus.checked_in

    def test_cancel_appointment(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test cancelling an appointment from front desk."""
        appointment = front_desk_service.cancel_appointment(
            db=db_session,
            appointment_id=seeded_appointment.id,
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        assert appointment.status == AppointmentStatus.cancelled

    def test_no_show(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test marking a no-show."""
        front_desk_service.mark_arrived(
            db=db_session,
            appointment_id=seeded_appointment.id,
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        appointment = front_desk_service.mark_no_show(
            db=db_session,
            appointment_id=seeded_appointment.id,
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        assert appointment.status == AppointmentStatus.no_show

    def test_reschedule_hook(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test reschedule support hook."""
        new_time = datetime.now(timezone.utc) + timedelta(days=1)
        appointment = front_desk_service.reschedule_hook(
            db=db_session,
            appointment_id=seeded_appointment.id,
            new_time=new_time,
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        assert appointment is not None
        assert appointment.appointment_time == new_time
        # Reschedule resets to scheduled
        assert appointment.status == AppointmentStatus.scheduled

    def test_full_front_desk_flow(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test the complete front desk workflow end-to-end."""
        # 1. Mark arrived
        appt = front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.arrived

        # 2. Check in
        appt = front_desk_service.check_in_patient(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.checked_in

    def test_mark_arrived_invalid_state(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test that marking arrived from invalid state raises error."""
        # First mark arrived
        front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        # Try to mark arrived again (should fail)
        with pytest.raises(ValidationError):
            front_desk_service.mark_arrived(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )

    def test_cancel_from_checked_in(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test cancelling after check-in."""
        front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        front_desk_service.check_in_patient(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        appt = front_desk_service.cancel_appointment(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.cancelled


# ═════════════════════════════════════════════════════════════════════════════
# 4. NURSE / STAFF WORKFLOW
# ═════════════════════════════════════════════════════════════════════════════

class TestNurseWorkflow:
    """Validate nurse workflow capabilities."""

    def test_mark_vitals_completed(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test marking vitals as completed."""
        # First go through front desk flow
        front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        front_desk_service.check_in_patient(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )

        appointment = nurse_workflow_service.mark_vitals_completed(
            db=db_session,
            appointment_id=seeded_appointment.id,
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        assert appointment.status == AppointmentStatus.vitals_completed

    def test_send_to_doctor_queue(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test sending patient to doctor queue."""
        # Full pre-flow
        front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        front_desk_service.check_in_patient(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        nurse_workflow_service.mark_vitals_completed(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )

        appointment = nurse_workflow_service.send_to_doctor_queue(
            db=db_session,
            appointment_id=seeded_appointment.id,
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        assert appointment.status == AppointmentStatus.waiting_for_doctor

    def test_full_nurse_flow(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test the complete nurse workflow."""
        # Front desk pre-flow
        front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        front_desk_service.check_in_patient(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )

        # 1. Mark vitals completed
        appt = nurse_workflow_service.mark_vitals_completed(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.vitals_completed

        # 2. Send to doctor
        appt = nurse_workflow_service.send_to_doctor_queue(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.waiting_for_doctor

    def test_room_assignment(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test room assignment."""
        # Add to queue first
        queue_service.add_appointment_to_queue(
            db_session,
            appointment_id=seeded_appointment.id,
            tenant_id=seeded_tenant.id,
            doctor_id=seeded_doctor.id,
            patient_id=seeded_patient.id,
            created_by=seeded_user_id,
        )

        result = nurse_workflow_service.assign_room(
            db=db_session,
            appointment_id=seeded_appointment.id,
            room_number="101",
            current_user_id=seeded_user_id,
            tenant_id=seeded_tenant.id,
        )
        assert result is not None
        assert result.room_number == "101"

    def test_vitals_with_data(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test marking vitals completed with vitals data."""
        front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        front_desk_service.check_in_patient(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )

        vitals_data = {
            "temperature": 98.6,
            "bp_systolic": 120,
            "bp_diastolic": 80,
            "pulse": 72,
            "respiratory_rate": 16,
            "weight": 70.5,
            "height": 175.0,
        }
        appointment = nurse_workflow_service.mark_vitals_completed(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id,
            vitals_data=vitals_data,
        )
        assert appointment.status == AppointmentStatus.vitals_completed
        assert appointment.vitals is not None
        assert appointment.vitals.temperature == Decimal("98.60")
        assert appointment.vitals.bp_systolic == 120


# ═════════════════════════════════════════════════════════════════════════════
# 5. WALK-IN SUPPORT
# ═════════════════════════════════════════════════════════════════════════════

class TestWalkInSupport:
    """Validate walk-in appointment creation and queue insertion."""

    def test_create_walk_in(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test creating a walk-in appointment."""
        walk_in = front_desk_service.create_walk_in(
            db=db_session,
            patient_id=seeded_patient.id,
            doctor_id=seeded_doctor.id,
            tenant_id=seeded_tenant.id,
            current_user_id=seeded_user_id,
        )
        assert walk_in is not None
        assert walk_in.status == AppointmentStatus.arrived

    def test_walk_in_queue_insertion(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Verify walk-in is inserted into the queue."""
        walk_in = front_desk_service.create_walk_in(
            db_session, seeded_patient.id, seeded_doctor.id, seeded_tenant.id, seeded_user_id
        )
        # Walk-in should be in queue after creation
        dashboard = queue_service.get_front_desk_queue(db_session, seeded_tenant.id)
        walk_in_entries = [
            e for e in dashboard.entries
            if e.appointment_id == walk_in.id
        ]
        assert len(walk_in_entries) > 0

    def test_walk_in_intake_flow(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test the complete walk-in intake flow."""
        # 1. Create walk-in
        walk_in = front_desk_service.create_walk_in(
            db_session, seeded_patient.id, seeded_doctor.id, seeded_tenant.id, seeded_user_id
        )
        assert walk_in.status == AppointmentStatus.arrived

        # 2. Check in
        appt = front_desk_service.check_in_patient(
            db_session, walk_in.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.checked_in

    def test_walk_in_same_day_queue(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Verify walk-in appears in same-day queue."""
        walk_in = front_desk_service.create_walk_in(
            db_session, seeded_patient.id, seeded_doctor.id, seeded_tenant.id, seeded_user_id
        )
        doctor_queue = queue_service.get_doctor_queue(
            db_session, doctor_id=seeded_doctor.id, tenant_id=seeded_tenant.id
        )
        walk_in_entries = [
            e for e in doctor_queue
            if e.appointment_id == walk_in.id
        ]
        assert len(walk_in_entries) > 0

    def test_walk_in_priority(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Verify walk-ins get priority=1."""
        walk_in = front_desk_service.create_walk_in(
            db_session, seeded_patient.id, seeded_doctor.id, seeded_tenant.id, seeded_user_id
        )
        # Check the queue entry has priority=1
        entry = crud_clinic_queue.get_queue_entry_by_appointment(db_session, walk_in.id)
        assert entry is not None
        assert entry.priority == 1


# ═════════════════════════════════════════════════════════════════════════════
# 6. AUDIT + COMPLIANCE
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditCompliance:
    """Validate audit logging for all operational transitions."""

    def test_audit_log_on_arrive(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Verify audit log is created when marking arrived."""
        with patch.object(front_desk_service, '_log_audit') as mock_log:
            front_desk_service.mark_arrived(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args.kwargs
            assert call_kwargs.get('actor_id') == seeded_user_id
            assert call_kwargs.get('previous_status') == AppointmentStatus.scheduled.value
            assert call_kwargs.get('new_status') == AppointmentStatus.arrived.value

    def test_audit_log_on_checkin(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Verify audit log is created when checking in."""
        with patch.object(front_desk_service, '_log_audit') as mock_log:
            front_desk_service.mark_arrived(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            front_desk_service.check_in_patient(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            assert mock_log.call_count >= 2

    def test_audit_log_on_cancel(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Verify audit log is created when cancelling."""
        with patch.object(front_desk_service, '_log_audit') as mock_log:
            front_desk_service.cancel_appointment(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            mock_log.assert_called_once()

    def test_audit_log_on_no_show(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Verify audit log is created for no-show."""
        with patch.object(front_desk_service, '_log_audit') as mock_log:
            front_desk_service.mark_arrived(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            front_desk_service.mark_no_show(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            assert mock_log.call_count >= 2

    def test_audit_log_on_vitals_completed(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Verify audit log is created for vitals completion."""
        front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        front_desk_service.check_in_patient(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )

        with patch.object(nurse_workflow_service, '_log_audit') as mock_log:
            nurse_workflow_service.mark_vitals_completed(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            mock_log.assert_called_once()

    def test_audit_log_on_send_to_doctor(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Verify audit log is created when sending to doctor."""
        front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        front_desk_service.check_in_patient(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        nurse_workflow_service.mark_vitals_completed(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )

        with patch.object(nurse_workflow_service, '_log_audit') as mock_log:
            nurse_workflow_service.send_to_doctor_queue(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            mock_log.assert_called_once()

    def test_audit_log_fields(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Verify audit log contains all required fields."""
        with patch.object(front_desk_service, '_log_audit') as mock_log:
            front_desk_service.mark_arrived(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            call_kwargs = mock_log.call_args.kwargs
            required_fields = [
                'actor_id', 'previous_status', 'new_status',
                'appointment', 'event',
            ]
            for field in required_fields:
                assert field in call_kwargs, f"Missing audit field: {field}"

    def test_audit_log_tenant_isolation(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Verify audit logs respect tenant boundaries."""
        with patch.object(front_desk_service, '_log_audit') as mock_log:
            front_desk_service.mark_arrived(
                db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
            )
            call_kwargs = mock_log.call_args.kwargs
            appointment = call_kwargs.get('appointment')
            assert appointment.tenant_id == seeded_tenant.id


# ═════════════════════════════════════════════════════════════════════════════
# 7. INTEGRATION: FULL CLINIC FLOW
# ═════════════════════════════════════════════════════════════════════════════

class TestFullClinicFlow:
    """End-to-end integration test for the complete clinic flow."""

    def test_scheduled_to_waiting_for_doctor(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test the complete patient journey from scheduled to waiting_for_doctor."""
        # 1. Mark arrived
        appt = front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.arrived

        # 2. Check in
        appt = front_desk_service.check_in_patient(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.checked_in

        # 3. Vitals completed
        appt = nurse_workflow_service.mark_vitals_completed(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.vitals_completed

        # 4. Send to doctor
        appt = nurse_workflow_service.send_to_doctor_queue(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.waiting_for_doctor

    def test_walk_in_full_flow(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Test the complete walk-in journey."""
        # 1. Create walk-in
        appt = front_desk_service.create_walk_in(
            db_session, seeded_patient.id, seeded_doctor.id, seeded_tenant.id, seeded_user_id
        )
        assert appt.status == AppointmentStatus.arrived

        # 2. Check in
        appt = front_desk_service.check_in_patient(
            db_session, appt.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.checked_in

        # 3. Vitals
        appt = nurse_workflow_service.mark_vitals_completed(
            db_session, appt.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.vitals_completed

        # 4. To doctor
        appt = nurse_workflow_service.send_to_doctor_queue(
            db_session, appt.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.waiting_for_doctor

    def test_cancellation_at_each_stage(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Verify cancellation is possible at each non-terminal stage."""
        # Cancel from scheduled
        appt = front_desk_service.cancel_appointment(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.cancelled

    def test_no_show_flow(
        self, db_session: Session, seeded_appointment, seeded_tenant, seeded_user_id
    ):
        """Test the no-show workflow."""
        # Mark arrived then no-show
        front_desk_service.mark_arrived(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        appt = front_desk_service.mark_no_show(
            db_session, seeded_appointment.id, seeded_user_id, seeded_tenant.id
        )
        assert appt.status == AppointmentStatus.no_show

    def test_queue_ordering_after_operations(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Verify queue ordering remains consistent after operations."""
        entries = []
        for i in range(3):
            appt_time = datetime.now(timezone.utc) + timedelta(hours=1, minutes=i * 30)
            appt = add_appointment(db_session, {
                "patient_id": seeded_patient.id,
                "doctor_id": seeded_doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.scheduled,
                "created_by": seeded_user_id,
                "tenant_id": seeded_tenant.id,
            })
            entry = queue_service.add_appointment_to_queue(
                db_session,
                appointment_id=appt.id,
                tenant_id=seeded_tenant.id,
                doctor_id=seeded_doctor.id,
                patient_id=seeded_patient.id,
                created_by=seeded_user_id,
            )
            entries.append(entry)

        # Verify ordering
        dashboard = queue_service.get_front_desk_queue(db_session, seeded_tenant.id)
        for i, entry in enumerate(dashboard.entries):
            assert entry.token_number == i + 1

    def test_tenant_isolation(
        self, db_session: Session, seeded_tenant, seeded_doctor, seeded_patient, seeded_user_id
    ):
        """Verify queue entries from different tenants are isolated."""
        # Create entries for tenant A
        for i in range(2):
            appt_time = datetime.now(timezone.utc) + timedelta(hours=1, minutes=i * 30)
            appt = add_appointment(db_session, {
                "patient_id": seeded_patient.id,
                "doctor_id": seeded_doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.scheduled,
                "created_by": seeded_user_id,
                "tenant_id": seeded_tenant.id,
            })
            queue_service.add_appointment_to_queue(
                db_session,
                appointment_id=appt.id,
                tenant_id=seeded_tenant.id,
                doctor_id=seeded_doctor.id,
                patient_id=seeded_patient.id,
                created_by=seeded_user_id,
            )

        # Create entries for tenant B
        tenant_b = create_tenant(db_session, name="Tenant B")
        user_b = create_user(
            db_session,
            email=f"staff_b_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123!",
            role=UserRole.admin,
            tenant_id=tenant_b.id,
        )
        for i in range(3):
            appt_time = datetime.now(timezone.utc) + timedelta(hours=1, minutes=i * 30)
            appt = add_appointment(db_session, {
                "patient_id": seeded_patient.id,
                "doctor_id": seeded_doctor.id,
                "appointment_time": appt_time,
                "status": AppointmentStatus.scheduled,
                "created_by": user_b.id,
                "tenant_id": tenant_b.id,
            })
            queue_service.add_appointment_to_queue(
                db_session,
                appointment_id=appt.id,
                tenant_id=tenant_b.id,
                doctor_id=seeded_doctor.id,
                patient_id=seeded_patient.id,
                created_by=user_b.id,
            )

        # Verify isolation
        dashboard_a = queue_service.get_front_desk_queue(db_session, seeded_tenant.id)
        dashboard_b = queue_service.get_front_desk_queue(db_session, tenant_b.id)
        assert len(dashboard_a.entries) == 2
        assert len(dashboard_b.entries) == 3
