import { NavLink, useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItemProps {
  path: string;
  label: string;
  icon: LucideIcon;
  isCollapsed: boolean;
  onNavigate?: () => void;
  /** When true, item is visible but not navigable (e.g. doctor not yet verified). */
  disabled?: boolean;
  /** Native tooltip (e.g. pending verification read-mostly hint). */
  title?: string;
  /** Small numeric badge (e.g. low-stock count). Hidden when 0 or unset. */
  badgeCount?: number;
}

export function NavItem({
  path,
  label,
  icon: Icon,
  isCollapsed,
  onNavigate,
  disabled = false,
  title,
  badgeCount,
}: NavItemProps) {
  const location = useLocation();
  const isActive = location.pathname === path || location.pathname.startsWith(`${path}/`);

  if (disabled) {
    return (
      <li>
        <div
          className={cn(
            'group relative flex cursor-not-allowed items-center gap-3 overflow-hidden rounded-xl px-3 py-2.5 opacity-50',
            'text-muted-foreground'
          )}
          aria-disabled="true"
          role="link"
          title={title ?? 'Available after your profile is verified'}
        >
          <div className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-primary opacity-0" />
          <Icon className="h-5 w-5 flex-shrink-0 text-muted-foreground" aria-hidden />
          <span className="flex min-w-0 flex-1 items-center justify-between gap-2">
            <span
              className={cn(
                'text-sm whitespace-nowrap transition-all duration-300',
                isCollapsed ? 'w-0 translate-x-2 overflow-hidden opacity-0' : 'w-auto translate-x-0 opacity-100'
              )}
            >
              {label}
            </span>
            {!isCollapsed && badgeCount != null && badgeCount > 0 ? (
              <span className="rounded-full bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-amber-950 dark:text-amber-100 shrink-0">
                {badgeCount > 99 ? '99+' : badgeCount}
              </span>
            ) : null}
          </span>
        </div>
      </li>
    );
  }

  return (
    <li>
      <NavLink
        to={path}
        onClick={onNavigate}
        title={title}
        className={({ isActive: navIsActive }) =>
          cn(
            'group relative flex items-center gap-3 overflow-hidden rounded-xl px-3 py-2.5 transition-all duration-200',
            navIsActive || isActive
              ? 'bg-primary/10 font-medium text-primary'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          )
        }
      >
        {/* Active indicator bar */}
        <div
          className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full transition-all duration-200 ${
            isActive ? 'bg-primary opacity-100' : 'bg-primary opacity-0'
          }`}
        />

        {/* Icon */}
        <Icon className={`h-5 w-5 flex-shrink-0 transition-all duration-200 ${
            isCollapsed ? 'mx-auto' : ''
          } ${isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'}`}
        />

        <span className="flex min-w-0 flex-1 items-center justify-between gap-2">
          <span
            className={`text-sm whitespace-nowrap transition-all duration-300 ${
              isCollapsed
                ? 'opacity-0 w-0 overflow-hidden translate-x-2'
                : 'opacity-100 w-auto translate-x-0'
            }`}
          >
            {label}
          </span>
          {!isCollapsed && badgeCount != null && badgeCount > 0 ? (
            <span className="rounded-full bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-amber-950 dark:text-amber-100 shrink-0">
              {badgeCount > 99 ? '99+' : badgeCount}
            </span>
          ) : null}
        </span>

        {/* Tooltip for collapsed state */}
        {isCollapsed && (
          <div className="absolute left-full z-50 ml-2 whitespace-nowrap rounded-md border border-border bg-popover px-2 py-1 text-xs text-popover-foreground opacity-0 shadow-lg transition-all duration-200 invisible group-hover:visible group-hover:opacity-100">
            {label}
            <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 border-4 border-transparent border-r-background" />
          </div>
        )}
      </NavLink>
    </li>
  );
}
