# Migration Graph Audit Report

**Date:** 2026-05-11  
**Status:** ✅ STABLE — Single healthy head, no broken chains, no circular refs  
**Production DB:** `z4_notification_communication` (head)

---

## 1. ROOT CAUSE ANALYSIS

### The "Can't locate revision: z4_notification_communication" Error

**Finding:** The error is **NOT** caused by a broken migration graph in this repository. The graph is healthy and resolves correctly.

**Likely root causes on production:**

1. **Deployment race condition:** The `z4_notification_communication.py` file was not present in the deployed artifact when `alembic upgrade head` ran. This can happen if:
   - The migration file was added to the repo but not deployed yet
   - A partial deploy occurred (e.g., code deployed but migrations not included)
   - The deployment process uses a different branch/tag than expected

2. **Stale `alembic_version` table:** If a previous deploy partially applied `z4_notification_communication` (or it was manually stamped), but the file was later removed or renamed, Alembic would fail to find it.

3. **Deployment script issue:** The start command `alembic upgrade head` runs before the code is fully extracted, or the `versions/` directory is incomplete.

### Cosmetic Issue Found (Non-Breaking)

| File | Internal `revision` | Filename | Impact |
|------|-------------------|----------|--------|
| `z1_full_tenant_cleanup_hardening.py` | `"z1_full_tenant_cleanup"` | `z1_full_tenant_cleanup_hardening.py` | **Cosmetic only.** The revision ID `"z1_full_tenant_cleanup"` is what's stamped in the DB. The filename mismatch does NOT break the graph because Alembic uses the internal `revision` field, not the filename. |

**No other filename-vs-revision mismatches exist** in the 49 migration files.

---

## 2. GRAPH VERIFICATION

### `alembic heads` — Single healthy head
```
z4_notification_communication (head)
```

### `alembic current` — DB is at head
```
z4_notification_communication (head)
```

### `alembic upgrade head` — Idempotent (no-op)
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```
(No migrations to run — already at head.)

### `alembic_version` table
```
version_num: z4_notification_communication
```

### Graph Structure

```
f8a1b2c3d4e5 (root)
  └── b2c3d4e5f6a7
       └── c3d4e5f6a7b8
            └── d4e5f6a7b8c9
                 └── e2f3a4b5c6d7
                      └── a1b2c3d4e5f6
                           └── b3c4d5e6f7a8
                                └── c5d6e7f8a9b0
                                     └── d5e6f7a8b9c0
                                          └── f0e1d2c3b4a5
                                               └── a9b8c7d6e5f4
                                                    └── f1a2b3c4d5e6
                                                         └── g2h3i4j5k6l7
                                                              └── h3i4j5k6l7m8
                                                                   └── i4j5k6l7m8n9
                                                                        └── j5k6l7m8n9o1
                                                                             └── k6l7m8n9o0p2
                                                                                  └── m7n8o9p0q1r2
                                                                                       └── n8o9p0q1r2s3
                                                                                            ├── p1q2r3s4t5u6
                                                                                            │    └── v1w2x3y4z5a6
                                                                                            │         └── w2x3y4z5a6b7
                                                                                            │              └── z1a2b3c4d5e6
                                                                                            │                   └── a2b3c4d5e6f7
                                                                                            │                        └── a3b4c5d6e7f8
                                                                                            │                             └── b4c5d6e7f8a1
                                                                                            │                                  └── c5d6e7f8a9b2
                                                                                            │                                       └── d6e7f8a9b0c3
                                                                                            │                                            └── f7a8b9c0d1e2
                                                                                            │                                                 └── g9h0i1j2k3l4
                                                                                            │                                                      └── h0i1j2k3l4m5
                                                                                            │                                                           └── h1i2j3k4l5m6
                                                                                            │                                                                └── i1j2k3l4m5n6
                                                                                            │                                                                     └── z1_full_tenant_cleanup ──┐
                                                                                            └── n9o0p1q2r3s4                                                                                    │
                                                                                                 └── 5a93cca8f072                                                                               │
                                                                                                      └── adfef084535d                                                                          │
                                                                                                           └── 0fe071b8e03e                                                                     │
                                                                                                                └── 19677072c567 ──┤                                                             │
                                                                                                                                   │                                                             │
                                                                                            o0p1q2r3s4t5 ──────────────────────────┘                                                             │
                                                                                                                                     │                                                             │
                                                                                            p1q2r3s4t6 (merge) ◄────────────────────┘                                                             │
                                                                                              └── z2a3b4c5d6e7                                                                                    │
                                                                                                   └── ecc6aa611584 ────────────────┘                                                             │
                                                                                                                                     │
                                                                                            z2_reporting_indexes (merge) ◄──────────┘
                                                                                              └── z3_tenant_branding_profiles
                                                                                                   └── z4_notification_communication (HEAD)
```

### Checks Passed

| Check | Result |
|-------|--------|
| Single head | ✅ `z4_notification_communication` |
| No orphaned revisions | ✅ All 49 files reachable from root |
| No broken chains | ✅ Every `down_revision` resolves to an existing file |
| No circular references | ✅ Graph is a DAG |
| `alembic upgrade head` | ✅ Idempotent (no-op on current DB) |
| `alembic current` | ✅ Matches head |
| `alembic_version` table | ✅ Single entry: `z4_notification_communication` |

---

## 3. FIXES APPLIED

**No code changes were needed.** The migration graph is healthy and deploy-safe.

The only issue found was cosmetic:
- `z1_full_tenant_cleanup_hardening.py` has internal `revision = "z1_full_tenant_cleanup"` (filename has `_hardening` suffix)
- **Not fixed** because changing it would break production compatibility (the DB already has `z1_full_tenant_cleanup` stamped)

---

## 4. DEPLOYMENT SAFETY RECOMMENDATIONS

To prevent the "Can't locate revision" error from recurring:

1. **Ensure migration files are included in the deployment artifact** — verify `alembic/versions/` is not in `.gitignore` or excluded from build
2. **Run `alembic upgrade head` as part of CI/CD** — not just at startup — to catch missing files early
3. **Use `alembic upgrade head --sql` in CI** to validate the graph without a database connection (note: some migrations use `sa.inspect()` which fails in offline mode — this is a known limitation)
4. **Pin deployment to a specific git tag** — avoid deploying from branches mid-development
5. **Add a pre-deploy check** that verifies all revisions referenced in `down_revision` fields exist as files

---

## 5. FUTURE CLEANUP STRATEGY

See [MIGRATION_CLEANUP_STRATEGY.md](./MIGRATION_CLEANUP_STRATEGY.md) for the documented plan.
