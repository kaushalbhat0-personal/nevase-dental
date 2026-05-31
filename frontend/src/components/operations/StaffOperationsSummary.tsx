/**
 * StaffOperationsSummary — operational KPIs, pending actions, queue health.
 *
 * Tablet-friendly: large stat cards, clear health indicators.
 */
import { useCallback, useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { operationsApi } from '../../services/clinicOperations';
import type { ClinicOperationsDashboard } from '../../services/clinicOperations';
import {
  Users,
  Stethoscope,
  Clock,
  DollarSign,
  FileText,
  Package,
  Truck,
  AlertTriangle,
} from 'lucide-react';

interface StaffOperationsSummaryProps {
  /** Auto-refresh interval in ms. Default 30000 (30s). Set 0 to disable. */
  refreshInterval?: number;
}

interface KpiCard {
  label: string;
  value: number | string;
  icon: typeof Users;
  color: string;
  bgColor: string;
  subtext?: string;
}

export function StaffOperationsSummary({ refreshInterval = 30000 }: StaffOperationsSummaryProps) {
  const [dashboard, setDashboard] = useState<ClinicOperationsDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await operationsApi.getDashboard();
      setDashboard(data);
    } catch {
      // silently fail — dashboard will show loading state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchDashboard();
    if (refreshInterval > 0) {
      const interval = setInterval(fetchDashboard, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchDashboard, refreshInterval]);

  if (loading && !dashboard) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Today's Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="h-24 rounded-lg bg-muted animate-pulse"
                aria-hidden
              />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!dashboard) return null;

  const s = dashboard.summary;

  const kpis: KpiCard[] = [
    {
      label: 'Waiting',
      value: s.waiting_patients,
      icon: Users,
      color: 'text-amber-600',
      bgColor: 'bg-amber-100 dark:bg-amber-950',
      subtext: 'patients',
    },
    {
      label: 'In Consultation',
      value: s.active_consultations,
      icon: Stethoscope,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100 dark:bg-blue-950',
      subtext: 'active',
    },
    {
      label: 'Overdue',
      value: s.overdue_appointments,
      icon: Clock,
      color: 'text-red-600',
      bgColor: 'bg-red-100 dark:bg-red-950',
      subtext: 'appointments',
    },
    {
      label: 'Pending Bills',
      value: s.pending_bills_count,
      icon: DollarSign,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-100 dark:bg-emerald-950',
      subtext: `₹${s.pending_bills_amount.toLocaleString()}`,
    },
    {
      label: 'Incomplete Encounters',
      value: s.incomplete_encounters,
      icon: FileText,
      color: 'text-violet-600',
      bgColor: 'bg-violet-100 dark:bg-violet-950',
      subtext: 'needs docs',
    },
    {
      label: 'Low Stock',
      value: s.low_stock_alerts,
      icon: Package,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100 dark:bg-orange-950',
      subtext: 'items',
    },
    {
      label: 'Procurement Pending',
      value: s.procurement_pending,
      icon: Truck,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-100 dark:bg-indigo-950',
      subtext: 'orders',
    },
    {
      label: 'Total Today',
      value: s.total_appointments_today,
      icon: AlertTriangle,
      color: 'text-gray-600',
      bgColor: 'bg-gray-100 dark:bg-gray-800',
      subtext: 'appointments',
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Today's Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {kpis.map((kpi) => {
            const Icon = kpi.icon;
            return (
              <div
                key={kpi.label}
                className={cn(
                  'flex items-center gap-3 rounded-lg border p-3 min-h-[72px] transition-colors hover:bg-accent/50'
                )}
              >
                <div
                  className={cn(
                    'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
                    kpi.bgColor
                  )}
                >
                  <Icon className={cn('h-5 w-5', kpi.color)} aria-hidden />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-muted-foreground truncate">{kpi.label}</p>
                  <p className="text-xl font-bold tabular-nums leading-tight">{kpi.value}</p>
                  {kpi.subtext && (
                    <p className="text-[10px] text-muted-foreground truncate">{kpi.subtext}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Queue Health Indicator */}
        {dashboard.doctor_queues.length > 0 && (
          <div className="mt-4">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Queue Health
            </h4>
            <div className="space-y-2">
              {dashboard.doctor_queues.map((dq) => {
                const totalWaiting = dq.waiting_count;
                const healthColor =
                  totalWaiting > 5
                    ? 'bg-red-500'
                    : totalWaiting > 3
                      ? 'bg-amber-500'
                      : 'bg-emerald-500';
                const healthLabel =
                  totalWaiting > 5
                    ? 'High load'
                    : totalWaiting > 3
                      ? 'Moderate'
                      : 'Healthy';
                return (
                  <div
                    key={dq.doctor_id}
                    className="flex items-center justify-between rounded-lg border px-3 py-2 min-h-[44px]"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div className={cn('h-2 w-2 rounded-full shrink-0', healthColor)} />
                      <span className="text-sm font-medium truncate">{dq.doctor_name}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-muted-foreground">
                        {dq.waiting_count} waiting · {dq.in_consultation_count} in
                      </span>
                      <span className="text-[10px] font-medium text-muted-foreground">
                        {healthLabel}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
