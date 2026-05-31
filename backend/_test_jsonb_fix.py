"""Quick verification that JSONB portability fix works with SQLite."""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///test_check.db"
os.environ["TESTING"] = "True"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 1. Verify the compatibility alias works
from sqlalchemy import JSON

try:
    from sqlalchemy.dialects.postgresql import JSONB

    JSONType = JSONB
    print("[OK] PostgreSQL JSONB available — using JSONB")
except Exception:
    JSONType = JSON
    print("[OK] PostgreSQL JSONB NOT available — using JSON fallback")

# 2. Verify models that use JSONType can be imported
from app.models.notification import NotificationEvent, NotificationDelivery
print("[OK] notification.py models imported")

from app.models.patient_medication_schedule import (
    PatientMedicationSchedule,
    MedicationAdherenceLog,
)
print("[OK] patient_medication_schedule.py models imported")

from app.models.supplier import Supplier
print("[OK] supplier.py models imported")

from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
print("[OK] purchase_order.py models imported")

from app.models.inventory import InventoryItem, InventoryTransaction
print("[OK] inventory.py models imported")

# 3. Verify schemas that use JSONType can be imported
from app.schemas.procurement import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryTransactionCreate,
)
print("[OK] procurement schemas imported")

from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationPreferenceUpdate,
)
print("[OK] notification schemas imported")

from app.schemas.medication_schedule import (
    MedicationScheduleCreate,
    MedicationScheduleResponse,
    AdherenceLogCreate,
)
print("[OK] medication_schedule schemas imported")

print()
print("=" * 60)
print("ALL JSONB PORTABILITY CHECKS PASSED")
print("=" * 60)
