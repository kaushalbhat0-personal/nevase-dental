# Architecture


---

## 1. System Overview

Full-stack multi-tenant hospital management system:

| Layer | Technology | Location |
|-------|-----------|----------|
| **Backend API** | FastAPI + Python 3.11+ | `backend/app/` |
| **Database** | PostgreSQL + SQLAlchemy ORM | `backend/app/models/` |
| **Migrations** | Alembic | `backend/alembic/` |
| **Frontend** | React 19 + TypeScript + Vite | `backend/frontend/` |
| **Auth** | JWT Bearer tokens | `backend/app/core/security.py` |

---

## 2. Backend Architecture

### Layered Pattern

```
Router (endpoints)
  → Service (business logic, transactions, idempotency)
    → CRUD (database operations)
      → ORM (SQLAlchemy models)
```

**Strict rule:** All mutation endpoints must go through the service layer. Routers never call CRUD directly for mutations.

### Directory Structure

```
backend/app/
├── main.py                    # FastAPI application entry
├── core/                      # Settings, database, security, tenancy
│   ├── config.py              # Environment configuration
│   ├── database.py            # DB connection & session
│   ├── security.py            # JWT encode/decode
│   ├── tenant_context.py      # Tenant resolution & enforcement
│   ├── workspace_context.py   # Active workspace resolution
│   ├── clinical_capabilities.py # Clinician capability check
│   ├── permissions.py         # Permission helpers
│   └── data_scope.py          # Data scope resolution
├── models/                    # SQLAlchemy models
│   ├── __init__.py            # Barrel exports
│   ├── user.py                # User, UserRole
│   ├── tenant.py              # Tenant
│   ├── patient.py             # Patient (global, tenant_id = NULL)
│   ├── doctor.py              # Doctor
│   ├── appointment.py         # Appointment (encounter anchor)
│   ├── billing.py             # Bill
│   ├── inventory.py           # Inventory items
│   ├── clinic_queue.py        # Queue entries
│   ├── notification.py        # Notifications
│   ├── patient_medication_schedule.py
│   ├── patient_communication_preference.py
│   ├── tenant_branding.py     # Branding profiles
│   ├── supplier.py            # Suppliers
│   ├── purchase_order.py      # Purchase orders
│   └── ...                    # Additional models
├── schemas/                   # Pydantic schemas (request/response)
├── services/                  # Business logic layer
│   ├── exceptions.py          # ServiceError, ForbiddenError, etc.
│   ├── appointment_service.py
│   ├── encounter_service.py
│   ├── inventory_service.py
│   ├── billing_service.py
│   ├── queue_service.py
│   ├── front_desk_service.py
│   ├── nurse_workflow_service.py
│   ├── clinic_operations_service.py
│   ├── doctor_service.py
│   ├── patient_service.py
│   ├── notification_service.py
│   ├── procurement_service.py
│   ├── integrity_scan_service.py
│   ├── appointment_invariants.py
│   ├── appointment_invariant_enforcement.py
│   └── ...
├── crud/                      # Database CRUD operations
├── api/v1/
│   ├── router.py              # Master router registration
│   ├── endpoints/             # Route handlers
│   └── api.py                 # API version prefix
└── utils/                     # Utility functions
```

### Dependency Injection

FastAPI `Depends` is used for:

| Dependency | Purpose |
|-----------|---------|
| `get_db` | SQLAlchemy session |
| `get_current_user` | Authenticated user from JWT |
| `get_current_active_user` | Active user (not disabled) |
| `get_scoped_tenant_id` | Tenant ID from header/JWT |
| `get_active_workspace` | Workspace context from header |
| `get_current_doctor` | Doctor record for current user |
| `get_current_tenant_context` | User + tenant context tuple |

---

## 3. Frontend Architecture

### Directory Structure

```
backend/frontend/src/
├── App.tsx                    # Main app with routing
├── main.tsx                   # React entry point
├── workspace/                 # Workspace system
│   ├── registry.tsx           # Workspace definitions (SINGLE SOURCE OF TRUTH)
│   ├── resolver.ts            # Workspace resolution from user context
│   ├── route-isolation.tsx    # Route scoping by workspace
│   ├── WorkspaceSwitcher.tsx  # Workspace switching UI
│   ├── contextual-redirects.ts # Post-login redirect logic
│   ├── useActiveWorkspace.ts  # Active workspace hook
│   └── layouts/               # Workspace-specific layouts
│       ├── DoctorWorkspaceLayout.tsx
│       ├── PatientWorkspaceLayout.tsx
│       ├── FrontDeskWorkspaceLayout.tsx
│       ├── OperationsWorkspaceLayout.tsx
│       ├── ProcurementWorkspaceLayout.tsx
│       ├── FinanceWorkspaceLayout.tsx
│       └── contextual-header.tsx
├── pages/                     # Page components
│   ├── doctor/                # Doctor workspace pages
│   ├── patient/               # Patient workspace pages
│   ├── procurement/           # Procurement pages
│   ├── Admin*.tsx             # Admin pages
│   └── ...                    # Other pages
├── components/                # Reusable UI components
│   ├── ui/                    # shadcn/ui components
│   ├── layout/                # Layout components
│   ├── doctor/                # Doctor-specific components
│   ├── patient/               # Patient-specific components
│   ├── frontdesk/             # Front desk components
│   └── operations/            # Operations components
├── services/                  # API client functions (axios)
├── hooks/                     # Custom React hooks
├── handlers/                  # API call handlers
├── types/                     # TypeScript interfaces
├── validation/                # Zod schemas
├── utils/                     # Helper functions
├── constants/                 # App constants
└── animations/                # Framer Motion components
```

### Container/Presentational Pattern

- **Pages** fetch data and manage state
- **Components** render UI with props
- **Hooks** encapsulate data fetching and state logic
- **Services** provide API client functions
- **Handlers** orchestrate API calls with error handling

---

## 4. Multi-Tenancy Architecture

See [MULTI_TENANCY.md](./MULTI_TENANCY.md) for the complete multi-tenancy documentation.

Key principles:
- **Resource ownership is authoritative** — `resource.tenant_id` is the source of truth
- **Patients are global** — `patient.tenant_id` is ALWAYS NULL
- **Tenant context derived from appointments** — not from patient records
- **Super_admin is NOT unrestricted root** — resource-level tenant scoping applies

---

## 5. Authorization Architecture

See [AUTHORIZATION_MODEL.md](./AUTHORIZATION_MODEL.md) for the complete authorization documentation.

Three-layer model:
1. **Identity** — Who the user is (role-based)
2. **Capability** — What the user can do (capability-based via Doctor linkage)
3. **Workspace Context** — What screen the user sees (UI-oriented)

### Workspace Is Contextual, Not Authoritative

**Workspace affects UI. Capabilities affect permissions.**

- Workspace context is resolved from the `X-Workspace` header for UI/operational context
- Workspace does NOT determine clinical permission — a tenant doctor in the finance workspace is still a clinician
- Authorization happens ONLY through:
  - Capability checks (`has_clinician_capability()`, `get_current_doctor()`)
  - Tenant/resource ownership (`assert_authorized()`, `enforce_tenant_match()`)
  - Explicit service authorization (`_assert_doctor_assigned_to_appointment()`)
- Invalid/missing workspace falls back gracefully (returns `None`) — does not block clinicians
- The `active_workspace` parameter in service-layer functions is informational only (logging/debugging)

---

## 6. Clinical Workflow Architecture

See [CLINICAL_WORKFLOW.md](./CLINICAL_WORKFLOW.md) for the complete clinical workflow documentation.

Key architectural decisions:
- **Appointment is the encounter anchor** — no separate Visit/Encounter table
- **Billing, inventory, prescriptions attach to appointments**
- **Invariant enforcement** — doctor/tenant alignment validated before mutations
- **Idempotency** — all CREATE operations support Idempotency-Key header

---

## 7. Invariant System

### Core Invariant Validation

```python
# backend/app/services/appointment_invariants.py
def validate_appointment_invariants(appointment: Appointment, doctor: Doctor) -> None:
    if appointment.doctor_id != doctor.id:
        raise ValidationError("Appointment does not match the provided doctor identity")
    if appointment.tenant_id != doctor.tenant_id:
        raise ValidationError("Cross-tenant appointment detected")
```

### AppointmentInvariantGuard

```python
# backend/app/services/appointment_invariant_enforcement.py
# Single entry point for post-commit/load validation
AppointmentInvariantGuard.finalize(db, appointment_id)
revalidate_appointment_invariants(appointment, db)
```

### Integrity Scan Service

Read-only corruption detection:
- Cross-tenant scans (super_admin only)
- Per-tenant scans (tenant administrators)
- Thread-safe caching with configurable TTL (default 5 minutes)
- Structured issue reporting with severity levels

---

## 8. Idempotency Pattern

All CREATE operations support `Idempotency-Key` header:

1. Hash the request body
2. Check `*_idempotency` table for existing key
3. If exists with same hash → return cached result (idempotent replay)
4. If exists with different hash → `ConflictError`
5. Store key+hash+result after successful operation

**Tables with idempotency support:**
- `tenant_creation_idempotency`
- `appointment_creation_idempotency`
- `doctor_creation_idempotency`
- `appointment_completion_idempotency`

---

## 9. Error Handling

### HTTP Status Semantics

| Status | Usage |
|--------|-------|
| 200 OK | Successful GET/PUT/PATCH |
| 201 Created | Successful POST |
| 204 No Content | Successful DELETE |
| 400 Bad Request | Validation errors |
| 401 Unauthorized | Missing/invalid authentication |
| 403 Forbidden | Insufficient permissions |
| 404 Not Found | Missing resources |
| 409 Conflict | Idempotency key conflicts |
| 422 Unprocessable Entity | Pydantic validation errors |
| 500 Internal Server Error | Unexpected errors |

### Service Layer Exceptions

Defined in `backend/app/services/exceptions.py`:
- `ServiceError` — Base exception
- `NotFoundError` — Resource not found
- `ForbiddenError` — Permission denied
- `ConflictError` — Idempotency conflict
- `ValidationError` — Input validation failure

---

## 10. Audit Logging

All critical operations generate structured audit events:

```python
log_structured_audit_event(
    event="appointment_completed",
    tenant_id=appointment.tenant_id,
    user_id=current_user.id,
    resource_id=appointment.id,
    details={"doctor_id": doctor.id, "completion_method": "api"}
)
```

Audit events include:
- Tenant context for cross-tenant visibility
- User identity and role information
- Resource IDs and operation types
- Timestamps and outcome status
- Security violation logging for RBAC failures

---

## 11. API Versioning

All endpoints are under `/api/v1/`. When creating new endpoints:
1. Add router in `backend/app/api/v1/endpoints/`
2. Register in `backend/app/api/v1/router.py`
3. Follow existing patterns for: auth, idempotency, tenant scoping, error handling

---

## 12. Testing Strategy

### Backend Tests
- **Framework:** pytest with pytest-asyncio
- **Default database:** SQLite in-memory (configured in `pytest.ini`)
- **PostgreSQL-only tests:** `@pytest.mark.postgres` marker
- **Fixtures:** `db_session`, `client` (httpx.AsyncClient)
- **Location:** `backend/tests/`

### Frontend Tests
- **E2E:** Playwright (`backend/frontend/e2e/`)
- **Run:** `npx playwright test`

### Test Coverage Requirements
- Tests for new service-layer functions
- Tests for new API endpoints
- Idempotency path tests for CREATE operations
- Tenant isolation tests (cross-tenant access should fail)
- Invariant enforcement tests (appointment-doctor mismatch should fail)
