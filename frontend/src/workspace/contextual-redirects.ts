/**
 * workspace/contextual-redirects.ts
 *
 * Contextual landing redirect logic.
 *
 * Provides:
 * - Login redirects: where to send users after login based on workspace
 * - Invalid workspace redirects: fallback when user hits wrong workspace
 * - Contextual fallbacks: patient hitting admin → patient landing
 *
 * DESIGN:
 * - UX-level redirects only (security remains backend capability-based)
 * - Workspace-aware fallback chains
 * - Clean, predictable redirect behavior
 */

import type { WorkspaceSlug } from './registry';
import { WORKSPACE_LANDING_ROUTES } from './WorkspaceSwitcher';

/* ──────────────────────────────────────────────
 * Workspace route boundaries
 *
 * Maps workspace slugs to route prefixes they "own".
 * Used for detecting when a user is in the wrong workspace.
 * ────────────────────────────────────────────── */

export const WORKSPACE_ROUTE_BOUNDARIES: Record<WorkspaceSlug, string[]> = {
  doctor: ['/doctor'],
  frontdesk: ['/appointments', '/queue'],
  nurse: ['/queue', '/nurse'],
  operations: ['/dashboard', '/operations'],
  procurement: ['/admin/inventory', '/admin/procurement', '/admin/suppliers'],
  finance: ['/billing', '/admin/finance'],
  admin: ['/admin'],
  patient: ['/patient'],
};

/* ──────────────────────────────────────────────
 * Redirect helpers
 * ────────────────────────────────────────────── */

/**
 * Determine if a given pathname belongs to a specific workspace's route boundary.
 *
 * This is UX isolation only — security remains backend capability-based.
 */
export function pathBelongsToWorkspace(
  pathname: string,
  workspaceSlug: WorkspaceSlug
): boolean {
  const boundaries = WORKSPACE_ROUTE_BOUNDARIES[workspaceSlug];
  if (!boundaries) return false;
  return boundaries.some((prefix) => pathname.startsWith(prefix));
}

/**
 * Find which workspace "owns" a given pathname.
 * Returns the workspace slug if found, or null if the path is generic.
 */
export function findWorkspaceForPath(pathname: string): WorkspaceSlug | null {
  const entries = Object.entries(WORKSPACE_ROUTE_BOUNDARIES) as [WorkspaceSlug, string[]][];
  for (const [slug, prefixes] of entries) {
    if (prefixes.some((prefix) => pathname.startsWith(prefix))) {
      return slug;
    }
  }
  return null;
}

/**
 * Get the appropriate landing route after login.
 *
 * @param primaryWorkspace - The user's primary resolved workspace
 * @param requestedPath - Optional path the user was trying to access before login
 * @returns The route to redirect to
 */
export function getLoginRedirectRoute(
  primaryWorkspace: WorkspaceSlug,
  requestedPath?: string
): string {
  // If user was trying to access a specific path, check if it belongs to their workspace
  if (requestedPath && requestedPath !== '/') {
    const pathWorkspace = findWorkspaceForPath(requestedPath);
    if (pathWorkspace === primaryWorkspace) {
      return requestedPath;
    }
    // If the path belongs to a different workspace, redirect to their own landing
    if (pathWorkspace && pathWorkspace !== primaryWorkspace) {
      return WORKSPACE_LANDING_ROUTES[primaryWorkspace];
    }
    // Generic path (like /) — redirect to workspace landing
    return WORKSPACE_LANDING_ROUTES[primaryWorkspace];
  }

  return WORKSPACE_LANDING_ROUTES[primaryWorkspace];
}

/**
 * Get a contextual fallback redirect when a user hits a route
 * that doesn't belong to their current workspace.
 *
 * Examples:
 * - patient trying /admin → /patient/home
 * - doctor hitting /admin/inventory → /doctor/dashboard
 * - procurement user hitting /appointments → /admin/inventory
 */
export function getContextualFallbackRedirect(
  currentWorkspace: WorkspaceSlug,
  attemptedPath: string
): string {
  const attemptedWorkspace = findWorkspaceForPath(attemptedPath);

  // If the attempted path belongs to a different workspace, redirect to current workspace landing
  if (attemptedWorkspace && attemptedWorkspace !== currentWorkspace) {
    return WORKSPACE_LANDING_ROUTES[currentWorkspace];
  }

  // If the path is unrecognized or generic, still go to workspace landing
  return WORKSPACE_LANDING_ROUTES[currentWorkspace];
}

/**
 * Get the landing route for a workspace.
 * Convenience re-export from WorkspaceSwitcher.
 */
export { WORKSPACE_LANDING_ROUTES } from './WorkspaceSwitcher';
export { getWorkspaceLandingRoute } from './WorkspaceSwitcher';
