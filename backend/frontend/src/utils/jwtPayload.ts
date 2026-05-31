/**
 * Decode the JWT payload (middle segment) without verifying signature.
 *
 * This is intentionally "best effort" for UI convenience only (role/tenant hints, debug).
 * Do NOT use this for security decisions — the server remains the source of truth.
 */
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const pad = base64.length % 4;
    if (pad) base64 += '='.repeat(4 - pad);
    const json = atob(base64);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function roleFromToken(token: string | null): string | undefined {
  if (!token) return undefined;
  const payload = decodeJwtPayload(token);
  const role = payload?.role;
  return typeof role === 'string' ? role : undefined;
}

/** `roles` claim when present; otherwise a single `role` string as a one-element list. */
export function rolesFromToken(token: string | null): string[] | undefined {
  if (!token) return undefined;
  const payload = decodeJwtPayload(token);
  const raw = payload?.roles;
  if (Array.isArray(raw) && raw.every((x) => typeof x === 'string')) {
    return raw as string[];
  }
  const single = payload?.role;
  if (typeof single === 'string') {
    return [single];
  }
  return undefined;
}

export function tenantIdFromToken(token: string | null): string | null | undefined {
  if (!token) return undefined;
  const payload = decodeJwtPayload(token);
  const tid = payload?.tenant_id;
  if (tid === null) return null;
  if (typeof tid === 'string') return tid;
  return undefined;
}

/** Linked doctor row id when present on the access token. */
export function doctorIdFromToken(token: string | null): string | null | undefined {
  if (!token) return undefined;
  const payload = decodeJwtPayload(token);
  const d = payload?.doctor_id;
  if (d === null) return null;
  if (typeof d === 'string' && d.length > 0) return d;
  return undefined;
}

export function isOwnerFromToken(token: string | null): boolean | undefined {
  if (!token) return undefined;
  const payload = decodeJwtPayload(token);
  const v = payload?.is_owner;
  if (typeof v === 'boolean') return v;
  return undefined;
}

/** Present on access tokens when a doctor roster row is linked; omitted for non-doctor logins. */
export function doctorProfileCompleteFromToken(token: string | null): boolean | null | undefined {
  if (!token) return undefined;
  const payload = decodeJwtPayload(token);
  const v = payload?.doctor_profile_complete;
  if (v === null) return null;
  if (typeof v === 'boolean') return v;
  return undefined;
}

/** JWT `sub` — same identifier as backend user id (UUID string). */
export function userIdFromAccessToken(token: string | null): string | undefined {
  if (!token) return undefined;
  const payload = decodeJwtPayload(token);
  const sub = payload?.sub;
  return typeof sub === 'string' ? sub : undefined;
}
