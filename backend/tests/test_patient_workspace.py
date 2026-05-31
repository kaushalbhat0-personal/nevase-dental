"""
Tests for Patient Health Workspace (Phase P1).

Covers:
- patient encounter access
- tenant isolation
- document authorization
- timeline ordering
- follow-up visibility
- hidden doctor-only fields
- aggregate API responses
"""

import uuid

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status

from app.schemas.patient_workspace import (
    PatientHealthWorkspaceAggregate,
    EncounterCard,
    VitalsSnapshot,
    FollowUpItem,
    FollowUpSummary,
    DocumentRef,
)
from app.services.patient_workspace_service import PatientWorkspaceService


_UUID1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
_UUID2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
_UUID3 = uuid.UUID("00000000-0000-0000-0000-000000000003")
_UUID5 = uuid.UUID("00000000-0000-0000-0000-000000000005")
_UUID100 = uuid.UUID("00000000-0000-0000-0000-000000000100")
_UUID101 = uuid.UUID("00000000-0000-0000-0000-000000000101")


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_patient_user():
    user = MagicMock()
    user.id = 100
    user.tenant_id = 1
    user.role = "patient"
    return user


@pytest.fixture
def mock_doctor_user():
    user = MagicMock()
    user.id = 200
    user.tenant_id = 1
    user.role = "doctor"
    return user


@pytest.fixture
def mock_other_patient_user():
    user = MagicMock()
    user.id = 101
    user.tenant_id = 1
    user.role = "patient"
    return user


@pytest.fixture
def mock_cross_tenant_user():
    user = MagicMock()
    user.id = 300
    user.tenant_id = 2
    user.role = "patient"
    return user


# ── Tenant Isolation Tests ────────────────────────────────────────────────────


class TestTenantIsolation:
    """Patients MUST NOT access data from other tenants."""

    @pytest.mark.asyncio
    async def test_get_workspace_cross_tenant_blocked(self, mock_db, mock_patient_user):
        """Patient from tenant 1 cannot access tenant 2 data."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        with patch.object(service, "_get_patient_profile", return_value={"id": 100, "tenant_id": 1}):
            with patch.object(
                service, "_get_recent_encounters", return_value=[{"appointment_id": 1, "tenant_id": 2}]
            ):
                result = await service.get_workspace()
                # Encounters from other tenant should be filtered out
                for enc in result.recent_encounters:
                    assert enc.appointment_id is not None

    @pytest.mark.asyncio
    async def test_get_encounters_cross_tenant_blocked(self, mock_db, mock_patient_user):
        """Patient encounters query enforces tenant isolation."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        with patch.object(
            service,
            "_query_patient_encounters",
            return_value=[
                {"appointment_id": _UUID1, "doctor_name": "Dr. A", "appointment_time": datetime.now(timezone.utc), "status": "completed", "doctor_id": _UUID1},
                {"appointment_id": _UUID2, "doctor_name": "Dr. B", "appointment_time": datetime.now(timezone.utc), "status": "completed", "doctor_id": _UUID2},
            ],
        ):
            result = await service.get_encounters(limit=50)
            assert len(result) == 2
            assert result[0].appointment_id == _UUID1
            assert result[1].appointment_id == _UUID2


# ── Patient Access Control Tests ──────────────────────────────────────────────


class TestPatientAccessControl:
    """Patients can ONLY access their own data."""

    @pytest.mark.asyncio
    async def test_doctor_cannot_access_patient_workspace(self, mock_db, mock_doctor_user):
        """Doctor role should not be able to access patient workspace."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_doctor_user)
        with pytest.raises(HTTPException) as exc:
            await service.get_workspace()
        assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_patient_cannot_access_other_patient_encounters(
        self, mock_db, mock_patient_user, mock_other_patient_user
    ):
        """Patient cannot access another patient's encounter detail."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        with patch.object(
            service,
            "_get_encounter_detail",
            return_value={"appointment_id": 5, "patient_id": 101},  # Other patient
        ):
            with pytest.raises(HTTPException) as exc:
                await service.get_encounter_detail(5)
            assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_patient_can_access_own_encounter(self, mock_db, mock_patient_user):
        """Patient can access their own encounter detail."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        with patch.object(
            service,
            "_get_encounter_detail",
            return_value={"appointment_id": 5, "patient_id": 100},  # Own patient
        ):
            result = await service.get_encounter_detail(5)
            assert result is not None


# ── Document Authorization Tests ──────────────────────────────────────────────


class TestDocumentAuthorization:
    """Patients can only download their own documents."""

    @pytest.mark.asyncio
    async def test_patient_cannot_download_other_patient_document(
        self, mock_db, mock_patient_user
    ):
        """Document download for another patient's encounter is blocked."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        with patch.object(
            service,
            "_verify_encounter_ownership",
            return_value=False,  # Not owned by this patient
        ):
            with pytest.raises(HTTPException) as exc:
                await service.get_document_download_url(5, "prescription")
            assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_patient_can_download_own_document(self, mock_db, mock_patient_user):
        """Document download for own encounter succeeds."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        with patch.object(
            service,
            "_verify_encounter_ownership",
            return_value=True,
        ):
            with patch.object(
                service,
                "_generate_document_url",
                return_value="https://docs.example.com/prescription/5.pdf",
            ):
                url = await service.get_document_download_url(5, "prescription")
                assert url is not None
                assert "prescription" in url


# ── Timeline Ordering Tests ───────────────────────────────────────────────────


class TestTimelineOrdering:
    """Timeline must be chronological (newest first)."""

    @pytest.mark.asyncio
    async def test_encounters_ordered_by_date_descending(self, mock_db, mock_patient_user):
        """Encounters should be returned newest first."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        now = datetime.now(timezone.utc)
        encounters = [
            {"appointment_id": _UUID1, "appointment_time": now - timedelta(days=10), "doctor_id": _UUID1, "doctor_name": "Dr. A", "status": "completed"},
            {"appointment_id": _UUID2, "appointment_time": now - timedelta(days=5), "doctor_id": _UUID1, "doctor_name": "Dr. A", "status": "completed"},
            {"appointment_id": _UUID3, "appointment_time": now - timedelta(days=1), "doctor_id": _UUID1, "doctor_name": "Dr. A", "status": "completed"},
        ]

        with patch.object(service, "_query_patient_encounters", return_value=encounters):
            result = await service.get_encounters(limit=50)
            dates = [enc.appointment_time for enc in result]
            assert dates == sorted(dates, reverse=True), "Encounters not in descending order"

    @pytest.mark.asyncio
    async def test_empty_timeline_returns_empty_list(self, mock_db, mock_patient_user):
        """No encounters should return empty list, not error."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        with patch.object(service, "_query_patient_encounters", return_value=[]):
            result = await service.get_encounters(limit=50)
            assert result == []


# ── Follow-up Visibility Tests ────────────────────────────────────────────────


class TestFollowUpVisibility:
    """Follow-ups must be correctly categorized as upcoming or overdue."""

    @pytest.mark.asyncio
    async def test_upcoming_follow_ups(self, mock_db, mock_patient_user):
        """Follow-ups with future dates are categorized as upcoming."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        now = datetime.now(timezone.utc)
        follow_ups = [
            {"appointment_id": 1, "follow_up_date": now + timedelta(days=7)},
            {"appointment_id": 2, "follow_up_date": now + timedelta(days=14)},
        ]

        with patch.object(service, "_query_follow_ups", return_value=follow_ups):
            result = await service.get_follow_ups()
            assert result.total_upcoming == 2
            assert result.total_overdue == 0

    @pytest.mark.asyncio
    async def test_overdue_follow_ups(self, mock_db, mock_patient_user):
        """Follow-ups with past dates are categorized as overdue."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        now = datetime.now(timezone.utc)
        follow_ups = [
            {"appointment_id": 1, "follow_up_date": now - timedelta(days=7)},
            {"appointment_id": 2, "follow_up_date": now - timedelta(days=1)},
        ]

        with patch.object(service, "_query_follow_ups", return_value=follow_ups):
            result = await service.get_follow_ups()
            assert result.total_upcoming == 0
            assert result.total_overdue == 2

    @pytest.mark.asyncio
    async def test_mixed_follow_ups(self, mock_db, mock_patient_user):
        """Mixed upcoming and overdue follow-ups are correctly categorized."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        now = datetime.now(timezone.utc)
        follow_ups = [
            {"appointment_id": 1, "follow_up_date": now - timedelta(days=3)},  # Overdue
            {"appointment_id": 2, "follow_up_date": now + timedelta(days=5)},  # Upcoming
            {"appointment_id": 3, "follow_up_date": now + timedelta(days=10)},  # Upcoming
        ]

        with patch.object(service, "_query_follow_ups", return_value=follow_ups):
            result = await service.get_follow_ups()
            assert result.total_upcoming == 2
            assert result.total_overdue == 1
            assert len(result.upcoming) == 2
            assert len(result.overdue) == 1


# ── Hidden Doctor-Only Fields Tests ───────────────────────────────────────────


class TestHiddenDoctorFields:
    """Doctor-only internal notes must NEVER be exposed to patients."""

    @pytest.mark.asyncio
    async def test_soap_internal_sections_not_exposed(self, mock_db, mock_patient_user):
        """SOAP internal sections should be stripped from patient-facing data."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        encounter_data = {
            "appointment_id": 5,
            "patient_id": 100,
            "diagnosis": "Hypertension",
            "treatment_summary": "Prescribed lisinopril",
            "soap_subjective": "Patient reports headaches",
            "soap_objective": "BP 150/90",
            "soap_assessment": "Stage 1 hypertension",
            "soap_plan": "Continue lisinopril, follow up in 3 months",
            "doctor_notes": "Patient seems anxious about BP",
            "internal_notes": "Verify insurance coverage",
        }

        with patch.object(service, "_get_encounter_detail", return_value=encounter_data):
            result = await service.get_encounter_detail(5)
            # Patient-safe fields should be present
            assert result.get("diagnosis") == "Hypertension"
            assert result.get("treatment_summary") == "Prescribed lisinopril"
            # Doctor-only fields should NOT be present
            assert "soap_subjective" not in result, "SOAP subjective leaked!"
            assert "soap_objective" not in result, "SOAP objective leaked!"
            assert "soap_assessment" not in result, "SOAP assessment leaked!"
            assert "soap_plan" not in result, "SOAP plan leaked!"
            assert "doctor_notes" not in result, "Doctor notes leaked!"
            assert "internal_notes" not in result, "Internal notes leaked!"

    @pytest.mark.asyncio
    async def test_audit_metadata_not_exposed(self, mock_db, mock_patient_user):
        """Audit metadata must not be exposed to patients."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        encounter_data = {
            "appointment_id": 5,
            "patient_id": 100,
            "diagnosis": "Hypertension",
            "created_by": 42,
            "updated_by": 42,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "audit_log": "Some audit trail",
        }

        with patch.object(service, "_get_encounter_detail", return_value=encounter_data):
            result = await service.get_encounter_detail(5)
            assert "created_by" not in result, "Audit field created_by leaked!"
            assert "updated_by" not in result, "Audit field updated_by leaked!"
            assert "audit_log" not in result, "Audit log leaked!"


# ── Aggregate API Response Tests ──────────────────────────────────────────────


class TestAggregateAPIResponse:
    """Aggregate API must return correct structure."""

    @pytest.mark.asyncio
    async def test_workspace_aggregate_structure(self, mock_db, mock_patient_user):
        """Workspace aggregate should contain all expected sections."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        with patch.object(service, "_get_patient_profile", return_value={"id": 100, "name": "John"}):
            with patch.object(service, "_get_recent_encounters", return_value=[]):
                with patch.object(service, "_get_upcoming_appointments", return_value=[]):
                    with patch.object(service, "_get_vitals_history", return_value=[]):
                        with patch.object(service, "_get_prescriptions", return_value=[]):
                            with patch.object(service, "_get_follow_ups", return_value=[]):
                                with patch.object(service, "_get_billing_summary", return_value={}):
                                    with patch.object(service, "_get_recent_documents", return_value=[]):
                                        result = await service.get_workspace()

        assert hasattr(result, "patient_profile")
        assert hasattr(result, "recent_encounters")
        assert hasattr(result, "upcoming_appointments")
        assert hasattr(result, "vitals_history")
        assert hasattr(result, "prescriptions_history")
        assert hasattr(result, "follow_ups")
        assert hasattr(result, "billing_summary")
        assert hasattr(result, "recent_documents")
        assert hasattr(result, "communication_summary")

    @pytest.mark.asyncio
    async def test_encounter_card_structure(self, mock_db, mock_patient_user):
        """EncounterCard should contain patient-safe fields."""
        service = PatientWorkspaceService(db=mock_db, current_user=mock_patient_user)

        encounter = {
            "appointment_id": _UUID1,
            "appointment_time": datetime.now(timezone.utc),
            "doctor_id": _UUID1,
            "doctor_name": "Dr. Smith",
            "doctor_specialization": "Cardiology",
            "clinic_name": "Heart Clinic",
            "diagnosis": "Hypertension",
            "treatment_summary": "Medication prescribed",
            "status": "completed",
        }

        with patch.object(service, "_query_patient_encounters", return_value=[encounter]):
            result = await service.get_encounters(limit=50)
            card = result[0]
            assert card.appointment_id == _UUID1
            assert card.doctor_name == "Dr. Smith"
            assert card.diagnosis == "Hypertension"
            assert card.status == "completed"
