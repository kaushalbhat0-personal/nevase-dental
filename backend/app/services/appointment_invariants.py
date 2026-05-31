"""
Hard invariants linking appointments to their assigned doctors.
Used before writes that touch billing, inventory, or completion.
"""

from __future__ import annotations

import logging

from app.core.tenancy import non_nil_tenant_id
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.services.exceptions import ValidationError

logger = logging.getLogger(__name__)


def validate_appointment_invariants(
    appointment: Appointment,
    doctor: Doctor,
) -> None:
    """Enforce tenant and identity alignment between a visit row and its doctor."""
    if appointment.doctor_id != doctor.id:
        logger.error(
            "[INVARIANT_VIOLATION] appointment.doctor_id=%s mismatches doctor.id=%s (appointment=%s)",
            appointment.doctor_id,
            doctor.id,
            appointment.id,
        )
        raise ValidationError("Appointment does not match the provided doctor identity")

    ap_tid = non_nil_tenant_id(appointment.tenant_id)
    doc_tid = non_nil_tenant_id(doctor.tenant_id)
    if ap_tid is None:
        logger.error(
            "[INVARIANT_VIOLATION] appointment.tenant_id missing appointment_id=%s",
            appointment.id,
        )
        raise ValidationError("Appointment tenant is not set")
    if doc_tid is None:
        logger.error(
            "[INVARIANT_VIOLATION] doctor.tenant_id missing doctor_id=%s",
            doctor.id,
        )
        raise ValidationError("Doctor tenant is not set")
    if ap_tid != doc_tid:
        logger.error(
            "[INVARIANT_VIOLATION] appointment.tenant_id=%s doctor.tenant_id=%s "
            "appointment_id=%s doctor_id=%s",
            ap_tid,
            doc_tid,
            appointment.id,
            doctor.id,
        )
        raise ValidationError(
            "Appointment organization must match the assigned doctor organization"
        )
