/**
 * PatientCareHub — unified longitudinal care workspace.
 *
 * This is the patient's health memory. Contains:
 * - Health Timeline
 * - Medicines
 * - Vitals
 * - Follow-ups
 * - Encounter details
 *
 * Uses segmented pill navigation for sub-sections.
 * Default view shows a summary overview.
 */

import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  HeartPulse,
  Pill,
  Activity,
  Timer,
} from 'lucide-react';
import { cn } from '@/lib/utils';

type CareTab = 'timeline' | 'medicines' | 'vitals' | 'follow-ups';

const careTabs: { key: CareTab; label: string; icon: React.ElementType; route: string }[] = [
  { key: 'timeline', label: 'Timeline', icon: HeartPulse, route: '/patient/care/timeline' },
  { key: 'medicines', label: 'Medicines', icon: Pill, route: '/patient/care/medicines' },
  { key: 'vitals', label: 'Vitals', icon: Activity, route: '/patient/care/vitals' },
  { key: 'follow-ups', label: 'Follow-ups', icon: Timer, route: '/patient/care/follow-ups' },
];

export function PatientCareHub() {
  const location = useLocation();
  const navigate = useNavigate();
  const pathname = location.pathname;

  // Determine active tab from current path
  const activeTab = careTabs.find((t) => pathname.startsWith(t.route))?.key ?? 'timeline';

  // If we're on a detail page (encounter), show just the outlet without the tab bar
  const isDetailPage = pathname.includes('/care/encounters/');

  if (isDetailPage) {
    return (
      <div className="pb-8">
        <Outlet />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-24">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
          Care Hub
        </h1>
        <p className="text-sm text-muted-foreground">
          Your health journey, all in one place
        </p>
      </div>

      {/* Segmented pill navigation */}
      <div className="sticky top-0 z-20 -mx-4 border-b border-border/50 bg-background/95 px-4 pb-3 pt-1 backdrop-blur-md sm:mx-0 sm:rounded-2xl sm:border sm:p-2 sm:shadow-sm">
        <nav
          className="flex gap-1 overflow-x-auto no-scrollbar [scrollbar-width:none]"
          role="tablist"
          aria-label="Care sections"
        >
          {careTabs.map(({ key, label, icon: Icon, route }) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={activeTab === key}
              onClick={() => navigate(route)}
              className={cn(
                'flex items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 py-2 text-sm font-medium transition-all duration-200 touch-manipulation min-h-[40px]',
                activeTab === key
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Sub-page content */}
      <Outlet />
    </div>
  );
}
