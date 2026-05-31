import type { User } from '../types';
import { getEffectiveRoles } from './roles';

/** Marketplace trust gate: only `approved` may use full practice APIs (per backend). */
export function isDoctorVerificationApproved(
  user: User | null | undefined,
  token: string | null
): boolean {
  if (!user?.doctor_id) return true;
  const eff = getEffectiveRoles(user, token);
  if (!eff.includes('doctor')) return true;
  return user.doctor_verification_status === 'approved';
}

function isRestrictedDoctorVerification(user: User | null | undefined): boolean {
  const st = user?.doctor_verification_status;
  return st == null || st === '' || st === 'draft' || st === 'rejected';
}

/** Items not listed here are hidden for draft / rejected clinicians (Overview + Profile only). */
export function isDoctorNavItemVisible(
  user: User | null | undefined,
  token: string | null,
  path: string
): boolean {
  if (!user?.doctor_id) return true;
  const eff = getEffectiveRoles(user, token);
  if (!eff.includes('doctor')) return true;
  if (!isRestrictedDoctorVerification(user)) return true;
  return path === '/doctor/dashboard' || path === '/complete-profile';
}

/**
 * Disabled/grey nav (legacy): unused for role-aware visibility — kept for callers that
 * still pass `disabled`; pending is never locked so exploration does not feel broken.
 */
export function isDoctorNavItemLocked(
  user: User | null | undefined,
  token: string | null,
  path: string
): boolean {
  void path;
  if (!user?.doctor_id) return false;
  const eff = getEffectiveRoles(user, token);
  if (!eff.includes('doctor')) return false;
  if (user.doctor_verification_status === 'pending') return false;
  return !isDoctorVerificationApproved(user, token);
}

/**
 * Redirect clinicians with draft/rejected verification away from practice routes
 * (direct URL bar) — allowed: `/doctor` and `/doctor/dashboard` only under `/doctor`.
 */
export function getDoctorVerificationRestrictedRedirect(
  pathname: string,
  user: User | null,
  token: string | null
): string | null {
  if (!user?.doctor_id) return null;
  const eff = getEffectiveRoles(user, token);
  if (!eff.includes('doctor')) return null;
  if (!isRestrictedDoctorVerification(user)) return null;
  if (!pathname.startsWith('/doctor')) return null;
  const allowed =
    pathname === '/doctor' ||
    pathname === '/doctor/' ||
    pathname.startsWith('/doctor/dashboard');
  if (allowed) return null;
  return '/doctor/dashboard';
}

/** Optional nav hint for pending review (read-mostly exploration). */
export function doctorNavItemHint(user: User | null | undefined, path: string): string | undefined {
  if (user?.doctor_verification_status !== 'pending') return undefined;
  if (path === '/doctor/dashboard' || path === '/complete-profile') return undefined;
  return 'Under review — some actions stay limited until you are verified';
}

const REJECTION_FIELD_KEYWORDS: { match: string[]; fields: string[] }[] = [
  { match: ['license', 'registration', 'reg no', 'reg. no', 'npi'], fields: ['registration_number', 'registration_council'] },
  { match: ['phone', 'mobile', 'contact'], fields: ['phone'] },
  { match: ['qualification', 'degree', 'education'], fields: ['qualification'] },
  { match: ['specialization', 'specialty', 'speciality'], fields: ['specialization'] },
  { match: ['name'], fields: ['full_name'] },
  { match: ['address', 'clinic'], fields: ['address', 'clinic_name'] },
  { match: ['city'], fields: ['city'] },
  { match: ['state'], fields: ['state'] },
  { match: ['experience'], fields: ['experience_years'] },
];

/**
 * Map free-text admin rejection reason to form field names for highlight hints.
 */
export function doctorProfileFieldsToReview(reason: string | null | undefined): string[] {
  if (!reason || !reason.trim()) {
    return ['full_name', 'phone', 'specialization', 'registration_number', 'qualification'];
  }
  const lower = reason.toLowerCase();
  const out = new Set<string>();
  for (const row of REJECTION_FIELD_KEYWORDS) {
    if (row.match.some((m) => lower.includes(m))) {
      for (const f of row.fields) out.add(f);
    }
  }
  if (out.size === 0) {
    return ['full_name', 'phone', 'specialization', 'registration_number', 'qualification'];
  }
  return [...out];
}
