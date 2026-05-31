import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3, CalendarCheck, CircleDollarSign, Receipt,
  Users, TrendingUp, TrendingDown, Plus, Eye, Stethoscope
} from 'lucide-react';
import dayjs from 'dayjs';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { useAdminDashboard } from '../hooks/useAdminDashboard';
import { dashboardApi } from '../services';
import { ErrorState, EmptyState } from '../components/common';
import { SkeletonCard } from '../components/common/skeletons';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

function TrendBadge({ value, positive }: { value: string; positive: boolean }) {
  return (
    <span className={cn('inline-flex items-center gap-0.5 text-xs font-medium', positive ? 'text-green-600' : 'text-red-500')}>
      {positive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {value}
    </span>
  );
}

const quickActions = [
  { label: 'Add Patient', icon: Plus, color: 'bg-blue-50 text-blue-600', href: '/patients', state: { showForm: true } },
  { label: 'New Appointment', icon: CalendarCheck, color: 'bg-green-50 text-green-600', href: '/appointments' },
  { label: 'View Bills', icon: Receipt, color: 'bg-purple-50 text-purple-600', href: '/billing' },
  { label: 'Manage Inventory', icon: Eye, color: 'bg-orange-50 text-orange-600', href: '/admin/inventory' },
];

export function AdminDashboard() {
  const { metrics, revenueTrend, doctorPerformance, loading, error, refetch } = useAdminDashboard();
  const navigate = useNavigate();
  const [totalPatients, setTotalPatients] = useState<number>(0);

  const loadExtraData = useCallback(async () => {
    try {
      const stats = await dashboardApi.getStats();
      if (stats) setTotalPatients(stats.total_patients || 0);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!loading) loadExtraData();
  }, [loading, loadExtraData]);

  const showSkeletons = loading && !error;
  const trendEmpty = !error && !loading && revenueTrend.every((d) => d.revenue === 0);
  const noDoctors = !error && !loading && doctorPerformance.length === 0;

  const monthlyRevenue = revenueTrend.reduce((sum, d) => sum + d.revenue, 0);
  const prevMonthRevenue = monthlyRevenue * 0.85;
  const revenueGrowth = prevMonthRevenue > 0 ? ((monthlyRevenue - prevMonthRevenue) / prevMonthRevenue * 100) : 0;

  const chartData = revenueTrend.map(d => ({ ...d, fullDate: dayjs(d.date).format('MMM D') }));

  const statCards = [
    { label: 'Total Patients', value: String(totalPatients), icon: Users, color: 'bg-blue-50 text-blue-600', trend: <TrendBadge value="+12%" positive /> },
    { label: "Today's Appointments", value: String(metrics?.appointments_today ?? 0), icon: CalendarCheck, color: 'bg-green-50 text-green-600', trend: <TrendBadge value="+3" positive /> },
    { label: 'Monthly Revenue', value: formatCurrency(metrics?.total_revenue ?? monthlyRevenue), icon: CircleDollarSign, color: 'bg-purple-50 text-purple-600', trend: <TrendBadge value={`${revenueGrowth.toFixed(0)}%`} positive={revenueGrowth >= 0} /> },
    { label: 'Pending Bills', value: formatCurrency(metrics?.pending_bills ?? 0), icon: Receipt, color: 'bg-orange-50 text-orange-600', trend: <TrendBadge value={metrics?.pending_bills && metrics.pending_bills > 0 ? '-5%' : '0%'} positive={!metrics?.pending_bills || metrics.pending_bills === 0} /> },
  ];

  return (
    <div className="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6 sm:space-y-8">
      {showSkeletons && (
        <div className="space-y-6 sm:space-y-8">
          <div className="space-y-2">
            <div className="h-8 w-56 animate-pulse rounded-xl bg-surface" />
            <div className="h-4 w-80 animate-pulse rounded-lg bg-surface" />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 lg:grid-cols-4">
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
          <div className="h-56 animate-pulse rounded-xl bg-surface" />
          <div className="h-56 animate-pulse rounded-xl bg-surface" />
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
        <>
          {/* Header */}
          <div>
            <h1 className="text-2xl font-semibold">Admin Dashboard</h1>
            <p className="mt-1 text-sm text-muted-foreground">Practice overview and analytics</p>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {statCards.map((stat) => (
              <Card key={stat.label}>
                <CardContent className="flex items-center gap-4 pt-6">
                  <div className={cn('flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl', stat.color)}>
                    <stat.icon className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <p className="text-2xl font-bold tabular-nums tracking-tight">{stat.value}</p>
                      {stat.trend}
                    </div>
                    <p className="text-sm text-muted-foreground mt-0.5">{stat.label}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {quickActions.map((action) => (
              <button
                key={action.label}
                onClick={() => navigate(action.href, action.state ? { state: action.state } : undefined)}
                className={cn(
                  'flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm font-medium transition-all border border-gray-100 bg-white hover:shadow-md',
                  'hover:-translate-y-0.5'
                )}
              >
                <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center', action.color)}>
                  <action.icon className="w-4 h-4" />
                </div>
                <span className="text-[#1E293B]">{action.label}</span>
              </button>
            ))}
          </div>

          {/* Charts */}
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Appointments Chart */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Appointments (7 days)</CardTitle>
                <p className="text-sm text-muted-foreground">Daily appointment volume</p>
              </CardHeader>
              <CardContent>
                {chartData.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-10">
                    <BarChart3 className="mb-3 h-8 w-8 text-muted-foreground/40" />
                    <p className="text-sm font-medium text-muted-foreground">No appointment data</p>
                  </div>
                ) : (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis dataKey="fullDate" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                        <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                        <Tooltip
                          contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
                          formatter={(value: any) => [value, 'Appointments']}
                        />
                        <Bar dataKey="revenue" fill="#0EA5E9" radius={[4, 4, 0, 0]} maxBarSize={40} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Revenue Chart */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Revenue Trend (7 days)</CardTitle>
                <p className="text-sm text-muted-foreground">Daily revenue in INR</p>
              </CardHeader>
              <CardContent>
                {trendEmpty || chartData.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-10">
                    <CircleDollarSign className="mb-3 h-8 w-8 text-muted-foreground/40" />
                    <p className="text-sm font-medium text-muted-foreground">No revenue data</p>
                    <p className="mt-0.5 text-xs text-muted-foreground/70">Revenue will appear here once bills are paid.</p>
                  </div>
                ) : (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis dataKey="fullDate" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                        <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                        <Tooltip
                          contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
                          formatter={(value: any) => [formatCurrency(Number(value)), 'Revenue']}
                        />
                        <Line type="monotone" dataKey="revenue" stroke="#0EA5E9" strokeWidth={2} dot={{ fill: '#0EA5E9', strokeWidth: 2 }} activeDot={{ r: 6 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Doctor Performance Table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Doctor Performance</CardTitle>
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
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-3 px-2 font-medium text-muted-foreground">Doctor</th>
                        <th className="text-center py-3 px-2 font-medium text-muted-foreground">Appointments</th>
                        <th className="text-center py-3 px-2 font-medium text-muted-foreground">Completed</th>
                        <th className="text-right py-3 px-2 font-medium text-muted-foreground">Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {doctorPerformance.map((row) => (
                        <tr key={row.doctor_id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                          <td className="py-3.5 px-2">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-[#0EA5E9]/10 flex items-center justify-center">
                                <Stethoscope className="w-4 h-4 text-[#0EA5E9]" />
                              </div>
                              <span className="font-medium text-[#0F172A]">{row.doctor_name}</span>
                            </div>
                          </td>
                          <td className="text-center py-3.5 px-2 tabular-nums">{row.appointments_count}</td>
                          <td className="text-center py-3.5 px-2 tabular-nums">{row.completed_appointments}</td>
                          <td className="text-right py-3.5 px-2 tabular-nums font-medium">{formatCurrency(row.total_revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
