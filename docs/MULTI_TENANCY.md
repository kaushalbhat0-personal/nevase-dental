# Multi-Tenancy Architecture

> **Last updated:** May 13, 2026
> **Canonical source:** `backend/app/core/tenant_context.py`, `backend/app/services/security_audit.py`

---

## 1. Overview

The system supports two tenant types:

| Tenant Type | Description | Example |
|-------------|-------------|---------|
| **Individual** | Solo doctor practice | A single doctor running their own clinic |
| **Organization** | Multi-doctor clinic/hospital | A hospital with multiple doctors and staff |

Tenant type is stored in `Tenant.type` and affects:
- UI mode (individual vs organization)
- Doctor creation flow
- Billing and reporting aggregation
- Marketplace discovery display

---

## 2. Tenant Model

### Core Entities

```
Tenant
├── id (UUID, PK)
├── name
├── slug (URL-safe key, optional)
├── type ("individual" | "organization")
├── is_active
├── is_deleted (super-admin soft-delete)
├── address, phone (optional)
└── created_at

User (global — not tenant-scoped)
├── id (UUID, PK)
├── email (unique)
├── role (UserRole enum)
├── roles (list, for dual-role)
└── is_active

UserTenant (links users to tenants)
├── user_id (FK → User)
├── tenant_id (FK → Tenant)
├── role (per-tenant role)
└── is_primary
```

### Key Design Decisions

1. **User is global** — a single User account can belong to multiple tenants
2. **UserTenant** — links users to tenants with per-tenant roles
3. **Tenant context is resolved per-request** — from JWT claims or `X-Tenant-ID` header
4. **Resource ownership is authoritative** — `resource.tenant_id` is the source of truth

---

## 3. Tenant Resolution

### Request Flow

```
Request
  │
  ├─ JWT token contains: user_id, role, tenant_id
  │
  ├─ get_current_tenant_id() dependency
  │     ├─ Extract tenant_id from JWT claims
  │     ├─ OR from X-Tenant-ID header (overrides JWT)
  │     ├─ Validate against UserTenant membership
  │     └─ Return resolved tenant_id
  │
  └─ All queries filter by tenant_id
```

### Dependency Functions

| Function | Purpose |
|----------|---------|
| `get_scoped_tenant_id()` | Required tenant context (raises if missing) |
| `get_optional_scoped_tenant_id()` | Optional tenant context (returns None) |
| `get_current_tenant_context()` | Returns `CurrentTenantContext(user, tenant_id)` |
| `get_active_workspace()` | Returns workspace context (not tenant) |

---

## 4. Tenant Isolation Rules

### Rule 1: Every Query Must Be Tenant-Scoped

```python
# ✅ CORRECT
appointments = db.query(Appointment).filter(
    Appointment.tenant_id == current_tenant_id
).all()

# ❌ WRONG — no tenant filter
appointments = db.query(Appointment).all()
```

### Rule 2: Resource Ownership Is Authoritative

```python
# align_operation_tenant_with_resource() enforces:
# resource.tenant_id MUST match request tenant_id
def align_operation_tenant_with_resource(
    resource_tenant_id: UUID,
    request_tenant_id: UUID,
) -> None:
    if resource_tenant_id != request_tenant_id:
        raise ForbiddenError("Cross-tenant access not allowed")
```

### Rule 3: Super Admin Is NOT Unrestricted Root

Super admin can operate across tenants, but ONLY when the resource belongs to the requested tenant scope:

```python
# Cross-tenant access is blocked even for super_admin
# Attempts are logged with [AUDIT] cross_tenant_blocked
```

### Rule 4: Patients Are Global

**`patient.tenant_id` is ALWAYS NULL.** Patients are global records.

- Tenant context is derived ONLY from appointments
- A patient belongs to a tenant only when they have an active `Appointment` with `Appointment.tenant_id` set
- Patient access control uses `patient_has_active_appointment_in_tenant()` — NOT `patient.tenant_id`
- **CRITICAL INVARIANT:** Never write to `patient.tenant_id`

### Rule 5: Appointment Is the Tenant Anchor

- `appointment.tenant_id` is **mandatory** (non-nullable)
- Billing inherits appointment tenant: `bill.tenant_id == appointment.tenant_id`
- Inventory usage must match appointment tenant
- Queue entries are tenant-scoped and appointment-linked

---

## 5. Tenant Enforcement Points

| File | Function | Purpose |
|------|----------|---------|
| `app/core/tenant_context.py` | `resolve_tenant_id_for_scoped_request()` | Resolve tenant from JWT/header |
| `app/core/tenant_context.py` | `align_operation_tenant_with_resource()` | Enforce resource tenant match |
| `app/services/security_audit.py` | `assert_authorized()` | Cross-tenant access validation |
| `app/services/security_audit.py` | `enforce_tenant_match()` | Tenant match enforcement |
| `app/services/appointment_invariants.py` | `validate_appointment_invariants()` | Doctor/tenant alignment |
| `app/api/deps.py` | `get_scoped_tenant_id()` | FastAPI dependency for tenant ID |

---

## 6. Tenant-Aware Operations

### Doctor Creation

```python
# POST /api/v1/doctors
# tenant_id is resolved from get_current_tenant_id()
# Super admin may pass ?tenant_id= query parameter
```

### Appointment Creation

```python
# POST /api/v1/appointments
# appointment.tenant_id is set from request tenant context
# Idempotency-Key header supported for safe retries
```

### Patient Access

```python
# Patient access is verified via:
patient_has_active_appointment_in_tenant(db, patient_id, tenant_id)
# NOT via patient.tenant_id (which is always NULL)
```

### Billing

```python
# Bill.tenant_id must match Appointment.tenant_id
# Integrity scan validates: bill.tenant_id == appointment.tenant_id
```

---

## 7. Cross-Tenant Operations

### Super Admin Integrity Scan

```python
# GET /api/v1/admin/integrity-scan?all_tenants=true
# Super admin only
# Scans all tenants for corruption
# Cached with 5-minute TTL
```

### Tenant Management

```python
# Super admin can create, deactivate, and manage tenants
# Tenant soft-delete via is_deleted flag
# Deactivated tenants hidden from lists and API scope
```

---

## 8. Trust Boundaries

### Explicit Rules

1. **Frontend tenant IDs are NOT trusted** — headers are hints only
2. **JWT tenant claims are NOT authoritative alone** — validated against UserTenant
3. **Resource ownership is authoritative** — `resource.tenant_id` is the source of truth
4. **Role names alone are NOT trusted** — capability-based auth via Doctor linkage

### Common Anti-Patterns

```python
# ❌ WRONG — trusting frontend tenant ID
tenant_id = request.headers.get("X-Tenant-ID")

# ✅ CORRECT — resolving through dependency
tenant_id = get_scoped_tenant_id(db, current_user, x_tenant_id)

# ❌ WRONG — forgetting tenant scope
doctor = crud_doctor.get_doctor(db, doctor_id)

# ✅ CORRECT — scoping by tenant
doctor = crud_doctor.get_doctor(db, doctor_id, tenant_id=current_tenant_id)
```

---

## 9. Tenant Branding

Each tenant can have branding profiles:

| Feature | Description |
|---------|-------------|
| Logo | Tenant logo for UI |
| Primary color | Brand color for UI theming |
| Clinic name | Display name in patient-facing UI |
| Address/Contact | Tenant contact information |

See `backend/app/models/tenant_branding.py` and `backend/app/api/v1/endpoints/branding.py`.

---

## 10. Tenant Organization Profile

Extended tenant metadata:

| Field | Description |
|-------|-------------|
| Registration number | Business registration |
| Tax ID | Tax identification |
| License number | Medical license |
| Type | Clinic, hospital, diagnostic center |
| Website | Organization website |

See `backend/app/models/tenant.py` and `backend/app/schemas/tenant_organization_profile.py`.
