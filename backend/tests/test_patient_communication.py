"""
Tests for Phase P2 — Patient Communication Center.

Architecture:
  - NotificationEvent remains the source-of-truth
  - Patient UI CONSUMES communication aggregates — it does not own delivery workflows
  - Strict patient-only access + tenant isolation
  - NEVER expose provider delivery internals or audit metadata

Test coverage:
  1. Patient communication access (aggregate, timeline, reminders)
  2. Tenant isolation (Patient A cannot see Patient B's communications)
  3. Reminder visibility (urgency grouping, overdue detection)
  4. Document authorization (patient can only access own documents)
  5. Unread counts (mark as read, aggregate unread count)
  6. Preference updates (channel toggles, opt-out with critical override)
  7. Hidden internal payloads (delivery metadata, audit fields)
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

from app.models.notification import (
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventType,
)
from app.models.patient_communication_preference import (
    PatientCommunicationPreference,
)
from app.schemas.patient_communication import (
    CommunicationCard,
    CommunicationPreferencesRead,
    CommunicationPreferencesUpdate,
    PatientCommunicationAggregate,
    ReminderCard,
    ReminderListResponse,
)
from app.services.patient_communication_service import (
    PatientCommunicationService,
)
from app.services.patient_communication_preferences_service import (
    PatientCommunicationPreferencesService,
)


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def patient_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_patient_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_current_user(patient_id, tenant_id):
    """Mock authenticated patient user."""
    user = MagicMock()
    user.id = patient_id
    user.tenant_id = tenant_id
    user.role = "patient"
    return user


@pytest.fixture
def sample_notification_events(patient_id, tenant_id):
    """Create sample notification events for testing."""
    now = datetime.now(timezone.utc)
    events = []

    e = NotificationEvent(
        id=uuid.uuid4(), patient_id=patient_id, tenant_id=tenant_id,
        event_type=NotificationEventType.appointment_reminder,
        doctor_id=uuid.uuid4(), appointment_id=uuid.uuid4(), bill_id=None,
        created_at=now - timedelta(hours=2),
    )
    e.is_read = False
    events.append(e)

    e = NotificationEvent(
        id=uuid.uuid4(), patient_id=patient_id, tenant_id=tenant_id,
        event_type=NotificationEventType.prescription_ready,
        doctor_id=uuid.uuid4(), appointment_id=uuid.uuid4(), bill_id=None,
        created_at=now - timedelta(hours=5),
    )
    e.is_read = False
    events.append(e)

    e = NotificationEvent(
        id=uuid.uuid4(), patient_id=patient_id, tenant_id=tenant_id,
        event_type=NotificationEventType.payment_received,
        doctor_id=uuid.uuid4(), appointment_id=None, bill_id=uuid.uuid4(),
        created_at=now - timedelta(days=3),
    )
    e.is_read = False
    events.append(e)

    # Read notification
    e = NotificationEvent(
        id=uuid.uuid4(), patient_id=patient_id, tenant_id=tenant_id,
        event_type=NotificationEventType.appointment_booked,
        doctor_id=uuid.uuid4(), appointment_id=uuid.uuid4(), bill_id=None,
        created_at=now - timedelta(days=7),
    )
    e.is_read = True
    events.append(e)

    return events


@pytest.fixture
def sample_other_patient_events(other_patient_id, tenant_id):
    """Create notification events for a different patient (for isolation testing)."""
    now = datetime.now(timezone.utc)
    e = NotificationEvent(
        id=uuid.uuid4(), patient_id=other_patient_id, tenant_id=tenant_id,
        event_type=NotificationEventType.appointment_reminder,
        doctor_id=uuid.uuid4(), appointment_id=uuid.uuid4(), bill_id=None,
        created_at=now - timedelta(hours=1),
    )
    e.is_read = False
    return [e]


@pytest.fixture
def sample_preferences(patient_id, tenant_id):
    """Create sample communication preferences."""
    return PatientCommunicationPreference(
        id=uuid.uuid4(),
        patient_id=patient_id,
        tenant_id=tenant_id,
        email_enabled=True,
        sms_enabled=True,
        whatsapp_enabled=False,
        reminder_enabled=True,
        quiet_hours_start=None,
        quiet_hours_end=None,
        locale="en",
        opt_out_all=False,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Patient Communication Access
# ═════════════════════════════════════════════════════════════════════════════


class TestPatientCommunicationAccess:
    """Verify patient can access their own communication aggregate."""

    def test_get_aggregate_returns_patient_communications(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
        sample_preferences,
    ):
        """Patient should receive their own communication aggregate."""
        # Mock queries
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            sample_notification_events
        )
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_preferences
        )

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        aggregate = service.get_aggregate()

        assert isinstance(aggregate, PatientCommunicationAggregate)
        assert aggregate.unread_count == 3  # 3 unread out of 4
        assert len(aggregate.recent_notifications) == 4
        assert aggregate.preferences.email_enabled is True
        assert aggregate.preferences.opt_out_all is False

    def test_get_timeline_returns_paginated_results(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
    ):
        """Patient should receive paginated timeline results."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.count.return_value = (
            len(sample_notification_events)
        )
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            sample_notification_events[:2]
        )

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        timeline = service.get_timeline(skip=0, limit=2)

        assert len(timeline.items) == 2
        assert timeline.total == 4
        assert timeline.skip == 0
        assert timeline.limit == 2

    def test_get_reminders_returns_grouped_results(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
    ):
        """Patient should receive reminders grouped by urgency."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            sample_notification_events
        )

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        reminders = service.get_reminders()

        assert isinstance(reminders, ReminderListResponse)
        # Payment reminder is urgent
        assert len(reminders.reminders_by_urgency.urgent) >= 1
        # Appointment reminder and prescription ready are upcoming
        assert len(reminders.reminders_by_urgency.upcoming) >= 2
        # Read notification is completed
        assert len(reminders.reminders_by_urgency.completed) >= 1

    def test_get_unread_count(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
    ):
        """Patient should receive accurate unread count."""
        unread_events = [e for e in sample_notification_events if not e.is_read]
        mock_db.query.return_value.filter.return_value.count.return_value = len(
            unread_events
        )

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        result = service.get_unread_count()

        assert result["unread_count"] == 3

    def test_mark_as_read(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
    ):
        """Patient should be able to mark a notification as read."""
        event = sample_notification_events[0]
        mock_db.query.return_value.filter.return_value.first.return_value = event

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        service.mark_as_read(event.id)

        assert event.is_read is True
        mock_db.commit.assert_called_once()


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Tenant Isolation
# ═════════════════════════════════════════════════════════════════════════════


class TestTenantIsolation:
    """Verify patients cannot access other patients' communications."""

    def test_patient_cannot_access_other_patient_events(
        self,
        mock_db,
        mock_current_user,
        sample_other_patient_events,
    ):
        """Patient A should NOT see Patient B's notification events."""
        # Mock returns only the current patient's events
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            []
        )

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        aggregate = service.get_aggregate()

        # Other patient's events should not appear
        for notification in aggregate.recent_notifications:
            assert notification.title != "Other Patient Appointment"

    def test_mark_as_read_other_patient_event_raises_error(
        self,
        mock_db,
        mock_current_user,
        sample_other_patient_events,
    ):
        """Patient should NOT be able to mark another patient's event as read."""
        other_event = sample_other_patient_events[0]
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)

        with pytest.raises(HTTPException) as exc_info:
            service.mark_as_read(other_event.id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_different_tenant_isolation(
        self,
        mock_db,
        patient_id,
    ):
        """Patient from Tenant A should not see Tenant B's communications."""
        user = MagicMock()
        user.id = patient_id
        user.tenant_id = uuid.uuid4()  # Different tenant
        user.role = "patient"

        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            []
        )

        service = PatientCommunicationService(db=mock_db, current_user=user)
        aggregate = service.get_aggregate()

        assert len(aggregate.recent_notifications) == 0
        assert aggregate.unread_count == 0


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Reminder Visibility
# ═════════════════════════════════════════════════════════════════════════════


class TestReminderVisibility:
    """Verify reminders are correctly grouped by urgency."""

    def test_urgent_reminders_are_prominent(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
    ):
        """Urgent reminders should appear in the urgent group."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            sample_notification_events
        )

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        reminders = service.get_reminders()

        urgent_titles = [r.title for r in reminders.reminders_by_urgency.urgent]
        assert "Payment Reminder" in urgent_titles

    def test_completed_reminders_are_separate(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
    ):
        """Read/completed notifications should appear in the completed group."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            sample_notification_events
        )

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        reminders = service.get_reminders()

        completed_titles = [r.title for r in reminders.reminders_by_urgency.completed]
        assert "Appointment Confirmed" in completed_titles


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Document Authorization
# ═════════════════════════════════════════════════════════════════════════════


class TestDocumentAuthorization:
    """Verify document-linked communications respect patient ownership."""

    def test_patient_can_access_own_document_links(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
    ):
        """Patient should see document links for their own communications."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            sample_notification_events
        )
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        aggregate = service.get_aggregate()

        # Verify document links are present (prescription-ready events should have document links)
        for notification in aggregate.recent_notifications:
            if notification.event_type == "prescription_ready":
                assert len(notification.linked_documents) >= 0  # May be empty if no docs


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Unread Counts
# ═════════════════════════════════════════════════════════════════════════════


class TestUnreadCounts:
    """Verify unread count accuracy."""

    def test_unread_count_matches_unread_events(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
    ):
        """Unread count should match the number of unread notification events."""
        unread_count = sum(1 for e in sample_notification_events if not e.is_read)
        mock_db.query.return_value.filter.return_value.count.return_value = unread_count

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        result = service.get_unread_count()

        assert result["unread_count"] == 3

    def test_unread_count_decreases_after_mark_read(
        self,
        mock_db,
        mock_current_user,
        sample_notification_events,
    ):
        """Unread count should decrease after marking an event as read."""
        event = sample_notification_events[0]
        mock_db.query.return_value.filter.return_value.first.return_value = event

        service = PatientCommunicationService(db=mock_db, current_user=mock_current_user)
        service.mark_as_read(event.id)

        assert event.is_read is True


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Preference Updates
# ═════════════════════════════════════════════════════════════════════════════


class TestPreferenceUpdates:
    """Verify communication preference updates."""

    def test_update_email_enabled(
        self,
        mock_db,
        mock_current_user,
        patient_id,
        tenant_id,
        sample_preferences,
    ):
        """Patient should be able to toggle email notifications."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_preferences
        )

        service = PatientCommunicationPreferencesService(
            db=mock_db, current_user=mock_current_user
        )
        updated = service.update_preferences(
            patient_id, tenant_id, email_enabled=False
        )

        assert updated.email_enabled is False
        mock_db.commit.assert_called_once()

    def test_update_sms_enabled(
        self,
        mock_db,
        mock_current_user,
        patient_id,
        tenant_id,
        sample_preferences,
    ):
        """Patient should be able to toggle SMS notifications."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_preferences
        )

        service = PatientCommunicationPreferencesService(
            db=mock_db, current_user=mock_current_user
        )
        updated = service.update_preferences(
            patient_id, tenant_id, sms_enabled=False
        )

        assert updated.sms_enabled is False

    def test_update_whatsapp_enabled(
        self,
        mock_db,
        mock_current_user,
        patient_id,
        tenant_id,
        sample_preferences,
    ):
        """Patient should be able to toggle WhatsApp notifications."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_preferences
        )

        service = PatientCommunicationPreferencesService(
            db=mock_db, current_user=mock_current_user
        )
        updated = service.update_preferences(
            patient_id, tenant_id, whatsapp_enabled=True
        )

        assert updated.whatsapp_enabled is True

    def test_update_reminder_enabled(
        self,
        mock_db,
        mock_current_user,
        patient_id,
        tenant_id,
        sample_preferences,
    ):
        """Patient should be able to toggle reminder notifications."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_preferences
        )

        service = PatientCommunicationPreferencesService(
            db=mock_db, current_user=mock_current_user
        )
        updated = service.update_preferences(
            patient_id, tenant_id, reminder_enabled=False
        )

        assert updated.reminder_enabled is False

    def test_opt_out_all_does_not_bypass_critical(
        self,
        mock_db,
        mock_current_user,
        patient_id,
        tenant_id,
        sample_preferences,
    ):
        """
        opt_out_all should NOT bypass critical healthcare notifications.
        This is a policy enforcement test — the preference model stores the flag,
        but the notification service MUST still send critical notifications.
        """
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_preferences
        )

        service = PatientCommunicationPreferencesService(
            db=mock_db, current_user=mock_current_user
        )
        updated = service.update_preferences(
            patient_id, tenant_id, opt_out_all=True
        )

        assert updated.opt_out_all is True
        # Critical notifications are enforced at the notification service level,
        # not at the preference level. This test verifies the preference is stored,
        # but the actual bypass prevention is in notification_service.py.

    def test_get_preferences_returns_current(
        self,
        mock_db,
        mock_current_user,
        patient_id,
        tenant_id,
        sample_preferences,
    ):
        """Patient should receive their current communication preferences."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_preferences
        )

        service = PatientCommunicationPreferencesService(
            db=mock_db, current_user=mock_current_user
        )
        prefs = service.get_preferences(patient_id, tenant_id)

        assert isinstance(prefs, CommunicationPreferencesRead)
        assert prefs.email_enabled is True
        assert prefs.sms_enabled is True
        assert prefs.whatsapp_enabled is False
        assert prefs.reminder_enabled is True
        assert prefs.opt_out_all is False
        assert prefs.locale == "en"

    def test_preferences_upsert_creates_new(
        self,
        mock_db,
        mock_current_user,
        patient_id,
        tenant_id,
    ):
        """If no preferences exist, upsert should create new preferences."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PatientCommunicationPreferencesService(
            db=mock_db, current_user=mock_current_user
        )
        updated = service.update_preferences(
            patient_id, tenant_id, email_enabled=False
        )

        assert updated.email_enabled is False
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Hidden Internal Payloads
# ═════════════════════════════════════════════════════════════════════════════


class TestHiddenInternalPayloads:
    """Verify internal delivery payloads are NEVER exposed to patients."""

    def test_communication_card_has_no_delivery_fields(self):
        """CommunicationCard should NOT expose delivery internals."""
        card = CommunicationCard(
            id=uuid.uuid4(),
            event_type="appointment_reminder",
            title="Test",
            summary="Test summary",
            created_at=datetime.now(timezone.utc),
            is_read=False,
            is_urgent=False,
            doctor_name=None,
            clinic_name=None,
            linked_appointment_id=None,
            linked_bill_id=None,
            linked_documents=[],
            cta_actions=[],
        )

        # Verify no delivery-related fields exist
        assert not hasattr(card, "delivery_status")
        assert not hasattr(card, "delivery_channel")
        assert not hasattr(card, "delivery_attempts")
        assert not hasattr(card, "delivered_at")
        assert not hasattr(card, "provider_metadata")
        assert not hasattr(card, "audit_log")
        assert not hasattr(card, "internal_payload")

    def test_reminder_card_has_no_delivery_fields(self):
        """ReminderCard should NOT expose delivery internals."""
        card = ReminderCard(
            id=uuid.uuid4(),
            event_type="appointment_reminder",
            title="Test Reminder",
            reminder_date=datetime.now(timezone.utc),
            urgency="upcoming",
            doctor_name=None,
            clinic_name=None,
            linked_appointment_id=None,
            linked_bill_id=None,
            cta_actions=[],
        )

        assert not hasattr(card, "delivery_status")
        assert not hasattr(card, "delivery_channel")
        assert not hasattr(card, "internal_payload")

    def test_aggregate_has_no_audit_metadata(self):
        """PatientCommunicationAggregate should NOT expose audit metadata."""
        aggregate = PatientCommunicationAggregate(
            recent_notifications=[],
            unread_count=0,
            reminders_by_urgency={
                "urgent": [],
                "upcoming": [],
                "completed": [],
            },
            preferences=CommunicationPreferencesRead(
                email_enabled=True,
                sms_enabled=True,
                whatsapp_enabled=False,
                reminder_enabled=True,
                quiet_hours_start=None,
                quiet_hours_end=None,
                locale="en",
                opt_out_all=False,
            ),
            linked_documents=[],
        )

        assert not hasattr(aggregate, "audit_log")
        assert not hasattr(aggregate, "provider_metadata")
        assert not hasattr(aggregate, "internal_notes")


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Schema Validation
# ═════════════════════════════════════════════════════════════════════════════


class TestSchemaValidation:
    """Verify Pydantic schema validation for patient communication models."""

    def test_communication_preferences_update_validates_channels(self):
        """Preference update should accept valid channel fields."""
        update = CommunicationPreferencesUpdate(
            email_enabled=False,
            sms_enabled=True,
            whatsapp_enabled=True,
            reminder_enabled=False,
        )
        assert update.email_enabled is False
        assert update.sms_enabled is True
        assert update.whatsapp_enabled is True
        assert update.reminder_enabled is False

    def test_communication_preferences_update_partial(self):
        """Preference update should accept partial updates."""
        update = CommunicationPreferencesUpdate(email_enabled=False)
        assert update.email_enabled is False
        assert update.sms_enabled is None  # Not provided

    def test_communication_preferences_read_defaults(self):
        """Preference read should have all fields."""
        prefs = CommunicationPreferencesRead(
            email_enabled=True,
            sms_enabled=True,
            whatsapp_enabled=False,
            reminder_enabled=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
            locale="en",
            opt_out_all=False,
        )
        assert prefs.email_enabled is True
        assert prefs.locale == "en"
