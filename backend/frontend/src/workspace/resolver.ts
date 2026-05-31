/**
 * workspace/resolver.ts
 *
 * Role → Workspace Resolution.
 *
 * Maps effective user roles to a workspace slug using the existing RBAC system.
 * This is a PURE mapping layer — it does NOT redesign or duplicate permissions.
 *
 * Resolution priority:
 * 1. First matching role wins (ordered by specificity)
 * 2. `patient` is resolved last to avoid catching doctor+patient dual-role users
 * 3. Falls back to `admin` for unrecognized staff roles
 *
 * REUSES:
 * - getEffectiveRoles() from utils/roles (existing auth)
 * - normalizeRoles() from utils/roles (existing normalization)
 * - No new RBAC — just a lookup table
 */

import type { User } from '../types';
import { getEffectiveRoles, normalizeRoles } from '../utils/roles';
import type { WorkspaceSlug } from './registry';
import { getAllWorkspaceSlugs } from './registry';
/* ──────────────────────────────────────────────
 * Role → Workspace Mapping
 * ──────────────────────────────────────────────
 *
 * Maps backend role strings to workspace slugs.
 * Order matters: first match wins.
 */

const ROLE_WORKSPACE_MAP: Record<string, WorkspaceSlug> = {
  receptionist: 'frontdesk',
  staff: 'frontdesk',
  doctor: 'doctor',
  nurse: 'nurse',
  operations: 'operations',
  procurement: 'procurement',
  finance: 'finance',
  admin: 'admin',
  super_admin: 'admin',
};

/**
 * Resolve the workspace slug for a given set of roles.
 *
 * @param roles - Normalized role strings (e.g. ['doctor'], ['admin', 'super_admin'])
 * @returns The resolved workspace slug
 */
export function resolveWorkspaceFromRoles(roles: string[]): WorkspaceSlug {
  const normalized = normalizeRoles(roles);

  // Check staff roles first (ordered by specificity)
  for (const role of normalized) {
    const mapped = ROLE_WORKSPACE_MAP[role];
    if (mapped) return mapped;
  }

  // Patient is last to avoid catching dual-role users
  if (normalized.includes('patient')) return 'patient';

  // Fallback for unrecognized roles
  return 'admin';
}

/**
 * Resolve the workspace slug for the current user.
 * Uses existing getEffectiveRoles() for authoritative role resolution.
 *
 * @param user - The current user object (may be null)
 * @param token - JWT token for role extraction
 * @returns The resolved workspace slug
 */
export function resolveUserWorkspace(
  user: User | null,
  token: string | null
): WorkspaceSlug {
  if (!user || !token) return 'admin';
  const effectiveRoles = getEffectiveRoles(user, token);
  return resolveWorkspaceFromRoles(effectiveRoles);
}

/**
 * Check if a user has access to a specific workspace.
 * Useful for route guards and conditional rendering.
 *
 * @param user - The current user object
 * @param token - JWT token
 * @param workspace - The workspace slug to check
 * @returns True if the user belongs to this workspace
 */
export function isUserInWorkspace(
  user: User | null,
  token: string | null,
  workspace: WorkspaceSlug
): boolean {
  return resolveUserWorkspace(user, token) === workspace;
}

/**
 * Resolve the list of workspace slugs visible to the user.
 *
 * UX visibility normalization:
 * - Admin / super_admin users see ALL workspaces (multi-workspace switcher).
 * - Normal users (doctor, nurse, receptionist, procurement, finance, patient)
 *   see ONLY their single resolved workspace — no dropdown.
 *
 * This is a PURE visibility filter. It does NOT change RBAC, route isolation,
 * or backend permissions.
 *
 * @param user - The current user object (may be null)
 * @param token - JWT token for role extraction
 * @returns Array of workspace slugs the user should see
 */
export function resolveUserWorkspaces(
  user: User | null,
  token: string | null
): WorkspaceSlug[] {
  if (!user || !token) return ['admin'];
  const effectiveRoles = getEffectiveRoles(user, token);
  const normalized = normalizeRoles(effectiveRoles);

  // Admin / super_admin see all workspaces (multi-workspace switcher)
  if (normalized.some((r) => r === 'admin' || r === 'super_admin')) {
    return getAllWorkspaceSlugs();
  }

  // Normal users see only their single resolved workspace
  const primary = resolveWorkspaceFromRoles(normalized);
  return [primary];
}
