/**
 * PatientLayout — mobile-first patient layout with sticky bottom navigation.
 *
 * Features:
 * - Simplified header (no duplicate navigation)
 * - Sticky bottom nav with 5 primary tabs
 * - Safe area aware
 * - Max-width container for mobile-native feel
 */

import { Outlet, useLocation } from 'react-router-dom';
import { HeartPulse } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { PatientBottomNav } from './PatientBottomNav';
export function PatientLayout() {
  const { user } = useAuth();
  const { pathname } = useLocation();

  // Hide header on detail pages for a cleaner experience
  const isDetailPage =
    pathname.includes('/care/encounters/') ||
    pathname.includes('/discover/doctor/') ||
    pathname.includes('/discover/clinic/');

  return (
    <div className="flex min-h-screen w-full flex-col bg-background text-foreground">
      {/* Simplified Header */}
      {!isDetailPage && (
        <header className="sticky top-0 z-40 border-b border-border/60 bg-white/90 shadow-sm backdrop-blur-md">
          <div className="mx-auto flex w-full max-w-md items-center justify-between px-4 py-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary shadow-sm">
                <HeartPulse className="h-5 w-5 text-primary-foreground" aria-hidden />
              </div>
              <div>
                <p className="text-sm font-semibold leading-tight text-foreground">Care</p>
                <p className="text-[10px] leading-tight text-muted-foreground">Your health workspace</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {user && (
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary">
                  {(user.full_name || user.email || 'U').charAt(0).toUpperCase()}
                </div>
              )}
            </div>
          </div>
        </header>
      )}

      {/* Main Content */}
      <main
        className="mx-auto w-full min-w-0 max-w-md flex-1 px-4 py-6"
        style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 80px)' }}
      >
        <Outlet />
      </main>

      {/* Bottom Navigation */}
      <PatientBottomNav />
    </div>
  );
}
