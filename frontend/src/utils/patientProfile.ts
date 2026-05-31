import type { Patient } from '../types';

function sameId(a: unknown, b: unknown): boolean {
  if (a == null || b == null) return false;
  return String(a).toLowerCase() === String(b).toLowerCase();
}

/**
 * Resolve the patient row for the logged-in user from GET /patients.
 * Only returns a row when `user_id` matches the logged-in user id or JWT subject.
 * Does not guess from list position (no single-row fallback).
 */
export function resolveLinkedPatient(
  patients: Patient[],
  loggedInUserId: string | number | undefined,
  tokenUserId: string | undefined
): Patient | null {
  const candidates = [loggedInUserId, tokenUserId].filter(
    (v): v is string | number => v !== undefined && v !== null && String(v) !== ''
  );
  for (const c of candidates) {
    const hit = patients.find((p) => p.user_id != null && sameId(p.user_id, c));
    if (hit) return hit;
  }
  return null;
}
