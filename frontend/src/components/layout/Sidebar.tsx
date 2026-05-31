import { X, PanelLeft } from 'lucide-react';

import type { User } from '../../types';
import {
  getEffectiveRoles,
  normalizeRoles,
} from '../../utils/roles';
import { doctorNavItemHint } from '../../utils/doctorVerification';
import { useAppMode } from '../../contexts/AppModeContext';
import { NavItem } from './NavItem';
import { cn } from '@/lib/utils';

/**
 * workspace-driven sidebar
 *
 * Replaces the old branching logic (staffNavBase, adminModeNavBase,
 * patientFallbackNavItems, DOCTOR_PRACTICE_NAV) with a single
 * workspace registry lookup.
 *
 * Each user sees ONLY their workspace's navigation — calm, focused,
 * operationally contextual.
 */
import {
  resolveUserWorkspace,
  WORKSPACE_REGISTRY,
  type WorkspaceConfig,
} from '../../workspace';

interface SidebarProps {
  user: User | null;
  onClose?: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export function Sidebar({ user, onClose, isCollapsed, onToggleCollapse }: SidebarProps) {
  const { resolvedMode } = useAppMode();
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const effRoles = getEffectiveRoles(user, token);
  const roles = normalizeRoles(effRoles);

  // Resolve workspace from user roles
  const workspaceSlug = resolveUserWorkspace(user, token);
  const workspace: WorkspaceConfig = WORKSPACE_REGISTRY[workspaceSlug];

  // Determine if admin mode layout styling should apply
  const useAdminModeLayout = resolvedMode === 'admin' && workspaceSlug === 'admin';

  // Quick actions for the sidebar footer
  const quickActions = workspace?.quickActions ?? [];

  return (
    <div
      className={cn(
        'flex h-full min-h-screen w-full flex-col border-r border-border/80 bg-white',
        useAdminModeLayout && 'border-slate-200/80 bg-white'
      )}
    >
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex h-16 flex-shrink-0 items-center justify-between border-b border-border/80 px-3">
        <div
          className={`flex items-center gap-2 overflow-hidden transition-all duration-300 ${
            isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'
          }`}
        >
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-primary text-sm font-bold text-primary-foreground shadow-sm">
            <workspace.icon className="h-5 w-5" />
          </div>
          <div className="whitespace-nowrap">
            <h1 className="text-sm font-semibold leading-tight text-foreground">{workspace.label}</h1>
            <p className="text-xs leading-tight text-muted-foreground">{workspace.description}</p>
          </div>
        </div>

        <div
          className={`flex flex-1 items-center justify-center transition-all duration-300 ${
            isCollapsed ? 'opacity-100' : 'w-0 overflow-hidden opacity-0'
          }`}
        >
          <div className="group relative">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary font-bold text-primary-foreground shadow-sm">
              <workspace.icon className="h-5 w-5" />
            </div>
            <div className="invisible absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-border bg-popover px-2 py-1 text-xs text-popover-foreground opacity-0 shadow-lg transition-all duration-200 group-hover:visible group-hover:opacity-100">
              {workspace.label}
              <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-border" />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={onToggleCollapse}
            className="hidden rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground lg:flex"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={isCollapsed ? 'Expand' : 'Collapse'}
            type="button"
          >
            <PanelLeft
              className={`h-4 w-4 transition-transform duration-300 ${isCollapsed ? 'rotate-180' : ''}`}
            />
          </button>

          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted lg:hidden"
            aria-label="Close menu"
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* ── Navigation ─────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-2 py-4">
        {workspace.sections.map((section, idx) => (
          <div key={section.title ?? idx} className="mb-4">
            {section.title && (
              <p
                className={cn(
                  'mb-1 px-3 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/60',
                  isCollapsed && 'sr-only'
                )}
              >
                {section.title}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => (
                <NavItem
                  key={item.path}
                  path={item.path}
                  label={item.label}
                  icon={item.icon}
                  isCollapsed={isCollapsed}
                  onNavigate={onClose}
                  title={
                    roles.includes('doctor') && !roles.includes('admin') && !roles.includes('super_admin')
                      ? doctorNavItemHint(user, item.path)
                      : undefined
                  }
                />
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* ── Quick Actions ──────────────────────────────── */}
      {quickActions.length > 0 && !isCollapsed && (
        <div className="flex-shrink-0 border-t border-border/80 px-2 py-3">
          <p className="mb-1 px-3 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/60">
            Quick Actions
          </p>
          <ul className="space-y-0.5">
            {quickActions.map((action) => (
              <NavItem
                key={action.path}
                path={action.path}
                label={action.label}
                icon={action.icon}
                isCollapsed={isCollapsed}
                onNavigate={onClose}
              />
            ))}
          </ul>
        </div>
      )}

      {/* ── Footer - User info ─────────────────────────── */}
      {user && (
        <div className="flex-shrink-0 border-t border-border/80 p-3">
          <div className={`flex items-center gap-3 ${isCollapsed ? 'justify-center' : ''}`}>
            <div className="relative flex-shrink-0">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
                {(user.full_name || user.email || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-success" />
            </div>

            <div
              className={`overflow-hidden transition-all duration-300 ${
                isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'
              }`}
            >
              <p className="max-w-[140px] truncate text-sm font-medium text-foreground">
                {user.full_name || user.email || 'User'}
              </p>
              <p className="max-w-[140px] truncate text-xs capitalize text-muted-foreground">
                {workspace.label}
              </p>
            </div>
          </div>

          {isCollapsed && (
            <div className="group relative">
              <div className="invisible absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md border border-border bg-popover px-2 py-1 text-xs text-popover-foreground opacity-0 shadow-lg transition-all group-hover:visible group-hover:opacity-100">
                {user.full_name || user.email || 'User'}
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-border" />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
