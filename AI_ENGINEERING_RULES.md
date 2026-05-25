# AI_ENGINEERING_RULES.md

> **Internal Engineering Governance Document**
> This is the permanent engineering and AI-agent operating contract for this repository.
> Not marketing. Not documentation. A hard contract.

---

## 1. Project Philosophy

- **Production-first mindset.** Every change is evaluated against its production impact. Dev-only convenience never justifies production risk.
- **Stabilization over rewrites.** Broken code is fixed incrementally. Rewrites are never justified unless the existing structure is provably un-fixable and explicitly approved.
- **Incremental changes over broad refactors.** One problem, one fix, one PR. Broad refactors introduce hidden regressions and are prohibited without an explicit stabilization plan.
- **Explicit invariants over implicit assumptions.** Every architectural rule must be stated explicitly. Assumed-safe behavior is not safe. If it isn't written, it isn't enforced.

---

## 2. Core Architectural Invariants

These rules must never be violated. Any change that touches these concerns requires explicit review.

- **Workspace is contextual only, never authorization.** A workspace identifies operational context (e.g., which clinic staff are assigned to). It is never a permission boundary. Authorization is never derived from workspace membership alone.
- **Appointment is the canonical encounter anchor.** All clinical encounters are anchored to an appointment record. Encounters do not exist independently of appointments.
- **Patient identities are global.** A `Patient` record is tenant-agnostic. `patient.tenant_id` is always `NULL`. Patients are shared across tenants.
- **User UUID ≠ Patient UUID ≠ Doctor UUID.** These are distinct identity domains. Cross-domain identity assumptions are a security vulnerability.
- **Prescriptions are canonical longitudinal records.** A prescription, once committed, is part of the permanent clinical record. It must not be silently overwritten, deleted, or reconstructed.
- **Inventory dispensing is separate from prescriptions.** Dispensing an item from inventory is a separate transaction from writing a prescription. They are linked but never merged.
- **Medication schedules derive from prescriptions.** Schedules are always derived from an existing prescription. A schedule without a prescription anchor is invalid.
- **Authorization is capability/resource based.** Permissions are checked via declared capabilities (e.g., `has_clinician_capability()`) and resource ownership. Role names alone are insufficient.
- **Resource ownership is authoritative.** The owner of a resource (appointment, prescription, document) is the authoritative access check. Ownership overrides general role checks.
- **Tenant isolation must never weaken.** No change may introduce a path where a tenant can read, write, or infer data belonging to another tenant.

---

## 3. Authorization Rules

- **`has_clinician_capability(user, resource)`** is the canonical check for clinical action permissions. It must be called with the full resource context, not just the user.
- **Tenant/resource ownership enforcement** must be applied at the service layer, not the view layer. Views must not be the last line of defense.
- **Assigned doctor enforcement** — only the doctor explicitly assigned to an appointment may perform clinical writes on that encounter unless an explicit escalation path is defined.
- **Frontend-trusted authorization is prohibited.** The backend must never trust authorization signals sent from the frontend (e.g., `is_admin: true` in request body). All authorization is backend-resolved.
- **Workspace-based permission checks are prohibited.** Membership in a workspace never grants capability. Workspace context is read-only metadata for scoping queries, not for granting access.

---

## 4. Multi-Tenancy Rules

- **`patient.tenant_id` is always `NULL`.** Patients are global. Any query filtering patients by `tenant_id` is incorrect.
- **`appointment.tenant_id` is authoritative.** The tenant context for any clinical operation is resolved from the appointment, not from the requesting user's profile or workspace.
- **All mutations must be tenant-scoped.** Any write operation that is not explicitly scoped to a resolved tenant is a violation.
- **Cross-tenant mutations are prohibited.** A user in Tenant A must never be able to create, update, or delete records owned by Tenant B, regardless of their role.
- **Superadmin limitations apply.** Superadmin access grants visibility, not unrestricted mutation. Superadmin operations that mutate tenant-specific data must still pass tenant-scoped validation.

---

## 5. Encounter & Prescription Rules

- **Encounter lifecycle:** `created → in_progress → completed`. Transitions are unidirectional. A completed encounter must not be re-opened without an explicit override flow.
- **Prescription persistence requirements:** Prescriptions must be persisted to the database before any derived operation (schedule creation, dispensing, billing) runs. In-memory-only prescriptions are invalid.
- **Medication schedule derivation:** Schedules are always computed from the persisted prescription. They are never written independently. If the prescription changes, the schedule must be invalidated and re-derived.
- **Inventory vs prescription separation:** An inventory dispense record references a prescription but does not replace it. The two records have independent lifecycles.
- **Immutable prescription history expectations:** Prescription history must be append-only. Corrections are additive (new record, deprecated old). Silent updates to historical prescriptions are forbidden.

---

## 6. Safe Editing Rules

These rules apply to all code changes, regardless of source (human or AI agent).

- **Avoid broad rewrites.** Do not reconstruct a file to fix a single issue. Identify the smallest possible change.
- **Avoid reconstructing files.** Never use a full file write to fix a logic error inside a function. Use surgical edits.
- **Prefer surgical edits.** Change only the lines that require change. Leave surrounding code untouched.
- **Inspect before modifying.** Read the full function and its call sites before editing. Never edit blind.
- **Never use `write_to_file` on existing service files.** Service files (e.g., `appointment_service.py`, `prescription_service.py`) must only be modified via targeted line replacements. Full overwrites are forbidden.
- **Test after every change.** Run the targeted test suite immediately after each change. Do not batch changes and test later.
- **Preserve API contracts unless explicitly migrating.** Function signatures, return shapes, and HTTP response structures must not change unless a migration plan is in place and approved.

---

## 7. AI Agent Workflow

All AI agents operating in this repository must follow this sequence strictly. Deviation is a violation.

```
1. INSPECT      — Read the relevant file(s) and understand current state.
2. UNDERSTAND   — Trace the execution path. Identify all affected call sites.
3. EXPLAIN      — State the root cause explicitly before proposing any fix.
4. PROPOSE      — Describe the minimal change required. Do not begin editing yet.
5. APPLY        — Make the minimal change only. No scope creep.
6. VALIDATE     — Run targeted tests against the changed code path.
7. STOP         — Report result. Do not continue into unrelated areas.
```

**Hard stops:** If corruption symptoms appear (data inconsistency, auth bypass, unexpected 500s), stop immediately. Do not attempt to self-recover without a checkpoint.

---

## 8. Dangerous Anti-Patterns

These must never appear in this codebase.

| Anti-Pattern | Description |
|---|---|
| **Hidden workspace auth** | Using workspace membership as an implicit authorization signal |
| **Identity mixing** | Treating `user_id` as `patient_id` or `doctor_id` interchangeably |
| **Frontend-trusted authorization** | Accepting permission claims from client request bodies |
| **Silent fallback permissions** | Defaulting to a permissive state when auth context is ambiguous |
| **Tenant leakage** | Any query path that returns cross-tenant data under any condition |
| **Giant service rewrites** | Replacing a full service file to fix a targeted issue |
| **Speculative refactors** | Refactoring code that is not directly related to the current task |
| **Stale schema assumptions** | Writing queries or migrations based on assumed schema without inspecting the current migrations |

---

## 9. Validation Requirements

After any change to service, model, migration, or authorization code, the following checks are required before the change is considered complete.

- **`pytest` targeted tests** — Run the test module(s) directly covering the changed code path. Not the full suite; the targeted subset.
- **TypeScript compile** — If any frontend code is modified, `tsc --noEmit` must pass.
- **Tenant isolation validation** — Confirm via test or manual trace that no cross-tenant data path is introduced.
- **Authorization validation** — Confirm that the capability check is called correctly and that no bypass path exists.
- **API contract validation** — Confirm that all public endpoints return the same shape as before. If shape changes, document the delta.
- **Migration safety check** — All migrations must be additive. Destructive migrations (column drops, table renames) require an explicit deprecation step and must not run in the same deploy as the feature change.

---

## 10. Production Safety Rules

- **No debug logs in production paths.** `print()`, `console.log()`, and ad-hoc debug statements must not exist in production code paths. Use structured logging only.
- **No exception leakage.** Internal exception details (stack traces, model field names, SQL errors) must never be returned to the client. Wrap and sanitize all errors at the API boundary.
- **Structured logging expectations.** All log events must include: `tenant_id`, `user_id`, `resource_type`, `resource_id`, and `action`. Unstructured log strings are unacceptable in service-layer code.
- **Idempotency requirements.** All mutation endpoints (create, update, dispense, schedule) must be idempotent where technically feasible. Duplicate submissions must not result in duplicate records.
- **Additive migration policy.** Migrations add columns, tables, or indexes. They do not drop, rename, or restructure existing columns in the same deploy window as a feature. Two-phase migration is required for destructive changes.

---

## 11. Technical Debt Areas

These are known debt items. They are documented here as awareness artifacts. **Do not refactor them without an explicit task.**

| Area | Debt Description |
|---|---|
| `appointment_service.py` | Excessive coupling. Handles scheduling, authorization, encounter linkage, and notification in a single service. Needs decomposition, but decomposition is risky without full test coverage. |
| Document service | Fragile file-path resolution logic. Sensitive to runtime environment differences. Do not touch without a dedicated stabilization task. |
| Standalone prescription auto-derive | Inconsistent behavior when prescriptions are created outside an encounter context. Schedule auto-derivation may silently fail. |
| Tenant resolution complexity | Tenant is resolved from multiple sources (appointment, user profile, workspace) with unclear precedence. This must be centralized but has wide blast radius. |
| Large service files | Several service files exceed reasonable size limits. They are not to be rewritten wholesale; incremental extraction only when a specific function is being modified. |

---

## 12. AI Session Rules

Rules that govern the scope and behavior of any AI-assisted development session.

- **Prefer small, focused tasks.** Each session should address one clearly scoped issue. Multi-issue sessions lead to entangled changes and hidden regressions.
- **Avoid endless investigation loops.** If the root cause is not identified within 3 inspection steps, stop and report. Do not keep digging without user direction.
- **Stop after root cause + fix.** Once the fix is applied and validated, the session ends. Do not proactively refactor adjacent code.
- **Checkpoint before risky changes.** Before modifying any file listed in §11 (Technical Debt Areas) or any authorization/migration file, explicitly state what is being changed and why, and wait for confirmation.
- **Never continue after corruption symptoms appear.** If any test reveals data inconsistency, a missing record, or an authorization bypass — stop. Report the symptom. Do not attempt to auto-repair without a clean understanding of the cause.

---

*Last updated: 2026-05-19*
*Maintained by: Engineering Lead*
*Applies to: All contributors, human and AI*
