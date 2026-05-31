"""
Central helpers so appointment mutations always re-check doctor/tenant alignment after writes.

Prefer calling ``revalidate_appointment_invariants`` on the persisted row before returning from
service-layer mutation APIs (update, delete-as-intent-check, post-commit completion, etc.).

Use ``AppointmentInvariantGuard.finalize`` before returning ``Appointment`` from mutations so new
paths do not skip a post-write invariant check (see Cursor rule appointment-invariants).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.services import doctor_service
from app.services.appointment_invariants import validate_appointment_invariants


def revalidate_appointment_invariants(db: Session, appointment: Appointment) -> None:
    """Load the assigned doctor and enforce the same invariants as billing/inventory paths."""
    doctor = doctor_service.get_doctor_or_404(db, appointment.doctor_id)
    validate_appointment_invariants(appointment, doctor)


class AppointmentInvariantGuard:
    """Single entry point post-commit/load for mutations that alter an appointment row."""

    @staticmethod
    def finalize(db: Session, appointment_id: UUID) -> Appointment:
        """Load the refreshed row and enforce invariants (raises if incompatible)."""
        from app.crud import crud_appointment
        from app.services.exceptions import NotFoundError

        row = crud_appointment.get_appointment(db, appointment_id)
        if row is None:
            raise NotFoundError("Appointment not found")
        revalidate_appointment_invariants(db, row)
        return row
