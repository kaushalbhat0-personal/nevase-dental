import { X, Stethoscope, UserRound } from 'lucide-react';
import type { User } from '../../types';
import { getEffectiveRoles, normalizeRoles } from '../../utils/roles';
import {
  doctorNavItemHint,
  isDoctorNavItemLocked,
  isDoctorNavItemVisible,
} from '../../utils/doctorVerification';
import { NavItem } from './NavItem';
import { DOCTOR_PRACTICE_NAV } from './doctorNav';

interface DoctorSidebarProps {
  user: User | null;
  onClose?: () => void;
}

export function DoctorSidebar({ user, onClose }: DoctorSidebarProps) {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const eff = getEffectiveRoles(user, token);
  const roles = normalizeRoles(eff);
  const isDoctor = roles.includes('doctor');

  const baseLinks = isDoctor
    ? DOCTOR_PRACTICE_NAV
    : DOCTOR_PRACTICE_NAV.filter((l) => l.path !== '/doctor/availability');
  const links = baseLinks.filter((item) => isDoctorNavItemVisible(user, token, item.path));

  return (
    <div className="flex h-full min-h-0 w-full flex-col border-r border-border/80 bg-white">
      <div className="flex h-16 flex-shrink-0 items-center justify-between border-b border-border/80 px-4">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-primary text-sm font-bold text-primary-foreground shadow-sm">
            <Stethoscope className="h-4 w-4" aria-hidden />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">Clinician</p>
            <p className="truncate text-xs text-muted-foreground">Workspace</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted lg:hidden"
          aria-label="Close menu"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-4">
        <ul className="space-y-0.5">
          {links.map((item) => (
            <NavItem
              key={item.path}
              path={item.path}
              label={item.label}
              icon={item.icon}
              isCollapsed={false}
              onNavigate={onClose}
              disabled={isDoctorNavItemLocked(user, token, item.path)}
              title={doctorNavItemHint(user, item.path)}
            />
          ))}
        </ul>
      </nav>

      {user && (
        <div className="flex-shrink-0 border-t border-border/80 p-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
              <UserRound className="h-4 w-4" aria-hidden />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">
                {user.full_name || 'Doctor'}
              </p>
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
              {user.doctor_id && user.doctor_verification_status && (
                <p
                  className="mt-1 text-[10px] font-medium uppercase tracking-wide"
                  title="Marketplace verification"
                >
                  {user.doctor_verification_status === 'approved' && (
                    <span className="text-emerald-600">Verified doctor</span>
                  )}
                  {user.doctor_verification_status === 'draft' && (
                    <span className="text-slate-600">Profile not submitted</span>
                  )}
                  {user.doctor_verification_status === 'pending' && (
                    <span className="text-amber-600">Under review</span>
                  )}
                  {user.doctor_verification_status === 'rejected' && (
                    <span className="text-red-600">Verification rejected</span>
                  )}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
