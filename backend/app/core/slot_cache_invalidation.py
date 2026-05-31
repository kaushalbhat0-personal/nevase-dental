"""Purge Upstash (shared) slot read cache after commit when availability, time off, or doctor timezone changes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import Session

# Session.info key: set[UUID] of doctor_ids whose (doctor,date) slot cache must be purged
_PENDING = "pending_doctor_slot_cache_invalidations"


def schedule_invalidate_doctor_slot_cache_on_commit(db: Session, doctor_id: UUID) -> None:
    """
    After this session successfully commits, drop all cached slot lists for the doctor
    (every date) via ``redis_delete_pattern("slots:{doctor_id}:*")``.

    Do not call after commit — register before commit/flush; SQLAlchemy runs the flush on commit.
    """
    db.info.setdefault(_PENDING, set()).add(doctor_id)


@event.listens_for(Session, "after_commit")
def _after_commit_purge_slot_cache(session: Session) -> None:
    pending = session.info.pop(_PENDING, None)
    if not pending:
        return
    from app.services import doctor_slot_service

    for doc_id in pending:
        logger.debug("Invalidating slot cache for: %s", doc_id)
        doctor_slot_service.invalidate_all_slots_cache_for_doctor(doc_id)


@event.listens_for(Session, "after_rollback")
def _after_rollback_clear_pending_slot_cache(session: Session) -> None:
    session.info.pop(_PENDING, None)
