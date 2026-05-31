"""
Delete appointment POST idempotency keys older than N days.

Schedule (example):
  0 3 * * * cd /path/to/backend && .venv/Scripts/python scripts/cleanup_appointment_idempotency.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python scripts/cleanup_appointment_idempotency.py` from backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.core.database import SessionLocal
from app.crud import crud_appointment


def main() -> None:
    db = SessionLocal()
    try:
        deleted = crud_appointment.delete_expired_appointment_idempotency_records(
            db, older_than_days=7
        )
        db.commit()
        print(f"deleted_rows={deleted}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
