"""Shared UTC normalization for appointment instants (slot alignment, comparisons)."""

from __future__ import annotations

from datetime import datetime, timezone


def normalize_appointment_time_utc(dt: datetime) -> datetime:
    """UTC-aware instant with second=0 and microsecond=0 for stable comparisons and storage."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(second=0, microsecond=0)
