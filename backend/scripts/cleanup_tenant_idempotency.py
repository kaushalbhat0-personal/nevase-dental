"""
Delete POST /tenants idempotency keys older than N days (table tenant_creation_idempotency).

Schedule (example, weekly):
  0 4 * * 0 cd /path/to/backend && .venv/Scripts/python scripts/cleanup_tenant_idempotency.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.core.database import SessionLocal
from app.crud import crud_tenant


def main() -> None:
    db = SessionLocal()
    try:
        deleted = crud_tenant.delete_expired_tenant_idempotency_records(db, older_than_days=7)
        db.commit()
        print(f"deleted_rows={deleted}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
