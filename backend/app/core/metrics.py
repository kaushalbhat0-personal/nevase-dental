"""Process-local counters for operations observability (Prometheus-compatible names, no deps)."""

from __future__ import annotations

import threading
from collections import defaultdict

_lock = threading.Lock()
_counters: defaultdict[str, int] = defaultdict(int)

# Counter names (stable for dashboards / future Prometheus wiring):
# appointments_completed_total
# inventory_deductions_total
# idempotency_replays_total
# cross_tenant_blocked_total
# idempotency_outcome_hash_mismatch_total


def inc_counter(name: str, delta: int = 1) -> None:
    if delta == 0:
        return
    with _lock:
        _counters[name] += delta


def get_counters_snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counters)
