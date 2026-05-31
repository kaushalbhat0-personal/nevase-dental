"""
Communication Templates — Phase 3D Communication Infrastructure.

Default templates for all notification event types.
Templates are tenant-scoped and support placeholders for dynamic content.

Placeholder resolution:
  {{ patient_name }}     — Patient's full name
  {{ doctor_name }}      — Doctor's full name
  {{ appointment_time }} — Formatted appointment datetime
  {{ clinic_name }}      — Tenant organization name
  {{ clinic_phone }}     — Tenant phone number
  {{ clinic_address }}   — Tenant formatted address
  {{ bill_amount }}      — Formatted bill amount with currency
  {{ bill_id }}          — Bill reference ID
  {{ payment_method }}   — Payment method used
  {{ follow_up_date }}   — Follow-up appointment date
  {{ prescription_link }}— Link to view prescription (future)

TODO: Phase 5 — Multilingual template rendering (locale-aware)
TODO: Phase 5 — Patient communication preferences / consent management
TODO: Phase 5 — Opt-out / unsubscribe handling
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.models.notification import (
    NotificationChannel,
    NotificationEventType,
)

logger = logging.getLogger(__name__)

# Pattern for matching placeholders like {{ placeholder_name }}
PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


# ═════════════════════════════════════════════════════════════════════════════
# Default Template Definitions
# ═════════════════════════════════════════════════════════════════════════════


class DefaultTemplates:
    """
    Default communication templates for all event types and channels.

    These are used as system defaults when no tenant-specific template exists.
    Each template is a dict with 'subject' (optional) and 'body' keys.
    """

    # ── Appointment Booked ──────────────────────────────────────────────

    appointment_booked = {
        NotificationChannel.email: {
            "subject": "Appointment Confirmed – {{ clinic_name }}",
            "body": (
                "Dear {{ patient_name }},\n\n"
                "Your appointment has been confirmed.\n\n"
                "Doctor: Dr. {{ doctor_name }}\n"
                "Date & Time: {{ appointment_time }}\n"
                "Clinic: {{ clinic_name }}\n"
                "Address: {{ clinic_address }}\n"
                "Phone: {{ clinic_phone }}\n\n"
                "Please arrive 10 minutes before your scheduled time.\n\n"
                "Thank you,\n"
                "{{ clinic_name }}"
            ),
        },
        NotificationChannel.sms: {
            "body": (
                "Appointment confirmed with Dr. {{ doctor_name }} "
                "on {{ appointment_time }} at {{ clinic_name }}. "
                "Contact: {{ clinic_phone }}"
            ),
        },
        NotificationChannel.whatsapp: {
            "body": (
                "✅ *Appointment Confirmed*\n\n"
                "Doctor: Dr. {{ doctor_name }}\n"
                "Date: {{ appointment_time }}\n"
                "Clinic: {{ clinic_name }}\n"
                "Address: {{ clinic_address }}\n\n"
                "Thank you for choosing {{ clinic_name }}."
            ),
        },
        NotificationChannel.in_app: {
            "subject": "Appointment Confirmed",
            "body": (
                "Your appointment with Dr. {{ doctor_name }} "
                "on {{ appointment_time }} has been confirmed."
            ),
        },
    }

    # ── Appointment Reminder ────────────────────────────────────────────

    appointment_reminder = {
        NotificationChannel.email: {
            "subject": "Reminder: Appointment Tomorrow at {{ appointment_time }}",
            "body": (
                "Dear {{ patient_name }},\n\n"
                "This is a reminder about your upcoming appointment.\n\n"
                "Doctor: Dr. {{ doctor_name }}\n"
                "Date & Time: {{ appointment_time }}\n"
                "Clinic: {{ clinic_name }}\n"
                "Address: {{ clinic_address }}\n"
                "Phone: {{ clinic_phone }}\n\n"
                "Please arrive 10 minutes before your scheduled time.\n"
                "To reschedule, please contact the clinic.\n\n"
                "Thank you,\n"
                "{{ clinic_name }}"
            ),
        },
        NotificationChannel.sms: {
            "body": (
                "Reminder: Appointment with Dr. {{ doctor_name }} "
                "on {{ appointment_time }} at {{ clinic_name }}. "
                "Contact: {{ clinic_phone }}"
            ),
        },
        NotificationChannel.whatsapp: {
            "body": (
                "⏰ *Appointment Reminder*\n\n"
                "Doctor: Dr. {{ doctor_name }}\n"
                "Date: {{ appointment_time }}\n"
                "Clinic: {{ clinic_name }}\n"
                "Address: {{ clinic_address }}\n\n"
                "Please arrive on time."
            ),
        },
        NotificationChannel.in_app: {
            "subject": "Appointment Reminder",
            "body": (
                "Reminder: You have an appointment with Dr. {{ doctor_name }} "
                "on {{ appointment_time }}."
            ),
        },
    }

    # ── Appointment Completed ───────────────────────────────────────────

    appointment_completed = {
        NotificationChannel.email: {
            "subject": "Visit Summary – {{ clinic_name }}",
            "body": (
                "Dear {{ patient_name }},\n\n"
                "Your visit with Dr. {{ doctor_name }} "
                "on {{ appointment_time }} has been completed.\n\n"
                "A detailed summary of your visit is available.\n"
                "If you have any questions, please contact the clinic.\n\n"
                "Thank you for visiting {{ clinic_name }}.\n"
                "{{ clinic_phone }}"
            ),
        },
        NotificationChannel.sms: {
            "body": (
                "Your visit with Dr. {{ doctor_name }} "
                "on {{ appointment_time }} is complete. "
                "Thank you for visiting {{ clinic_name }}."
            ),
        },
        NotificationChannel.in_app: {
            "subject": "Visit Completed",
            "body": (
                "Your visit with Dr. {{ doctor_name }} "
                "on {{ appointment_time }} has been completed."
            ),
        },
    }

    # ── Prescription Ready ──────────────────────────────────────────────

    prescription_ready = {
        NotificationChannel.email: {
            "subject": "Prescription Ready – {{ clinic_name }}",
            "body": (
                "Dear {{ patient_name }},\n\n"
                "Your prescription from Dr. {{ doctor_name }} "
                "is now ready.\n\n"
                "You can view and download your prescription from your patient portal.\n\n"
                "{{ prescription_link }}\n\n"
                "Thank you,\n"
                "{{ clinic_name }}"
            ),
        },
        NotificationChannel.sms: {
            "body": (
                "Your prescription from Dr. {{ doctor_name }} is ready. "
                "View it in your patient portal. – {{ clinic_name }}"
            ),
        },
        NotificationChannel.in_app: {
            "subject": "Prescription Ready",
            "body": (
                "Your prescription from Dr. {{ doctor_name }} is now ready. "
                "You can view it in your visit details."
            ),
        },
    }

    # ── Bill Generated ──────────────────────────────────────────────────

    bill_generated = {
        NotificationChannel.email: {
            "subject": "Invoice from {{ clinic_name }}",
            "body": (
                "Dear {{ patient_name }},\n\n"
                "An invoice has been generated for your recent visit.\n\n"
                "Bill ID: {{ bill_id }}\n"
                "Amount: {{ bill_amount }}\n"
                "Clinic: {{ clinic_name }}\n\n"
                "You can view and pay the invoice from your patient portal.\n\n"
                "Thank you,\n"
                "{{ clinic_name }}"
            ),
        },
        NotificationChannel.sms: {
            "body": (
                "Invoice generated: {{ bill_amount }}. "
                "Bill ID: {{ bill_id }}. "
                "Pay via patient portal. – {{ clinic_name }}"
            ),
        },
        NotificationChannel.in_app: {
            "subject": "New Invoice",
            "body": (
                "An invoice of {{ bill_amount }} has been generated. "
                "Bill ID: {{ bill_id }}."
            ),
        },
    }

    # ── Payment Received ────────────────────────────────────────────────

    payment_received = {
        NotificationChannel.email: {
            "subject": "Payment Received – {{ clinic_name }}",
            "body": (
                "Dear {{ patient_name }},\n\n"
                "We have received your payment.\n\n"
                "Amount: {{ bill_amount }}\n"
                "Payment Method: {{ payment_method }}\n"
                "Bill ID: {{ bill_id }}\n"
                "Clinic: {{ clinic_name }}\n\n"
                "Thank you for your payment.\n"
                "{{ clinic_name }}"
            ),
        },
        NotificationChannel.sms: {
            "body": (
                "Payment of {{ bill_amount }} received. "
                "Thank you! – {{ clinic_name }}"
            ),
        },
        NotificationChannel.in_app: {
            "subject": "Payment Received",
            "body": (
                "Payment of {{ bill_amount }} via {{ payment_method }} has been received. "
                "Thank you!"
            ),
        },
    }

    # ── Follow-up Reminder ──────────────────────────────────────────────

    follow_up_reminder = {
        NotificationChannel.email: {
            "subject": "Follow-up Reminder – {{ clinic_name }}",
            "body": (
                "Dear {{ patient_name }},\n\n"
                "This is a reminder about your scheduled follow-up.\n\n"
                "Doctor: Dr. {{ doctor_name }}\n"
                "Follow-up Date: {{ follow_up_date }}\n"
                "Clinic: {{ clinic_name }}\n"
                "Phone: {{ clinic_phone }}\n\n"
                "Please contact the clinic if you need to reschedule.\n\n"
                "Thank you,\n"
                "{{ clinic_name }}"
            ),
        },
        NotificationChannel.sms: {
            "body": (
                "Follow-up reminder: Dr. {{ doctor_name }} "
                "on {{ follow_up_date }}. "
                "Contact: {{ clinic_phone }} – {{ clinic_name }}"
            ),
        },
        NotificationChannel.in_app: {
            "subject": "Follow-up Reminder",
            "body": (
                "Reminder: Your follow-up with Dr. {{ doctor_name }} "
                "is scheduled for {{ follow_up_date }}."
            ),
        },
    }


# Map event types to their template definitions
DEFAULT_TEMPLATES: dict[NotificationEventType, dict[NotificationChannel, dict[str, str]]] = {
    NotificationEventType.appointment_booked: DefaultTemplates.appointment_booked,
    NotificationEventType.appointment_reminder: DefaultTemplates.appointment_reminder,
    NotificationEventType.appointment_completed: DefaultTemplates.appointment_completed,
    NotificationEventType.prescription_ready: DefaultTemplates.prescription_ready,
    NotificationEventType.bill_generated: DefaultTemplates.bill_generated,
    NotificationEventType.payment_received: DefaultTemplates.payment_received,
    NotificationEventType.follow_up_reminder: DefaultTemplates.follow_up_reminder,
}


# ═════════════════════════════════════════════════════════════════════════════
# Template Rendering
# ═════════════════════════════════════════════════════════════════════════════


def render_template(
    template_body: str,
    context: dict[str, Any],
) -> str:
    """
    Render a template by replacing placeholders with context values.

    Unresolved placeholders are left as-is for debugging visibility.

    Args:
        template_body: Template string with {{ placeholder }} markers.
        context: Dict mapping placeholder names to values.

    Returns:
        Rendered string with placeholders replaced.
    """
    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        value = context.get(key)
        if value is None:
            logger.warning("Unresolved placeholder: {{ %s }}", key)
            return match.group(0)  # Leave unresolved for debugging
        return str(value)

    return PLACEHOLDER_PATTERN.sub(_replacer, template_body)


def render_subject(
    template_subject: str | None,
    context: dict[str, Any],
) -> str | None:
    """
    Render a subject template by replacing placeholders.

    Args:
        template_subject: Subject template string or None.
        context: Dict mapping placeholder names to values.

    Returns:
        Rendered subject string, or None if input was None.
    """
    if template_subject is None:
        return None
    return render_template(template_subject, context)


def get_default_template(
    event_type: NotificationEventType,
    channel: NotificationChannel,
) -> dict[str, str] | None:
    """
    Get the default template for an event type and channel.

    Args:
        event_type: The notification event type.
        channel: The delivery channel.

    Returns:
        Dict with 'subject' (optional) and 'body' keys, or None if not found.
    """
    event_templates = DEFAULT_TEMPLATES.get(event_type)
    if event_templates is None:
        return None
    return event_templates.get(channel)


def get_available_placeholders() -> dict[str, str]:
    """
    Get all available placeholders with descriptions.

    Returns:
        Dict mapping placeholder names to descriptions.
    """
    return {
        "patient_name": "Patient's full name",
        "doctor_name": "Doctor's full name",
        "appointment_time": "Formatted appointment date and time",
        "clinic_name": "Tenant/clinic organization name",
        "clinic_phone": "Tenant phone number",
        "clinic_address": "Tenant formatted address",
        "bill_amount": "Formatted bill amount with currency",
        "bill_id": "Bill reference ID",
        "payment_method": "Payment method used",
        "follow_up_date": "Follow-up appointment date",
        "prescription_link": "Link to view prescription (future)",
    }
