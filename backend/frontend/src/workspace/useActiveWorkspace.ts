/**
 * workspace/useActiveWorkspace.ts
 *
 * Active workspace context hook.
 *
 * Provides the ACTUAL current workspace (from localStorage persistence),
 * not the role-resolved workspace. This is the source of truth for
 * workspace-aware UI decisions.
 *
 * DESIGN:
 * - Reads medical_webapp_last_workspace from localStorage
 * - Falls back to resolveUserWorkspace() if unset
 * - Validates stored workspace is in user's available workspaces
 * - Provides switchWorkspace() that persists + returns new slug
 * - Exports isClinicianWorkspaceActive() helper
 *
 * Workspace = operational context
 * Role = identity
 * Capabilities = authorization
 *
 * This hook does NOT change RBAC. It only provides workspace context.
 */
import { useCallback, useMemo, useState } from 'react';
import type { User } from '../types';
import { getEffectiveRoles, normalizeRoles } from '../utils/roles';
import type { WorkspaceSlug } from './registry';
import { getAllWorkspaceSlugs } from './registry';
import { resolveUserWorkspace } from './resolver';
import { persistLastWorkspace, getLastWorkspace } from './WorkspaceSwitcher';

/* ──────────────────────────────────────────────
 * Helpers
 * ────────────────────────────────────────────── */


/**
 * Check if a user has clinician capability (doctor role).
 * This is a capability check, NOT a workspace check.
 */
export function hasClinicianCapability(user: User | null, token: string | null): boolean {
  if (!user || !token) return false;
  const roles = normalizeRoles(getEffectiveRoles(user, token));
  return roles.includes('doctor');
}

/**
 * Resolve the actual active workspace slug.
 *
 * Priority:
 * 1. Stored last workspace (from localStorage)
 * 2. Role-resolved workspace (fallback)
 *
 * Validates that the stored workspace is in the user's available workspaces.
 */
export function resolveActiveWorkspace(
  user: User | null,
  token: string | null
): WorkspaceSlug {
  if (!user || !token) return 'admin';

  const stored = getLastWorkspace();
  const available = resolveAvailableWorkspaces(user, token);

  // If stored workspace is valid and available, use it
  if (stored && available.includes(stored)) {
    return stored;
  }

  // Fallback to role-resolved workspace
  return resolveUserWorkspace(user, token);
}

/**
 * Resolve the list of workspace slugs visible to the user.
 * Same logic as resolveUserWorkspaces in resolver.ts.
 */
export function resolveAvailableWorkspaces(
  user: User | null,
  token: string | null
): WorkspaceSlug[] {
  if (!user || !token) return ['admin'];
  const roles = normalizeRoles(getEffectiveRoles(user, token));

  // Admin / super_admin see all workspaces
  if (roles.some((r) => r === 'admin' || r === 'super_admin')) {
    return getAllWorkspaceSlugs();
  }

  // Normal users see only their single resolved workspace
  const primary = resolveUserWorkspace(user, token);
  return [primary];
}

/* ──────────────────────────────────────────────
 * Hook
 * ────────────────────────────────────────────── */

export interface ActiveWorkspaceState {
  /** The actual current workspace slug */
  workspace: WorkspaceSlug;
  /** All workspace slugs the user has access to */
  availableWorkspaces: WorkspaceSlug[];
  /** True when active workspace === 'doctor' */
  isClinician: boolean;
  /** True when user has doctor role (can use clinician workspace) */
  hasClinicianCapability: boolean;
  /** Switch to a different workspace */
  switchWorkspace: (slug: WorkspaceSlug) => void;
}

/**
 * useActiveWorkspace — provides the actual current workspace context.
 *
 * This is the single source of truth for workspace-aware UI decisions.
 * All components should use this hook instead of resolving workspace
 * from roles directly.
 */
export function useActiveWorkspace(
  user: User | null,
  token: string | null
): ActiveWorkspaceState {
  const [workspace, setWorkspace] = useState<WorkspaceSlug>(() =>
    resolveActiveWorkspace(user, token)
  );

  const availableWorkspaces = useMemo(
    () => resolveAvailableWorkspaces(user, token),
    [user, token]
  );

  const isClinician = workspace === 'doctor';

  const clinicianCapability = useMemo(
    () => hasClinicianCapability(user, token),
    [user, token]
  );

  const switchWorkspace = useCallback(
    (slug: WorkspaceSlug) => {
      persistLastWorkspace(slug);
      setWorkspace(slug);
    },
    []
  );

  return {
    workspace,
    availableWorkspaces,
    isClinician,
    hasClinicianCapability: clinicianCapability,
    switchWorkspace,
  };
}
