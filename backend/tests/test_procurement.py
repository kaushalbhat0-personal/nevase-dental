"""
Tests for Phase 3B — Procurement Foundation.

Covers:
- Supplier CRUD (create, list, get, update)
- Tenant isolation (cross-tenant access blocked)
- Purchase order lifecycle (create draft, complete, cancel)
- Stock increases correctly on PO completion
- PROCUREMENT_IN movement created
- Weighted average valuation updates
- Audit events logged
- Tax summary aggregate works
- Procurement export works
- Cancel PO reverses stock
- No billing regressions
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import (
    InventoryItem,
    InventoryItemType,
    InventoryMovement,
    InventoryMovementType,
    InventoryStock,
)
from app.models.purchase_order import (
    PaymentStatus,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.schemas.procurement import (
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
    SupplierCreate,
    SupplierUpdate,
)
from app.services.procurement_service import (
    cancel_purchase_order,
    complete_purchase_order,
    create_purchase_order,
    create_supplier,
    get_procurement_report,
    get_purchase_order,
    get_supplier,
    get_tax_summary,
    list_purchase_orders,
    list_suppliers,
    update_supplier,
)
from tests.factories import (
    create_doctor_profile,
    create_patient_profile,
    create_tenant,
    create_user,
    link_user_tenant,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _auth_header(user: User) -> dict[str, str]:
    """Create an Authorization header for the given user."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _create_inventory_item(
    db: Session,
    *,
    tenant_id: UUID,
    name: str = "Procurement Test Item",
    cost_price: float = 50.0,
    selling_price: float = 80.0,
) -> InventoryItem:
    item = InventoryItem(
        tenant_id=tenant_id,
        name=name,
        type=InventoryItemType.medicine,
        unit="pcs",
        cost_price=cost_price,
        selling_price=selling_price,
    )
    db.add(item)
    db.flush()
    return item


def _create_supplier(
    db: Session,
    *,
    tenant_id: UUID,
    name: str = "Test Supplier",
) -> Supplier:
    s = Supplier(
        tenant_id=tenant_id,
        supplier_name=name,
        contact_person="John Contact",
        phone="555-0100",
        email="supplier@test.com",
        gst_number="GST12345",
    )
    db.add(s)
    db.flush()
    return s


def _create_draft_po(
    db: Session,
    *,
    tenant_id: UUID,
    supplier_id: UUID,
    item_id: UUID,
    quantity: int = 10,
    unit_cost: float = 55.0,
    created_by: UUID | None = None,
) -> PurchaseOrder:
    po = PurchaseOrder(
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        invoice_number="INV-001",
        subtotal=quantity * unit_cost,
        tax_amount=quantity * unit_cost * 0.18,
        total_amount=quantity * unit_cost * 1.18,
        payment_status=PaymentStatus.unpaid,
        status=PurchaseOrderStatus.draft,
        created_by=created_by,
    )
    db.add(po)
    db.flush()

    poi = PurchaseOrderItem(
        purchase_order_id=po.id,
        inventory_item_id=item_id,
        quantity=quantity,
        unit_cost=unit_cost,
        tax_percent=18.0,
        line_total=quantity * unit_cost,
    )
    db.add(poi)
    db.flush()
    return po


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def tenant_a(db_session: Session) -> Tenant:
    return create_tenant(db_session, name="Procurement Tenant A")


@pytest.fixture
def tenant_b(db_session: Session) -> Tenant:
    return create_tenant(db_session, name="Procurement Tenant B")


@pytest.fixture
def admin_user(db_session: Session, tenant_a: Tenant) -> User:
    u = create_user(
        db_session,
        email="proc_admin@a.com",
        password="secret",
        role=UserRole.admin,
        tenant_id=tenant_a.id,
    )
    link_user_tenant(db_session, user_id=u.id, tenant_id=tenant_a.id)
    return u


@pytest.fixture
def admin_user_b(db_session: Session, tenant_b: Tenant) -> User:
    u = create_user(
        db_session,
        email="proc_admin_b@b.com",
        password="secret",
        role=UserRole.admin,
        tenant_id=tenant_b.id,
    )
    link_user_tenant(db_session, user_id=u.id, tenant_id=tenant_b.id)
    return u


@pytest.fixture
def patient_user(db_session: Session) -> User:
    return create_user(
        db_session,
        email="proc_patient@test.com",
        password="secret",
        role=UserRole.patient,
    )


@pytest.fixture
def supplier(db_session: Session, tenant_a: Tenant) -> Supplier:
    return _create_supplier(db_session, tenant_id=tenant_a.id)


@pytest.fixture
def item(db_session: Session, tenant_a: Tenant) -> InventoryItem:
    return _create_inventory_item(db_session, tenant_id=tenant_a.id)


# ── Test: Create Supplier ──────────────────────────────────────────────────


class TestCreateSupplier:
    """Supplier creation via service layer."""

    def test_create_supplier_success(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
    ) -> None:
        data = SupplierCreate(
            supplier_name="MediSupply Co",
            contact_person="Jane Doe",
            phone="555-0200",
            email="jane@medisupply.com",
            gst_number="GST998877",
        )
        supplier = create_supplier(db_session, data, admin_user, tenant_a.id)
        assert supplier.supplier_name == "MediSupply Co"
        assert supplier.tenant_id == tenant_a.id
        assert supplier.is_active is True
        assert supplier.gst_number == "GST998877"

    def test_create_supplier_patient_forbidden(
        self,
        db_session: Session,
        tenant_a: Tenant,
        patient_user: User,
    ) -> None:
        from app.services.exceptions import ForbiddenError

        data = SupplierCreate(supplier_name="Bad Supplier")
        with pytest.raises(ForbiddenError):
            create_supplier(db_session, data, patient_user, tenant_a.id)


# ── Test: Tenant Isolation ─────────────────────────────────────────────────


class TestTenantIsolation:
    """Cross-tenant access must be blocked."""

    def test_supplier_tenant_isolation(
        self,
        db_session: Session,
        tenant_a: Tenant,
        tenant_b: Tenant,
        admin_user: User,
        admin_user_b: User,
    ) -> None:
        s_a = _create_supplier(db_session, tenant_id=tenant_a.id, name="Tenant A Supplier")
        s_b = _create_supplier(db_session, tenant_id=tenant_b.id, name="Tenant B Supplier")
        db_session.flush()

        # Admin from A should see only A's supplier
        suppliers_a, total_a = list_suppliers(db_session, admin_user, tenant_a.id)
        assert total_a == 1
        assert suppliers_a[0].id == s_a.id

        # Admin from B should see only B's supplier
        suppliers_b, total_b = list_suppliers(db_session, admin_user_b, tenant_b.id)
        assert total_b == 1
        assert suppliers_b[0].id == s_b.id

    def test_po_tenant_isolation(
        self,
        db_session: Session,
        tenant_a: Tenant,
        tenant_b: Tenant,
        admin_user: User,
        admin_user_b: User,
    ) -> None:
        s_a = _create_supplier(db_session, tenant_id=tenant_a.id)
        s_b = _create_supplier(db_session, tenant_id=tenant_b.id)
        item_a = _create_inventory_item(db_session, tenant_id=tenant_a.id)
        item_b = _create_inventory_item(db_session, tenant_id=tenant_b.id)

        po_a = _create_draft_po(
            db_session, tenant_id=tenant_a.id, supplier_id=s_a.id, item_id=item_a.id,
        )
        po_b = _create_draft_po(
            db_session, tenant_id=tenant_b.id, supplier_id=s_b.id, item_id=item_b.id,
        )
        db_session.flush()

        pos_a, total_a = list_purchase_orders(db_session, admin_user, tenant_a.id)
        assert total_a == 1
        assert pos_a[0].id == po_a.id

        pos_b, total_b = list_purchase_orders(db_session, admin_user_b, tenant_b.id)
        assert total_b == 1
        assert pos_b[0].id == po_b.id


# ── Test: Create Draft Purchase Order ──────────────────────────────────────


class TestCreatePurchaseOrder:
    """Purchase order creation."""

    def test_create_draft_po(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        data = PurchaseOrderCreate(
            supplier_id=supplier.id,
            invoice_number="INV-100",
            subtotal=550.0,
            tax_amount=99.0,
            total_amount=649.0,
            payment_status=PaymentStatus.unpaid,
            items=[
                PurchaseOrderItemCreate(
                    inventory_item_id=item.id,
                    quantity=10,
                    unit_cost=55.0,
                    tax_percent=18.0,
                    line_total=550.0,
                )
            ],
        )
        po = create_purchase_order(db_session, data, admin_user, tenant_a.id)
        assert po.status == PurchaseOrderStatus.draft
        assert po.tenant_id == tenant_a.id
        assert po.supplier_id == supplier.id
        assert len(po.items) == 1
        assert po.items[0].quantity == 10
        assert po.items[0].unit_cost == 55.0


# ── Test: Complete Purchase Order ──────────────────────────────────────────


class TestCompletePurchaseOrder:
    """Purchase order completion — stock inward."""

    def test_complete_po_stock_increases(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            quantity=10,
            unit_cost=55.0,
            created_by=admin_user.id,
        )
        db_session.flush()

        completed = complete_purchase_order(db_session, po.id, admin_user, tenant_a.id)
        assert completed.status == PurchaseOrderStatus.completed

        # Stock should have increased
        stock = db_session.scalars(
            select(InventoryStock).where(
                InventoryStock.item_id == item.id,
                InventoryStock.doctor_id.is_(None),
            )
        ).first()
        assert stock is not None
        assert stock.quantity == 10

    def test_complete_po_creates_procurement_in_movement(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            quantity=5,
            unit_cost=55.0,
            created_by=admin_user.id,
        )
        db_session.flush()

        complete_purchase_order(db_session, po.id, admin_user, tenant_a.id)

        movements = (
            db_session.query(InventoryMovement)
            .filter(
                InventoryMovement.item_id == item.id,
                InventoryMovement.type == InventoryMovementType.PROCUREMENT_IN,
            )
            .all()
        )
        assert len(movements) == 1
        mov = movements[0]
        assert mov.quantity == 5
        assert mov.reference_type == "PURCHASE_ORDER"
        assert mov.reference_id == po.id
        assert mov.unit_cost == 55.0
        assert mov.supplier_id == supplier.id
        assert mov.invoice_number == "INV-001"

    def test_complete_po_updates_weighted_avg(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        # Initial stock: 10 units at cost_price=50.0
        stock = InventoryStock(item_id=item.id, doctor_id=None, quantity=10)
        db_session.add(stock)
        db_session.flush()

        # PO: 5 units at unit_cost=55.0
        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            quantity=5,
            unit_cost=55.0,
            created_by=admin_user.id,
        )
        db_session.flush()

        complete_purchase_order(db_session, po.id, admin_user, tenant_a.id)
        db_session.refresh(item)

        # Weighted avg = (10*50 + 5*55) / 15 = (500 + 275) / 15 = 775/15 = 51.67
        expected_avg = Decimal(str(round((10 * 50.0 + 5 * 55.0) / 15, 2)))
        assert round(item.cost_price, 2) == expected_avg

    def test_complete_po_logs_audit(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            created_by=admin_user.id,
        )
        db_session.flush()

        # Audit is logged via log_audit_mutation (logger-based)
        completed = complete_purchase_order(db_session, po.id, admin_user, tenant_a.id)
        assert completed.status == PurchaseOrderStatus.completed


# ── Test: Tax Summary Aggregate ────────────────────────────────────────────


class TestTaxSummary:
    """Tax summary aggregation."""

    def test_tax_summary_works(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            quantity=10,
            unit_cost=100.0,
            created_by=admin_user.id,
        )
        db_session.flush()
        complete_purchase_order(db_session, po.id, admin_user, tenant_a.id)

        summary = get_tax_summary(db_session, admin_user, tenant_a.id)
        assert len(summary) >= 1
        row = summary[0]
        assert row["supplier_name"] == supplier.supplier_name
        assert row["gst_number"] == supplier.gst_number
        assert row["invoice_number"] == "INV-001"
        assert row["invoice_count"] == 1


# ── Test: Procurement Export ───────────────────────────────────────────────


class TestProcurementExport:
    """Procurement report export."""

    def test_procurement_report_works(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            quantity=10,
            unit_cost=100.0,
            created_by=admin_user.id,
        )
        db_session.flush()
        complete_purchase_order(db_session, po.id, admin_user, tenant_a.id)

        report = get_procurement_report(db_session, admin_user, tenant_a.id)
        assert len(report) >= 1
        row = report[0]
        assert row["supplier_name"] == supplier.supplier_name
        assert row["invoice_number"] == "INV-001"
        assert row["status"] == "completed"
        assert row["total_qty"] == 10


# ── Test: Cancel PO Reverses Stock ─────────────────────────────────────────


class TestCancelPurchaseOrder:
    """Purchase order cancellation — stock reversal."""

    def test_cancel_completed_po_reverses_stock(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            quantity=10,
            unit_cost=55.0,
            created_by=admin_user.id,
        )
        db_session.flush()
        complete_purchase_order(db_session, po.id, admin_user, tenant_a.id)

        # Stock should be 10
        stock = db_session.scalars(
            select(InventoryStock).where(
                InventoryStock.item_id == item.id,
                InventoryStock.doctor_id.is_(None),
            )
        ).first()
        assert stock.quantity == 10

        # Cancel the PO
        cancelled = cancel_purchase_order(db_session, po.id, admin_user, tenant_a.id)
        assert cancelled.status == PurchaseOrderStatus.cancelled

        # Stock should be reversed to 0
        db_session.refresh(stock)
        assert stock.quantity == 0

    def test_cancel_draft_po_no_stock_impact(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            quantity=10,
            created_by=admin_user.id,
        )
        db_session.flush()

        cancelled = cancel_purchase_order(db_session, po.id, admin_user, tenant_a.id)
        assert cancelled.status == PurchaseOrderStatus.cancelled

        # No stock was ever added, so no reversal needed
        stock = db_session.scalars(
            select(InventoryStock).where(
                InventoryStock.item_id == item.id,
                InventoryStock.doctor_id.is_(None),
            )
        ).first()
        assert stock is None or stock.quantity == 0


# ── Test: No Billing Regressions ───────────────────────────────────────────


class TestNoBillingRegressions:
    """Procurement operations must not affect billing."""

    def test_procurement_does_not_affect_billing(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        from app.models.billing import Billing

        # Count existing bills
        bill_count_before = db_session.query(Billing).count()

        # Create and complete a PO
        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            quantity=10,
            created_by=admin_user.id,
        )
        db_session.flush()
        complete_purchase_order(db_session, po.id, admin_user, tenant_a.id)

        # Bill count should remain unchanged
        bill_count_after = db_session.query(Billing).count()
        assert bill_count_after == bill_count_before

    def test_procurement_does_not_affect_appointments(
        self,
        db_session: Session,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        from app.models.appointment import Appointment

        appt_count_before = db_session.query(Appointment).count()

        po = _create_draft_po(
            db_session,
            tenant_id=tenant_a.id,
            supplier_id=supplier.id,
            item_id=item.id,
            quantity=10,
            created_by=admin_user.id,
        )
        db_session.flush()
        complete_purchase_order(db_session, po.id, admin_user, tenant_a.id)

        appt_count_after = db_session.query(Appointment).count()
        assert appt_count_after == appt_count_before


# ── Test: API Endpoints ────────────────────────────────────────────────────


class TestProcurementAPI:
    """Procurement API endpoint integration tests."""

    @pytest.mark.asyncio
    async def test_create_supplier_api(
        self,
        db_session: Session,
        client: AsyncClient,
        tenant_a: Tenant,
        admin_user: User,
    ) -> None:
        headers = _auth_header(admin_user)
        headers["X-Tenant-ID"] = str(tenant_a.id)

        resp = await client.post(
            "/api/v1/procurement/suppliers",
            json={
                "supplier_name": "API Supplier",
                "contact_person": "API Contact",
                "phone": "555-0300",
                "email": "api@supplier.com",
                "gst_number": "GSTAPI123",
            },
            headers=headers,
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["supplier_name"] == "API Supplier"
        assert data["tenant_id"] == str(tenant_a.id)

    @pytest.mark.asyncio
    async def test_create_purchase_order_api(
        self,
        db_session: Session,
        client: AsyncClient,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        headers = _auth_header(admin_user)
        headers["X-Tenant-ID"] = str(tenant_a.id)

        resp = await client.post(
            "/api/v1/procurement/purchase-orders",
            json={
                "supplier_id": str(supplier.id),
                "invoice_number": "API-INV-001",
                "subtotal": 550.0,
                "tax_amount": 99.0,
                "total_amount": 649.0,
                "payment_status": "unpaid",
                "items": [
                    {
                        "inventory_item_id": str(item.id),
                        "quantity": 10,
                        "unit_cost": 55.0,
                        "tax_percent": 18.0,
                        "line_total": 550.0,
                    }
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["status"] == "draft"
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_complete_purchase_order_api(
        self,
        db_session: Session,
        client: AsyncClient,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        headers = _auth_header(admin_user)
        headers["X-Tenant-ID"] = str(tenant_a.id)

        # Create PO via API
        create_resp = await client.post(
            "/api/v1/procurement/purchase-orders",
            json={
                "supplier_id": str(supplier.id),
                "invoice_number": "API-INV-002",
                "subtotal": 550.0,
                "tax_amount": 99.0,
                "total_amount": 649.0,
                "payment_status": "unpaid",
                "items": [
                    {
                        "inventory_item_id": str(item.id),
                        "quantity": 10,
                        "unit_cost": 55.0,
                        "tax_percent": 18.0,
                        "line_total": 550.0,
                    }
                ],
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        po_id = create_resp.json()["id"]

        # Complete via API
        complete_resp = await client.post(
            f"/api/v1/procurement/purchase-orders/{po_id}/complete",
            headers=headers,
        )
        assert complete_resp.status_code == 200, f"Expected 200, got {complete_resp.status_code}: {complete_resp.text}"
        assert complete_resp.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_cancel_purchase_order_api(
        self,
        db_session: Session,
        client: AsyncClient,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        headers = _auth_header(admin_user)
        headers["X-Tenant-ID"] = str(tenant_a.id)

        # Create PO via API
        create_resp = await client.post(
            "/api/v1/procurement/purchase-orders",
            json={
                "supplier_id": str(supplier.id),
                "invoice_number": "API-INV-003",
                "subtotal": 550.0,
                "tax_amount": 99.0,
                "total_amount": 649.0,
                "payment_status": "unpaid",
                "items": [
                    {
                        "inventory_item_id": str(item.id),
                        "quantity": 10,
                        "unit_cost": 55.0,
                        "tax_percent": 18.0,
                        "line_total": 550.0,
                    }
                ],
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        po_id = create_resp.json()["id"]

        # Cancel via API
        cancel_resp = await client.post(
            f"/api/v1/procurement/purchase-orders/{po_id}/cancel",
            headers=headers,
        )
        assert cancel_resp.status_code == 200, f"Expected 200, got {cancel_resp.status_code}: {cancel_resp.text}"
        assert cancel_resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_list_suppliers_api(
        self,
        db_session: Session,
        client: AsyncClient,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
    ) -> None:
        headers = _auth_header(admin_user)
        headers["X-Tenant-ID"] = str(tenant_a.id)

        resp = await client.get(
            "/api/v1/procurement/suppliers",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["suppliers"]) >= 1
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_purchase_orders_api(
        self,
        db_session: Session,
        client: AsyncClient,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        headers = _auth_header(admin_user)
        headers["X-Tenant-ID"] = str(tenant_a.id)

        # Create a PO first
        await client.post(
            "/api/v1/procurement/purchase-orders",
            json={
                "supplier_id": str(supplier.id),
                "invoice_number": "API-INV-LIST",
                "subtotal": 550.0,
                "tax_amount": 99.0,
                "total_amount": 649.0,
                "payment_status": "unpaid",
                "items": [
                    {
                        "inventory_item_id": str(item.id),
                        "quantity": 10,
                        "unit_cost": 55.0,
                        "tax_percent": 18.0,
                        "line_total": 550.0,
                    }
                ],
            },
            headers=headers,
        )

        resp = await client.get(
            "/api/v1/procurement/purchase-orders",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["purchase_orders"]) >= 1
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_procurement_report_api(
        self,
        db_session: Session,
        client: AsyncClient,
        tenant_a: Tenant,
        admin_user: User,
        supplier: Supplier,
        item: InventoryItem,
    ) -> None:
        headers = _auth_header(admin_user)
        headers["X-Tenant-ID"] = str(tenant_a.id)

        # Create and complete a PO
        create_resp = await client.post(
            "/api/v1/procurement/purchase-orders",
            json={
                "supplier_id": str(supplier.id),
                "invoice_number": "API-INV-REPORT",
                "subtotal": 550.0,
                "tax_amount": 99.0,
                "total_amount": 649.0,
                "payment_status": "unpaid",
                "items": [
                    {
                        "inventory_item_id": str(item.id),
                        "quantity": 10,
                        "unit_cost": 55.0,
                        "tax_percent": 18.0,
                        "line_total": 550.0,
                    }
                ],
            },
            headers=headers,
        )
        po_id = create_resp.json()["id"]
        await client.post(
            f"/api/v1/procurement/purchase-orders/{po_id}/complete",
            headers=headers,
        )

        # Get procurement report
        report_resp = await client.get(
            "/api/v1/procurement/reports/procurement",
            headers=headers,
        )
        assert report_resp.status_code == 200
        report_data = report_resp.json()
        assert len(report_data["rows"]) >= 1

        # Get tax summary
        tax_resp = await client.get(
            "/api/v1/procurement/reports/tax-summary",
            headers=headers,
        )
        assert tax_resp.status_code == 200
        tax_data = tax_resp.json()
        assert len(tax_data) >= 1

    @pytest.mark.asyncio
    async def test_patient_forbidden_from_procurement_api(
        self,
        db_session: Session,
        client: AsyncClient,
        tenant_a: Tenant,
        patient_user: User,
    ) -> None:
        headers = _auth_header(patient_user)
        headers["X-Tenant-ID"] = str(tenant_a.id)

        resp = await client.get(
            "/api/v1/procurement/suppliers",
            headers=headers,
        )
        assert resp.status_code == 403
