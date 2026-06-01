/**
 * PatientBottomNav — mobile-first sticky bottom navigation.
 *
 * 5 primary tabs:
 * 1. Appointments — View and book appointments
 * 2. Prescriptions — Download prescriptions
 * 3. Messages — Communication center
 * 4. Medicines — View prescribed medications
 * 5. Profile — Personal account + records
 *
 * Design:
 * - Mobile-native sticky bottom
 * - Large touch targets (min 48px)
 * - Active-state highlighting
 * - Safe area aware
 * - Smooth transitions
 */

import { NavLink, useLocation } from 'react-router-dom';
import {
  Calendar,
  FileText,
  MessageSquare,
  Pill,
  User,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const tabs = [
  { to: '/patient/appointments', label: 'Appointments', icon: Calendar },
  { to: '/patient/prescriptions', label: 'Prescriptions', icon: FileText },
  { to: '/patient/messages', label: 'Messages', icon: MessageSquare },
  { to: '/patient/medications', label: 'Medicines', icon: Pill },
  { to: '/patient/profile', label: 'Profile', icon: User },
] as const;

export function PatientBottomNav() {
  const { pathname } = useLocation();

  // Don't show bottom nav on detail pages within care
  const isDetailPage =
    pathname.includes('/care/encounters/');

  if (isDetailPage) return null;

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 border-t border-border/80 bg-white/95 shadow-[0_-2px_16px_rgba(0,0,0,0.06)] backdrop-blur-md"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="mx-auto flex max-w-md items-center justify-around px-2 py-1">
        {tabs.map(({ to, label, icon: Icon }) => {
          const isActive =
            pathname === to ||
            (to === '/patient/appointments' && (pathname === '/patient/appointments' || pathname === '/patient/home')) ||
            (to === '/patient/prescriptions' && pathname.startsWith('/patient/prescriptions')) ||
            (to === '/patient/messages' && pathname.startsWith('/patient/messages')) ||
            (to === '/patient/medications' && pathname.startsWith('/patient/medications')) ||
            (to === '/patient/profile' && pathname.startsWith('/patient/profile/'));

          return (
            <NavLink
              key={to}
              to={to}
              className={cn(
                'flex flex-col items-center justify-center gap-0.5 rounded-xl px-3 py-1.5 transition-all duration-200 touch-manipulation',
                'min-h-[48px] min-w-[56px]',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
              )}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className={cn('h-5 w-5 transition-transform duration-200', isActive && 'scale-110')} />
              <span className="text-[10px] font-medium leading-tight">{label}</span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
