import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Menu, Bell, Settings, ChevronDown, Building2 } from 'lucide-react';
import { tenantsApi } from '../../services';
import type { Tenant, User } from '../../types';
import { getEffectiveRoles, isSuperAdminRole } from '../../utils/roles';
import {
  clearActiveTenantId,
  getActiveTenantId,
  TENANT_ID_STORAGE_EVENT,
  setActiveTenantId,
} from '../../utils/tenantIdForRequest';
import { cn } from '@/lib/utils';
import { ModeSwitcher } from './ModeSwitcher';
import { WorkspaceSwitcher } from '../../workspace/WorkspaceSwitcher';
import { useActiveWorkspace } from '../../workspace/useActiveWorkspace';



export interface HeaderProps {
  user: User | null;
  onLogout: () => void;
  onMenuToggle: () => void;
  /** e.g. doctor workspace title */
  centerSlot?: ReactNode;
}

export function Header({ user, onLogout, onMenuToggle, centerSlot }: HeaderProps) {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeTenantId, setActiveTenantIdState] = useState<string | null>(() =>
    typeof window !== 'undefined' ? getActiveTenantId() : null
  );
  const switcherRef = useRef<HTMLDivElement>(null);

  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const { workspace: activeWorkspace, availableWorkspaces, switchWorkspace } = useActiveWorkspace(user, token);


  const showSwitcher = isSuperAdminRole(getEffectiveRoles(user, localStorage.getItem('token')));

  const loadTenants = useCallback(async () => {
    if (!showSwitcher) return;
    try {
      const list = await tenantsApi.getAll();
      const activeOnly = list.filter((t) => !t.is_deleted);
      setTenants(activeOnly);
      const selected = getActiveTenantId();
      if (selected && !activeOnly.some((t) => t.id === selected)) {
        if (activeOnly[0]) {
          setActiveTenantId(activeOnly[0].id);
        } else {
          clearActiveTenantId();
        }
      }
    } catch {
      setTenants([]);
    }
  }, [showSwitcher]);

  useEffect(() => {
    void loadTenants();
  }, [loadTenants]);

  useEffect(() => {
    const sync = () => {
      setActiveTenantIdState(getActiveTenantId());
    };
    window.addEventListener(TENANT_ID_STORAGE_EVENT, sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener(TENANT_ID_STORAGE_EVENT, sync);
      window.removeEventListener('storage', sync);
    };
  }, []);

  useEffect(() => {
    if (!menuOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (switcherRef.current?.contains(e.target as Node)) return;
      setMenuOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [menuOpen]);

  const selectedTenant = tenants.find((t) => t.id === activeTenantId);
  const switcherLabel = selectedTenant?.name ?? 'Select organization';

  const onSelectTenant = (t: Tenant) => {
    setActiveTenantId(t.id);
    setMenuOpen(false);
    window.location.assign('/admin/dashboard');
  };

  return (
    <header
      className={cn(
        'sticky top-0 z-30 flex h-14 shrink-0 items-center justify-between border-b border-border/80 bg-white/90 px-4 backdrop-blur-md md:px-6',
        'shadow-sm shadow-black/[0.03]'
      )}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl text-foreground transition-colors hover:bg-muted lg:hidden"
          aria-label="Open menu"
          type="button"
        >
          <Menu className="h-5 w-5" />
        </button>

        {centerSlot && <div className="min-w-0 flex-1">{centerSlot}</div>}

        {showSwitcher && activeTenantId && !centerSlot ? (
          <span className="hidden max-w-[220px] truncate text-sm text-muted-foreground sm:inline">
            Managing:{' '}
            <span className="font-medium text-foreground">
              {selectedTenant?.name ?? (tenants.length ? 'Unknown organization' : '…')}
            </span>
          </span>
        ) : null}

        {showSwitcher && !centerSlot ? (
          <div className="relative min-w-0 max-w-[min(100%,280px)]" ref={switcherRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              className={cn(
                'flex min-h-9 w-full items-center gap-2 rounded-xl border border-border/80 bg-background px-3 py-1.5 text-left text-sm transition-colors hover:bg-muted/60'
              )}
              aria-expanded={menuOpen}
              aria-haspopup="listbox"
            >
              <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate font-medium text-foreground">{switcherLabel}</span>
              <ChevronDown
                className={cn(
                  'h-4 w-4 shrink-0 text-muted-foreground transition-transform',
                  menuOpen && 'rotate-180'
                )}
              />
            </button>
            {menuOpen && (
              <ul
                className="absolute left-0 top-full z-50 mt-1 max-h-64 w-full min-w-[220px] overflow-auto rounded-xl border border-border bg-popover py-1 shadow-md"
                role="listbox"
              >
                {tenants.length === 0 ? (
                  <li className="px-3 py-2 text-sm text-muted-foreground">No organizations</li>
                ) : (
                  tenants.map((t) => (
                    <li key={t.id} role="option" aria-selected={t.id === activeTenantId}>
                      <button
                        type="button"
                        className={cn(
                          'w-full px-3 py-2 text-left text-sm hover:bg-muted',
                          t.id === activeTenantId && 'bg-muted/80 font-medium'
                        )}
                        onClick={() => onSelectTenant(t)}
                      >
                        <span className="block truncate">{t.name}</span>
                        <span className="text-xs capitalize text-muted-foreground">{t.type}</span>
                      </button>
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        ) : null}
      </div>

      {/* Workspace Switcher - shown when user has multiple workspaces */}
      {user && (
        <WorkspaceSwitcher
          currentWorkspace={activeWorkspace}
          availableWorkspaces={availableWorkspaces}
          onSwitch={switchWorkspace}
        />
      )}


      <div className="ml-3 flex min-w-0 flex-shrink-0 items-center gap-1 sm:gap-2">
        {user && <ModeSwitcher user={user} />}

        <div className="hidden items-center gap-0.5 sm:flex">
          <button
            className="relative rounded-xl p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            title="Notifications"
            type="button"
          >
            <Bell className="h-5 w-5" />
            <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
              3
            </span>
          </button>
          <button
            className="rounded-xl p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            title="Settings"
            type="button"
          >
            <Settings className="h-5 w-5" />
          </button>
        </div>

        <div className="flex sm:hidden">
          <button
            onClick={onLogout}
            className="rounded-lg px-2 py-1.5 text-xs font-medium text-destructive transition-colors hover:bg-destructive/10"
            type="button"
          >
            Logout
          </button>
        </div>

        {user && (
          <div className="hidden items-center gap-3 sm:flex">
            <span className="hidden max-w-[140px] truncate text-sm text-muted-foreground md:inline">
              {user.email || user.full_name || 'User'}
            </span>
            <button
              onClick={onLogout}
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
              type="button"
            >
              Logout
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
