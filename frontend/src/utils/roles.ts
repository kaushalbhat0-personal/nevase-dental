import { getActiveTenantId } from './tenantIdForRequest';
import { roleFromToken, rolesFromToken } from './jwtPayload';
import { readStoredAppMode, type AppMode } from '../constants/appMode';

export function normalizeRoles(roles: string | string[] | null | undefined): string[] {
  if (roles == null) return [];
  if (Array.isArray(roles)) {
    return roles.map((r) => String(r).toLowerCase());
  }
  return [String(roles).toLowerCase()];
}

export type RoleHint = { roles?: string[]; role?: string } | null | undefined;

/** User shape for tenant-scoped checks that also need merged JWT roles. */
export type TenantVerifyUser =
  | (NonNullable<RoleHint> & {
      tenant?: { type?: string } | null;
      is_owner?: boolean;
    })
  | null
  | undefined;

/** Merge role lists from multiple sources (local user blob, JWT). Preserves first-seen order, dedupes. */
export function mergeRoleSources(
  ...sources: (string[] | string | null | undefined)[]
): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const s of sources) {
    if (s == null) continue;
    const arr = Array.isArray(s) ? s : [s];
    for (const r of normalizeRoles(arr)) {
      if (!seen.has(r)) {
        seen.add(r);
        out.push(r);
      }
    }
  }
  return out;
}

/**
 * Authoritative list for the signed-in user: merges stored `user.roles` with JWT `roles` /
 * `role` so a stale localStorage blob (e.g. only `admin`) cannot hide `doctor` from the token.
 */
export function getEffectiveRoles(user: RoleHint, token: string | null): string[] {
  const fromUser =
    user?.roles && user.roles.length > 0
      ? user.roles
      : user?.role
        ? [user.role]
        : [];
  const tr = rolesFromToken(token);
  const single = roleFromToken(token);
  const fromToken = tr && tr.length > 0 ? tr : single ? [single] : [];
  const merged = mergeRoleSources(fromUser, fromToken);
  return merged.length > 0 ? merged : [];
}

/** Practice ↔ Admin toggle: must have both clinician and tenant org-admin (literal `admin`). */
export function isDoctorAndOrgAdminRoles(roles: string | string[] | null | undefined): boolean {
  const r = normalizeRoles(roles);
  return r.includes('doctor') && r.includes('admin');
}

/** Backend sends role enum as lowercase string (e.g. patient, admin, doctor). */
export function isPatientRole(roles: string | string[] | null | undefined): boolean {
  return normalizeRoles(roles).includes('patient');
}

export function isDoctorRole(roles: string | string[] | null | undefined): boolean {
  return normalizeRoles(roles).includes('doctor');
}

/** Solo doctor account: effective roles are only `doctor` (not org admin, patient, etc.). */
export function isDoctorOnlyRole(user: RoleHint, token: string | null): boolean {
  const r = getEffectiveRoles(user, token);
  return r.length === 1 && r[0] === 'doctor';
}

/** Admin dashboard and admin-only APIs (admin or super_admin). */
export function isAdminRole(roles: string | string[] | null | undefined): boolean {
  return normalizeRoles(roles).some((r) => r === 'admin' || r === 'super_admin');
}

/** Admin dashboard, inventory, org settings — only org `admin` / `super_admin` in roles (not solo-doctor is_owner). */
export function canAccessAdminUI(roles: string | string[] | null | undefined): boolean {
  const r = normalizeRoles(roles);
  return r.some((x) => x === 'admin' || x === 'super_admin');
}

export function isSuperAdminRole(roles: string | string[] | null | undefined): boolean {
  return normalizeRoles(roles).includes('super_admin');
}

/**
 * Who may review marketplace doctor verification (align with backend `can_verify_doctor_profile`):
 * super_admin, or organization-tenant org admins (admin/staff) / practice owner.
 * Solo individual-practice doctors never get approval UI (tenant.type must be `organization`).
 */
export function canVerifyDoctorsInTenant(
  user: TenantVerifyUser,
  token: string | null
): boolean {
  const eff = getEffectiveRoles(user, token);
  if (isSuperAdminRole(eff)) return true;
  if (user?.tenant?.type !== 'organization') return false;
  const r = normalizeRoles(eff);
  if (r.includes('admin') || r.includes('staff')) return true;
  if (r.includes('doctor') && user?.is_owner) return true;
  return false;
}

export function staffHomePath(): string {
  return '/dashboard';
}

export function patientHomePath(): string {
  return '/patient/home';
}

export function doctorHomePath(): string {
  return '/doctor/dashboard';
}

/** Default landing path after login or post-registration, by role. */
export function needsStructuredDoctorProfile(
  user: { doctor_id?: string | null; doctor_profile_complete?: boolean | null } | null
): boolean {
  if (!user?.doctor_id || String(user.doctor_id).length === 0) return false;
  return user.doctor_profile_complete === false;
}

/** Where to go after sign-in. Pass `user` (or an object with `doctor_id` + `doctor_profile_complete`) so incomplete doctor profiles are gated. */
export function postLoginHomePath(
  roles: string | string[] | null | undefined,
  userOrHints?: { doctor_id?: string | null; doctor_profile_complete?: boolean | null } | null
): string {
  const r = normalizeRoles(roles);
  if (r.includes('patient')) return patientHomePath();
  const hasDoc = r.includes('doctor');
  const hasAdm = r.some((x) => x === 'admin' || x === 'super_admin');
  if (userOrHints && needsStructuredDoctorProfile(userOrHints)) {
    return '/complete-profile';
  }
  if (hasDoc && hasAdm) {
    const m: AppMode = readStoredAppMode() ?? 'practice';
    return m === 'admin' ? '/admin/dashboard' : doctorHomePath();
  }
  if (r.includes('doctor')) return doctorHomePath();
  if (r.includes('super_admin')) {
    return getActiveTenantId() ? '/admin/dashboard' : '/admin/tenants';
  }
  if (hasAdm) return '/admin/dashboard';
  return staffHomePath();
}
