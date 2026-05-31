/**
 * ClinicOperationsDashboard — main clinic operations console.
 *
 * Sections (operational priority grouping):
 * 1. Sticky operational header with today's summary cards
 * 2. Waiting patients + active consultations
 * 3. Delayed queue alerts + pending bills
 * 4. Low stock alerts + procurement pending
 * 5. Incomplete encounters
 * 6. Activity feed + task list (side panels)
 *
 * UX:
 * - Operational priority grouping
 * - Sticky operational header
 * - Fast scanning
 * - Responsive grid layout
 * - Tablet-optimized: large touch targets, clear hierarchy
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StaffOperationsSummary } from './StaffOperationsSummary';
import { OperationalTaskList } from './OperationalTaskList';
import { OperationalActivityFeed } from './OperationalActivityFeed';
import { OperationalAlertBanner } from './OperationalAlertBanner';
import { operationsApi } from '../../services/clinicOperations';
import type {
  ClinicOperationsDashboard as DashboardData,
  OperationalAlertItem,
  WaitingPatientItem,
} from '../../services/clinicOperations';
import {
  Users,
  Stethoscope,
  Clock,
  DollarSign,
  FileText,
  Package,
  Truck,
  AlertTriangle,
  RefreshCw,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react';


interface ClinicOperationsDashboardProps {
  /** Auto-refresh interval in ms. Default 20000 (20s). Set 0 to disable. */
  refreshInterval?: number;
}

function formatWaitTime(minutes: number): string {
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m`;
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hrs}h ${mins}m`;
}

export function ClinicOperationsDashboard({
  refreshInterval = 20000,
}: ClinicOperationsDashboardProps) {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [alerts, setAlerts] = useState<OperationalAlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [dashData, alertData] = await Promise.all([
        operationsApi.getDashboard(),
        operationsApi.getAlerts(),
      ]);
      setDashboard(dashData);
      setAlerts(alertData.items);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
    if (refreshInterval > 0) {
      intervalRef.current = setInterval(fetchAll, refreshInterval);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchAll, refreshInterval]);

  const handleDismissAlert = useCallback((id: string) => {
    setDismissedAlerts((prev) => new Set(prev).add(id));
  }, []);

  const visibleAlerts = alerts.filter((a) => !dismissedAlerts.has(a.id));

  if (loading && !dashboard) {
    return (
      <div className="space-y-4 p-4 md:p-6">
        <div className="h-12 w-64 rounded-lg bg-muted animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <div className="h-32 rounded-lg bg-muted animate-pulse" />
            <div className="h-64 rounded-lg bg-muted animate-pulse" />
          </div>
          <div className="space-y-4">
            <div className="h-48 rounded-lg bg-muted animate-pulse" />
            <div className="h-48 rounded-lg bg-muted animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (!dashboard) return null;

  const s = dashboard.summary;

  return (
    <div className="space-y-4 p-4 md:p-6 max-w-7xl mx-auto">
      {/* ── Sticky Operational Header ── */}
      <div className="sticky top-0 z-20 -mx-4 md:-mx-6 px-4 md:px-6 pb-2 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-lg font-semibold tracking-tight">Clinic Operations</h1>
          <Button
            variant="outline"
            size="sm"
            onClick={() => { setLoading(true); void fetchAll(); }}
            disabled={loading}
            className="h-9 min-h-[36px]"
          >
            <RefreshCw className={cn('h-4 w-4 mr-1', loading && 'animate-spin')} aria-hidden />
            Refresh
          </Button>
        </div>

        {/* Summary Cards Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          <SummaryStatCard
            icon={Users}
            label="Waiting"
            value={s.waiting_patients}
            color="text-amber-600"
            bgColor="bg-amber-100 dark:bg-amber-950"
          />
          <SummaryStatCard
            icon={Stethoscope}
            label="In Consult"
            value={s.active_consultations}
            color="text-blue-600"
            bgColor="bg-blue-100 dark:bg-blue-950"
          />
          <SummaryStatCard
            icon={Clock}
            label="Overdue"
            value={s.overdue_appointments}
            color="text-red-600"
            bgColor="bg-red-100 dark:bg-red-950"
          />
          <SummaryStatCard
            icon={DollarSign}
            label="Bills"
            value={s.pending_bills_count}
            color="text-emerald-600"
            bgColor="bg-emerald-100 dark:bg-emerald-950"
          />
          <SummaryStatCard
            icon={FileText}
            label="Incomplete"
            value={s.incomplete_encounters}
            color="text-violet-600"
            bgColor="bg-violet-100 dark:bg-violet-950"
          />
          <SummaryStatCard
            icon={Package}
            label="Low Stock"
            value={s.low_stock_alerts}
            color="text-orange-600"
            bgColor="bg-orange-100 dark:bg-orange-950"
          />
          <SummaryStatCard
            icon={Truck}
            label="Procurement"
            value={s.procurement_pending}
            color="text-indigo-600"
            bgColor="bg-indigo-100 dark:bg-indigo-950"
          />
          <SummaryStatCard
            icon={AlertTriangle}
            label="Total"
            value={s.total_appointments_today}
            color="text-gray-600"
            bgColor="bg-gray-100 dark:bg-gray-800"
          />
        </div>
      </div>

      {/* ── Alert Banners ── */}
      {visibleAlerts.length > 0 && (
        <div className="space-y-2">
          {visibleAlerts.slice(0, 3).map((alert) => (
            <OperationalAlertBanner
              key={alert.id}
              alert={alert}
              onDismiss={handleDismissAlert}
            />
          ))}
          {visibleAlerts.length > 3 && (
            <p className="text-xs text-muted-foreground text-center">
              +{visibleAlerts.length - 3} more alerts
            </p>
          )}
        </div>
      )}

      {/* ── Main Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left Column: Operational Data */}
        <div className="lg:col-span-2 space-y-4">
          {/* Waiting Patients */}
          {dashboard.waiting_patients.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Users className="h-4 w-4 text-amber-500" aria-hidden />
                  Waiting Patients ({dashboard.waiting_patients.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {dashboard.waiting_patients.slice(0, 8).map((wp) => (
                  <WaitingPatientRow key={wp.appointment_id} patient={wp} />
                ))}
                {dashboard.waiting_patients.length > 8 && (
                  <p className="text-xs text-muted-foreground text-center pt-1">
                    +{dashboard.waiting_patients.length - 8} more
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Active Consultations */}
          {dashboard.active_consultations.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Stethoscope className="h-4 w-4 text-blue-500" aria-hidden />
                  Active Consultations ({dashboard.active_consultations.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {dashboard.active_consultations.map((ac) => (
                  <div
                    key={ac.appointment_id}
                    className="flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/20 p-3 min-h-[52px]"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
                        <Stethoscope className="h-4 w-4 text-blue-600 dark:text-blue-400" aria-hidden />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{ac.patient_name}</p>
                        <p className="text-xs text-muted-foreground">
                          Dr. {ac.doctor_name} · {ac.duration_minutes}m elapsed
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className="shrink-0 bg-blue-100/50 text-blue-700 border-blue-200 dark:bg-blue-900/50 dark:text-blue-300 dark:border-blue-800">
                      In Progress
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Overdue Appointments */}
          {dashboard.overdue_appointments.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Clock className="h-4 w-4 text-red-500" aria-hidden />
                  Delayed Queue ({dashboard.overdue_appointments.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {dashboard.overdue_appointments.slice(0, 5).map((oa) => (
                  <div
                    key={oa.appointment_id}
                    className="flex items-center justify-between rounded-lg border border-red-100 bg-red-50/50 dark:border-red-900 dark:bg-red-950/20 p-3 min-h-[48px]"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Clock className="h-4 w-4 shrink-0 text-red-500" aria-hidden />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{oa.patient_name}</p>
                        <p className="text-xs text-muted-foreground">
                          Dr. {oa.doctor_name} · {oa.minutes_overdue}m overdue
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className="shrink-0 text-red-600 border-red-200 bg-red-50 dark:text-red-400 dark:border-red-800 dark:bg-red-950/50">
                      {oa.minutes_overdue}m
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Pending Bills */}
          {dashboard.pending_bills.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-emerald-500" aria-hidden />
                  Pending Bills ({dashboard.pending_bills.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {dashboard.pending_bills.slice(0, 5).map((pb) => (
                  <div
                    key={pb.bill_id}
                    className="flex items-center justify-between rounded-lg border p-3 min-h-[48px]"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{pb.patient_name}</p>
                      <p className="text-xs text-muted-foreground">
                        ₹{pb.amount.toLocaleString()} · {pb.days_pending}d pending
                      </p>
                    </div>
                    <Badge variant="secondary" className="shrink-0">
                      ₹{pb.amount.toLocaleString()}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Low Stock Alerts */}
          {dashboard.low_stock_alerts.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Package className="h-4 w-4 text-orange-500" aria-hidden />
                  Low Stock Alerts ({dashboard.low_stock_alerts.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {dashboard.low_stock_alerts.slice(0, 5).map((ls) => (
                  <div
                    key={ls.item_id}
                    className="flex items-center justify-between rounded-lg border border-orange-100 bg-orange-50/50 dark:border-orange-900 dark:bg-orange-950/20 p-3 min-h-[48px]"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{ls.item_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {ls.current_quantity} / {ls.low_stock_threshold} {ls.unit}
                        {ls.days_until_out !== null && ` · ~${ls.days_until_out}d remaining`}
                      </p>
                    </div>
                    <Badge variant="outline" className="shrink-0 text-orange-600 border-orange-200 bg-orange-50 dark:text-orange-400 dark:border-orange-800 dark:bg-orange-950/50">
                      {ls.current_quantity} left
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Procurement Pending */}
          {dashboard.procurement_pending.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Truck className="h-4 w-4 text-indigo-500" aria-hidden />
                  Procurement Pending ({dashboard.procurement_pending.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {dashboard.procurement_pending.slice(0, 5).map((pp) => (
                  <div
                    key={pp.po_id}
                    className="flex items-center justify-between rounded-lg border p-3 min-h-[48px]"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{pp.supplier_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {pp.item_count} items · ₹{pp.total_amount.toLocaleString()} · {pp.days_pending}d
                      </p>
                    </div>
                    <Badge variant="secondary" className="shrink-0">
                      {pp.status}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Incomplete Encounters */}
          {dashboard.incomplete_encounters.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <FileText className="h-4 w-4 text-violet-500" aria-hidden />
                  Incomplete Encounters ({dashboard.incomplete_encounters.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {dashboard.incomplete_encounters.slice(0, 5).map((ie) => (
                  <div
                    key={ie.appointment_id}
                    className="flex items-center justify-between rounded-lg border p-3 min-h-[48px]"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{ie.patient_name}</p>
                      <p className="text-xs text-muted-foreground">Dr. {ie.doctor_name}</p>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      {ie.missing_clinical_notes && (
                        <Badge variant="outline" className="text-xs">Notes</Badge>
                      )}
                      {ie.missing_prescriptions && (
                        <Badge variant="outline" className="text-xs">Rx</Badge>
                      )}
                      {ie.missing_billing && (
                        <Badge variant="outline" className="text-xs">Bill</Badge>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Empty state */}
          {dashboard.waiting_patients.length === 0 &&
            dashboard.active_consultations.length === 0 &&
            dashboard.overdue_appointments.length === 0 &&
            dashboard.pending_bills.length === 0 &&
            dashboard.low_stock_alerts.length === 0 &&
            dashboard.procurement_pending.length === 0 &&
            dashboard.incomplete_encounters.length === 0 && (
              <Card>
                <CardContent className="py-12 text-center">
                  <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto mb-3" aria-hidden />
                  <p className="text-lg font-medium text-foreground">All clear</p>
                  <p className="text-sm text-muted-foreground">
                    No pending operational items — everything is up to date
                  </p>
                </CardContent>
              </Card>
            )}
        </div>

        {/* Right Column: Tasks + Activity */}
        <div className="space-y-4">
          <StaffOperationsSummary refreshInterval={refreshInterval} />
          <OperationalTaskList refreshInterval={refreshInterval} />
          <OperationalActivityFeed refreshInterval={refreshInterval} />
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ──

interface SummaryStatCardProps {
  icon: typeof Users;
  label: string;
  value: number;
  color: string;
  bgColor: string;
}

function SummaryStatCard({ icon: Icon, label, value, color, bgColor }: SummaryStatCardProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border bg-card p-2 min-h-[52px]">
      <div className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-full', bgColor)}>
        <Icon className={cn('h-4 w-4', color)} aria-hidden />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] text-muted-foreground leading-tight truncate">{label}</p>
        <p className="text-sm font-bold tabular-nums leading-tight">{value}</p>
      </div>
    </div>
  );
}

interface WaitingPatientRowProps {
  patient: WaitingPatientItem;
}

function WaitingPatientRow({ patient }: WaitingPatientRowProps) {
  const waitColor =
    patient.wait_time_minutes > 30
      ? 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-950'
      : patient.wait_time_minutes > 15
        ? 'text-amber-600 bg-amber-100 dark:text-amber-400 dark:bg-amber-950'
        : 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800';

  return (
    <div className="flex items-center justify-between rounded-lg border p-2.5 min-h-[48px]">
      <div className="flex items-center gap-3 min-w-0">
        {patient.token_number && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-xs font-bold">
            {patient.token_number}
          </div>
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{patient.patient_name}</p>
          <p className="text-xs text-muted-foreground truncate">Dr. {patient.doctor_name}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium', waitColor)}>
          <Clock className="h-3 w-3 mr-0.5" aria-hidden />
          {formatWaitTime(patient.wait_time_minutes)}
        </span>
        <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden />
      </div>
    </div>
  );
}


