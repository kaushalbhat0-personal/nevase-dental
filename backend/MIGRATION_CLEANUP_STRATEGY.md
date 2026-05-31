# Migration Cleanup Strategy (Future — DO NOT EXECUTE NOW)

**Status:** 📋 Documented plan only — NOT for immediate execution  
**Prerequisite:** All z-series migrations must be applied on production first

---

## Overview

The migration graph currently has 49 files with 2 merge points and a long chain dating back to the initial schema. While the graph is healthy, it is large and complex. This document outlines a strategy to consolidate the history **without rewriting production history**.

---

## Strategy: Baseline Snapshot Migration

### Step 1 — Create a Baseline Snapshot

Create a single migration that captures the **current schema state** as a new root:

```python
"""Migration baseline snapshot — consolidates all prior migrations.

Revision ID: baseline_2026_05_11
Revises: None  # ← This is the key: it becomes the new root
"""
```

This migration would:
- Have `down_revision = None` (becomes the new root)
- Contain `op.create_table(...)` for every table in the current schema
- Contain `op.execute("CREATE TYPE ...")` for every enum
- Contain `op.create_index(...)` for every index
- Contain `op.create_unique_constraint(...)` for every constraint
- Be **empty** in `upgrade()` (no-op) — the schema already exists
- Be used only for fresh database provisioning

### Step 2 — Archive Old Revisions

Move all existing migration files to an archive directory:

```
alembic/
├── versions/          # ← Only the baseline + future migrations
│   └── baseline_2026_05_11.py
├── archive/           # ← Historical migrations (reference only)
│   ├── f8a1b2c3d4e5_initial_postgresql_schema.py
│   ├── b2c3d4e5f6a7_add_tenant_address_phone.py
│   └── ...
└── env.py
```

Alembic will only look in `versions/`. The archive is for reference and audit.

### Step 3 — Staging Verification

1. **Provision a fresh staging database** (no existing schema)
2. Run `alembic upgrade head` — should apply the baseline only
3. Verify all tables, enums, indexes, and constraints exist
4. Run the application test suite
5. Run integrity scans

### Step 4 — Production Cutover

**Critical: Do NOT stamp or modify the production `alembic_version` table.**

The baseline is for **new database provisioning only**. Production keeps its existing `alembic_version` entry.

For production:
- Continue using the existing migration chain
- The baseline is only used when provisioning a **new** database (e.g., new tenant shard, disaster recovery)

### Step 5 — Future Migrations

After the baseline is in place:
- New migrations use `down_revision = "baseline_2026_05_11"`
- They apply on top of the baseline for fresh DBs
- They apply on top of the existing chain for existing DBs (Alembic handles this automatically)

---

## Alternative: Squash + Re-stamp (Higher Risk)

This approach is **NOT recommended** for production systems with active data.

1. Create a squash migration that contains all DDL from all 49 migrations
2. On production: `alembic stamp baseline_2026_05_11` to mark the DB as at the baseline
3. Remove old migration files from `versions/`
4. Future migrations reference the baseline

**Risks:**
- `alembic stamp` is a manual operation that can silently corrupt the version table
- If the squash misses any DDL, the schema diverges from the migration history
- Rollback becomes impossible without the full chain
- Debugging production issues becomes harder without the granular history

---

## Recommendation

**Do not squash.** Use the **Baseline Snapshot** approach (Step 1-5 above) when:

1. The migration count exceeds 100 files
2. New team members consistently struggle with the migration history
3. Fresh database provisioning takes more than 5 minutes
4. A new major version (v2.0) is being released

Until then, the current graph is healthy and maintainable.

---

## Pre-requisites Before Executing

- [ ] All z-series migrations applied on production
- [ ] No pending migrations in any environment
- [ ] Staging DB is in sync with production
- [ ] Full backup of production database
- [ ] Team consensus on the approach
- [ ] Rollback plan documented
