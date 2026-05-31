"""Dialect-aware UUID values for ORM, seeds, and raw SQL."""

from __future__ import annotations

from typing import Any
from uuid import UUID


def as_db_uuid(value: str, db: Any) -> str | UUID:
    """
    Return a plain string for SQLite, :class:`uuid.UUID` for other dialects.

    Avoids type coercion that breaks some SQLite/bootstrap paths while keeping
    PostgreSQL-typed columns happy elsewhere.
    """
    url: str
    if hasattr(db, "get_bind"):
        url = str(db.get_bind().url)
    elif hasattr(db, "url"):
        url = str(db.url)
    elif hasattr(db, "engine") and db.engine is not None:
        url = str(db.engine.url)
    else:
        url = str(db)
    return value if "sqlite" in url.lower() else UUID(value)
