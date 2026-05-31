/**
 * workspace/route-isolation.tsx
 *
 * UX-level route isolation component.
 *
 * Wraps routes to ensure users only see navigation/routes relevant
 * to their current workspace.
 *
 * IMPORTANT:
 * This is UX isolation ONLY.
 * Security remains backend capability-based.
 *
 * BEHAVIOR:
 * - If the current path belongs to the user's workspace → render children
 * - If the current path belongs to a DIFFERENT workspace → redirect to workspace landing
 * - If the current path is generic (e.g. /) → render children (landing page handles it)
 *
 * EXAMPLES:
 * - doctor workspace should not expose procurement routes in normal navigation flow
 * - procurement workspace should not expose patient-care routes
 * - patient trying admin route → redirected to patient workspace landing
 */

import { useEffect, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { WorkspaceSlug } from './registry';
import { findWorkspaceForPath } from './contextual-redirects';
import { getWorkspaceLandingRoute } from './WorkspaceSwitcher';

interface RouteIsolationProps {
  /** The current active workspace slug */
  workspaceSlug: WorkspaceSlug;
  /** Child routes to render if isolation passes */
  children: ReactNode;
}

/**
 * RouteIsolation component.
 *
 * Provides UX-level route isolation by checking if the current path
 * belongs to the user's workspace. If not, redirects to the workspace landing.
 *
 * This is a soft boundary — it prevents accidental navigation to
 * out-of-workspace routes via the UI. Backend security is unchanged.
 */
export function RouteIsolation({ workspaceSlug, children }: RouteIsolationProps) {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const pathWorkspace = findWorkspaceForPath(location.pathname);

    // If the path belongs to a different workspace, redirect
    if (pathWorkspace && pathWorkspace !== workspaceSlug) {
      const landingRoute = getWorkspaceLandingRoute(workspaceSlug);
      navigate(landingRoute, { replace: true });
    }
    // If path is generic (no workspace owner), let it render
    // The landing page or workspace layout will handle it
  }, [location.pathname, workspaceSlug, navigate]);

  return <>{children}</>;
}
