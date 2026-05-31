/**
 * workspace/layouts/contextual-header.tsx
 *
 * Contextual header bar for workspace layouts.
 *
 * Each workspace gets:
 * - Workspace identity (icon, label, description from registry)
 * - Operational status indicators (badges, counts)
 * - Quick action buttons
 *
 * DESIGN:
 * - Calm, focused, uncluttered
 * - Shows only what's relevant to the current workspace
 * - No cross-role noise
 */

import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  AlertTriangle,
  CalendarCheck,
  Clock,
  CreditCard,
  FileText,
  ShoppingCart,
  Stethoscope,
  Users,
  UserRound,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { buttonVariants } from '@/components/ui/button';
import type { WorkspaceSlug } from '../registry';
import { WORKSPACE_REGISTRY } from '../registry';

/* ──────────────────────────────────────────────
 * Types
 * ────────────────────────────────────────────── */

export interface WorkspaceStatusIndicator {
  label: string;
  value: string | number;
  icon: LucideIcon;
  variant?: 'default' | 'warning' | 'danger' | 'success';
}

export interface WorkspaceQuickAction {
  path: string;
  label: string;
  icon: LucideIcon;
}

export interface WorkspaceContextConfig {
  /** Primary status indicators shown in the header */
  statusIndicators: WorkspaceStatusIndicator[];
  /** Quick action buttons */
  quickActions: WorkspaceQuickAction[];
  /** Optional subtitle / context line */
  subtitle?: string;
}

/* ──────────────────────────────────────────────
 * Workspace Context Configurations
 * ────────────────────────────────────────────── */

const WORKSPACE_CONTEXT_CONFIG: Record<WorkspaceSlug, WorkspaceContextConfig> = {
  frontdesk: {
    statusIndicators: [
      { label: 'Waiting', value: '—', icon: Clock, variant: 'default' },
      { label: 'Walk-ins Today', value: '—', icon: UserRound, variant: 'default' },
    ],
    quickActions: [
      { path: '/appointments', label: 'New Appointment', icon: CalendarCheck },
    ],
    subtitle: 'Patient arrivals, queue, and scheduling',
  },

  doctor: {
    statusIndicators: [
      { label: 'Today Queue', value: '—', icon: Clock, variant: 'default' },
      { label: 'Pending Notes', value: '—', icon: FileText, variant: 'warning' },
    ],
    quickActions: [
      { path: '/doctor/appointments', label: 'New Encounter', icon: Stethoscope },
    ],
    subtitle: 'Schedule, patients, and clinical care',
  },

  nurse: {
    statusIndicators: [
      { label: 'In Queue', value: '—', icon: Clock, variant: 'default' },
      { label: 'Vitals Pending', value: '—', icon: Activity, variant: 'warning' },
    ],
    quickActions: [
      { path: '/queue', label: 'Next Patient', icon: Users },
    ],
    subtitle: 'Vitals, queue, and clinical tasks',
  },

  operations: {
    statusIndicators: [
      { label: 'Active Alerts', value: '—', icon: AlertTriangle, variant: 'warning' },
      { label: 'Staff on Duty', value: '—', icon: Users, variant: 'default' },
    ],
    quickActions: [
      { path: '/dashboard', label: 'Activity Feed', icon: Activity },
    ],
    subtitle: 'Clinic operations, staff, and activity',
  },

  procurement: {
    statusIndicators: [
      { label: 'Low Stock Alerts', value: '—', icon: AlertTriangle, variant: 'danger' },
      { label: 'Pending POs', value: '—', icon: FileText, variant: 'warning' },
    ],
    quickActions: [
      { path: '/admin/procurement', label: 'New Order', icon: ShoppingCart },
    ],
    subtitle: 'Inventory, suppliers, and purchase orders',
  },

  finance: {
    statusIndicators: [
      { label: "Today's Revenue", value: '—', icon: CreditCard, variant: 'success' },
      { label: 'Pending Bills', value: '—', icon: FileText, variant: 'warning' },
    ],
    quickActions: [
      { path: '/billing', label: 'New Bill', icon: CreditCard },
    ],
    subtitle: 'Billing, reports, and revenue',
  },

  admin: {
    statusIndicators: [
      { label: 'Active Tenants', value: '—', icon: Users, variant: 'default' },
    ],
    quickActions: [],
    subtitle: 'Organization management and settings',
  },

  patient: {
    statusIndicators: [
      { label: 'Upcoming', value: '—', icon: CalendarCheck, variant: 'default' },
      { label: 'Messages', value: '—', icon: Activity, variant: 'default' },
    ],
    quickActions: [
      { path: '/patient/home', label: 'Book Appointment', icon: CalendarCheck },
    ],
    subtitle: 'Your health workspace',
  },
};

/** Get the contextual config for a workspace slug. */
export function getWorkspaceContext(slug: WorkspaceSlug): WorkspaceContextConfig {
  return WORKSPACE_CONTEXT_CONFIG[slug] ?? {
    statusIndicators: [],
    quickActions: [],
    subtitle: '',
  };
}

/* ──────────────────────────────────────────────
 * Contextual Header Component
 * ────────────────────────────────────────────── */

interface ContextualHeaderProps {
  workspaceSlug: WorkspaceSlug;
  /** Override status indicator values dynamically (e.g. from API) */
  statusOverrides?: Partial<Record<string, string | number>>;
  className?: string;
}

/**
 * Contextual header bar rendered inside each workspace layout.
 *
 * Shows:
 * - Workspace identity (icon + label from registry)
 * - Operational status indicators
 * - Quick action buttons
 */
export function ContextualHeader({
  workspaceSlug,
  statusOverrides,
  className,
}: ContextualHeaderProps) {
  const workspace = WORKSPACE_REGISTRY[workspaceSlug];
  const context = getWorkspaceContext(workspaceSlug);

  const indicators = useMemo(() => {
    if (!statusOverrides) return context.statusIndicators;
    return context.statusIndicators.map((indicator) => ({
      ...indicator,
      value: statusOverrides[indicator.label] ?? indicator.value,
    }));
  }, [context.statusIndicators, statusOverrides]);

  if (!workspace) return null;

  const Icon = workspace.icon;

  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 border-b border-border/60 bg-muted/20 px-4 py-2.5 md:px-6 lg:px-8',
        className
      )}
    >
      {/* Left: Workspace identity + status indicators */}
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
        {/* Workspace identity */}
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="h-4 w-4" aria-hidden />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">{workspace.label}</p>
            {context.subtitle && (
              <p className="truncate text-xs text-muted-foreground">{context.subtitle}</p>
            )}
          </div>
        </div>

        {/* Divider */}
        <div className="hidden h-6 w-px bg-border/60 sm:block" aria-hidden />

        {/* Status indicators */}
        <div className="flex flex-wrap items-center gap-2">
          {indicators.map((indicator) => {
            const IndicatorIcon = indicator.icon;
            const variantStyles = {
              default: 'bg-muted/80 text-muted-foreground border-border/60',
              warning: 'bg-amber-50 text-amber-800 border-amber-200/60 dark:bg-amber-950/20 dark:text-amber-300',
              danger: 'bg-red-50 text-red-800 border-red-200/60 dark:bg-red-950/20 dark:text-red-300',
              success: 'bg-emerald-50 text-emerald-800 border-emerald-200/60 dark:bg-emerald-950/20 dark:text-emerald-300',
            }[indicator.variant ?? 'default'];

            return (
              <Badge
                key={indicator.label}
                variant="outline"
                className={cn('gap-1.5 px-2.5 py-1 text-xs font-normal normal-case', variantStyles)}
              >
                <IndicatorIcon className="h-3.5 w-3.5" aria-hidden />
                <span className="tabular-nums">{indicator.value}</span>
                <span className="hidden sm:inline">{indicator.label}</span>
              </Badge>
            );
          })}
        </div>
      </div>

      {/* Right: Quick actions */}
      {context.quickActions.length > 0 && (
        <div className="flex shrink-0 items-center gap-2">
          {context.quickActions.map((action) => {
            const ActionIcon = action.icon;
            return (
              <Link
                key={action.path}
                to={action.path}
                className={cn(
                  buttonVariants({ variant: 'default', size: 'sm' }),
                  'gap-1.5 text-xs font-medium shadow-sm'
                )}
              >
                <ActionIcon className="h-3.5 w-3.5" aria-hidden />
                <span className="hidden sm:inline">{action.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
