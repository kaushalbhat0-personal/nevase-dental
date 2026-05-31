import {
  BarChart3,
  CalendarCheck,
  CircleDollarSign,
  Receipt,
  Wallet,
} from 'lucide-react';
import dayjs from 'dayjs';
import { useAdminDashboard } from '../hooks/useAdminDashboard';
import { ErrorState, EmptyState } from '../components/common';
import { SkeletonCard } from '../components/common/skeletons';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
}

function RevenueLineChart({
  data,
  className,
}: {
  data: { date: string; revenue: number }[];
  className?: string;
}) {
  const w = 100;
  const h = 40;
  const padX = 4;
  const padY = 4;
  const innerW = w - padX * 2;
  const innerH = h - padY * 2;
  const maxRev = Math.max(...data.map((d) => d.revenue), 0.0001);
  const n = data.length;
  const points = data.map((d, i) => {
    const x = n <= 1 ? w / 2 : padX + (i / (n - 1)) * innerW;
    const y = padY + innerH * (1 - d.revenue / maxRev);
    return `${x},${y}`;
  });
  const pathD = `M ${points.join(' L ')}`;
  const areaD = `${pathD} L ${points[points.length - 1].split(',')[0]},${h - padY} L ${points[0].split(',')[0]},${h - padY} Z`;

  return (
    <div className={cn('w-full', className)}>
      <div className="relative w-full" style={{ minHeight: 200 }}>
        <svg
          className="h-48 w-full text-primary"
          viewBox={`0 0 ${w} ${h}`}
          preserveAspectRatio="none"
          role="img"
          aria-label="Revenue over the last 7 days"
        >
          <defs>
            <linearGradient id="rev-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.15" />
              <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.02" />
            </linearGradient>
          </defs>
          <path d={areaD} fill="url(#rev-grad)" />
          <line
            x1={padX}
            y1={h - padY}
            x2={w - padX}
            y2={h - padY}
            className="stroke-border"
            strokeWidth={0.3}
            vectorEffect="non-scaling-stroke"
          />
          <path
            d={pathD}
            fill="none"
            className="stroke-primary"
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        <div className="mt-2 flex w-full justify-between gap-0.5 px-0.5 sm:px-1">
          {data.map((row) => (
            <span
              key={row.date}
              className="text-[10px] text-muted-foreground sm:text-xs"
              style={{ maxWidth: `${100 / n}%` }}
            >
              {dayjs(row.date).format('M/D')}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function AdminDashboard() {
  const { metrics, revenueTrend, doctorPerformance, loading, error, refetch } = useAdminDashboard();

  const showSkeletons = loading && !error;
  const trendEmpty = !error && !loading && revenueTrend.every((d) => d.revenue === 0);
  const noDoctors = !error && !loading && doctorPerformance.length === 0;

  return (
    <div className="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {showSkeletons && (
        <div className="space-y-6 sm:space-y-8">
          <div className="space-y-2">
            <div className="h-8 w-56 animate-pulse rounded-xl bg-surface" />
            <div className="h-4 w-80 animate-pulse rounded-lg bg-surface" />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 lg:grid-cols-5">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="h-56 animate-pulse rounded-xl bg-surface" />
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 animate-pulse rounded-2xl bg-muted" />
            ))}
          </div>
        </div>
      )}

      {error && (
        <ErrorState
          title="Failed to load admin dashboard"
          description="Unable to fetch admin metrics. Please try again."
          error={error}
          onRetry={() => void refetch()}
        />
      )}

      {!error && !loading && metrics && (
        <div className="space-y-6 sm:space-y-8">
          <div>
            <h1 className="text-2xl font-semibold">Admin dashboard</h1>
            <p className="mt-1 text-sm text-muted-foreground">KPIs, revenue trend, and doctor performance</p>
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 sm:gap-6 lg:grid-cols-5">
            <Card>
              <CardContent className="flex items-center gap-4">
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10">
                  <Wallet className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground">Total revenue</p>
                  <p className="text-2xl font-bold tabular-nums tracking-tight">
                    {formatCurrency(metrics.total_revenue)}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-4">
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10">
                  <CircleDollarSign className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground">Revenue today</p>
                  <p className="text-2xl font-bold tabular-nums tracking-tight">
                    {formatCurrency(metrics.revenue_today)}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-4">
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10">
                  <BarChart3 className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground">Appointments today</p>
                  <p className="text-2xl font-bold tabular-nums tracking-tight">{metrics.appointments_today}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-4">
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10">
                  <CalendarCheck className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground">Completed appointments</p>
                  <p className="text-2xl font-bold tabular-nums tracking-tight">{metrics.completed_appointments}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-4">
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10">
                  <Receipt className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground">Pending bills</p>
                  <p className="text-2xl font-bold tabular-nums tracking-tight">
                    {formatCurrency(metrics.pending_bills)}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Revenue (7 days)</CardTitle>
              <p className="text-sm text-muted-foreground">Paid bill amounts by day</p>
            </CardHeader>
            <CardContent>
              {revenueTrend.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10">
                  <BarChart3 className="mb-3 h-8 w-8 text-muted-foreground/40" />
                  <p className="text-sm font-medium text-muted-foreground">No revenue data</p>
                  <p className="mt-0.5 text-xs text-muted-foreground/70">Revenue will appear here once bills are paid.</p>
                </div>
              ) : (
                <>
                  {trendEmpty && (
                    <p className="mb-3 text-xs text-muted-foreground/70">
                      All days show $0.00 in this window
                    </p>
                  )}
                  <RevenueLineChart data={revenueTrend} />
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Doctor performance</CardTitle>
              <p className="text-sm text-muted-foreground">Last 7 days, sorted by revenue</p>
            </CardHeader>
            <CardContent className="space-y-3">
              {noDoctors ? (
                <div className="py-2">
                  <EmptyState
                    title="No doctors"
                    description="Add doctors to see performance metrics for your tenant."
                  />
                </div>
              ) : (
                <ul className="space-y-3">
                  {doctorPerformance.map((row) => (
                    <li
                      key={row.doctor_id}
                      className="flex flex-col gap-3 rounded-xl border border-border/80 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="min-w-0">
                        <p className="font-medium text-foreground">{row.doctor_name}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground/70">Last 7 days</p>
                      </div>
                      <div className="grid grid-cols-3 gap-2 sm:flex sm:flex-wrap sm:gap-5">
                        <div className="text-center sm:text-right">
                          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 sm:text-xs">
                            Appts
                          </p>
                          <p className="mt-0.5 tabular-nums text-sm font-semibold">{row.appointments_count}</p>
                        </div>
                        <div className="text-center sm:text-right">
                          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 sm:text-xs">
                            Done
                          </p>
                          <p className="mt-0.5 tabular-nums text-sm font-semibold">{row.completed_appointments}</p>
                        </div>
                        <div className="text-center sm:text-right">
                          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 sm:text-xs">
                            Revenue
                          </p>
                          <p className="mt-0.5 tabular-nums text-sm font-semibold">{formatCurrency(row.total_revenue)}</p>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
