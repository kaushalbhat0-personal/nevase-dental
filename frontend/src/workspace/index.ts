/**
 * workspace/index.ts
 *
 * Public API for the workspace system.
 *
 * Usage:
 *   import { resolveUserWorkspace, WORKSPACE_REGISTRY } from '../workspace';
 *   const ws = WORKSPACE_REGISTRY[resolveUserWorkspace(user, token)];
 *   // ws.sections → sidebar nav items
 *   // ws.label → sidebar header label
 *   // ws.icon → sidebar header icon
 */

export {
  WORKSPACE_REGISTRY,
  getWorkspaceNavItems,
  getAllWorkspaceSlugs,
  isValidWorkspace,
} from './registry';

export {
  resolveWorkspaceFromRoles,
  resolveUserWorkspace,
  resolveUserWorkspaces,
  isUserInWorkspace,
} from './resolver';

export type {
  WorkspaceSlug,
  WorkspaceConfig,
  WorkspaceNavItem,
  WorkspaceSidebarSection,
} from './registry';

/* ── Layouts ─────────────────────────────────── */
export {
  ContextualHeader,
  getWorkspaceContext,
  DoctorWorkspaceLayout,
  FrontDeskWorkspaceLayout,
  OperationsWorkspaceLayout,
  ProcurementWorkspaceLayout,
  FinanceWorkspaceLayout,
  PatientWorkspaceLayout,
} from './layouts';

export type {
  WorkspaceStatusIndicator,
  WorkspaceQuickAction,
  WorkspaceContextConfig,
} from './layouts';

/* ── Workspace Switcher ──────────────────────── */
export {
  WorkspaceSwitcher,
  persistLastWorkspace,
  getLastWorkspace,
  getWorkspaceLandingRoute,
  WORKSPACE_LANDING_ROUTES,
} from './WorkspaceSwitcher';

/* ── Contextual Redirects ────────────────────── */
export {
  pathBelongsToWorkspace,
  findWorkspaceForPath,
  getLoginRedirectRoute,
  getContextualFallbackRedirect,
  WORKSPACE_ROUTE_BOUNDARIES,
} from './contextual-redirects';

/* ── Route Isolation ─────────────────────────── */
export { RouteIsolation } from './route-isolation';

/* ── Active Workspace ────────────────────────── */
export {
  useActiveWorkspace,
  resolveActiveWorkspace,
  resolveAvailableWorkspaces,
  hasClinicianCapability,
} from './useActiveWorkspace';

export type { ActiveWorkspaceState } from './useActiveWorkspace';
