import logging
from collections import defaultdict
from uuid import UUID

from sqlalchemy import Select, and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.data_scope import DataScopeKind, ResolvedDataScope
from app.core.metrics import inc_counter
from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Billing
from app.models.doctor import Doctor
from app.models.inventory import (
    AppointmentInventoryUsage,
    InventoryItem,
    InventoryItemType,
    InventoryMovement,
    InventoryMovementType,
    InventoryReferenceType,
    InventoryStock,
)
from app.models.user import User, UserRole
from app.services import doctor_service
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryUseLine,
    StockAddRequest,
    StockAdjustRequest,
    StockReduceRequest,
)
from app.core.tenant_context import MISSING_X_TENANT_ID_MSG
from app.core.clinical_capabilities import has_clinician_capability

from app.services.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.services.security_audit import (
    assert_authorized,
    log_audit_mutation,
    log_rbac_mutation_violation,
)

logger = logging.getLogger(__name__)


def effective_inventory_doctor_id(
    data_scope: ResolvedDataScope,
    query_doctor_id: UUID | None,
    current_user: User,
) -> UUID | None:
    """
    Under practice (doctor) scope, non-doctor roles use the scoped doctor for stock;
    doctor role remains bound by _resolve_effective_doctor_id_for_stock.
    """
    if data_scope.kind != DataScopeKind.doctor or data_scope.doctor_id is None:
        return query_doctor_id
    if current_user.role == UserRole.doctor:
        return query_doctor_id
    if query_doctor_id is not None and query_doctor_id != data_scope.doctor_id:
        log_rbac_mutation_violation(
            current_user, "inventory", action="stock_scope"
        )
        raise ForbiddenError("doctor_id does not match practice data scope")
    return data_scope.doctor_id


def _forbid_patients(current_user: User, action: str = "inventory") -> None:
    if current_user.role == UserRole.patient:
        log_rbac_mutation_violation(current_user, action)
        raise ForbiddenError("Patients cannot access inventory")


def _resolve_effective_doctor_id_for_stock(
    db: Session,
    current_user: User,
    doctor_id: UUID | None,
) -> UUID | None:
    """Doctors are forced to their own stock scope; other roles use the request scope."""
    if current_user.role == UserRole.doctor:
        doc = doctor_service.get_current_doctor(db, current_user)
        if doctor_id is not None and doctor_id != doc.id:
            log_rbac_mutation_violation(
                current_user, "inventory", action="stock_scope"
            )
            raise ForbiddenError("You may only access your own stock")
        return doc.id
    return doctor_id


def _authorize_item_tenant(
    item: InventoryItem,
    current_user: User,
    tenant_id: UUID | None,
) -> None:
    if tenant_id is None:
        raise ValidationError(MISSING_X_TENANT_ID_MSG)
    if current_user.role == UserRole.super_admin:
        if item.tenant_id != tenant_id:
            raise ForbiddenError("Item is not in the selected organization")
        return
    assert_authorized(
        "access",
        "inventory",
        current_user,
        tenant_id,
        resource_tenant_id=item.tenant_id,
    )


def _resolve_item_tenant_for_create(request_tenant_id: UUID | None) -> UUID:
    if request_tenant_id is None:
        raise ValidationError(MISSING_X_TENANT_ID_MSG)
    return request_tenant_id


def get_item_or_404(db: Session, item_id: UUID) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise NotFoundError("Inventory item not found")
    return item


def get_stock(
    db: Session,
    item_id: UUID,
    doctor_id: UUID | None = None,
    *,
    current_user: User,
    tenant_id: UUID | None,
    data_scope: ResolvedDataScope | None = None,
) -> int:
    """
    Read current quantity for one item and doctor scope (tenant level if doctor_id is None).
    If no row exists in inventory_stock, returns 0.
    """
    _forbid_patients(current_user)
    item = get_item_or_404(db, item_id)
    _authorize_item_tenant(item, current_user, tenant_id)
    q_doc = doctor_id
    if data_scope is not None:
        q_doc = effective_inventory_doctor_id(data_scope, doctor_id, current_user)
    eff_doctor = _resolve_effective_doctor_id_for_stock(db, current_user, q_doc)
    _validate_doctor_for_item_tenant(db, eff_doctor, item.tenant_id)
    row = db.scalars(_stock_query(item_id, eff_doctor)).first()
    return int(row.quantity) if row is not None else 0


def _enforce_inventory_item_matches_appointment_tenant(
    item: InventoryItem,
    appointment: Appointment,
) -> None:
    apt_tid = appointment.tenant_id
    if apt_tid is None:
        logger.error(
            "[INVENTORY_INVARIANT_VIOLATION] appointment tenant missing appointment_id=%s",
            appointment.id,
        )
        raise ValidationError("Appointment organization is not set")
    if item.tenant_id != apt_tid:
        logger.error(
            "[INVENTORY_INVARIANT_VIOLATION] item.tenant_id=%s appointment.tenant_id=%s "
            "item_id=%s appointment_id=%s",
            item.tenant_id,
            apt_tid,
            item.id,
            appointment.id,
        )
        raise ValidationError(
            "Inventory item organization must match the visit organization"
        )


def get_bulk_stock(
    tenant_id: UUID | None,
    doctor_id: UUID | None = None,
    item_ids: list[UUID] | None = None,
    *,
    db: Session,
    current_user: User,
    data_scope: ResolvedDataScope | None = None,
    tenant_stock_only: bool = False,
) -> list[tuple[UUID, int]]:
    """
    One-query stock for all items in the tenant (optionally doctor-scoped).
    Items without a stock row get quantity 0.

    When ``tenant_stock_only`` is True, always uses clinic (tenant-level) stock rows
    (``doctor_id IS NULL``) and ignores per-doctor pools — used when doctors consume
    shared clinic inventory.
    """
    _forbid_patients(current_user)
    if tenant_stock_only:
        if tenant_id is None:
            raise ValidationError(MISSING_X_TENANT_ID_MSG)
        eff_doctor_id: UUID | None = None
        filter_tenant = tenant_id
        if current_user.role == UserRole.doctor:
            doc = doctor_service.get_current_doctor(db, current_user)
            if doc.tenant_id != tenant_id:
                log_rbac_mutation_violation(
                    current_user, "inventory", action="tenant_stock_scope"
                )
                raise ForbiddenError("Not allowed to view this tenant inventory")
    else:
        q_doc = doctor_id
        if data_scope is not None:
            q_doc = effective_inventory_doctor_id(data_scope, doctor_id, current_user)
        eff_doctor_id = _resolve_effective_doctor_id_for_stock(db, current_user, q_doc)
        filter_tenant: UUID | None = tenant_id
        if eff_doctor_id is not None:
            doctor = db.get(Doctor, eff_doctor_id)
            if doctor is None:
                raise NotFoundError("Doctor not found")
            if tenant_id is not None and doctor.tenant_id != tenant_id:
                raise ValidationError("Doctor does not belong to the current tenant")
            filter_tenant = doctor.tenant_id
        else:
            if tenant_id is None:
                raise ValidationError(MISSING_X_TENANT_ID_MSG)
            filter_tenant = tenant_id

    join_cond = and_(
        InventoryStock.item_id == InventoryItem.id,
        (
            InventoryStock.doctor_id.is_(None)
            if eff_doctor_id is None
            else InventoryStock.doctor_id == eff_doctor_id
        ),
    )
    q = select(InventoryItem.id, func.coalesce(InventoryStock.quantity, 0)).outerjoin(
        InventoryStock,
        join_cond,
    )
    q = q.where(InventoryItem.tenant_id == filter_tenant)
    if item_ids is not None and len(item_ids) > 0:
        q = q.where(InventoryItem.id.in_(item_ids))
    q = q.order_by(InventoryItem.name.asc())
    return [(r[0], int(r[1])) for r in db.execute(q).all()]


def _validate_doctor_for_item_tenant(
    db: Session,
    doctor_id: UUID | None,
    item_tenant_id: UUID,
) -> None:
    if doctor_id is None:
        return
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise NotFoundError("Doctor not found")
    if doctor.tenant_id != item_tenant_id:
        raise ValidationError("Doctor does not belong to the same tenant as this item")


def _validate_billing_reference(
    db: Session,
    billing_id: UUID | None,
    item_tenant_id: UUID,
) -> None:
    if billing_id is None:
        return
    bill = db.get(Billing, billing_id)
    if bill is None:
        raise NotFoundError("Billing record not found")
    if bill.tenant_id is not None and bill.tenant_id != item_tenant_id:
        raise ValidationError("Billing record belongs to a different tenant")


def _stock_query(item_id: UUID, doctor_id: UUID | None) -> Select[tuple[InventoryStock]]:
    q = select(InventoryStock).where(InventoryStock.item_id == item_id)
    if doctor_id is None:
        q = q.where(InventoryStock.doctor_id.is_(None))
    else:
        q = q.where(InventoryStock.doctor_id == doctor_id)
    return q


def _get_or_create_stock_row(
    db: Session,
    item_id: UUID,
    doctor_id: UUID | None,
) -> InventoryStock:
    row = db.scalars(_stock_query(item_id, doctor_id).with_for_update(of=InventoryStock)).first()
    if row is not None:
        return row
    row = InventoryStock(item_id=item_id, doctor_id=doctor_id, quantity=0)
    db.add(row)
    db.flush()
    locked = db.scalars(_stock_query(item_id, doctor_id).with_for_update(of=InventoryStock)).first()
    return locked if locked is not None else row


def _subtract_stock_atomic_out(
    db: Session,
    item: InventoryItem,
    doctor_id: UUID | None,
    quantity: int,
) -> int:
    """Guarded decrement on the locked stock row (single-statement ``WHERE quantity >= …``)."""
    stock = _get_or_create_stock_row(db, item.id, doctor_id)
    stmt = (
        update(InventoryStock)
        .where(
            InventoryStock.id == stock.id,
            InventoryStock.quantity >= quantity,
        )
        .values(quantity=InventoryStock.quantity - quantity)
    )
    res = db.execute(stmt)
    if res.rowcount != 1:
        raise ValidationError(
            f"Insufficient stock for {item.name!r} (cannot deduct {quantity})"
        )
    db.refresh(stock)
    return int(stock.quantity)


def _apply_movement(
    db: Session,
    item: InventoryItem,
    doctor_id: UUID | None,
    movement_type: InventoryMovementType,
    quantity: int,
    *,
    billing_id: UUID | None,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    created_by: UUID | None = None,
    created_by_role: str | None = None,
) -> tuple[InventoryMovement, int]:
    _validate_doctor_for_item_tenant(db, doctor_id, item.tenant_id)
    _validate_billing_reference(db, billing_id, item.tenant_id)

    if movement_type == InventoryMovementType.IN:
        if quantity < 1:
            raise ValidationError("IN movement requires a positive quantity")
        stock = _get_or_create_stock_row(db, item.id, doctor_id)
        new_balance = stock.quantity + quantity
        stock.quantity = new_balance
    elif movement_type == InventoryMovementType.OUT:
        if quantity < 1:
            raise ValidationError("OUT movement requires a positive quantity")
        new_balance = _subtract_stock_atomic_out(db, item, doctor_id, quantity)
    else:
        stock = _get_or_create_stock_row(db, item.id, doctor_id)
        new_balance = stock.quantity + quantity
        if new_balance < 0:
            raise ValidationError("Insufficient stock (cannot go negative)")
        stock.quantity = new_balance

    movement = InventoryMovement(
        item_id=item.id,
        doctor_id=doctor_id,
        type=movement_type,
        quantity=quantity,
        billing_id=billing_id,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by=created_by,
        created_by_role=created_by_role,
    )
    db.add(movement)
    db.flush()
    threshold = getattr(item, "low_stock_threshold", None)
    if threshold is not None and new_balance <= threshold:
        logger.warning(
            "[LOW_STOCK] item_id=%s tenant=%s qty=%s threshold=%s",
            item.id,
            item.tenant_id,
            new_balance,
            threshold,
        )
    return movement, new_balance


def create_item(
    db: Session,
    data: InventoryItemCreate,
    current_user: User,
    tenant_id: UUID | None,
) -> InventoryItem:
    _forbid_patients(current_user)
    effective_tenant = _resolve_item_tenant_for_create(tenant_id)
    assert_authorized(
        "create",
        "inventory",
        current_user,
        tenant_id,
        resource_tenant_id=effective_tenant,
    )

    item = InventoryItem(
        tenant_id=effective_tenant,
        name=data.name,
        type=data.type,
        unit=data.unit,
        cost_price=data.cost_price,
        selling_price=data.selling_price,
        is_active=data.is_active,
        low_stock_threshold=data.low_stock_threshold,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info(
        "[INVENTORY] created item id=%s tenant=%s by user=%s",
        item.id,
        item.tenant_id,
        current_user.id,
    )
    return item


def update_item(
    db: Session,
    item_id: UUID,
    data: InventoryItemUpdate,
    current_user: User,
    tenant_id: UUID | None,
) -> InventoryItem:
    _forbid_patients(current_user)
    item = get_item_or_404(db, item_id)
    _authorize_item_tenant(item, current_user, tenant_id)

    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(item, k, v)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_items(
    db: Session,
    current_user: User,
    tenant_id: UUID | None,
    *,
    skip: int = 0,
    limit: int = 50,
    type_filter: InventoryItemType | None = None,
    active_only: bool = False,
) -> list[InventoryItem]:
    _forbid_patients(current_user)
    if tenant_id is None:
        raise ValidationError(MISSING_X_TENANT_ID_MSG)
    q = select(InventoryItem).where(InventoryItem.tenant_id == tenant_id)

    if type_filter:
        q = q.where(InventoryItem.type == type_filter)
    if active_only:
        q = q.where(InventoryItem.is_active.is_(True))

    q = q.order_by(InventoryItem.name.asc()).offset(skip).limit(limit)
    return list(db.scalars(q).all())


def add_stock(
    db: Session,
    body: StockAddRequest,
    current_user: User,
    tenant_id: UUID | None,
    data_scope: ResolvedDataScope | None = None,
) -> tuple[UUID, int]:
    _forbid_patients(current_user)
    item = get_item_or_404(db, body.item_id)
    _authorize_item_tenant(item, current_user, tenant_id)
    if not item.is_active:
        raise ValidationError("Cannot adjust stock for an inactive item")

    q_doc = body.doctor_id
    if data_scope is not None:
        q_doc = effective_inventory_doctor_id(data_scope, body.doctor_id, current_user)
    eff_doctor = _resolve_effective_doctor_id_for_stock(
        db, current_user, q_doc
    )
    movement, balance = _apply_movement(
        db,
        item,
        eff_doctor,
        InventoryMovementType.IN,
        body.quantity,
        billing_id=body.billing_id,
        created_by_role=current_user.role.value,
    )
    db.commit()
    db.refresh(movement)
    return movement.id, balance


def reduce_stock(
    db: Session,
    body: StockReduceRequest,
    current_user: User,
    tenant_id: UUID | None,
    data_scope: ResolvedDataScope | None = None,
) -> tuple[UUID, int]:
    _forbid_patients(current_user)
    item = get_item_or_404(db, body.item_id)
    _authorize_item_tenant(item, current_user, tenant_id)
    if not item.is_active:
        raise ValidationError("Cannot adjust stock for an inactive item")

    q_doc = body.doctor_id
    if data_scope is not None:
        q_doc = effective_inventory_doctor_id(data_scope, body.doctor_id, current_user)
    eff_doctor = _resolve_effective_doctor_id_for_stock(
        db, current_user, q_doc
    )
    movement, balance = _apply_movement(
        db,
        item,
        eff_doctor,
        InventoryMovementType.OUT,
        body.quantity,
        billing_id=body.billing_id,
        created_by_role=current_user.role.value,
    )
    db.commit()
    db.refresh(movement)
    return movement.id, balance


def adjust_stock(
    db: Session,
    body: StockAdjustRequest,
    current_user: User,
    tenant_id: UUID | None,
    data_scope: ResolvedDataScope | None = None,
) -> tuple[UUID, int]:
    if current_user.role not in (
        UserRole.admin,
        UserRole.staff,
        UserRole.super_admin,
    ):
        log_rbac_mutation_violation(
            current_user, "inventory", action="adjust_inventory"
        )
        raise ForbiddenError("Only administrators can post stock adjustments (ADJUST)")
    _forbid_patients(current_user)
    item = get_item_or_404(db, body.item_id)
    _authorize_item_tenant(item, current_user, tenant_id)
    if not item.is_active:
        raise ValidationError("Cannot adjust stock for an inactive item")

    q_doc = body.doctor_id
    if data_scope is not None:
        q_doc = effective_inventory_doctor_id(data_scope, body.doctor_id, current_user)
    eff_doctor = _resolve_effective_doctor_id_for_stock(
        db, current_user, q_doc
    )
    movement, balance = _apply_movement(
        db,
        item,
        eff_doctor,
        InventoryMovementType.ADJUST,
        body.quantity,
        billing_id=body.billing_id,
        created_by_role=current_user.role.value,
    )
    db.commit()
    db.refresh(movement)
    return movement.id, balance


def get_inventory_for_user(
    db: Session,
    current_user: User,
    tenant_id: UUID | None,
    *,
    skip: int = 0,
    limit: int = 200,
    active_only: bool = False,
    search: str | None = None,
) -> list[tuple[InventoryItem, int]]:
    """
    Items plus clinic (tenant-level) stock for doctors, admins, and super admins
    operating under ``tenant_id``.
    """
    rows = _query_inventory_items_with_tenant_scope(
        db,
        current_user,
        tenant_id,
        skip=skip,
        limit=limit,
        active_only=active_only,
        search=search,
    )
    if not rows:
        return []
    ids = [i.id for i in rows]
    pairs = get_bulk_stock(
        tenant_id,
        item_ids=ids,
        db=db,
        current_user=current_user,
        tenant_stock_only=True,
    )
    qty_by_id = {i: q for i, q in pairs}
    return [(i, int(qty_by_id.get(i.id, 0))) for i in rows]


def _query_inventory_items_with_tenant_scope(
    db: Session,
    current_user: User,
    tenant_id: UUID | None,
    *,
    skip: int,
    limit: int,
    active_only: bool,
    search: str | None,
) -> list[InventoryItem]:
    _forbid_patients(current_user)
    if tenant_id is None:
        raise ValidationError(MISSING_X_TENANT_ID_MSG)
    if current_user.role == UserRole.doctor:
        doc = doctor_service.get_current_doctor(db, current_user)
        if doc.tenant_id != tenant_id:
            raise ForbiddenError("Tenant scope does not match your practice")
    q = select(InventoryItem).where(InventoryItem.tenant_id == tenant_id)
    if active_only:
        q = q.where(InventoryItem.is_active.is_(True))
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.where(InventoryItem.name.ilike(term))
    q = q.order_by(InventoryItem.name.asc()).offset(skip).limit(limit)
    return list(db.scalars(q).all())


def _record_visit_inventory_deductions(
    db: Session,
    appointment: Appointment,
    totals: dict[UUID, int],
    current_user: User,
    tenant_id: UUID | None,
) -> None:
    """Validate all lines, then deduct stock and insert usage rows (per item; replay-safe)."""
    existing_item_ids = set(
        db.scalars(
            select(AppointmentInventoryUsage.item_id).where(
                AppointmentInventoryUsage.appointment_id == appointment.id
            )
        ).all()
    )

    validated: list[tuple[InventoryItem, int]] = []
    for item_id in sorted(totals.keys()):
        need = totals[item_id]
        item = db.get(InventoryItem, item_id)
        if item is None:
            raise NotFoundError("Inventory item not found")
        _enforce_inventory_item_matches_appointment_tenant(item, appointment)
        _authorize_item_tenant(item, current_user, tenant_id)
        if not item.is_active:
            raise ValidationError("Cannot use an inactive inventory item")
        validated.append((item, need))

    for item, need in validated:
        if item.id in existing_item_ids:
            continue

        _apply_movement(
            db,
            item,
            None,
            InventoryMovementType.OUT,
            need,
            billing_id=None,
            reference_type=InventoryReferenceType.APPOINTMENT.value,
            reference_id=appointment.id,
            created_by=current_user.id,
            created_by_role=current_user.role.value,
        )

        try:
            with db.begin_nested():
                db.add(
                    AppointmentInventoryUsage(
                        appointment_id=appointment.id,
                        item_id=item.id,
                        quantity=need,
                    )
                )
                db.flush()
        except IntegrityError:
            pass
        else:
            inc_counter("inventory_deductions_total")

        existing_item_ids.add(item.id)
    db.flush()
    log_audit_mutation(
        "consume_inventory",
        current_user,
        "appointment_inventory",
        appointment.id,
        appointment.tenant_id,
    )


def consume_inventory_for_appointment(
    db: Session,
    appointment: Appointment,
    items: list[InventoryUseLine],
    current_user: User,
    tenant_id: UUID | None,
    *,
    require_scheduled: bool = True,
) -> None:
    """
    Deduct clinic (tenant-level) stock, write movements and ``appointment_inventory_usage``
    rows. Caller must commit.

    Idempotent per ``(appointment_id, item_id)``: existing lines are skipped; concurrent duplicate
    inserts are tolerated without double-counting metrics.

    CLINICIAN CAPABILITY: The user must have clinician capability (doctor role,
    normalized doctor role, or linked Doctor record). Workspace context does NOT
    grant clinical authority — a pure admin without a Doctor record cannot consume
    clinical inventory regardless of workspace.
    """
    if not items:
        return

    # CLINICIAN CAPABILITY: The user must have clinician capability (doctor role,
    # normalized doctor role, or linked Doctor record). Workspace context does NOT
    # grant clinical authority — a pure admin without a Doctor record cannot consume
    # clinical inventory regardless of workspace.
    if not has_clinician_capability(db, current_user):
        log_rbac_mutation_violation(
            current_user, "inventory", action="consume_inventory"
        )
        raise ForbiddenError("Only clinicians can record visit inventory usage")

    doc = doctor_service.get_current_doctor(db, current_user)
    if appointment.tenant_id is not None and doc.tenant_id != appointment.tenant_id:
        raise ForbiddenError("Cross-tenant access not allowed")
    if appointment.doctor_id != doc.id:
        raise ForbiddenError("Not your appointment")

    if require_scheduled and appointment.status != AppointmentStatus.scheduled:
        raise ValidationError("Inventory can only be consumed for scheduled visits")
    if (
        tenant_id is not None
        and appointment.tenant_id is not None
        and appointment.tenant_id != tenant_id
    ):
        raise ForbiddenError("Appointment does not belong to the selected organization")

    totals: dict[UUID, int] = defaultdict(int)
    for row in items:
        totals[row.item_id] += row.quantity

    _record_visit_inventory_deductions(db, appointment, totals, current_user, tenant_id)


def consume_inventory_admin_manual(
    db: Session,
    appointment: Appointment,
    items: list[InventoryUseLine],
    current_user: User,
    tenant_id: UUID | None,
) -> None:
    """
    Admin/staff/super-admin only: deduct clinic stock and record usage tied to an appointment.

    Visiting doctors must use ``POST /appointments/{id}/mark-completed`` instead.
    """
    if current_user.role not in (
        UserRole.admin,
        UserRole.staff,
        UserRole.super_admin,
    ):
        raise ForbiddenError("Only administrators can use this legacy inventory endpoint")
    if not items:
        return

    if appointment.status != AppointmentStatus.scheduled:
        raise ValidationError(
            "Inventory can only be recorded for scheduled visits here; "
            "doctors finalize usage with POST /appointments/{id}/mark-completed."
        )

    totals: dict[UUID, int] = defaultdict(int)
    for row in items:
        totals[row.item_id] += row.quantity

    _record_visit_inventory_deductions(db, appointment, totals, current_user, tenant_id)


def use_inventory(
    db: Session,
    item_id: UUID,
    quantity: int,
    appointment_id: UUID,
    user: User,
    tenant_id: UUID | None,
) -> None:
    """Deduct one item line against an appointment’s clinic pool (doctor flow)."""
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise NotFoundError("Appointment not found")
    consume_inventory_for_appointment(
        db,
        appt,
        [InventoryUseLine(item_id=item_id, quantity=quantity)],
        user,
        tenant_id,
    )


def add_inventory_stock(
    db: Session,
    item_id: UUID,
    quantity: int,
    current_user: User,
    tenant_id: UUID | None,
) -> tuple[UUID, int]:
    """
    Administrators only (not practicing doctors): add clinic-level stock via IN movement.
    """
    _forbid_patients(current_user)
    if current_user.role not in (
        UserRole.admin,
        UserRole.staff,
        UserRole.super_admin,
    ):
        log_rbac_mutation_violation(
            current_user, "inventory", action="admin_inventory_add"
        )
        raise ForbiddenError(
            "Only administrators can add stock through this endpoint"
        )
    body = StockAddRequest(
        item_id=item_id,
        quantity=quantity,
        doctor_id=None,
        billing_id=None,
    )
    return add_stock(db, body, current_user, tenant_id, data_scope=None)
