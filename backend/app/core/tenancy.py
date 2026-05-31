import uuid
from uuid import UUID

from sqlalchemy import text

from app.core.database import engine
from app.models.tenant import TenantType
from app.utils.db_uuids import as_db_uuid

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Sentinel sometimes stored by mistake; treat as “no tenant” like NULL.
NIL_TENANT_UUID_SENTINEL = UUID("00000000-0000-0000-0000-000000000000")


def non_nil_tenant_id(value: UUID | None) -> UUID | None:
    """Map NULL and the all-zero UUID sentinel to None for tenant resolution."""
    if value is None or value == NIL_TENANT_UUID_SENTINEL:
        return None
    return value
DEFAULT_TENANT_NAME = "Default"


def ensure_default_tenant_exists() -> None:
    """
    Idempotent: guarantees the well-known default tenant row exists.

    We keep a fixed UUID as a "sentinel" tenant so foreign keys (e.g. user↔tenant association)
    always have at least one valid tenant to reference in fresh databases.

    Implementation notes:
    - Uses a direct INSERT ... ON CONFLICT for startup safety and to avoid importing ORM models
      (which can trigger extra side effects during application boot).
    - Runs inside a transaction so it can be safely called at startup in a process supervisor.
    """
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO tenants (id, name, type, is_active) "
                    "VALUES (:id, :name, :type, true) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": as_db_uuid(str(DEFAULT_TENANT_ID), conn),
                    "name": DEFAULT_TENANT_NAME,
                    "type": TenantType.organization.value,
                },
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not seed default tenant: {e}")
