import logging
import uuid
from uuid import UUID

from sqlalchemy import text

from app.core.database import engine
from app.core.security import hash_password
from app.models.tenant import TenantType
from app.utils.db_uuids import as_db_uuid

logger = logging.getLogger(__name__)

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Sentinel sometimes stored by mistake; treat as "no tenant" like NULL.
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

            # ── Seed default admin user if none exists ──
            logger.info("Checking if admin user exists...")
            existing_admin = conn.execute(
                text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
            ).fetchone()
            logger.info(f"Existing admin found: {existing_admin is not None}")

            if not existing_admin:
                logger.info("No admin found, creating default admin...")
                try:
                    conn.execute(
                        text("""
                            INSERT INTO users (id, email, hashed_password, full_name, role, is_active)
                            VALUES (:id, :email, :password, :name, :role, true)
                            ON CONFLICT (email) DO NOTHING
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "email": "admin@nevase.com",
                            "password": hash_password("Admin@123"),
                            "name": "Clinic Admin",
                            "role": "admin",
                        },
                    )
                    logger.info("Default admin user created: admin@nevase.com")
                except Exception as inner:
                    logger.error(f"Failed to insert admin user: {inner}")
                    raise
            else:
                logger.info(f"Admin already exists: id={existing_admin[0]}")
    except Exception as e:
        logger.warning(f"Could not seed default tenant: {e}")
