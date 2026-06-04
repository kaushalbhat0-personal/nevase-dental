"""
Reporting service — READ-ONLY derived aggregates for financial reporting.

Billing remains the source-of-truth for patient charges.
Inventory movements remain the source-of-truth for stock history.
Reporting is READ-MODEL driven — no transactional tables are overloaded.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.data_scope import DataScopeKind, ResolvedDataScope
from app.core.permissions import has_tenant_admin_privileges
from app.crud import crud_billing
from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Billing, BillingStatus
from app.models.doctor import Doctor
from app.models.inventory import (
    AppointmentInventoryUsage,
    InventoryItem,
    InventoryMovement,
    InventoryMovementType,
)
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.reporting import (
    BillingReportAggregate,
    BillingReportFilter,
    BillingReportResult,
    InventoryLedgerFilter,
    InventoryLedgerResult,
    InventoryLedgerRow,
    PatientBillSummary,
    PatientEncounterRef,
    PatientFinancialLedger,
)
from app.services import doctor_service, patient_service
from app.services.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.services.security_audit import (
    assert_authorized,
    log_audit_mutation,
    log_rbac_mutation_violation,
    log_structured_audit_event,
)

logger = logging.getLogger(__name__)


# ── Authorization helpers ────────────────────────────────────────────────────


def _authorize_report_access(
    db: Session,
    current_user: User,
    tenant_id: UUID | None,
    data_scope: ResolvedDataScope | None = None,
    *,
    rbac_action: str = "view_report",
) -> UUID | None:
    """
    Authorize access to tenant-scoped reports.

    Returns the effective tenant_id for the query.
    Raises ForbiddenError if the user has no access.
    """
    if current_user.role == UserRole.patient:
        log_rbac_mutation_violation(current_user, "reporting", action=rbac_action)
        raise ForbiddenError("Patients cannot access reports")

    if tenant_id is None:
        raise ValidationError("Tenant context is required for reports")

    if current_user.role == UserRole.super_admin:
        return tenant_id

    assert_authorized(
        "read",
        "reporting",
        current_user,
        tenant_id,
        resource_tenant_id=tenant_id,
    )

    # For doctor role, verify they belong to this tenant
    if current_user.role == UserRole.doctor:
        doc = doctor_service.get_current_doctor(db, current_user)
        if doc.tenant_id != tenant_id:
            log_rbac_mutation_violation(
                current_user, "reporting", action=rbac_action
            )
            raise ForbiddenError("Doctor does not belong to this organization")

    return tenant_id


def _get_effective_doctor_scope(
    db: Session,
    current_user: User,
    data_scope: ResolvedDataScope | None,
    tenant_id: UUID | None,
) -> UUID | None:
    """
    Returns a doctor_id to restrict queries to, or None for full tenant scope.

    - Admin/staff/super_admin: uses data_scope restriction if present
    - Doctor (non-owner): always restricted to their own doctor_id
    - Doctor (owner): uses data_scope or full tenant
    """
    if current_user.role == UserRole.doctor:
        doc = doctor_service.get_current_doctor(db, current_user)
        if current_user.is_owner and (
            data_scope is None or data_scope.kind == DataScopeKind.tenant
        ):
            return None  # Owner can see full tenant
        return doc.id

    if data_scope is not None and data_scope.kind == DataScopeKind.doctor:
        return data_scope.doctor_id

    return None


# ── Billing Report ───────────────────────────────────────────────────────────


def _compute_inventory_amounts(
    db: Session, bill_ids: list[UUID]
) -> dict[UUID, Decimal]:
    """
    Compute sum(qty × item.selling_price) for each bill's appointment inventory usage.

    Returns dict mapping bill_id -> inventory_amount.
    """
    if not bill_ids:
        return {}

    # Get bills with their appointment_ids
    bill_appt = (
        select(Billing.id, Billing.appointment_id)
        .where(Billing.id.in_(bill_ids), Billing.appointment_id.isnot(None))
    )
    bill_appt_map = {row.id: row.appointment_id for row in db.execute(bill_appt).all()}

    if not bill_appt_map:
        return {}

    appt_ids = list(bill_appt_map.values())

    # Sum inventory usage per appointment
    stmt = (
        select(
            AppointmentInventoryUsage.appointment_id,
            func.sum(
                AppointmentInventoryUsage.quantity * InventoryItem.selling_price
            ).label("total"),
        )
        .join(
            InventoryItem,
            InventoryItem.id == AppointmentInventoryUsage.item_id,
        )
        .where(AppointmentInventoryUsage.appointment_id.in_(appt_ids))
        .group_by(AppointmentInventoryUsage.appointment_id)
    )

    appt_inv_map: dict[UUID, Decimal] = {}
    for row in db.execute(stmt):
        appt_inv_map[row.appointment_id] = Decimal(str(row.total or "0.00"))

    # Map back to bill_ids
    result: dict[UUID, Decimal] = {}
    for bill_id, appt_id in bill_appt_map.items():
        result[bill_id] = appt_inv_map.get(appt_id, Decimal("0.00"))

    return result


def get_billing_report(
    db: Session,
    current_user: User,
    tenant_id: UUID | None,
    filters: BillingReportFilter,
    *,
    data_scope: ResolvedDataScope | None = None,
) -> BillingReportResult:
    """
    Get paginated billing report with filters.

    Returns BillingReportResult with items and total count.
    """
    eff_tenant_id = _authorize_report_access(
        db, current_user, tenant_id, data_scope, rbac_action="billing_report_viewed"
    )
    eff_doctor_id = _get_effective_doctor_scope(
        db, current_user, data_scope, eff_tenant_id
    )

    # Build base query
    stmt = (
        select(Billing)
        .where(Billing.is_deleted == False)
        .options(
            joinedload(Billing.patient),
            joinedload(Billing.appointment).joinedload(Appointment.doctor),
        )
    )

    if eff_tenant_id is not None:
        stmt = stmt.where(Billing.tenant_id == eff_tenant_id)

    # Apply filters
    if filters.date_from is not None:
        stmt = stmt.where(Billing.created_at >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(Billing.created_at <= filters.date_to)
    if filters.status is not None:
        stmt = stmt.where(Billing.status == filters.status)
    if filters.patient_id is not None:
        stmt = stmt.where(Billing.patient_id == filters.patient_id)

    # Doctor filter: join through appointment
    if filters.doctor_id is not None or eff_doctor_id is not None:
        doctor_filter = filters.doctor_id or eff_doctor_id
        stmt = stmt.join(Billing.appointment).where(
            Appointment.doctor_id == doctor_filter,
            Appointment.is_deleted == False,
        )

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Apply pagination
    stmt = stmt.order_by(Billing.created_at.desc())
    stmt = stmt.offset(filters.skip).limit(filters.limit)

    bills = list(db.scalars(stmt).unique().all())

    if not bills:
        return BillingReportResult(
            items=[], total=0, skip=filters.skip, limit=filters.limit
        )

    # Compute inventory amounts for all bills with appointments
    bill_ids = [b.id for b in bills]
    inv_amounts = _compute_inventory_amounts(db, bill_ids)

    # Build aggregates
    items: list[BillingReportAggregate] = []
    for bill in bills:
        inv_amt = inv_amounts.get(bill.id, Decimal("0.00"))
        consult_amt = Decimal(str(bill.amount)) - inv_amt
        if consult_amt < Decimal("0.00"):
            consult_amt = Decimal("0.00")

        doctor_name: str | None = None
        appointment_time: datetime | None = None
        if bill.appointment is not None:
            doctor_name = bill.appointment.doctor.name if bill.appointment.doctor else None
            appointment_time = bill.appointment.appointment_time

        items.append(
            BillingReportAggregate(
                bill_id=bill.id,
                patient_id=bill.patient_id,
                patient_name=bill.patient.name if bill.patient else "Unknown",
                doctor_id=bill.appointment.doctor_id if bill.appointment else None,
                doctor_name=doctor_name,
                appointment_id=bill.appointment_id,
                appointment_time=appointment_time,
                tenant_id=bill.tenant_id if bill.tenant_id else eff_tenant_id or UUID(int=0),
                bill_amount=Decimal(str(bill.amount)),
                consultation_amount=consult_amt,
                inventory_amount=inv_amt,
                status=bill.status,
                paid_at=bill.paid_at,
                paid_via=bill.payment_method,
                created_by=bill.created_by,
                created_at=bill.created_at,
            )
        )

    # Log audit event
    log_structured_audit_event(
        event="billing_report_viewed",
        tenant_id=eff_tenant_id,
        resource_id=None,
        actor_id=str(current_user.id),
        filters=filters.model_dump(mode="json", exclude={"skip", "limit"}),
    )

    return BillingReportResult(
        items=items, total=total, skip=filters.skip, limit=filters.limit
    )


def get_billing_aggregate(
    db: Session,
    bill_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
) -> BillingReportAggregate:
    """Load a single billing aggregate by bill_id with related appointment/patient/doctor data."""
    bill = (
        db.query(Billing)
        .options(
            joinedload(Billing.patient),
            joinedload(Billing.appointment)
            .joinedload(Appointment.doctor)
            .joinedload(Doctor.structured_profile),
        )
        .filter(Billing.id == bill_id, Billing.is_deleted == False)
        .first()
    )
    if bill is None:
        raise NotFoundError("Bill not found")

    doctor_name: str | None = None
    doctor_specialization: str | None = None
    appointment_time: datetime | None = None
    tenant_name: str | None = None
    if bill.appointment is not None:
        doctor_name = bill.appointment.doctor.name if bill.appointment.doctor else None
        sp = bill.appointment.doctor.structured_profile if bill.appointment.doctor else None
        doctor_specialization = sp.specialization if sp else None
        appointment_time = bill.appointment.appointment_time
        if bill.appointment.tenant_id:
            from app.models.tenant import Tenant
            t = db.get(Tenant, bill.appointment.tenant_id)
            tenant_name = t.name if t else None

    inv_amounts = _compute_inventory_amounts(db, [bill_id])
    inv_amt = inv_amounts.get(bill_id, Decimal("0.00"))
    consult_amt = Decimal(str(bill.amount)) - inv_amt
    if consult_amt < Decimal("0.00"):
        consult_amt = Decimal("0.00")

    inventory_items: list[dict] = []
    if bill.appointment:
        from app.models.inventory import AppointmentInventoryUsage, InventoryItem
        usages = (
            db.query(AppointmentInventoryUsage)
            .options(joinedload(AppointmentInventoryUsage.item))
            .filter(AppointmentInventoryUsage.appointment_id == bill.appointment.id)
            .all()
        )
        inventory_items = [
            {
                "item_name": u.item.name if u.item else "Unknown",
                "quantity": u.quantity_used,
                "unit_price": float(u.unit_price) if u.unit_price else 0,
                "total_price": float(u.total_price) if u.total_price else 0,
            }
            for u in usages
        ]

    return BillingReportAggregate(
        bill_id=bill.id,
        patient_id=bill.patient_id,
        patient_name=bill.patient.name if bill.patient else "Unknown",
        doctor_id=bill.appointment.doctor_id if bill.appointment else None,
        doctor_name=doctor_name,
        doctor_specialization=doctor_specialization,
        appointment_id=bill.appointment_id,
        appointment_time=appointment_time,
        tenant_id=bill.tenant_id if bill.tenant_id else tenant_id or UUID(int=0),
        tenant_name=tenant_name,
        bill_amount=Decimal(str(bill.amount)),
        consultation_amount=consult_amt,
        inventory_amount=inv_amt,
        inventory_items=inventory_items,
        status=bill.status,
        paid_at=bill.paid_at,
        paid_via=bill.payment_method,
        created_by=bill.created_by,
        created_at=bill.created_at,
    )


# ── Inventory Ledger ─────────────────────────────────────────────────────────


def get_inventory_ledger(
    db: Session,
    current_user: User,
    tenant_id: UUID | None,
    filters: InventoryLedgerFilter,
    *,
    data_scope: ResolvedDataScope | None = None,
) -> InventoryLedgerResult:
    """
    Get paginated inventory movement ledger with running stock.

    Running stock is computed via SQL window function for accuracy.
    """
    eff_tenant_id = _authorize_report_access(
        db,
        current_user,
        tenant_id,
        data_scope,
        rbac_action="inventory_ledger_viewed",
    )

    # Build base query — join through item to get tenant scope
    stmt = (
        select(
            InventoryMovement,
            InventoryItem.name,
            InventoryItem.type,
        )
        .join(InventoryItem, InventoryItem.id == InventoryMovement.item_id)
        .where(InventoryItem.tenant_id == eff_tenant_id)
    )

    # Apply filters
    if filters.date_from is not None:
        stmt = stmt.where(InventoryMovement.created_at >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(InventoryMovement.created_at <= filters.date_to)
    if filters.item_id is not None:
        stmt = stmt.where(InventoryMovement.item_id == filters.item_id)
    if filters.movement_type is not None:
        stmt = stmt.where(InventoryMovement.type == filters.movement_type)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Apply pagination
    stmt = stmt.order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc())
    stmt = stmt.offset(filters.skip).limit(filters.limit)

    rows = db.execute(stmt).all()

    if not rows:
        return InventoryLedgerResult(
            items=[], total=0, skip=filters.skip, limit=filters.limit
        )

    # Compute running stock for each item using window function
    # We need to get all movements up to each movement's timestamp for the same item
    movement_ids = [r.InventoryMovement.id for r in rows]
    item_ids = list({r.InventoryMovement.item_id for r in rows})

    # Build running stock via subquery for each item
    running_stock_map: dict[UUID, int] = {}

    for item_id in item_ids:
        # Get all movements for this item up to the latest in our result set
        item_movements = (
            select(
                InventoryMovement.id,
                case(
                    (InventoryMovement.type == InventoryMovementType.IN, InventoryMovement.quantity),
                    (InventoryMovement.type == InventoryMovementType.OUT, -InventoryMovement.quantity),
                    else_=InventoryMovement.quantity,
                ).label("signed_qty"),
                func.sum(
                    case(
                        (InventoryMovement.type == InventoryMovementType.IN, InventoryMovement.quantity),
                        (InventoryMovement.type == InventoryMovementType.OUT, -InventoryMovement.quantity),
                        else_=InventoryMovement.quantity,
                    )
                ).over(
                    order_by=[InventoryMovement.created_at, InventoryMovement.id],
                    rows=(None, 0),  # ROWS UNBOUNDED PRECEDING to current row
                ).label("running"),
            )
            .where(InventoryMovement.item_id == item_id)
            .order_by(InventoryMovement.created_at, InventoryMovement.id)
        )
        for mov_row in db.execute(item_movements).all():
            if mov_row.id in movement_ids:
                running_stock_map[mov_row.id] = int(mov_row.running)

    # Build ledger rows
    items: list[InventoryLedgerRow] = []
    for row in rows:
        movement = row.InventoryMovement
        signed_qty: int = movement.quantity
        if movement.type == InventoryMovementType.OUT:
            signed_qty = -movement.quantity

        encounter_id: UUID | None = None
        if movement.reference_type == "APPOINTMENT" and movement.reference_id is not None:
            encounter_id = movement.reference_id

        items.append(
            InventoryLedgerRow(
                movement_id=movement.id,
                item_id=movement.item_id,
                item_name=row.name,
                item_type=row.type,
                movement_type=movement.type,
                quantity=signed_qty,
                running_stock=running_stock_map.get(movement.id, 0),
                doctor_id=movement.doctor_id,
                billing_id=movement.billing_id,
                encounter_id=encounter_id,
                actor_id=movement.created_by,
                actor_role=movement.created_by_role,
                created_at=movement.created_at,
            )
        )

    # Log audit event
    log_structured_audit_event(
        event="inventory_ledger_viewed",
        tenant_id=eff_tenant_id,
        resource_id=None,
        actor_id=str(current_user.id),
        filters=filters.model_dump(mode="json", exclude={"skip", "limit"}),
    )

    return InventoryLedgerResult(
        items=items, total=total, skip=filters.skip, limit=filters.limit
    )


# ── Patient Financial Ledger ─────────────────────────────────────────────────


def _authorize_patient_financial_access(
    db: Session,
    current_user: User,
    patient_id: UUID,
    tenant_id: UUID | None,
    data_scope: ResolvedDataScope | None = None,
) -> UUID:
    """
    Authorize access to a patient's financial ledger.

    - Patients can only view their own ledger
    - Doctors can view their own patients
    - Admin/staff can view any patient in their tenant
    - super_admin can view any patient
    """
    if current_user.role == UserRole.patient:
        try:
            acting_patient = patient_service.get_patient_by_user_id(db, current_user.id)
        except NotFoundError:
            raise ForbiddenError("Patient profile not found")
        if acting_patient.id != patient_id:
            raise ForbiddenError("Not allowed to access this patient's financials")
        return acting_patient.tenant_id or UUID(int=0)

    if tenant_id is None:
        raise ValidationError("Tenant context is required")

    if current_user.role == UserRole.super_admin:
        return tenant_id

    assert_authorized(
        "read",
        "patient_financial",
        current_user,
        tenant_id,
        resource_tenant_id=tenant_id,
    )

    # Verify patient belongs to this tenant
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise NotFoundError("Patient not found")
    if patient.tenant_id is not None and patient.tenant_id != tenant_id:
        raise ForbiddenError("Patient does not belong to this organization")

    # Doctor scope: verify patient relationship
    if current_user.role == UserRole.doctor:
        doc = doctor_service.get_current_doctor(db, current_user)
        if doc.tenant_id != tenant_id:
            raise ForbiddenError("Doctor does not belong to this organization")
        # Verify doctor has an appointment with this patient
        has_relationship = db.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.doctor_id == doc.id,
                Appointment.patient_id == patient_id,
                Appointment.is_deleted == False,
            )
        )
        if not has_relationship:
            raise ForbiddenError("Not allowed to access this patient's financials")

    return tenant_id


def get_patient_financial_ledger(
    db: Session,
    current_user: User,
    patient_id: UUID,
    tenant_id: UUID | None,
    *,
    data_scope: ResolvedDataScope | None = None,
) -> PatientFinancialLedger:
    """
    Get full financial ledger for a patient — all bills, payments, balances, encounters.
    """
    eff_tenant_id = _authorize_patient_financial_access(
        db, current_user, patient_id, tenant_id, data_scope
    )

    patient = db.get(Patient, patient_id)
    if patient is None:
        raise NotFoundError("Patient not found")

    # Get all non-deleted bills for this patient
    bills_stmt = (
        select(Billing)
        .where(
            Billing.patient_id == patient_id,
            Billing.is_deleted == False,
        )
        .order_by(Billing.created_at.desc())
    )
    if eff_tenant_id is not None and current_user.role != UserRole.patient:
        bills_stmt = bills_stmt.where(Billing.tenant_id == eff_tenant_id)

    bills = list(db.scalars(bills_stmt).all())

    # Compute aggregates
    total_billed = Decimal("0.00")
    total_paid = Decimal("0.00")
    total_unpaid = Decimal("0.00")
    last_payment_at: datetime | None = None
    bill_summaries: list[PatientBillSummary] = []

    for bill in bills:
        amt = Decimal(str(bill.amount))
        total_billed += amt
        if bill.status == BillingStatus.paid:
            total_paid += amt
            if bill.paid_at is not None and (
                last_payment_at is None or bill.paid_at > last_payment_at
            ):
                last_payment_at = bill.paid_at
        else:
            total_unpaid += amt

        bill_summaries.append(
            PatientBillSummary(
                bill_id=bill.id,
                appointment_id=bill.appointment_id,
                amount=amt,
                status=bill.status,
                paid_at=bill.paid_at,
                created_at=bill.created_at,
            )
        )

    balance = total_billed - total_paid

    # Get encounters (appointments) for this patient
    encounters_stmt = (
        select(Appointment)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.is_deleted == False,
        )
        .options(joinedload(Appointment.doctor))
        .order_by(Appointment.appointment_time.desc())
    )
    if eff_tenant_id is not None and current_user.role != UserRole.patient:
        encounters_stmt = encounters_stmt.where(Appointment.tenant_id == eff_tenant_id)

    appointments = list(db.scalars(encounters_stmt).unique().all())

    # Build set of appointment_ids that have bills
    billed_appt_ids = {b.appointment_id for b in bills if b.appointment_id is not None}

    encounter_refs: list[PatientEncounterRef] = []
    for appt in appointments:
        encounter_refs.append(
            PatientEncounterRef(
                appointment_id=appt.id,
                appointment_time=appt.appointment_time,
                doctor_name=appt.doctor.name if appt.doctor else "Unknown",
                has_bill=appt.id in billed_appt_ids,
            )
        )

    return PatientFinancialLedger(
        patient_id=patient_id,
        patient_name=patient.name,
        total_billed=total_billed,
        total_paid=total_paid,
        total_unpaid=total_unpaid,
        balance=balance,
        last_payment_at=last_payment_at,
        bills=bill_summaries,
        encounters=encounter_refs,
    )
