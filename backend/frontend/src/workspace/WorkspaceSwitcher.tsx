/**
 * workspace/WorkspaceSwitcher.tsx
 *
 * Workspace switcher dropdown.
 *
 * Allows users with multiple valid workspaces to switch between them.
 * - Remembers last workspace via localStorage
 * - Shows contextual workspace badges
 * - Dropdown UX with workspace icons and labels
 *
 * DESIGN:
 * - Only visible for users with multiple valid workspaces
 * - Clean dropdown with workspace identity
 * - Badge shows current workspace
 * - Smooth transitions between workspaces
 */

import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, ChevronDown, LayoutDashboard } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import type { WorkspaceSlug } from './registry';
import { WORKSPACE_REGISTRY } from './registry';
import { getWorkspaceContext } from './layouts/contextual-header';

/* ──────────────────────────────────────────────
 * Storage key for remembering last workspace
 * ────────────────────────────────────────────── */

const STORAGE_KEY = 'medical_webapp_last_workspace';

/** Persist the last active workspace slug. */
export function persistLastWorkspace(slug: WorkspaceSlug): void {
  try {
    localStorage.setItem(STORAGE_KEY, slug);
  } catch {
    // localStorage may be unavailable
  }
}

/** Retrieve the last persisted workspace slug. */
export function getLastWorkspace(): WorkspaceSlug | null {
  try {
    return localStorage.getItem(STORAGE_KEY) as WorkspaceSlug | null;
  } catch {
    return null;
  }
}

/* ──────────────────────────────────────────────
 * Workspace landing routes
 * ────────────────────────────────────────────── */

/**
 * Contextual landing redirects per workspace.
 * These are the "home" routes for each workspace.
 */
export const WORKSPACE_LANDING_ROUTES: Record<WorkspaceSlug, string> = {
  doctor: '/doctor/dashboard',
  frontdesk: '/appointments',
  nurse: '/queue',
  operations: '/dashboard',
  procurement: '/admin/inventory',
  finance: '/billing',
  admin: '/admin',
  patient: '/patient/home',
};

/** Get the landing route for a workspace slug. */
export function getWorkspaceLandingRoute(slug: WorkspaceSlug): string {
  return WORKSPACE_LANDING_ROUTES[slug] ?? '/';
}

/* ──────────────────────────────────────────────
 * Workspace Switcher Component
 * ────────────────────────────────────────────── */

interface WorkspaceSwitcherProps {
  /** Current active workspace slug */
  currentWorkspace: WorkspaceSlug;
  /** All workspace slugs the user has access to */
  availableWorkspaces: WorkspaceSlug[];
  /** Callback when workspace changes */
  onSwitch: (slug: WorkspaceSlug) => void;
  className?: string;
}

/**
 * WorkspaceSwitcher dropdown.
 *
 * Only renders when the user has access to multiple workspaces.
 * Shows workspace icons, labels, and contextual badges.
 * Persists the last selected workspace.
 */
export function WorkspaceSwitcher({
  currentWorkspace,
  availableWorkspaces,
  onSwitch,
  className,
}: WorkspaceSwitcherProps) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const currentMeta = WORKSPACE_REGISTRY[currentWorkspace];
  const CurrentIcon = currentMeta?.icon ?? LayoutDashboard;

  // Only show switcher if user has multiple workspaces
  if (availableWorkspaces.length < 2) return null;

  const handleSwitch = useCallback(
    (slug: WorkspaceSlug) => {
      persistLastWorkspace(slug);
      onSwitch(slug);
      navigate(getWorkspaceLandingRoute(slug));
      setOpen(false);
    },
    [navigate, onSwitch]
  );

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            'gap-2 px-2 text-sm font-medium hover:bg-accent/50',
            className
          )}
        >
          <CurrentIcon className="h-4 w-4 text-primary" aria-hidden />
          <span className="hidden sm:inline">{currentMeta?.label ?? 'Workspace'}</span>
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel className="text-xs font-medium text-muted-foreground">
          Switch Workspace
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {availableWorkspaces.map((slug) => {
          const meta = WORKSPACE_REGISTRY[slug];
          if (!meta) return null;

          const Icon = meta.icon;
          const isActive = slug === currentWorkspace;
          const context = getWorkspaceContext(slug);

          return (
            <DropdownMenuItem
              key={slug}
              disabled={isActive}
              onSelect={() => handleSwitch(slug)}
              className={cn(
                'flex items-center gap-3 py-2.5',
                isActive && 'bg-accent/50'
              )}
            >
              {/* Workspace icon */}
              <div
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                <Icon className="h-4 w-4" aria-hidden />
              </div>

              {/* Workspace info */}
              <div className="flex min-w-0 flex-1 flex-col">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{meta.label}</span>
                  {isActive && (
                    <Badge variant="outline" className="h-5 px-1.5 text-[10px]">
                      Active
                    </Badge>
                  )}
                </div>
                {context.subtitle && (
                  <span className="truncate text-xs text-muted-foreground">
                    {context.subtitle}
                  </span>
                )}
              </div>

              {/* Checkmark for active */}
              {isActive && (
                <Check className="h-4 w-4 text-primary" aria-hidden />
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
