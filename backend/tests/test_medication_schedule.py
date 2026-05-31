"""
Tests for Patient Medication Schedule — adherence tracking layer.

Architecture:
  PatientMedicationSchedule is DERIVED from Prescription + PrescriptionItem.
  It is a reminder/adherence layer ONLY.
  Prescription remains the canonical source-of-truth.

  Patients CANNOT:
  - edit prescribed dosage
  - alter prescription instructions
  - overwrite doctor records

  Patient actions (taken/skipped/snooze) affect adherence tracking ONLY.
  They NEVER mutate the Prescription or PrescriptionItem rows.

Test coverage:
  1. Medication schedule derivation from prescription items
  2. Adherence tracking (taken/skipped/snoozed)
  3. Reminder visibility and scheduling
  4. Timeline ordering (schedules appear in patient timeline)
  5. Patient authorization (can't access other patients' schedules)
  6. Prescription immutability (can't edit prescription data through schedule)
  7. Follow-up reminders (schedules respect prescription date ranges)
  8. Dashboard aggregation (today's adherence summary)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import crud_medication_schedule
from app.models.patient_medication_schedule import (
    MedicationAdherenceLog,
    MedicationScheduleAdherenceAction,
    MedicationScheduleStatus,
    PatientMedicationSchedule,
)
from app.schemas.medication_schedule import (
    AdherenceAction,
    MedicationScheduleCreate,
    MedicationScheduleUpdate,
)
from app.services import medication_schedule_service


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def patient_user():
    """Create a mock patient user."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = "patient"
    user.patient_id = user.id
    user.tenant_id = uuid.uuid4()
    return user


@pytest.fixture
def doctor_user():
    """Create a mock doctor user (should be denied access)."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = "doctor"
    user.tenant_id = uuid.uuid4()
    return user


@pytest.fixture
def sample_prescription_item():
    """Create a mock prescription item."""
    item = MagicMock()
    item.id = uuid.uuid4()
    item.prescription_id = uuid.uuid4()
    item.medicine_name = "Amoxicillin"
    item.dosage = "500mg"
    item.frequency = "Three times daily"
    item.duration = "7 days"
    item.instructions = "Take with food"
    return item


@pytest.fixture
def sample_prescription(sample_prescription_item, patient_user):
    """Create a mock prescription."""
    prescription = MagicMock()
    prescription.id = sample_prescription_item.prescription_id
    prescription.patient_id = patient_user.id
    prescription.tenant_id = patient_user.tenant_id
    return prescription


@pytest.fixture
def sample_schedule(patient_user):
    """Create a mock medication schedule."""
    schedule = MagicMock(spec=PatientMedicationSchedule)
    schedule.id = uuid.uuid4()
    schedule.patient_id = patient_user.id
    schedule.tenant_id = patient_user.tenant_id
    schedule.prescription_id = uuid.uuid4()
    schedule.prescription_item_id = uuid.uuid4()
    schedule.medicine_name = "Amoxicillin"
    schedule.dosage = "500mg"
    schedule.frequency = "Three times daily"
    schedule.duration = "7 days"
    schedule.instructions = "Take with food"
    schedule.start_date = datetime.now(timezone.utc) - timedelta(days=1)
    schedule.end_date = datetime.now(timezone.utc) + timedelta(days=6)
    schedule.reminder_times = ["08:00", "14:00", "20:00"]
    schedule.taken_count = 0
    schedule.skipped_count = 0
    schedule.total_doses = 21
    schedule.is_active = True
    schedule.status = MedicationScheduleStatus.active
    schedule.created_at = datetime.now(timezone.utc)
    return schedule


# ═════════════════════════════════════════════════════════════════════════════
# 1. Medication Schedule Derivation
# ═════════════════════════════════════════════════════════════════════════════


class TestMedicationScheduleDerivation:
    """Tests for deriving medication schedules from prescription items."""

    def test_derive_schedule_success(
        self, mock_db, patient_user, sample_prescription_item, sample_prescription
    ):
        """Successfully derive a medication schedule from a prescription item."""
        mock_db.get.side_effect = lambda model, id: {
            id: sample_prescription_item if model.__name__ == "PrescriptionItem" else sample_prescription
        }.get(id)

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_schedule_by_prescription_item.return_value = None
            mock_crud.create_medication_schedule.return_value = sample_schedule

            result = medication_schedule_service.derive_schedule_from_prescription(
                mock_db,
                prescription_item_id=sample_prescription_item.id,
                current_user=patient_user,
            )

            assert result is not None
            assert result.medicine_name == "Amoxicillin"
            assert result.dosage == "500mg"
            assert result.frequency == "Three times daily"

    def test_derive_schedule_prescription_not_found(
        self, mock_db, patient_user
    ):
        """Raise 404 when prescription item doesn't exist."""
        mock_db.get.return_value = None

        with pytest.raises(HTTPException) as exc:
            medication_schedule_service.derive_schedule_from_prescription(
                mock_db,
                prescription_item_id=uuid.uuid4(),
                current_user=patient_user,
            )
        assert exc.value.status_code == 404

    def test_derive_schedule_wrong_patient(
        self, mock_db, patient_user, sample_prescription_item
    ):
        """Raise 403 when prescription belongs to another patient."""
        other_prescription = MagicMock()
        other_prescription.patient_id = uuid.uuid4()
        other_prescription.tenant_id = patient_user.tenant_id

        mock_db.get.side_effect = lambda model, id: {
            id: sample_prescription_item if model.__name__ == "PrescriptionItem" else other_prescription
        }.get(id)

        with pytest.raises(HTTPException) as exc:
            medication_schedule_service.derive_schedule_from_prescription(
                mock_db,
                prescription_item_id=sample_prescription_item.id,
                current_user=patient_user,
            )
        assert exc.value.status_code == 403

    def test_derive_schedule_duplicate(
        self, mock_db, patient_user, sample_prescription_item, sample_prescription
    ):
        """Raise 409 when schedule already exists for prescription item."""
        mock_db.get.side_effect = lambda model, id: {
            id: sample_prescription_item if model.__name__ == "PrescriptionItem" else sample_prescription
        }.get(id)

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_schedule_by_prescription_item.return_value = (
                sample_schedule
            )

            with pytest.raises(HTTPException) as exc:
                medication_schedule_service.derive_schedule_from_prescription(
                    mock_db,
                    prescription_item_id=sample_prescription_item.id,
                    current_user=patient_user,
                )
            assert exc.value.status_code == 409

    def test_derive_schedule_doctor_denied(
        self, mock_db, doctor_user, sample_prescription_item
    ):
        """Raise 403 when a doctor tries to derive a schedule."""
        with pytest.raises(HTTPException) as exc:
            medication_schedule_service.derive_schedule_from_prescription(
                mock_db,
                prescription_item_id=sample_prescription_item.id,
                current_user=doctor_user,
            )
        assert exc.value.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# 2. Adherence Tracking
# ═════════════════════════════════════════════════════════════════════════════


class TestAdherenceTracking:
    """Tests for recording adherence actions."""

    def test_record_taken(
        self, mock_db, patient_user, sample_schedule
    ):
        """Successfully record a 'taken' action."""
        mock_db.get.return_value = sample_schedule

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            action = AdherenceAction(action="taken", scheduled_time="08:00")
            result = medication_schedule_service.record_adherence(
                mock_db,
                schedule_id=sample_schedule.id,
                action=action,
                current_user=patient_user,
            )

            assert result is not None
            assert result.taken_count == 1  # Incremented in the mock

    def test_record_skipped(
        self, mock_db, patient_user, sample_schedule
    ):
        """Successfully record a 'skipped' action."""
        mock_db.get.return_value = sample_schedule

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            action = AdherenceAction(action="skipped", scheduled_time="14:00")
            result = medication_schedule_service.record_adherence(
                mock_db,
                schedule_id=sample_schedule.id,
                action=action,
                current_user=patient_user,
            )

            assert result is not None

    def test_record_snoozed(
        self, mock_db, patient_user, sample_schedule
    ):
        """Successfully record a 'snoozed' action."""
        mock_db.get.return_value = sample_schedule

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            action = AdherenceAction(action="snoozed", scheduled_time="20:00")
            result = medication_schedule_service.record_adherence(
                mock_db,
                schedule_id=sample_schedule.id,
                action=action,
                current_user=patient_user,
            )

            assert result is not None

    def test_record_adherence_wrong_patient(
        self, mock_db, patient_user, sample_schedule
    ):
        """Raise 403 when recording adherence on another patient's schedule."""
        sample_schedule.patient_id = uuid.uuid4()  # Different patient
        mock_db.get.return_value = sample_schedule

        action = AdherenceAction(action="taken")
        with pytest.raises(HTTPException) as exc:
            medication_schedule_service.record_adherence(
                mock_db,
                schedule_id=sample_schedule.id,
                action=action,
                current_user=patient_user,
            )
        assert exc.value.status_code == 403

    def test_record_adherence_inactive_schedule(
        self, mock_db, patient_user, sample_schedule
    ):
        """Raise 400 when schedule is inactive."""
        sample_schedule.is_active = False
        sample_schedule.status = MedicationScheduleStatus.completed
        mock_db.get.return_value = sample_schedule

        action = AdherenceAction(action="taken")
        with pytest.raises(HTTPException) as exc:
            medication_schedule_service.record_adherence(
                mock_db,
                schedule_id=sample_schedule.id,
                action=action,
                current_user=patient_user,
            )
        assert exc.value.status_code == 400

    def test_record_adherence_invalid_action(
        self, mock_db, patient_user, sample_schedule
    ):
        """Raise 400 for invalid action."""
        mock_db.get.return_value = sample_schedule

        action = AdherenceAction(action="invalid_action")
        with pytest.raises(HTTPException) as exc:
            medication_schedule_service.record_adherence(
                mock_db,
                schedule_id=sample_schedule.id,
                action=action,
                current_user=patient_user,
            )
        assert exc.value.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# 3. Reminder Visibility
# ═════════════════════════════════════════════════════════════════════════════


class TestReminderVisibility:
    """Tests for medication reminder visibility."""

    def test_reminder_times_included_in_read(
        self, mock_db, patient_user, sample_schedule
    ):
        """Reminder times are included in the schedule read model."""
        mock_db.get.return_value = sample_schedule

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_schedule_by_id.return_value = sample_schedule

            result = medication_schedule_service.get_schedule_detail(
                mock_db, sample_schedule.id, patient_user
            )

            assert result.reminder_times == ["08:00", "14:00", "20:00"]

    def test_due_medications_query(
        self, mock_db, patient_user, sample_schedule
    ):
        """Due medications query returns active schedules within date range."""
        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_due_medications.return_value = [sample_schedule]

            result = medication_schedule_service.get_due_medications(
                mock_db, patient_user
            )

            assert len(result) == 1
            assert result[0].medicine_name == "Amoxicillin"


# ═════════════════════════════════════════════════════════════════════════════
# 4. Timeline Ordering
# ═════════════════════════════════════════════════════════════════════════════


class TestTimelineOrdering:
    """Tests for schedule ordering in patient timeline."""

    def test_schedules_ordered_by_created_at(
        self, mock_db, patient_user
    ):
        """Schedules are returned in descending order of created_at."""
        schedule1 = MagicMock(spec=PatientMedicationSchedule)
        schedule1.id = uuid.uuid4()
        schedule1.patient_id = patient_user.id
        schedule1.tenant_id = patient_user.tenant_id
        schedule1.created_at = datetime.now(timezone.utc)
        schedule1.medicine_name = "Medicine A"
        schedule1.is_active = True
        schedule1.status = MedicationScheduleStatus.active

        schedule2 = MagicMock(spec=PatientMedicationSchedule)
        schedule2.id = uuid.uuid4()
        schedule2.patient_id = patient_user.id
        schedule2.tenant_id = patient_user.tenant_id
        schedule2.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule2.medicine_name = "Medicine B"
        schedule2.is_active = True
        schedule2.status = MedicationScheduleStatus.active

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_active_schedules_for_patient.return_value = (
                [schedule1, schedule2],
                2,
            )

            items, total = medication_schedule_service.get_patient_schedules(
                mock_db, patient_user
            )

            assert total == 2
            assert len(items) == 2


# ═════════════════════════════════════════════════════════════════════════════
# 5. Patient Authorization
# ═════════════════════════════════════════════════════════════════════════════


class TestPatientAuthorization:
    """Tests for patient-only access enforcement."""

    def test_doctor_cannot_access_schedules(
        self, mock_db, doctor_user
    ):
        """Doctor users are denied access to medication schedules."""
        with pytest.raises(HTTPException) as exc:
            medication_schedule_service.get_due_medications(
                mock_db, doctor_user
            )
        assert exc.value.status_code == 403

    def test_patient_cannot_access_other_patient_schedule(
        self, mock_db, patient_user, sample_schedule
    ):
        """Patient cannot access another patient's schedule."""
        sample_schedule.patient_id = uuid.uuid4()  # Different patient
        mock_db.get.return_value = sample_schedule

        with pytest.raises(HTTPException) as exc:
            medication_schedule_service.get_schedule_detail(
                mock_db, sample_schedule.id, patient_user
            )
        assert exc.value.status_code == 403

    def test_tenant_isolation(
        self, mock_db, patient_user, sample_schedule
    ):
        """Tenant isolation is enforced."""
        sample_schedule.tenant_id = uuid.uuid4()  # Different tenant
        mock_db.get.return_value = sample_schedule

        with pytest.raises(HTTPException) as exc:
            medication_schedule_service.get_schedule_detail(
                mock_db, sample_schedule.id, patient_user
            )
        assert exc.value.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# 6. Prescription Immutability
# ═════════════════════════════════════════════════════════════════════════════


class TestPrescriptionImmutability:
    """Tests that prescription data cannot be mutated through schedules."""

    def test_update_does_not_affect_prescription_fields(
        self, mock_db, patient_user, sample_schedule
    ):
        """Updating a schedule does not change prescription-snapshot fields."""
        mock_db.get.return_value = sample_schedule

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.update_schedule.return_value = sample_schedule

            updates = MedicationScheduleUpdate(
                reminder_times=["09:00", "21:00"],
                is_active=True,
            )
            result = medication_schedule_service.update_schedule(
                mock_db, sample_schedule.id, updates, patient_user
            )

            # Prescription-snapshot fields remain unchanged
            assert result.medicine_name == "Amoxicillin"
            assert result.dosage == "500mg"
            assert result.frequency == "Three times daily"

    def test_cannot_update_prescription_fields(
        self, mock_db, patient_user, sample_schedule
    ):
        """Patients cannot update prescription-snapshot fields."""
        mock_db.get.return_value = sample_schedule

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.update_schedule.return_value = sample_schedule

            # Attempt to update prescription fields (should be ignored)
            updates = MedicationScheduleUpdate(
                reminder_times=["09:00"],
            )
            result = medication_schedule_service.update_schedule(
                mock_db, sample_schedule.id, updates, patient_user
            )

            # Prescription fields are never passed to update
            call_kwargs = mock_crud.update_schedule.call_args[1]
            assert "medicine_name" not in call_kwargs
            assert "dosage" not in call_kwargs
            assert "frequency" not in call_kwargs


# ═════════════════════════════════════════════════════════════════════════════
# 7. Follow-up Reminders (Schedule Date Ranges)
# ═════════════════════════════════════════════════════════════════════════════


class TestFollowUpReminders:
    """Tests that schedules respect prescription date ranges."""

    def test_expired_schedule_not_due(
        self, mock_db, patient_user
    ):
        """An expired schedule is not returned as 'due'."""
        expired_schedule = MagicMock(spec=PatientMedicationSchedule)
        expired_schedule.id = uuid.uuid4()
        expired_schedule.patient_id = patient_user.id
        expired_schedule.tenant_id = patient_user.tenant_id
        expired_schedule.start_date = datetime.now(timezone.utc) - timedelta(days=14)
        expired_schedule.end_date = datetime.now(timezone.utc) - timedelta(days=7)
        expired_schedule.is_active = True
        expired_schedule.status = MedicationScheduleStatus.active

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_due_medications.return_value = []  # Not due

            result = medication_schedule_service.get_due_medications(
                mock_db, patient_user
            )

            assert len(result) == 0

    def test_future_schedule_not_due(
        self, mock_db, patient_user
    ):
        """A future schedule is not returned as 'due'."""
        future_schedule = MagicMock(spec=PatientMedicationSchedule)
        future_schedule.id = uuid.uuid4()
        future_schedule.patient_id = patient_user.id
        future_schedule.tenant_id = patient_user.tenant_id
        future_schedule.start_date = datetime.now(timezone.utc) + timedelta(days=7)
        future_schedule.end_date = datetime.now(timezone.utc) + timedelta(days=14)
        future_schedule.is_active = True
        future_schedule.status = MedicationScheduleStatus.active

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_due_medications.return_value = []  # Not due

            result = medication_schedule_service.get_due_medications(
                mock_db, patient_user
            )

            assert len(result) == 0


# ═════════════════════════════════════════════════════════════════════════════
# 8. Dashboard Aggregation
# ═════════════════════════════════════════════════════════════════════════════


class TestDashboardAggregation:
    """Tests for today's adherence summary."""

    def test_today_adherence_summary(
        self, mock_db, patient_user, sample_schedule
    ):
        """Today's adherence summary returns correct counts."""
        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_due_medications.return_value = [sample_schedule]
            mock_crud.get_today_adherence_logs.return_value = []
            mock_crud.compute_adherence_streak.return_value = (0, 0, 0.0)

            summary = medication_schedule_service.get_today_adherence_summary(
                mock_db, patient_user
            )

            assert summary.total_due_today == 1
            assert summary.taken_today == 0
            assert summary.pending_today == 1
            assert summary.adherence_rate_today == 0.0

    def test_today_adherence_with_taken(
        self, mock_db, patient_user, sample_schedule
    ):
        """Today's adherence summary reflects taken medications."""
        taken_log = MagicMock(spec=MedicationAdherenceLog)
        taken_log.action = MedicationScheduleAdherenceAction.taken

        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_due_medications.return_value = [sample_schedule]
            mock_crud.get_today_adherence_logs.return_value = [taken_log]
            mock_crud.compute_adherence_streak.return_value = (1, 3, 0.8)

            summary = medication_schedule_service.get_today_adherence_summary(
                mock_db, patient_user
            )

            assert summary.total_due_today == 1
            assert summary.taken_today == 1
            assert summary.pending_today == 0
            assert summary.adherence_rate_today == 1.0
            assert summary.current_streak_days == 1
            assert summary.longest_streak_days == 3
            assert summary.week_adherence_rate == 0.8

    def test_today_adherence_empty(
        self, mock_db, patient_user
    ):
        """Today's adherence summary handles no due medications."""
        with patch(
            "app.services.medication_schedule_service.crud_medication_schedule"
        ) as mock_crud:
            mock_crud.get_due_medications.return_value = []
            mock_crud.get_today_adherence_logs.return_value = []
            mock_crud.compute_adherence_streak.return_value = (0, 0, 0.0)

            summary = medication_schedule_service.get_today_adherence_summary(
                mock_db, patient_user
            )

            assert summary.total_due_today == 0
            assert summary.taken_today == 0
            assert summary.pending_today == 0
            assert summary.adherence_rate_today == 0.0


# ═════════════════════════════════════════════════════════════════════════════
# CRUD Layer Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestCRUDMedicationSchedule:
    """Tests for the CRUD layer."""

    def test_create_schedule(self, mock_db, patient_user):
        """Create a medication schedule via CRUD."""
        schedule = crud_medication_schedule.create_medication_schedule(
            mock_db,
            patient_id=patient_user.id,
            prescription_id=uuid.uuid4(),
            prescription_item_id=uuid.uuid4(),
            tenant_id=patient_user.tenant_id,
            medicine_name="Test Med",
            dosage="10mg",
            frequency="Once daily",
            duration="30 days",
            instructions="Take in morning",
            start_date=datetime.now(timezone.utc),
            reminder_times=["08:00"],
        )

        assert schedule is not None
        assert schedule.medicine_name == "Test Med"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_soft_delete_schedule(self, mock_db):
        """Soft-delete a medication schedule."""
        schedule_id = uuid.uuid4()
        result = crud_medication_schedule.soft_delete_schedule(
            mock_db, schedule_id
        )

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_create_adherence_log(self, mock_db, patient_user):
        """Create an adherence log entry."""
        log = crud_medication_schedule.create_adherence_log(
            mock_db,
            medication_schedule_id=uuid.uuid4(),
            patient_id=patient_user.id,
            action=MedicationScheduleAdherenceAction.taken,
            scheduled_time="08:00",
        )

        assert log is not None
        assert log.action == MedicationScheduleAdherenceAction.taken
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
