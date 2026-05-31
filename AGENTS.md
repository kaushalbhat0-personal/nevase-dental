# Nevase Dental — Session Log

## Session 2 — May 31, 2026

**Goal:** Fix admin dashboard bugs (patient list, doctors routing, doctor verification).

### Changes

**Backend — `backend/app/`**

1. **Patient list not showing after creation** (`patient_repository.py`, `patient_service.py`, `PatientPatientsPage.tsx`)
   - `apply_patient_scope`: added `Patient.tenant_id` filter (was missing admin tenant scope)
   - Patient creation: set `tenant_id = audit_tenant`
   - Frontend: local `newlyCreated` state for instant display + `useEffect` dedup loop polling API

2. **Missing admin routes** (`App.tsx`, `registry.tsx`)
   - Added routes: `/admin/doctors`, `/admin/patients`, `/admin/appointments`, `/admin/billing`, `/admin/reports`
   - Changed Doctors sidebar link from `/doctors` → `/admin/doctors`

3. **Doctor verification endpoint** (`doctor.py` router, `doctor_service.py`)
   - Added `PATCH /doctors/{id}/verify` using `require_current_user_admin_or_owner`
   - Auto-verify (`is_verified=True`, `verification_status="approved"`) on doctor creation via `create_hospital_doctor_with_login`
   - Fixed schema import: `DoctorProfileVerificationAdmin` → `DoctorProfileVerificationReview`
   - Frontend `doctorVerificationAdmin.ts`: API URL from `/admin/doctor-profiles/{id}/verification` → `/doctors/{id}/verify`

4. **Cascade delete User** (`doctor_service.py:delete_doctor`)
   - Deletes associated `User` record when a `Doctor` is deleted

5. **Idempotent doctor creation** (`doctor_service.py:create_hospital_doctor_with_login`)
   - If email already exists, reuses existing `User` instead of failing with duplicate-key error

**Frontend — visual/UI (previous session)**

6. **Clean sidebar** (`registry.tsx`)
   - Removed Tenants, Verifications
   - Added Patients, Appointments, Doctors, Billing, Inventory
   - Renamed header to "Nevase's Dental Clinic"
   - Moved Reports under Settings

7. **Light mode** (`AppLayout.tsx`, `Sidebar.tsx`)
   - Removed `dark:` Tailwind classes
   - Layout background: `bg-[#F8FAFC]`
   - Sidebar: white background

8. **AdminDashboard cards** — colored left borders per stat, removed redundant outer padding
