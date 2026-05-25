# Codebase Expert Analysis — Hospital Management System

> **Status:** Stabilization phase · **Phase:** Read-only expert survey · **Date:** 2026-05-18

---

## 1. High-Level Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                     │
│   React 19 + TypeScript SPA   │   External API consumers (JWT)     │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ HTTPS
┌──────────────────▼──────────────────────────────────────────────────┐
│                    FastAPI  (backend/app/main.py)                   │
│  Middleware stack:                                                  │
│    CORS → request_trace → debug_cors_origin → log_requests         │
│    PublicEndpointRateLimitMiddleware                                │
│    AuthenticatedWritePostRateLimitMiddleware                        │
│    IntegrityScanGetRateLimitMiddleware                              │
│                                                                     │
│  /health  (no auth)   /api/v1/* (all versioned routes)             │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────────┐
│                  API Router  (api/v1/router.py)                     │
│  29 endpoint modules registered                                     │
└──────────┬────────────────────────────────────────┬─────────────────┘
           │ Depends()                              │
┌──────────▼──────────┐                 ┌──────────▼────────────────┐
│   deps.py           │                 │  Service layer            │
│   - get_current_user│                 │  (42 service files)       │
│   - get_scoped_     │                 │  appointment_service.py   │
│     tenant_id       │                 │  billing_service.py       │
│   - get_active_     │                 │  encounter_service.py     │
│     workspace       │                 │  inventory_service.py     │
│   - get_current_    │                 │  medication_schedule_     │
│     doctor          │                 │   service.py  …etc        │
└──────────┬──────────┘                 └──────────┬────────────────┘
           │                                       │
┌──────────▼───────────────────────────────────────▼────────────────┐
│                       CRUD layer  (app/crud/)                      │
└──────────────────────────────────┬────────────────────────────────┘
                                   │
┌──────────────────────────────────▼────────────────────────────────┐
│               SQLAlchemy 2.0 ORM  (app/models/)                   │
│   PostgreSQL (prod) / SQLite in-memory (tests)                    │
└───────────────────────────────────────────────────────────────────┘
```

**Strict Layering Rule** (documented + enforced):
`Router → Service → CRUD → ORM`
Routers never call CRUD directly for mutations.

---

## 2. Backend Domain / Service Structure

### Domain Map

| Domain | Key Models | Key Services | Endpoints |
|--------|-----------|--------------|-----------|
| **Identity & Auth** | `User`, `UserTenant` | `auth_service`, `user_roles_service` | `auth.py`, `users.py` |
| **Tenancy** | `Tenant`, `UserTenant`, `TenantCreationIdempotency` | `tenant_service` | `tenant.py` |
| **Encounter** | `Appointment`, `AppointmentVitals`, `AppointmentInventoryUsage`, `Prescription`, `PrescriptionItem` | `appointment_service`, `encounter_service` | `appointment.py`, `encounter.py` |
| **Clinical Scheduling** | `DoctorAvailability`, `DoctorSlot` | `doctor_availability_service`, `doctor_slot_service` | via `doctor.py` |
| **Prescriptions** | `Prescription`, `PrescriptionItem` | `appointment_service` (embedded) | `appointment.py` |
| **Medication Schedules** | `PatientMedicationSchedule`, `MedicationAdherenceLog` | `medication_schedule_service` | `medication_schedule.py` |
| **Billing** | `Billing` | `billing_service` | `billing.py` |
| **Inventory** | `InventoryItem`, `InventoryStock`, `InventoryMovement`, `AppointmentInventoryUsage` | `inventory_service`, `procurement_service` | `inventory.py`, `procurement.py` |
| **Queue** | `ClinicQueue` | `queue_service`, `front_desk_service` | `clinic_queue.py`, `front_desk.py` |
| **Patient** | `Patient`, `PatientCommunicationPreference` | `patient_service`, `patient_workspace_service`, `patient_communication_service` | `patient.py`, `patient_workspace.py`, `patient_communication.py` |
| **Doctor Profile** | `DoctorProfile`, `DoctorVerificationLog` | `doctor_profile_service`, `doctor_service` | `doctor.py`, `doctor_profile.py` |
| **Notifications** | `Notification` | `notification_service`, `reminder_service` | `communications.py` |
| **Documents** | `Document` | `document_service` | `documents.py` |
| **Operations** | `ClinicAlert`, `StaffTask` | `clinic_operations_service` | `clinic_operations.py` |
| **Reporting** | — | `reporting_service`, `dashboard_service` | `reporting.py`, `dashboard.py` |
| **Branding** | `TenantBrandingProfile`, `TenantOrganizationProfile` | `tenant_branding_service` | `branding.py` |
| **Discovery** | — | `public_discovery_service` | `public_discovery.py` |

### Core Module (`app/core/`)

| File | Purpose |
|------|---------|
| `tenant_context.py` | Tenant resolution + enforcement (`resolve_tenant_id_for_scoped_request`, `align_operation_tenant_with_resource`) |
| `clinical_capabilities.py` | `has_clinician_capability()` — canonical clinical auth check |
| `workspace_context.py` | `ActiveWorkspace`, `ROLE_ALLOWED_WORKSPACES`, `is_elevated_workspace_access()` |
| `data_scope.py` | `X-Data-Scope` header — doctor vs tenant view |
| `permissions.py` | `has_tenant_admin_privileges`, `require_admin_or_owner` |
| `security.py` | JWT encode/decode |
| `rate_limit.py` | Three middleware rate limiters |
| `config.py` | Pydantic settings |
| `database.py` | SQLAlchemy session + engine |
| `slot_cache_invalidation.py` | SQLAlchemy event hooks for slot cache |

---

## 3. Frontend Workspace / Component Structure

### Workspace System (DO NOT REWRITE — documented)

```
workspace/
  registry.tsx          ← SINGLE SOURCE OF TRUTH for workspace definitions
  resolver.ts           ← post-login redirect logic
  route-isolation.tsx   ← route guards by workspace
  WorkspaceSwitcher.tsx ← UI switching
  useActiveWorkspace.ts ← hook
  contextual-redirects.ts
  layouts/
    DoctorWorkspaceLayout.tsx
    PatientWorkspaceLayout.tsx
    FrontDeskWorkspaceLayout.tsx
    OperationsWorkspaceLayout.tsx
    ProcurementWorkspaceLayout.tsx
    FinanceWorkspaceLayout.tsx
    contextual-header.tsx
```

### 6 Workspaces

| Slug | Layout | Roles |
|------|--------|-------|
| `admin` | Admin pages | `super_admin`, `admin` |
| `doctor` | `DoctorWorkspaceLayout` | `doctor` |
| `patient` | `PatientWorkspaceLayout` | `patient` |
| `frontdesk` | `FrontDeskWorkspaceLayout` | `staff` |
| `operations` | `OperationsWorkspaceLayout` | `staff` |
| `procurement` | `ProcurementWorkspaceLayout` | `staff` |
| `finance` | `FinanceWorkspaceLayout` | `staff`, `admin` |

### Pages (Containers) by Workspace

- **Doctor**: `DoctorAppointmentsPage`, `DoctorAppointmentDetailPage`, `DoctorPatientDetailPage`, `EncounterWorkspacePage`
- **Patient**: 15 patient pages (timeline, medicines, family, emergency, documents, discover…)
- **Procurement**: `PurchaseEntryModal`, `SupplierManagement`, `ProcurementReports`
- **Admin/Shared**: Dashboard, Patients, Doctors, Appointments, Billing, Branding, Communications, Financial

### Services Layer Pattern

`services/api.ts` — Axios instance with:
- **Request interceptor**: Attaches `Authorization: Bearer <token>`
- **Response interceptor**: 401→login, 403→toast, 500→error toast

Each domain has a typed service file (e.g., `services/appointments.ts`) with methods for list/get/create/update.

---

## 4. Authorization Flow Summary

### Three Independent Layers

```
Layer 1: IDENTITY     → User.role (from JWT)
Layer 2: CAPABILITY   → Doctor.user_id linkage (has_clinician_capability())
Layer 3: WORKSPACE    → X-Workspace header (UI context ONLY, NOT authorization)
```

### Canonical Capability Check

```python
# has_clinician_capability() returns True if ANY:
# 1. current_user.role == "doctor"
# 2. "doctor" in current_user.roles (dual-role list)
# 3. Doctor record exists where Doctor.user_id == current_user.id
```

### Authorization Decision Points

| Check | File | Purpose |
|-------|------|---------|
| `has_clinician_capability()` | `core/clinical_capabilities.py` | Clinical action gate |
| `assert_authorized()` | `services/security_audit.py` | Resource tenant match |
| `enforce_tenant_match()` | `services/security_audit.py` | Strict tenant enforcement |
| `validate_appointment_invariants()` | `services/appointment_invariants.py` | Doctor+tenant alignment |
| `align_operation_tenant_with_resource()` | `core/tenant_context.py` | Super-admin cross-tenant block |
| `resolve_tenant_id_for_scoped_request()` | `core/tenant_context.py` | Tenant resolution |

### Trust Boundaries (enforced)

1. Frontend tenant IDs → hints only (validated via `UserTenant` membership)
2. JWT claims → not authoritative alone (validated against DB)
3. Role names → not trusted for clinical actions (capability check required)
4. Resource `tenant_id` → always authoritative

---

## 5. Encounter Lifecycle Summary

```
Appointment.status transitions (AppointmentStatus enum):

scheduled → confirmed → arrived → checked_in → vitals_completed
         → waiting_for_doctor → in_consultation → completed
                               ↘ cancelled / no_show (terminal)
```

> **Note:** The model has MORE states than the docs describe (9 states vs 5 documented). `confirmed`, `arrived`, `vitals_completed`, `waiting_for_doctor`, `no_show` exist in the ORM enum but the docs only mention 5.

### Completion Side Effects (atomic transaction)

1. `appointment.status → completed`
2. Inventory deduction (if `items` provided)
3. Bill generation (if `generate_bill=True`)
4. Idempotency record created (`appointment_completion_idempotency`)
5. `AppointmentInvariantGuard.finalize()` called
6. Audit log emitted

### Encounter Aggregate (`EncounterDetailAggregate`)

Contains: Appointment + Patient + Doctor + Vitals + Clinical Notes + SOAP Notes + Diagnosis + Treatment Summary + Bills + Inventory Items + Queue Entry

---

## 6. Prescription + Medication Lifecycle Summary

### Two Distinct Systems

```
Prescription (canonical, immutable after creation)
  └── PrescriptionItem (per-medicine line)
        └── [auto-derived] PatientMedicationSchedule (adherence layer)
              └── MedicationAdherenceLog (patient actions: taken/skipped/snoozed)
```

### Prescription Creation Paths

| Path | Trigger | Function |
|------|---------|----------|
| **During completion** | `mark_appointment_completed` with `prescriptions[]` | `_create_appointment_prescriptions()` |
| **Standalone** | `POST /appointments/{id}/prescriptions` | `create_prescription_for_appointment()` |
| **Update** | `PUT /prescriptions/{id}` | `update_prescription()` |

### Medication Schedule Auto-Derivation

On prescription creation, `_derive_medication_schedules_from_prescription()` fires automatically:
- Each `PrescriptionItem` → one `PatientMedicationSchedule`
- `start_date` = `datetime.now(UTC)` at prescription creation
- `end_date` = parsed from `duration` string (supports: `7 days`, `2 weeks`, `1 month`, `1 year`)
- `is_active=True`, `status=active`
- Snapshotted fields: `medicine_name`, `dosage`, `frequency`, `duration`, `instructions` (read-only after creation)

### Key Invariant

> `PatientMedicationSchedule` is DERIVED, NEVER the source of truth.  
> Patient adherence actions (`taken`/`skipped`/`snoozed`) update `MedicationAdherenceLog` ONLY.  
> They NEVER mutate `Prescription` or `PrescriptionItem`.

---

## 7. Multi-Tenancy Enforcement Summary

### Tenant Isolation Rules (enforced in code)

| Rule | Implementation |
|------|---------------|
| Every query must be tenant-scoped | `filter(Model.tenant_id == tenant_id)` in all CRUD |
| Resource ownership is authoritative | `assert_authorized()` + `enforce_tenant_match()` |
| Super admin is NOT unrestricted | `align_operation_tenant_with_resource()` blocks cross-tenant mutations |
| Patients are GLOBAL (`tenant_id = NULL`) | Patient model has nullable `tenant_id` FK — MUST always be NULL |
| Appointment is tenant anchor | `appointment.tenant_id` is non-nullable, mandatory |
| Billing inherits appointment tenant | Integrity scan validates `bill.tenant_id == appointment.tenant_id` |

### Tenant Resolution Chain

```
Request arrives with X-Tenant-ID header + JWT
  ↓
resolve_tenant_id_for_scoped_request()
  ├─ patient → None (own data via patient row)
  ├─ super_admin → X-Tenant-ID required (validated against DB)
  └─ others → home tenant from DB; header must match (no spoofing)
```

### Idempotency Tables

- `tenant_creation_idempotency`
- `appointment_creation_idempotency`
- `appointment_completion_idempotency`
- `doctor_creation_idempotency` (from docs; not confirmed in model scan)

---

## 8. Critical Invariants That Must Never Break

| # | Invariant | Where Enforced |
|---|-----------|---------------|
| 1 | `appointment.doctor_id == doctor.id` for any encounter mutation | `validate_appointment_invariants()` |
| 2 | `appointment.tenant_id == doctor.tenant_id` | `validate_appointment_invariants()` |
| 3 | `patient.tenant_id` is ALWAYS NULL | DB model (nullable FK), documented constraint |
| 4 | `appointment.tenant_id` is NEVER NULL | Non-nullable column + DB constraint |
| 5 | `bill.tenant_id == appointment.tenant_id` | Integrity scan service |
| 6 | Appointment status transitions are forward-only | Service layer checks in `appointment_service.py` |
| 7 | `completed` and `cancelled` are terminal states | No code path should re-open them |
| 8 | `PatientMedicationSchedule` never mutates Prescription rows | Model design + service isolation |
| 9 | Inventory dispensing is separate from prescriptions | Two distinct systems: `AppointmentInventoryUsage` vs `PatientMedicationSchedule` |
| 10 | User UUID ≠ Patient UUID ≠ Doctor UUID | Separate tables; `Patient.user_id` is optional FK |
| 11 | Clinical capability via `Doctor.user_id` linkage, NOT role name alone | `has_clinician_capability()` |
| 12 | Workspace context NEVER grants authorization | Enforced in `workspace_context.py` design + all service checks |
| 13 | Additive-only migrations (never drop columns/tables) | Migration governance docs + `.clinerules` |
| 14 | All CREATE operations are idempotency-key aware | Idempotency tables + SHA256 hash check |

---

## 9. Technical Debt Hotspots

| Hotspot | Location | Risk |
|---------|----------|------|
| **`appointment_service.py` is 1,327 lines** — god service | `services/appointment_service.py` | High: changing any part risks breaking prescription, billing, inventory, invariant flows |
| **`clinic_operations_service.py` is 51,264 bytes** | `services/clinic_operations_service.py` | Medium: monolithic, hard to test in isolation |
| **`billing_service.py` is 30,371 bytes** | `services/billing_service.py` | Medium: billing logic tightly mixed with appointment state |
| **`medication_schedule_service.py` vs embedded derivation** | `appointment_service.py:_derive_medication_schedules_from_prescription()` | Medium: duplication risk between two code paths |
| **`complete_appointment` is 9 parameters** | `appointment_service.py:mark_appointment_completed()` | Medium: side-effect complexity hidden behind one function |
| **`_document_service_missing.py`** | `services/_document_service_missing.py` (9,857 bytes) | High: orphaned service file, may indicate incomplete document feature |
| **Leftover debug scripts in backend root** | `debug_auth.py`, `debug_profile*.py`, `check_encoding.py`, etc. | Low-Medium: production noise, should be cleaned up |
| **`fix_document_service.py` in backend root** | `backend/fix_document_service.py` (14,167 bytes) | Medium: one-off fix script that may indicate doc service is fragile |
| **`[TRACE_MC]` logger.warning calls in production code** | `deps.py`, `security_audit.py` | Low-Medium: debug traces left in prod paths, pollutes logs |
| **`appointment.completion_notes` deprecated column** | `models/appointment.py:L112-115` | Low: backward compat field still in model, migration needed eventually |
| **Duration parsing via regex in service layer** | `appointment_service.py:_derive_medication_schedules_from_prescription()` | Low: inline regex, not reusable or testable independently |
| **User.roles list not in ORM model** | `models/user.py` — no `roles` column visible | Medium: `has_clinician_capability()` checks `current_user.roles` list, but User model shows no such column — likely added via runtime attribute or separate migration |

---

## 10. Potential Risky Coupling Areas

| Area | Coupling Risk |
|------|--------------|
| **`appointment_service.py` → billing, inventory, prescription, medication_schedule, doctor_slot** | Changing billing logic can inadvertently break appointment completion |
| **Prescription creation embedded in `_create_appointment_prescriptions`** | Prescription creation is not a standalone, testable unit — it's buried inside the completion flow |
| **`PatientMedicationSchedule` derives from `PrescriptionItem`** | If `PrescriptionItem` rows are deleted (cascade), medication schedules become orphaned (`ondelete=RESTRICT` prevents this, but any refactor risks it) |
| **`InventoryStock` has doctor-level and tenant-level rows** | Two-level stock model (tenant stock + doctor-scoped stock) adds join complexity; easy to query the wrong level |
| **`Billing` → `Appointment` 1:1 relationship** | `billing = relationship("Billing", uselist=False)` — if multiple bills per appointment are needed in future, this breaks |
| **`AppointmentInventoryUsage` unique constraint `(appointment_id, item_id)`** | Only one usage line per item per appointment — if same item needs to appear twice (different workflows), this breaks |
| **Slot cache invalidation via SQLAlchemy event hooks** | `core/slot_cache_invalidation.py` wires into after_commit/rollback events — fragile if transaction semantics change |
| **`User.tenant_id` vs `UserTenant` table** | Two sources of truth for user-tenant membership; `get_current_tenant_id()` has a 4-step fallback chain |
| **`Appointment.is_deleted` partial index in PostgreSQL** | Unique index `uq_appointments_doctor_time_active` uses `postgresql_where` — SQLite tests use a different code path, masking Postgres-specific bugs |

---

## 11. Areas That Need Better Tests

| Gap | Risk |
|-----|------|
| **No test file for `appointment_service.py`** (prescription + medication derivation paths) | High: core clinical workflow; `test_appointments.py` exists but may not cover prescription auto-derivation |
| **No visible test for `mark_appointment_completed` billing side-effect** | High: billing generated at completion — regressions possible |
| **Dual-role (`admin+doctor`) capability scenarios** | Medium: `has_clinician_capability()` with admin role + Doctor record is not obviously covered |
| **Workspace context is UI-only — frontend routing isolation tests** | Low-Medium: Playwright E2E exists but workspace isolation boundary is hard to test |
| **`resolve_tenant_id_for_scoped_request()` edge cases** | Medium: super_admin without X-Tenant-ID, patient with header, multi-tenant user switching |
| **Idempotency key hash collision path** | Low: `ConflictError` on same key + different body is a security boundary |
| **Medication schedule status transitions** | Low-Medium: `active → completed → paused` state machine not clearly tested |
| **Patient global identity** — creating appointments across tenants for same patient | High: invariant that `patient.tenant_id = NULL` is never written |
| **`_validate_appointment_can_be_completed_time()` time window** | Medium: 15-minute grace window logic, timezone handling |
| **Integrity scan service caching** | Low: 5-minute TTL cache needs test for stale-state behavior |

---

## 12. Performance Concerns

| Concern | Location | Impact |
|---------|----------|--------|
| **`EncounterDetailAggregate` loads multiple relationships eagerly** | `encounter_service.py` | N+1 risk on queue/vitals/billing relationships if not using joined loads |
| **`_validate_doctor_availability()` runs a full range query on each appointment create** | `appointment_service.py:L94` | Adds latency to booking hot path |
| **`has_clinician_capability()` makes a DB query (Doctor lookup) on every request** | `clinical_capabilities.py:L80` | Every clinical endpoint does an extra DB round-trip; no caching |
| **`get_primary_tenant_id_from_db()` has a 4-step fallback with multiple queries** | `tenant_context.py` | Multiple DB hits per request for tenant resolution |
| **No pagination guard on `get_appointments()`** | `appointment_service.py:L358` | Default `limit=10` but callers could pass large values |
| **`debug_cors_origin` middleware logs on EVERY request** | `main.py:L99-107` | Log volume in production; two `logger.info` per request |
| **Integrity scan service uses thread-safe caching** | `integrity_scan_service.py` | TTL cache is in-process only — not shared across workers |
| **Slot cache uses Redis** | `core/redis.py` | If Redis is unavailable, fallback behavior unclear |
| **`apply_patient_scope()` uses correlated EXISTS subqueries** | `core/data_scope.py:L99-118` | On large datasets, correlated EXISTS can be slow without proper indexes |

---

## 13. Dangerous Anti-Patterns Found

| Anti-Pattern | Location | Severity |
|-------------|----------|---------|
| **`logger.warning()` used for TRACE-level debug output in production code** | `deps.py` — `[TRACE_MC]` lines throughout | ⚠️ Medium: every authenticated request emits warning-level traces, defeating log triage |
| **`handle_generic_exception` leaks internal error details** | `main.py:L150-153` — `content={"detail": f"Internal error: {error_msg}"}` | 🔴 High: raw exception messages exposed to clients; comment says "TEMP DEBUG" but it's in production |
| **Backward-compat JWT default role** | `deps.py:L70-71` — missing role defaults to `"admin"` | 🔴 High: if JWT role claim is missing, user silently gets `admin` role |
| **`patient.tenant_id` is nullable but could be written** | `models/patient.py:L34` — nullable FK with no write guard in DB | ⚠️ Medium: invariant enforced by convention only, not DB constraint |
| **`_document_service_missing.py`** in services | `services/_document_service_missing.py` | ⚠️ Medium: orphaned file, may be imported by mistake |
| **Duration parsing inline regex** | `appointment_service.py:L532` — `re.match(...)` | Low: no validation for negative numbers, invalid units; silent fallback to NULL `end_date` |
| **Multiple `logger.warning("[TRACE_MC]...")` left in `security_audit.py:enforce_tenant_match()`** | Production security enforcement path | ⚠️ Medium: security enforcement emits warning logs that look like violations, complicating security monitoring |
| **`ConflictError` maps to status 400** | `services/exceptions.py:L18` — `status_code = 400` | Low: idempotency conflicts and general conflicts both return 400; RFC 7231 expects 409 for idempotency conflicts |
| **`StaleStateError` maps to 409 but `ConflictError` maps to 400** | `services/exceptions.py` | Low: naming inconsistency — `ConflictError` should be 409 |
| **`completion_notes` deprecated but still writable** | `models/appointment.py:L115` | Low: deprecated field has no write protection; could be written by old clients |
| **`is_owner` flag on User** | `models/user.py:L54` — `is_owner: bool` | Low: undocumented flag; used in `authorize_appointment_create` and `apply_patient_scope`; creates implicit privilege escalation path |

---

## Summary for Stabilization Phase

### Do Not Touch (stable boundaries)
- `workspace/` system (registry.tsx, route-isolation.tsx)
- `appointment_invariants.py` + `appointment_invariant_enforcement.py`
- `tenant_context.py` + `clinical_capabilities.py`
- Migration files (additive only rule)
- Idempotency tables and their CRUD

### Highest Priority Stabilization Items
1. **Remove `[TRACE_MC]` debug `logger.warning()` calls** from `deps.py` and `security_audit.py` (log pollution + security monitoring confusion)
2. **Fix `handle_generic_exception` to not leak internal details** in production
3. **Fix JWT backward-compat default role** — missing `role` claim should raise 401, not silently grant `admin`
4. **Add guard to prevent writing `patient.tenant_id`** (DB-level or service-level)
5. **Investigate `_document_service_missing.py`** — is it imported anywhere? Should it be removed?
6. **Fix `ConflictError.status_code = 409`** — currently maps to 400 which breaks API semantics

### Monitoring Recommendations
- Watch `[INVARIANT_VIOLATION]` log lines — these indicate data corruption
- Watch `[AUDIT] cross_tenant_blocked` — these indicate boundary probing
- Watch `[RBAC] denied` — security violations
- The integrity scan service (TTL-cached) is a useful operational tool — expose it in admin dashboard

