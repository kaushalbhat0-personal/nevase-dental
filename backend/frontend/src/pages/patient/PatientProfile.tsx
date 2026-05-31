/**
 * PatientProfile — personal account + records hub.
 *
 * Contains:
 * - Documents
 * - Bills
 * - Appointments
 * - Settings / Communication Preferences
 * - Future: insurance, dependents
 */

import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  FileText,
  Receipt,
  Calendar,
  Settings,
  ChevronRight,
  HeartPulse,
  Heart,
  AlertTriangle,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '@/components/ui/button';

const profileSections = [
  { key: 'documents', label: 'Documents', icon: FileText, route: '/patient/profile/documents', description: 'Prescriptions, summaries, invoices' },
  { key: 'bills', label: 'Bills', icon: Receipt, route: '/patient/profile/bills', description: 'Payment history and statements' },
  { key: 'appointments', label: 'Appointments', icon: Calendar, route: '/patient/profile/appointments', description: 'Upcoming and past visits' },
  { key: 'settings', label: 'Settings', icon: Settings, route: '/patient/profile/settings', description: 'Preferences and communication' },
] as const;

export function PatientProfile() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const pathname = location.pathname;

  // Check if we're on a sub-page (not the index)
  const isSubPage = pathname !== '/patient/profile';

  // If on a sub-page, render just the outlet
  if (isSubPage) {
    return (
      <div className="pb-24">
        <Outlet />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-24">
      {/* Profile Header */}
      <div className="flex items-center gap-4 rounded-2xl border border-border/80 bg-card p-4 shadow-sm">
        <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-primary/10">
          <HeartPulse className="h-8 w-8 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="text-lg font-bold text-foreground truncate">
            {user?.full_name || 'Patient'}
          </h1>
          <p className="text-sm text-muted-foreground truncate">{user?.email}</p>
        </div>
      </div>

      {/* Menu Sections */}
      <nav className="space-y-2" aria-label="Profile sections">
        {profileSections.map(({ key, label, icon: Icon, route, description }) => (
          <button
            key={key}
            type="button"
            onClick={() => navigate(route)}
            className="flex w-full items-center gap-3 rounded-2xl border border-border/60 bg-card p-4 text-left shadow-sm transition hover:shadow-md active:scale-[0.99] touch-manipulation"
          >
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <Icon className="h-6 w-6 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground">{label}</p>
              <p className="text-xs text-muted-foreground">{description}</p>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
          </button>
        ))}
      </nav>

      {/* Trust & Safety Section */}
      <div className="pt-2">
        <p className="px-1 pb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Trust & Safety
        </p>
        <nav className="space-y-2" aria-label="Trust and safety sections">
          {/* Emergency Profile */}
          <button
            type="button"
            onClick={() => navigate('/patient/emergency-profile')}
            className="flex w-full items-center gap-3 rounded-2xl border border-border/60 bg-card p-4 text-left shadow-sm transition hover:shadow-md active:scale-[0.99] touch-manipulation"
          >
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-50">
              <AlertTriangle className="h-6 w-6 text-amber-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground">Emergency Profile</p>
              <p className="text-xs text-muted-foreground">Blood group, allergies, emergency contacts</p>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
          </button>

          {/* Family & Trust */}
          <button
            type="button"
            onClick={() => navigate('/patient/family')}
            className="flex w-full items-center gap-3 rounded-2xl border border-border/60 bg-card p-4 text-left shadow-sm transition hover:shadow-md active:scale-[0.99] touch-manipulation"
          >
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-rose-50">
              <Heart className="h-6 w-6 text-rose-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground">Family & Trust</p>
              <p className="text-xs text-muted-foreground">Family members, trusted contacts, caregivers</p>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
          </button>
        </nav>
      </div>

      {/* Logout */}
      <div className="pt-4">
        <Button
          variant="outline"
          onClick={logout}
          className="w-full rounded-2xl border-destructive/20 text-destructive hover:bg-destructive/10 h-12"
        >
          Log out
        </Button>
      </div>
    </div>
  );
}
