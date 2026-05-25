# Authorization Model

> **Last updated:** May 14, 2026

---

## 1. Three-Layer Authorization Architecture

The system separates authorization into three distinct layers:

| Layer | Concern | Source of Truth |
|-------|---------|-----------------|
| **Identity** | Who the user is | `User` model, JWT claims |
| **Capability** | What the user can do | `Doctor.user_id` linkage, `has_clinician_capability()` |
| **Workspace Context** | What screen the user sees | `X-Workspace` header, `ActiveWorkspace` |

**Critical rule:** These layers are independent. Workspace context does NOT grant capability. Capability does NOT change identity.

---

## 2. Identity Layer (Role-Based)

### User Roles

Defined in `backend/app/models/user.py` (`UserRole` enum):

| Role | Description | Typical Access |
|------|-------------|----------------|
| `super_admin` | System-wide administrator | Cross-tenant operations, tenant management, integrity scans |
| `admin` | Tenant administrator | Tenant management, doctor creation, branding, reports |
| `staff` | Tenant staff | Front desk, operations, queue management |
| `doctor` | Clinician | Encounters, prescriptions, patient records |
| `patient` | Patient | Own appointments, health records, communication |

### Role Resolution

- Primary role is stored in `User.role`
- Users may have multiple roles via `User.roles` (list) — supports dual-role users (e.g., `admin+doctor`)
- JWT tokens carry `role` and `tenant_id` claims
- Frontend receives `roles[]` array from `GET /me` and login response

---

## 3. Capability Layer (Capability-Based)

### The Core Principle

**Capability is derived from data linkages, NOT from role names.**

A user has **clinician capability** if they are linked to a `Doctor` record via `Doctor.user_id`. This is independent of their `User.role`.

### `has_clinician_capability()` — Canonical Check

```python
from app.core.clinical_capabilities import has_clinician_capability

if not has_clinician_capability(db, current_user):
    raise ForbiddenError("Only clinicians can perform this action")
```

**Returns `True` if ANY of the following are true:**

1. `current_user.role == "doctor"` (direct role check — fastest path)
2. `current_user.roles` contains `"doctor"` (normalized role for dual-role users)
3. A `Doctor` record exists where `Doctor.user_id == current_user.id` (any role)

**This means:**
- An `admin` with a linked `Doctor` record **has clinician capability**
- A `staff` user with a linked `Doctor` record **has clinician capability**
- A `doctor` user without a linked `Doctor` record **does NOT have clinician capability** (edge case — should not occur in practice)

### Capability-Based Authorization Pattern

```python
# ✅ CORRECT — capability-based
doctor = doctor_service.get_current_doctor(db, current_user)
if doctor.id != appointment.doctor_id:
    raise ForbiddenError("Only the assigned doctor can complete this appointment")

# ❌ WRONG — role-based check for doctor actions
if current_user.role != UserRole.doctor:
    raise ForbiddenError("Only doctors can do this")
```

### Where Capability-Based Auth Is Used

| Action | Check | File |
|--------|-------|------|
| Complete encounter | `_assert_doctor_assigned_to_appointment()` | `appointment_service.py` |
| Consume clinical inventory | `has_clinician_capability()` | `inventory_service.py` |
| Access encounter workspace | `has_clinician_capability()` | `encounter_service.py` |
| Prescribe medications | `has_clinician_capability()` | `medication_schedule_service.py` |

### Where Role-Based Auth Is Used

| Action | Check | File |
|--------|-------|------|
| Create doctor | `admin` or `super_admin` role | `doctor.py` endpoints |
| View all appointments | `admin` or `super_admin` role | `appointment.py` endpoints |
| Tenant management | `super_admin` role | `tenant.py` endpoints |
| Patient self-access | `patient` role | `patient_workspace.py` |

---

## 4. Workspace Context Layer

### Design Principle

Workspace = UX/Operational Context (what screen the user is looking at)

**Workspace does NOT determine clinical permission.** A tenant doctor in the finance workspace is still a clinician. A pure admin (no Doctor record) in the doctor workspace is NOT a clinician.

### Workspace Resolution

```python
from app.core.workspace_context import (
    ActiveWorkspace, WorkspaceSlug, is_elevated_workspace_access
)
```

- Resolved from `X-Workspace` header via `get_active_workspace()` dependency
- Returns `ActiveWorkspace | None` (backward-compatible fallback)
- Validated against `ROLE_ALLOWED_WORKSPACES` whitelist

### Role-to-Workspace Mapping

| Role | Allowed Workspaces |
|------|-------------------|
| `super_admin` | admin, doctor, nurse, frontdesk, operations, procurement, finance, patient |
| `admin` | admin, doctor, frontdesk, operations, procurement, finance |
| `staff` | frontdesk, operations |
| `doctor` | doctor |
| `patient` | patient |

### Scoped Elevation

`is_elevated_workspace_access()` checks if an admin/super_admin is operating in a specific workspace context:

```python
is_elevated_workspace_access(
    current_user,
    active_workspace,
    target_slug=WorkspaceSlug.doctor
)
```

Returns `True` when:
- User is `admin` or `super_admin`
- AND active workspace matches `target_slug`

This is used for scoped elevation at specific bottleneck checks (doctor-record requirement, inventory doctor-scope).

---

## 5. Authorization Flow Diagrams

### Appointment Completion Authorization

```
Request: POST /appointments/{id}/mark-completed
  │
  ├─ 1. Authenticate (JWT) ────────────────── Identity Layer
  │     └─ Extract user_id, role, tenant_id
  │
  ├─ 2. Authorize appointment access ───────── Role + Capability Layer
  │     ├─ super_admin → bypass (role-based)
  │     ├─ patient → self-access only (role-based)
  │     └─ all others → capability check:
  │           ├─ get_current_doctor(db, current_user)
  │           ├─ doctor.id == appointment.doctor_id?
  │           └─ doctor.tenant_id == appointment.tenant_id?
  │
  ├─ 3. Validate invariants ────────────────── Invariant Layer
  │     ├─ appointment.doctor_id == doctor.id
  │     └─ appointment.tenant_id == doctor.tenant_id
  │
  ├─ 4. Execute completion ─────────────────── Service Layer
  │     ├─ Update status → completed
  │     ├─ Deduct inventory (if items provided)
  │     ├─ Generate bill (if requested)
  │     ├─ Create idempotency record
  │     └─ Finalize with AppointmentInvariantGuard
  │
  └─ 5. Return result
```

### Encounter Workspace Access

```
Request: GET /encounters/{appointment_id}
  │
  ├─ 1. Authenticate (JWT)
  │
  ├─ 2. has_clinician_capability(db, current_user)?
  │     ├─ Yes → proceed
  │     └─ No → 403 Forbidden
  │
  ├─ 3. Tenant alignment check
  │     └─ appointment.tenant_id matches request scope
  │
  └─ 4. Return EncounterDetailAggregate
```

---

## 6. Dual-Role Scenarios

### Scenario: Admin + Doctor

A user with `User.role = "admin"` who also has a `Doctor` record:

| Action | Authorized? | Reason |
|--------|------------|--------|
| View admin dashboard | ✅ | Role-based (admin) |
| Create doctors | ✅ | Role-based (admin) |
| Complete encounters | ✅ | Capability-based (has Doctor record) |
| Consume clinical inventory | ✅ | Capability-based (has Doctor record) |
| View tenant billing | ✅ | Role-based (admin) |

### Scenario: Staff + Doctor

A user with `User.role = "staff"` who also has a `Doctor` record:

| Action | Authorized? | Reason |
|--------|------------|--------|
| Manage front desk queue | ✅ | Role-based (staff) |
| Complete encounters | ✅ | Capability-based (has Doctor record) |
| Access doctor workspace | ❌ | Not in staff allowed workspaces |

### Scenario: Pure Admin (No Doctor Record)

| Action | Authorized? | Reason |
|--------|------------|--------|
| View admin dashboard | ✅ | Role-based |
| Complete encounters | ❌ | No clinician capability |
| Consume clinical inventory | ❌ | No clinician capability |
| Access encounter workspace | ❌ | No clinician capability |

---

## 7. Trust Boundaries

### Rule 1: Frontend tenant IDs are NOT trusted
- Headers like `X-Tenant-ID` are hints only; validated against `user_tenant` membership
- Resource ownership (`appointment.tenant_id`, `billing.tenant_id`) is authoritative

### Rule 2: Role names alone are NOT trusted
- Capability-based authorization via `Doctor.user_id` linkage
- `current_user.role == "doctor"` checks are forbidden for clinical actions

### Rule 3: JWT/header tenant hints are NOT authoritative alone
- Validated against `user_tenant` membership AND resource ownership
- `align_operation_tenant_with_resource()` enforces resource tenant matches request scope

### Rule 4: Resource ownership + invariants are authoritative
- `assert_authorized()` enforces `resource_tenant_id == tenant_id`
- Appointment invariants enforce doctor/tenant alignment

### Enforcement Points

| File | Function | Purpose |
|------|----------|---------|
| `app/core/tenant_context.py` | `align_operation_tenant_with_resource()` | Resource tenant must match request scope |
| `app/services/security_audit.py` | `enforce_tenant_match()` | Cross-tenant access validation |
| `app/services/appointment_invariants.py` | `validate_appointment_invariants()` | Doctor/tenant alignment |
| `app/core/clinical_capabilities.py` | `has_clinician_capability()` | Clinician capability check |

---

## 8. Common Pitfalls

### ❌ Role-based check for doctor actions
```python
if current_user.role != UserRole.doctor:
    raise ForbiddenError("Only doctors can do this")
```
**Problem:** Blocks admin+doctor dual-role users. Use capability-based check instead.

### ❌ Missing tenant scope on doctor lookup
```python
doctor = crud_doctor.get_doctor(db, doctor_id)  # Could be from any tenant!
```
**Problem:** Cross-tenant access. Always scope by tenant or verify after fetch.

### ❌ Trusting workspace context for authorization
```python
if active_workspace.slug == "doctor":
    # Assume user is a clinician
```
**Problem:** Workspace context is UI-only. Use `has_clinician_capability()` instead.

### ❌ Using `user.role` for patient identification
```python
if current_user.role == "patient":
    # Show patient data
```
**Problem:** Use `patient_has_active_appointment_in_tenant()` to verify patient access within a tenant context.

---

## 9. Frontend Authorization

### Workspace-Aware Routing

The frontend uses workspace-based routing via `route-isolation.tsx`:

- Routes are scoped by workspace
- `WorkspaceSwitcher` allows users to switch workspaces
- `resolver.ts` determines which workspace a user should see after login

### Clinician Capability in Frontend

The frontend receives clinician capability information from:

1. **`GET /me` response** — includes `doctor_id`, `roles[]`, `doctor_profile_complete`
2. **Login response** — includes `doctor_id`, `roles[]`
3. **JWT claims** — `role` and `roles` claims

Frontend components check `roles.includes('doctor')` or `doctor_id !== null` to conditionally render clinician UI elements.

### Important Frontend Rules

- Workspace context is informational/UI-oriented
- Frontend does NOT make authorization decisions — it relies on backend 403 responses
- Route isolation enforces workspace scoping, not capability scoping
- Clinician-only UI elements should be gated by `doctor_id` presence, not workspace
