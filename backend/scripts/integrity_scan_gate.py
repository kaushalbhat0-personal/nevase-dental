"""
Run system integrity checks against PostgreSQL without going through HTTP.

Designed for cron or deploy pipelines wired with ``DATABASE_URL``:

  python scripts/integrity_scan_gate.py --tenant-id "<uuid>"
  python scripts/integrity_scan_gate.py --all-tenants   # privileged: scans everything

Deploy gate:

  Exit code 1 when ``critical_count > 0`` (fail CI/CD / rollback).
  Optional: set ``INTEGRITY_ALERT_WEBHOOK_URL`` (Slack/Discord incoming webhook)
  for a POST on any detected issue.

Environment:

  DATABASE_URL — required (same as API).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import UUID

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _maybe_alert_webhook(url: str | None, body: dict) -> None:
    if not url or not str(url).strip():
        return
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(str(url).strip(), data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except urllib.error.HTTPError:
        sys.stderr.write("integrity_scan_gate: webhook POST failed (HTTP)\n")
    except urllib.error.URLError as exc:
        sys.stderr.write(f"integrity_scan_gate: webhook POST failed: {exc}\n")


def main() -> None:
    from app.core.database import SessionLocal
    from app.services import integrity_scan_service

    ap = argparse.ArgumentParser(description="DB integrity gate (CRITICAL-safe deploy blocker)")
    ap.add_argument(
        "--tenant-id",
        dest="tenant_id",
        default=None,
        help="Tenant UUID to scan (omit with --all-tenants only)",
    )
    ap.add_argument(
        "--all-tenants",
        action="store_true",
        help="Scan all tenants (heavy; intended for guarded automation only)",
    )
    args = ap.parse_args()

    if args.all_tenants:
        tenant_uuid = None
    elif args.tenant_id:
        tenant_uuid = UUID(args.tenant_id)
    else:
        ap.error("provide --tenant-id or --all-tenants")

    db = SessionLocal()
    try:
        snapshot = integrity_scan_service.scan_system_invariants(
            db,
            tenant_id=tenant_uuid,
            all_tenants=bool(args.all_tenants),
        )
        db.commit()
        out = snapshot.model_dump(mode="json")
        print(json.dumps(out, indent=2))
        webhook = os.getenv("INTEGRITY_ALERT_WEBHOOK_URL")

        warning_count = int(snapshot.warning_count)
        critical_count = int(snapshot.critical_count)
        if critical_count > 0 or warning_count > 0:
            _maybe_alert_webhook(
                webhook,
                {
                    "text": json.dumps(out)[:3900],
                    "critical_count": critical_count,
                    "warning_count": warning_count,
                },
            )

        sys.exit(1 if critical_count > 0 else 0)
    finally:
        db.close()


if __name__ == "__main__":
    main()
