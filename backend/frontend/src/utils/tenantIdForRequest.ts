import { roleFromToken, rolesFromToken, tenantIdFromToken } from './jwtPayload';

/** Postgres nil / sentinel UUID — must never be sent as `X-Tenant-ID`. */
export const NIL_TENANT_UUID = '00000000-0000-0000-0000-000000000000';

/** Canonical localStorage key for the org switcher (super admin) and aligned tenant header for staff. */
export const ACTIVE_TENANT_ID_STORAGE_KEY = 'activeTenantId';

/** Alias used by some clients; always kept in sync with `activeTenantId` when set. */
export const ACTIVE_TENANT_ID_ALIAS_KEY = 'active_tenant_id';

/** @deprecated Legacy key; still read for migration */
const TENANT_ID_LEGACY_STORAGE_KEY = 'tenant_id';

/** @deprecated Legacy fallback */
const ADMIN_SELECTED_TENANT_STORAGE_KEY = 'adminSelectedTenantId';

/** Dispatched on the window after the active tenant id changes (same-tab listeners). */
export const TENANT_ID_STORAGE_EVENT = 'tenant_id_changed';

/** @deprecated Use ACTIVE_TENANT_ID_STORAGE_KEY */
export const TENANT_ID_STORAGE_KEY = ACTIVE_TENANT_ID_STORAGE_KEY;

function isUsableTenantString(id: string | null | undefined): id is string {
  const t = id?.trim();
  return !!t && t !== NIL_TENANT_UUID;
}

export function getActiveTenantId(): string | null {
  const primary = localStorage.getItem(ACTIVE_TENANT_ID_STORAGE_KEY)?.trim();
  if (isUsableTenantString(primary)) {
    if (localStorage.getItem(ACTIVE_TENANT_ID_ALIAS_KEY) !== primary) {
      try {
        localStorage.setItem(ACTIVE_TENANT_ID_ALIAS_KEY, primary);
      } catch {
        // ignore
      }
    }
    return primary;
  }
  const alias = localStorage.getItem(ACTIVE_TENANT_ID_ALIAS_KEY)?.trim();
  if (isUsableTenantString(alias)) {
    localStorage.setItem(ACTIVE_TENANT_ID_STORAGE_KEY, alias);
    return alias;
  }
  const legacy = localStorage.getItem(TENANT_ID_LEGACY_STORAGE_KEY)?.trim();
  if (isUsableTenantString(legacy)) {
    localStorage.setItem(ACTIVE_TENANT_ID_STORAGE_KEY, legacy);
    try {
      localStorage.setItem(ACTIVE_TENANT_ID_ALIAS_KEY, legacy);
    } catch {
      // ignore
    }
    return legacy;
  }
  const adminPick = localStorage.getItem(ADMIN_SELECTED_TENANT_STORAGE_KEY)?.trim();
  if (isUsableTenantString(adminPick)) {
    localStorage.setItem(ACTIVE_TENANT_ID_STORAGE_KEY, adminPick);
    try {
      localStorage.setItem(ACTIVE_TENANT_ID_ALIAS_KEY, adminPick);
    } catch {
      // ignore
    }
    return adminPick;
  }
  return null;
}

export function setActiveTenantId(tenantId: string): void {
  const id = tenantId.trim();
  localStorage.setItem(ACTIVE_TENANT_ID_STORAGE_KEY, id);
  try {
    localStorage.setItem(ACTIVE_TENANT_ID_ALIAS_KEY, id);
  } catch {
    // ignore
  }
  localStorage.removeItem(TENANT_ID_LEGACY_STORAGE_KEY);
  localStorage.removeItem(ADMIN_SELECTED_TENANT_STORAGE_KEY);
  window.dispatchEvent(new Event(TENANT_ID_STORAGE_EVENT));
}

/** Clear super-admin org selection (no `X-Tenant-ID` until another org is chosen). */
export function clearActiveTenantId(): void {
  localStorage.removeItem(ACTIVE_TENANT_ID_STORAGE_KEY);
  try {
    localStorage.removeItem(ACTIVE_TENANT_ID_ALIAS_KEY);
  } catch {
    // ignore
  }
  localStorage.removeItem(TENANT_ID_LEGACY_STORAGE_KEY);
  localStorage.removeItem(ADMIN_SELECTED_TENANT_STORAGE_KEY);
  window.dispatchEvent(new Event(TENANT_ID_STORAGE_EVENT));
}

function isSuperAdminFromStoredUser(userStr: string | null, token: string | null): boolean {
  if (userStr) {
    try {
      const u = JSON.parse(userStr) as { roles?: string[]; role?: string };
      if (Array.isArray(u.roles) && u.roles.some((r) => String(r).toLowerCase() === 'super_admin')) {
        return true;
      }
      if (u.role && String(u.role).toLowerCase() === 'super_admin') return true;
    } catch {
      // ignore
    }
  }
  const fromJwt = rolesFromToken(token) ?? (roleFromToken(token) ? [roleFromToken(token)!] : []);
  return fromJwt.some((r) => r.toLowerCase() === 'super_admin');
}

/**
 * Resolves the tenant id to send as `X-Tenant-ID` for scoped APIs.
 * - super_admin: only the selected org (`activeTenantId`); never JWT/env guessing.
 * - others: selected org, then user profile / JWT home tenant.
 */
export function getTenantIdForRequest(): string | undefined {
  const token = localStorage.getItem('token');
  const userStr = localStorage.getItem('user');

  const active = getActiveTenantId() ?? undefined;

  if (isSuperAdminFromStoredUser(userStr, token)) {
    return active;
  }

  if (active) {
    return active;
  }

  if (userStr) {
    try {
      const user = JSON.parse(userStr) as { role?: string; tenant_id?: string | null };
      const fromUser = user.tenant_id != null ? String(user.tenant_id) : undefined;
      if (isUsableTenantString(fromUser)) {
        return fromUser;
      }
    } catch {
      // fall through
    }
  }

  const fromJwt = tenantIdFromToken(token);
  if (isUsableTenantString(fromJwt)) {
    return fromJwt;
  }
  const fromEnvRaw = import.meta.env.VITE_DEV_TENANT_ID as string | undefined;
  return isUsableTenantString(fromEnvRaw) ? fromEnvRaw : undefined;
}
