import logging
from datetime import datetime, timezone
from uuid import UUID

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.data_scope import DataScopeKind, ResolvedDataScope
from app.core.permissions import has_tenant_admin_privileges
from app.core.tenant_context import align_operation_tenant_with_resource
from app.core.tenancy import non_nil_tenant_id
from app.crud import crud_billing
from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Billing, BillingStatus
from app.models.inventory import AppointmentInventoryUsage, InventoryItem
from app.models.user import User, UserRole
from app.schemas.billing import BillingCreate, BillingEventRead, BillingUpdate
from app.services import appointment_service, doctor_service, patient_service
from app.services.appointment_invariants import validate_appointment_invariants
from app.services.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.services.security_audit import (
    assert_authorized,
    enforce_tenant_match,
    log_audit_mutation,
    log_rbac_mutation_violation,
)

logger = logging.getLogger(__name__)


def _inventory_selling_addon_for_appointment(
    db: Session, appointment_id: UUID
) -> tuple[Decimal, str]:
    stmt = (
        select(
            AppointmentInventoryUsage.quantity,
            InventoryItem.selling_price,
            InventoryItem.name,
        )
        .join(InventoryItem, InventoryItem.id == AppointmentInventoryUsage.item_id)
        .where(AppointmentInventoryUsage.appointment_id == appointment_id)
    )
    total = Decimal("0.00")
    parts: list[str] = []
    for qty, sell, name in db.execute(stmt):
        sub = (Decimal(str(sell)) * int(qty)).quantize(Decimal("0.01"))
        total += sub
        parts.append(f"{name} × {int(qty)} → ₹{sub}")
    return total, "; ".join(parts)[:450]


def appointment_inventory_materials_selling_total(
    db: Session, appointment_id: UUID
) -> Decimal:
    """Sum of ``quantity × selling_price`` for inventory tied to a completed visit (billing parity)."""
    total, _ = _inventory_selling_addon_for_appointment(db, appointment_id)
    return total


def _validate_appointment_completed_for_billing(appointment: Appointment) -> None:
    if appointment.status != AppointmentStatus.completed:
        logger.warning(
            "Billing blocked: appointment not completed",
            extra={
                "appointment_id": str(appointment.id),
                "status": appointment.status.value if appointment.status else None,
            },
        )
        raise ValidationError("Only completed visits can be billed")


def _validate_appointment_exists(db: Session, appointment_id: UUID) -> None:
    appointment_service.get_appointment_or_404(db, appointment_id)


def _validate_appointment_not_cancelled(db: Session, appointment_id: UUID) -> None:
    appointment = appointment_service.get_appointment_or_404(db, appointment_id)
    if appointment.status == AppointmentStatus.cancelled:
        raise ValidationError("Cannot create bill for cancelled appointment")


def _validate_no_duplicate_bill(db: Session, appointment_id: UUID) -> None:
    existing_bill = crud_billing.get_bill_by_appointment(db, appointment_id)
    if existing_bill is not None:
        raise ValidationError("Bill already exists for this appointment")


def _validate_idempotency_key(db: Session, idempotency_key: str | None) -> None:
    if idempotency_key is None:
        return
    existing_bill = crud_billing.get_bill_by_idempotency_key(db, idempotency_key)
    if existing_bill is not None:
        raise ConflictError("Request with this idempotency key already processed")


def _validate_patient_matches_appointment(
    db: Session,
    patient_id: UUID,
    appointment_id: UUID | None,
) -> None:
    if appointment_id is None:
        return
    appointment = appointment_service.get_appointment_or_404(db, appointment_id)
    if appointment.patient_id != patient_id:
        raise ValidationError("Patient ID does not match appointment's patient")


def _validate_status_regression(
    existing_status: BillingStatus,
    new_status: BillingStatus | None,
) -> None:
    if existing_status == BillingStatus.paid and new_status is not None:
        if new_status != BillingStatus.paid:
            raise ValidationError("Paid bill status cannot be reverted")


def _validate_not_already_paid(existing_status: BillingStatus) -> None:
    if existing_status == BillingStatus.paid:
        raise ValidationError("Bill already paid")


def authorize_bill_create(
    db: Session,
    billing_in: BillingCreate,
    current_user: User,
    tenant_id: UUID | None,
) -> None:
    if current_user.role == UserRole.patient:
        log_rbac_mutation_violation(current_user, "billing")
        raise ForbiddenError("Patients cannot create bills")

    if (
        current_user.role == UserRole.doctor
        and not current_user.is_owner
        and billing_in.appointment_id is None
    ):
        log_rbac_mutation_violation(current_user, "billing")
        raise ForbiddenError("Doctors must create bills with an appointment")

    if billing_in.appointment_id is None:
        if current_user.role not in (
            UserRole.admin,
            UserRole.super_admin,
        ) and not (current_user.role == UserRole.doctor and current_user.is_owner):
            log_rbac_mutation_violation(current_user, "billing")
            raise ForbiddenError(
                "Bills without an appointment can only be created by administrators or practice owners"
            )
        return

    appointment = appointment_service.get_appointment_or_404(db, billing_in.appointment_id)

    if current_user.role == UserRole.super_admin:
        enforce_tenant_match(
            appointment.tenant_id,
            tenant_id,
            current_user,
            "billing",
        )
        return

    assert_authorized(
        "create",
        "billing",
        current_user,
        tenant_id,
        resource_tenant_id=appointment.tenant_id,
    )

    if current_user.role in (UserRole.admin, UserRole.staff):
        return

    if current_user.role == UserRole.doctor:
        try:
            doc = doctor_service.get_current_doctor(db, current_user)
        except ForbiddenError:
            log_rbac_mutation_violation(
                current_user, "billing", action="create_bill"
            )
            raise
        if appointment.doctor_id != doc.id:
            log_rbac_mutation_violation(
                current_user,
                "billing",
                action="create_bill",
                tenant_type=doc.tenant.type if doc.tenant else None,
            )
            raise ForbiddenError(
                "Cannot create bill for an appointment you are not assigned to"
            )
        return

    log_rbac_mutation_violation(current_user, "billing")
    raise ForbiddenError("Not allowed to create bills")


def create_bill(
    db: Session,
    billing_in: BillingCreate,
    current_user: User,
    tenant_id: UUID | None,
) -> Billing:
    logger.info(f"[RBAC] role={current_user.role}, user={current_user.id}")
    logger.info("[BILLING SERVICE] Creating bill")
    scoped_tenant = tenant_id
    appointment: Appointment | None = None
    if billing_in.appointment_id is not None:
        appointment = appointment_service.get_appointment_or_404(
            db, billing_in.appointment_id
        )
        scoped_tenant = align_operation_tenant_with_resource(
            current_user,
            tenant_id,
            appointment.tenant_id,
        )
        bill_doctor = doctor_service.get_doctor_or_404(db, appointment.doctor_id)
        validate_appointment_invariants(appointment, bill_doctor)

    authorize_bill_create(db, billing_in, current_user, scoped_tenant)

    # Validate patient exists
    try:
        patient_service.get_patient_or_404(db, billing_in.patient_id)
    except NotFoundError:
        logger.warning(
            "Billing failed: patient not found",
            extra={"patient_id": str(billing_in.patient_id)},
        )
        raise ValidationError(f"Patient not found: {billing_in.patient_id}")

    if billing_in.appointment_id is not None:
        assert appointment is not None
        if appointment.patient_id is None:
            logger.warning(
                "Billing failed: missing patient for visit",
                extra={"appointment_id": str(appointment.id)},
            )
            raise ValidationError("Missing patient for this visit")
        req_tid = non_nil_tenant_id(scoped_tenant)
        ap_tid = non_nil_tenant_id(appointment.tenant_id)
        if (
            req_tid is not None
            and ap_tid is not None
            and ap_tid != req_tid
        ):
            logger.warning(
                "Billing failed: invalid tenant access",
                extra={
                    "appointment_id": str(appointment.id),
                    "appointment_tenant_id": str(appointment.tenant_id),
                    "request_tenant_id": str(scoped_tenant),
                },
            )
            raise ForbiddenError("Invalid tenant access")
        _validate_appointment_not_cancelled(db, billing_in.appointment_id)
        _validate_no_duplicate_bill(db, billing_in.appointment_id)
        _validate_patient_matches_appointment(
            db,
            patient_id=billing_in.patient_id,
            appointment_id=billing_in.appointment_id,
        )
        _validate_appointment_completed_for_billing(appointment)
    _validate_idempotency_key(db, billing_in.idempotency_key)

    billing_data = billing_in.model_dump(
        exclude={"include_appointment_inventory_selling_total"},
    )
    billing_data["created_by"] = current_user.id
    if appointment is not None:
        if appointment.tenant_id is None:
            logger.error(
                "[TENANT INTEGRITY] appointment.tenant_id is None for appointment_id=%s",
                appointment.id,
            )
            logger.warning(
                "Billing failed: appointment tenant not set",
                extra={"appointment_id": str(appointment.id)},
            )
            raise ValidationError("Appointment tenant is not set")
        billing_data["tenant_id"] = appointment.tenant_id
    else:
        if scoped_tenant is None:
            raise ValidationError(
                "Tenant must be specified when no appointment is linked"
            )
        billing_data["tenant_id"] = scoped_tenant

    assert_authorized(
        "create",
        "billing",
        current_user,
        scoped_tenant,
        resource_tenant_id=billing_data["tenant_id"],
    )

    if (
        appointment is not None
        and billing_in.appointment_id is not None
        and billing_in.include_appointment_inventory_selling_total
    ):
        inv_total, inv_snip = _inventory_selling_addon_for_appointment(
            db, billing_in.appointment_id
        )
        if inv_total > 0:
            base_amt = Decimal(str(billing_data["amount"]))
            billing_data["amount"] = base_amt + inv_total
            prev = (billing_data.get("description") or "").strip()
            materials = f"[Medicines] {inv_snip}" if inv_snip else "[Medicines]"
            billing_data["description"] = (
                f"{prev}; {materials}"[:500] if prev else materials[:500]
            )

    try:
        bill = crud_billing.create_bill(db, billing_data)
    except IntegrityError as e:
        msg = str(getattr(e, "orig", e))
        msg_compact_lower = msg.lower().replace(" ", "")
        if (
            "uq_billing_active_appointment" in msg
            or "uniq_bill_per_appointment" in msg
            or ("billings.appointment_id" in msg_compact_lower and "unique" in msg_compact_lower)
        ):
            raise ValidationError("Bill already exists for this appointment") from e
        raise
    except Exception as e:
        logger.exception("[BILLING SERVICE] DB ERROR")
        raise

    # Create initial billing event
    crud_billing.create_billing_event(
        db,
        billing_id=bill.id,
        previous_status=None,
        new_status=bill.status.value,
        event_type="created",
        event_metadata=f"Bill created with amount {bill.amount} {bill.currency}",
        created_by=current_user.id,
    )
    log_audit_mutation(
        "create",
        current_user,
        "billing",
        bill.id,
        bill.tenant_id,
    )
    return bill


def get_bill_or_404(db: Session, bill_id: UUID) -> Billing:
    bill = crud_billing.get_bill(db, bill_id)
    if bill is None:
        raise NotFoundError("Bill not found")
    return bill


def get_bills(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 10,
    patient_id: UUID | None = None,
    appointment_id: UUID | None = None,
    status: BillingStatus | None = None,
    tenant_id: UUID | None = None,
    *,
    data_scope: ResolvedDataScope,
) -> list[Billing]:
    if current_user.role not in (
        UserRole.admin,
        UserRole.super_admin,
        UserRole.doctor,
        UserRole.patient,
        UserRole.staff,
    ):
        log_rbac_mutation_violation(current_user, "billing")
        raise ForbiddenError("Not authorized")
    logger.info(f"[RBAC] role={current_user.role}, user={current_user.id}")
    eff_patient_id = patient_id
    eff_doctor_id: UUID | None = None
    eff_user_id: UUID | None = None
    eff_tenant_id = tenant_id

    if current_user.role == UserRole.doctor:
        if (
            data_scope.kind == DataScopeKind.tenant
            and has_tenant_admin_privileges(current_user)
        ):
            eff_doctor_id = None
            eff_patient_id = None
        else:
            doc = doctor_service.get_current_doctor(db, current_user)
            eff_doctor_id = doc.id
            eff_patient_id = None
    elif current_user.role == UserRole.patient:
        eff_user_id = current_user.id
        eff_patient_id = None
    elif current_user.role in (UserRole.admin, UserRole.super_admin, UserRole.staff):
        if (
            data_scope.kind == DataScopeKind.doctor
            and data_scope.doctor_id is not None
        ):
            eff_doctor_id = data_scope.doctor_id

    rows = crud_billing.get_bills(
        db,
        skip=skip,
        limit=limit,
        patient_id=eff_patient_id,
        appointment_id=appointment_id,
        status=status,
        doctor_id=eff_doctor_id,
        tenant_id=eff_tenant_id,
        user_id=eff_user_id,
    )
    logger.info(
        "[BILLING_SCOPE] scope=%s eff_doctor_id=%s tenant_id=%s user=%s returned=%d",
        data_scope.kind.value,
        eff_doctor_id,
        eff_tenant_id,
        current_user.id,
        len(rows),
    )
    return rows


def authorize_bill_read(
    db: Session,
    bill: Billing,
    current_user: User,
    tenant_id: UUID | None,
    *,
    rbac_action: str = "read_bill",
    restrict_to_doctor_id: UUID | None = None,
) -> None:
    if current_user.role == UserRole.super_admin:
        if restrict_to_doctor_id is not None:
            if bill.appointment_id is None:
                log_rbac_mutation_violation(
                    current_user, "billing", action=rbac_action
                )
                raise ForbiddenError("Not allowed to access this bill")
            appointment = appointment_service.get_appointment_or_404(
                db, bill.appointment_id
            )
            if appointment.doctor_id != restrict_to_doctor_id:
                log_rbac_mutation_violation(
                    current_user, "billing", action=rbac_action
                )
                raise ForbiddenError("Not allowed to access this bill")
        return

    if current_user.role == UserRole.patient:
        try:
            acting_patient = patient_service.get_patient_by_user_id(db, current_user.id)
        except NotFoundError:
            log_rbac_mutation_violation(current_user, "billing")
            raise ForbiddenError("Patient profile not found for this user")
        if bill.patient_id != acting_patient.id:
            log_rbac_mutation_violation(current_user, "billing")
            raise ForbiddenError("Not allowed to access this bill")
        return

    assert_authorized(
        "read",
        "billing",
        current_user,
        tenant_id,
        resource_tenant_id=bill.tenant_id,
    )

    if current_user.role in (UserRole.admin, UserRole.staff):
        if restrict_to_doctor_id is not None:
            if bill.appointment_id is None:
                log_rbac_mutation_violation(
                    current_user, "billing", action=rbac_action
                )
                raise ForbiddenError("Not allowed to access this bill")
            appointment = appointment_service.get_appointment_or_404(
                db, bill.appointment_id
            )
            if appointment.doctor_id != restrict_to_doctor_id:
                log_rbac_mutation_violation(
                    current_user, "billing", action=rbac_action
                )
                raise ForbiddenError("Not allowed to access this bill")
        return

    if current_user.role == UserRole.doctor:
        if bill.appointment_id is None:
            log_rbac_mutation_violation(
                current_user, "billing", action=rbac_action
            )
            raise ForbiddenError("Not allowed to access this bill")
        appointment = appointment_service.get_appointment_or_404(db, bill.appointment_id)
        doc = doctor_service.get_current_doctor(db, current_user)
        if appointment.doctor_id != doc.id:
            log_rbac_mutation_violation(
                current_user,
                "billing",
                action=rbac_action,
                tenant_type=doc.tenant.type if doc.tenant else None,
            )
            raise ForbiddenError("Not allowed to access this bill")
        if (
            restrict_to_doctor_id is not None
            and appointment.doctor_id != restrict_to_doctor_id
        ):
            log_rbac_mutation_violation(
                current_user, "billing", action=rbac_action
            )
            raise ForbiddenError("Not allowed to access this bill")
        return

    log_rbac_mutation_violation(current_user, "billing", action=rbac_action)
    raise ForbiddenError("Not allowed to access this bill")


def authorize_bill_mutate(
    db: Session,
    bill: Billing,
    current_user: User,
    tenant_id: UUID | None,
    *,
    rbac_action: str = "mutate_bill",
    restrict_to_doctor_id: UUID | None = None,
) -> None:
    if current_user.role == UserRole.patient:
        log_rbac_mutation_violation(current_user, "billing")
        raise ForbiddenError("Patients cannot modify bills")

    if current_user.role == UserRole.super_admin:
        if restrict_to_doctor_id is not None:
            if bill.appointment_id is None:
                log_rbac_mutation_violation(
                    current_user, "billing", action=rbac_action
                )
                raise ForbiddenError("Not allowed to access this bill")
            appointment = appointment_service.get_appointment_or_404(
                db, bill.appointment_id
            )
            if appointment.doctor_id != restrict_to_doctor_id:
                log_rbac_mutation_violation(
                    current_user, "billing", action=rbac_action
                )
                raise ForbiddenError("Not allowed to access this bill")
        return

    assert_authorized(
        "mutate",
        "billing",
        current_user,
        tenant_id,
        resource_tenant_id=bill.tenant_id,
    )

    if bill.appointment_id is None and current_user.role not in (
        UserRole.admin,
        UserRole.super_admin,
    ) and not (current_user.role == UserRole.doctor and current_user.is_owner):
        log_rbac_mutation_violation(current_user, "billing")
        raise ForbiddenError("Only administrators may modify bills without an appointment")

    if current_user.role in (UserRole.admin, UserRole.staff):
        if restrict_to_doctor_id is not None:
            if bill.appointment_id is None:
                log_rbac_mutation_violation(
                    current_user, "billing", action=rbac_action
                )
                raise ForbiddenError("Not allowed to access this bill")
            appointment = appointment_service.get_appointment_or_404(
                db, bill.appointment_id
            )
            if appointment.doctor_id != restrict_to_doctor_id:
                log_rbac_mutation_violation(
                    current_user, "billing", action=rbac_action
                )
                raise ForbiddenError("Not allowed to access this bill")
        return

    if current_user.role == UserRole.doctor:
        if bill.appointment_id is None:
            log_rbac_mutation_violation(
                current_user, "billing", action=rbac_action
            )
            raise ForbiddenError("Not allowed to access this bill")
        appointment = appointment_service.get_appointment_or_404(db, bill.appointment_id)
        doc = doctor_service.get_current_doctor(db, current_user)
        if appointment.doctor_id != doc.id:
            log_rbac_mutation_violation(
                current_user,
                "billing",
                action=rbac_action,
                tenant_type=doc.tenant.type if doc.tenant else None,
            )
            raise ForbiddenError("Not allowed to access this bill")
        if (
            restrict_to_doctor_id is not None
            and appointment.doctor_id != restrict_to_doctor_id
        ):
            log_rbac_mutation_violation(
                current_user, "billing", action=rbac_action
            )
            raise ForbiddenError("Not allowed to access this bill")
        return

    log_rbac_mutation_violation(current_user, "billing", action=rbac_action)
    raise ForbiddenError("Not allowed to access this bill")


authorize_bill_update = authorize_bill_mutate
authorize_bill_delete = authorize_bill_mutate


def update_bill(
    db: Session,
    bill_id: UUID,
    billing_in: BillingUpdate,
    current_user: User,
    tenant_id: UUID | None,
    *,
    restrict_to_doctor_id: UUID | None = None,
) -> Billing:
    bill = get_bill_or_404(db, bill_id)
    authorize_bill_mutate(
        db,
        bill,
        current_user,
        tenant_id,
        rbac_action="update_bill",
        restrict_to_doctor_id=restrict_to_doctor_id,
    )

    update_data = billing_in.model_dump(exclude_unset=True)
    if not update_data:
        return bill

    new_status = update_data.get("status")
    _validate_status_regression(bill.status, new_status)

    # Prevent double payment
    if new_status == BillingStatus.paid:
        _validate_not_already_paid(bill.status)

    # Auto-set paid_at when status changes to paid
    if new_status == BillingStatus.paid and bill.status != BillingStatus.paid:
        update_data["paid_at"] = datetime.now(timezone.utc)

    new_appointment_id = update_data.get("appointment_id", bill.appointment_id)
    new_patient_id = update_data.get("patient_id", bill.patient_id)

    if "appointment_id" in update_data and new_appointment_id is None:
        if current_user.role not in (
            UserRole.admin,
            UserRole.super_admin,
        ) and not (current_user.role == UserRole.doctor and current_user.is_owner):
            log_rbac_mutation_violation(current_user, "billing")
            raise ForbiddenError("Only administrators may unlink an appointment from a bill")

    if (
        "appointment_id" in update_data
        and new_appointment_id is not None
        and new_appointment_id != bill.appointment_id
    ):
        _validate_appointment_exists(db, new_appointment_id)
        _validate_appointment_not_cancelled(db, new_appointment_id)
        existing_bill = crud_billing.get_bill_by_appointment(db, new_appointment_id)
        if existing_bill is not None and existing_bill.id != bill_id:
            raise ValidationError("Bill already exists for this appointment")

    if new_appointment_id is not None and (
        "patient_id" in update_data or "appointment_id" in update_data
    ):
        _validate_patient_matches_appointment(db, new_patient_id, new_appointment_id)

    if "appointment_id" in update_data and update_data["appointment_id"] is not None:
        linked_appt = appointment_service.get_appointment_or_404(
            db, update_data["appointment_id"]
        )
        update_data["tenant_id"] = linked_appt.tenant_id

    previous_status = bill.status.value
    updated_bill = crud_billing.update_bill(db, bill, update_data)

    # Create billing event if status changed
    if new_status is not None and new_status != previous_status:
        crud_billing.create_billing_event(
            db,
            billing_id=updated_bill.id,
            previous_status=previous_status,
            new_status=new_status.value,
            event_type="status_changed",
            event_metadata=f"Status changed from {previous_status} to {new_status.value}",
            created_by=current_user.id,
        )

    log_audit_mutation(
        "update",
        current_user,
        "billing",
        updated_bill.id,
        updated_bill.tenant_id,
    )
    return updated_bill


def mark_bill_paid(
    db: Session,
    bill_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    payment_method: str | None = None,
    *,
    restrict_to_doctor_id: UUID | None = None,
) -> Billing:
    """
    Mark a bill as paid with optional payment method.
    
    Requirements:
    - Tenant-safe
    - Resource-authoritative
    - Audited
    - Idempotent-safe
    """
    bill = get_bill_or_404(db, bill_id)
    authorize_bill_mutate(
        db,
        bill,
        current_user,
        tenant_id,
        rbac_action="mark_bill_paid",
        restrict_to_doctor_id=restrict_to_doctor_id,
    )

    if bill.status == BillingStatus.paid:
        # Idempotent: already paid
        return bill

    update_data = {
        "status": BillingStatus.paid,
        "paid_at": datetime.now(timezone.utc),
    }
    if payment_method is not None:
        update_data["payment_method"] = payment_method

    previous_status = bill.status.value
    updated_bill = crud_billing.update_bill(db, bill, update_data)

    # Create billing event
    crud_billing.create_billing_event(
        db,
        billing_id=updated_bill.id,
        previous_status=previous_status,
        new_status=BillingStatus.paid.value,
        event_type="mark_bill_paid",
        event_metadata=f"Bill marked as paid{payment_method and f' via {payment_method}' or ''}",
        created_by=current_user.id,
    )

    log_audit_mutation(
        "mark_bill_paid",
        current_user,
        "billing",
        updated_bill.id,
        updated_bill.tenant_id,
    )
    return updated_bill


def get_total_revenue(
    db: Session,
    *,
    tenant_id: UUID | None = None,
) -> float:
    if tenant_id is None:
        return 0.0
    return crud_billing.get_total_revenue(db, tenant_id=tenant_id)


def get_today_revenue(
    db: Session,
    *,
    tenant_id: UUID | None = None,
) -> float:
    if tenant_id is None:
        return 0.0
    return crud_billing.get_today_revenue(db, tenant_id=tenant_id)


def get_pending_payments(
    db: Session, *, tenant_id: UUID | None = None
) -> dict[str, int | float]:
    if tenant_id is None:
        return {"count": 0, "total_amount": 0.0}
    count, total = crud_billing.get_pending_payments(db, tenant_id=tenant_id)
    return {"count": count, "total_amount": total}


def soft_delete_bill(
    db: Session,
    bill_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    *,
    restrict_to_doctor_id: UUID | None = None,
) -> Billing:
    bill = get_bill_or_404(db, bill_id)
    authorize_bill_mutate(
        db,
        bill,
        current_user,
        tenant_id,
        rbac_action="delete_bill",
        restrict_to_doctor_id=restrict_to_doctor_id,
    )

    if bill.is_deleted:
        raise ValidationError("Bill already deleted")

    previous_status = bill.status.value
    updated_bill = crud_billing.update_bill(db, bill, {"is_deleted": True})

    # Create billing event for soft delete
    crud_billing.create_billing_event(
        db,
        billing_id=updated_bill.id,
        previous_status=previous_status,
        new_status=updated_bill.status.value,
        event_type="soft_deleted",
        event_metadata="Bill soft deleted",
        created_by=current_user.id,
    )
    log_audit_mutation(
        "delete",
        current_user,
        "billing",
        updated_bill.id,
        updated_bill.tenant_id,
    )
    return updated_bill


def get_billing_history(
    db: Session,
    bill_id: UUID,
    current_user: User,
    tenant_id: UUID | None,
    skip: int = 0,
    limit: int = 100,
    *,
    restrict_to_doctor_id: UUID | None = None,
) -> list[BillingEventRead]:
    bill = get_bill_or_404(db, bill_id)
    authorize_bill_read(
        db,
        bill,
        current_user,
        tenant_id,
        restrict_to_doctor_id=restrict_to_doctor_id,
    )

    events = crud_billing.get_billing_events(db, bill_id, skip=skip, limit=limit)
    return [BillingEventRead.model_validate(event) for event in events]
