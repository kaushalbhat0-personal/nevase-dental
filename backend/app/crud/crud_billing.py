from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.appointment import Appointment
from app.models.billing import Billing, BillingEvent, BillingStatus
from app.models.patient import Patient


def create_bill(db: Session, billing_data: dict[str, Any]) -> Billing:
    bill = Billing(**billing_data)
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def get_bill(db: Session, bill_id: UUID) -> Billing | None:
    stmt = (
        select(Billing)
        .where(Billing.id == bill_id, Billing.is_deleted == False)
        .options(joinedload(Billing.patient))
    )
    return db.scalars(stmt).first()


def get_bill_by_idempotency_key(db: Session, idempotency_key: str) -> Billing | None:
    stmt = select(Billing).where(
        Billing.idempotency_key == idempotency_key,
        Billing.is_deleted == False
    )
    return db.scalars(stmt).first()


def get_bill_by_appointment(db: Session, appointment_id: UUID) -> Billing | None:
    stmt = select(Billing).where(
        Billing.appointment_id == appointment_id,
        Billing.is_deleted == False
    )
    return db.scalars(stmt).first()


def get_bills_by_patient(
    db: Session,
    patient_id: UUID,
    limit: int = 20,
) -> list[Billing]:
    """Get bills for a specific patient, newest first.

    Args:
        db: Database session.
        patient_id: UUID of the patient.
        limit: Maximum number of bills to return (default 20).

    Returns:
        List of Billing objects ordered by created_at descending.
    """
    stmt = (
        select(Billing)
        .where(Billing.patient_id == patient_id)
        .where(Billing.is_deleted == False)
        .order_by(Billing.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_bills(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    patient_id: UUID | None = None,
    appointment_id: UUID | None = None,
    status: BillingStatus | None = None,
    doctor_id: UUID | None = None,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    include_deleted: bool = False,
) -> list[Billing]:
    stmt = (
        select(Billing)
        .order_by(Billing.created_at.desc())
        .options(joinedload(Billing.patient))
    )

    if not include_deleted:
        stmt = stmt.where(Billing.is_deleted == False)
    if patient_id is not None:
        stmt = stmt.where(Billing.patient_id == patient_id)
    if appointment_id is not None:
        stmt = stmt.where(Billing.appointment_id == appointment_id)
    if status is not None:
        stmt = stmt.where(Billing.status == status)
    if doctor_id is not None:
        # Restrict bills to those linked to appointments for this doctor
        stmt = stmt.join(Billing.appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.is_deleted == False,
        )
    if user_id is not None:
        stmt = stmt.join(Billing.patient).where(Patient.user_id == user_id)
    if tenant_id is not None:
        stmt = stmt.where(Billing.tenant_id == tenant_id)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).unique().all())


def update_bill(
    db: Session,
    bill: Billing,
    update_data: dict[str, Any],
) -> Billing:
    for field, value in update_data.items():
        setattr(bill, field, value)

    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def get_total_revenue(db: Session, *, tenant_id: UUID | None = None) -> float:
    stmt = select(func.sum(Billing.amount)).where(
        Billing.status == BillingStatus.paid,
        Billing.is_deleted == False,  # noqa: E712
    )
    if tenant_id is not None:
        stmt = stmt.where(Billing.tenant_id == tenant_id)
    result = db.scalar(stmt)
    return float(result) if result else 0.0


def get_today_revenue(db: Session, *, tenant_id: UUID | None = None) -> float:
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())

    stmt = select(func.sum(Billing.amount)).where(
        Billing.status == BillingStatus.paid,
        Billing.paid_at >= start_of_day,
        Billing.paid_at <= end_of_day,
        Billing.is_deleted == False,  # noqa: E712
    )
    if tenant_id is not None:
        stmt = stmt.where(Billing.tenant_id == tenant_id)
    result = db.scalar(stmt)
    return float(result) if result else 0.0


def get_pending_payments(
    db: Session,
    *,
    tenant_id: UUID | None = None,
) -> tuple[int, float]:
    stmt = select(
        func.count(Billing.id),
        func.coalesce(func.sum(Billing.amount), 0.0),
    ).where(
        Billing.status == BillingStatus.unpaid,
        Billing.is_deleted == False,  # noqa: E712
    )
    if tenant_id is not None:
        stmt = stmt.where(Billing.tenant_id == tenant_id)
    result = db.execute(stmt).first()
    return result[0], float(result[1]) if result[1] else 0.0


def create_billing_event(
    db: Session,
    billing_id: UUID,
    previous_status: str | None,
    new_status: str,
    event_type: str,
    event_metadata: str | None = None,
    created_by: UUID | None = None,
) -> BillingEvent:
    event = BillingEvent(
        billing_id=billing_id,
        previous_status=previous_status,
        new_status=new_status,
        event_type=event_type,
        event_metadata=event_metadata,
        created_by=created_by,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_billing_events(
    db: Session,
    billing_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[BillingEvent]:
    stmt = select(BillingEvent).where(
        BillingEvent.billing_id == billing_id
    ).order_by(BillingEvent.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())
