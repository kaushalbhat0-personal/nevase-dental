import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CalendarCheck, CircleDollarSign, Receipt, Users,
  Eye, Stethoscope, Clock, ArrowRight, AlertTriangle,
  UserPlus, CalendarPlus, ExternalLink, CheckCircle, XCircle
} from 'lucide-react';
import dayjs from 'dayjs';
import { useAdminDashboard } from '../hooks/useAdminDashboard';
import { appointmentsApi, patientsApi, dashboardApi } from '../services';
import { cn } from '@/lib/utils';
import type { Appointment, Patient } from '../types';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    scheduled: 'bg-blue-50 text-blue-600',
    confirmed: 'bg-blue-50 text-blue-600',
    'in_consultation': 'bg-yellow-50 text-yellow-600',
    completed: 'bg-green-50 text-green-600',
    cancelled: 'bg-red-50 text-red-600',
    'no_show': 'bg-gray-100 text-gray-500',
  };
  const label = status.replace(/_/g, ' ');
  return (
    <span className={cn('px-2.5 py-1 rounded-full text-xs font-medium capitalize', colors[status] || 'bg-gray-50 text-gray-500')}>
      {label}
    </span>
  );
}

const quickActions = [
  { label: 'Add Patient', icon: UserPlus, color: 'bg-blue-50 text-blue-600', href: '/patients', state: { showForm: true } },
  { label: 'New Appointment', icon: CalendarPlus, color: 'bg-green-50 text-green-600', href: '/appointments' },
  { label: 'View Bills', icon: Receipt, color: 'bg-purple-50 text-purple-600', href: '/billing' },
  { label: 'Inventory', icon: Eye, color: 'bg-orange-50 text-orange-600', href: '/admin/inventory' },
  { label: 'Settings', icon: ExternalLink, color: 'bg-gray-50 text-gray-600', href: '/admin/branding' },
];

export default function AdminDashboard() {
  const { metrics, doctorPerformance, loading, error, refetch } = useAdminDashboard();
  const navigate = useNavigate();
  const [totalPatients, setTotalPatients] = useState(0);
  const [todayAppts, setTodayAppts] = useState<Appointment[]>([]);
  const [recentPatients, setRecentPatients] = useState<Patient[]>([]);
  const [extraLoading, setExtraLoading] = useState(true);

  const loadData = useCallback(async () => {
    setExtraLoading(true);
    try {
      const [stats, appts, patients] = await Promise.all([
        dashboardApi.getStats(),
        appointmentsApi.getAll({ limit: 50 }),
        patientsApi.getAll({ limit: 50 }),
      ]);
      if (stats) setTotalPatients(stats.total_patients || 0);
      const today = dayjs().format('YYYY-MM-DD');
      const todays = (Array.isArray(appts) ? appts : []).filter((a) => {
        const t = a.scheduled_at || a.appointment_time || '';
        return t.startsWith(today);
      });
      setTodayAppts(todays);
      const sorted = (Array.isArray(patients) ? patients : [])
        .filter((p) => p.created_at)
        .sort((a, b) => new Date(b.created_at!).getTime() - new Date(a.created_at!).getTime())
        .slice(0, 5);
      setRecentPatients(sorted);
    } catch {
      /* silent */
    } finally {
      setExtraLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!loading) loadData();
  }, [loading, loadData]);

  const busy = loading || extraLoading;
  const todayStr = dayjs().format('dddd, MMMM D, YYYY');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6 sm:space-y-8 py-6 sm:py-8">
      {/* ── TOP BAR ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#0F172A]">
            {getGreeting()}, Admin 👋
          </h1>
          <p className="text-sm text-[#1E293B]/60 mt-1">{todayStr}</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/patients', { state: { showForm: true } })}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] transition-all shadow-sm"
          >
            <UserPlus className="w-4 h-4" />
            Add Patient
          </button>
          <button
            onClick={() => navigate('/appointments')}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-[#0EA5E9] bg-[#0EA5E9]/10 hover:bg-[#0EA5E9]/20 transition-all"
          >
            <CalendarPlus className="w-4 h-4" />
            New Appointment
          </button>
        </div>
      </div>

      {/* ── LOADING ── */}
      {(busy) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 rounded-2xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      )}

      {/* ── ERROR ── */}
      {error && !busy && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center">
          <p className="text-red-600 font-medium">Failed to load dashboard</p>
          <p className="text-red-500/70 text-sm mt-1">{error}</p>
          <button onClick={() => refetch()} className="mt-3 px-4 py-2 rounded-lg text-sm font-medium text-red-600 bg-red-100 hover:bg-red-200 transition-colors">
            Try Again
          </button>
        </div>
      )}

      {/* ── CONTENT ── */}
      {!error && !busy && metrics && (
        <>
          {/* ── 4 STAT CARDS ── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-all">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-3xl font-bold text-[#0F172A]">{metrics.appointments_today}</p>
                  <p className="text-sm text-[#1E293B]/60 mt-1">Today's Appointments</p>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-green-50 flex items-center justify-center">
                  <CalendarCheck className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-all">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-3xl font-bold text-[#0F172A]">{totalPatients}</p>
                  <p className="text-sm text-[#1E293B]/60 mt-1">Total Patients</p>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center">
                  <Users className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-all">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-3xl font-bold text-[#0F172A]">{metrics.pending_bills}</p>
                  <p className="text-sm text-[#1E293B]/60 mt-1">Pending Bills</p>
                  {metrics.pending_bills > 0 && (
                    <p className="text-xs text-yellow-600 mt-0.5">{formatCurrency(metrics.pending_bills * 1500)} est.</p>
                  )}
                </div>
                <div className="w-12 h-12 rounded-2xl bg-yellow-50 flex items-center justify-center">
                  <Receipt className="w-6 h-6 text-yellow-600" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-all">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-3xl font-bold text-[#0F172A]">{formatCurrency(metrics.total_revenue)}</p>
                  <p className="text-sm text-[#1E293B]/60 mt-1">This Month Revenue</p>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-purple-50 flex items-center justify-center">
                  <CircleDollarSign className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </div>
          </div>

          {/* ── PENDING BILLS ALERT ── */}
          {metrics.pending_bills > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-4 sm:p-5 flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-yellow-600 shrink-0" />
                <p className="text-sm font-medium text-yellow-800">
                  {metrics.pending_bills} patient{metrics.pending_bills > 1 ? 's have' : ' has'} unpaid bills
                </p>
              </div>
              <button
                onClick={() => navigate('/billing')}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-yellow-700 bg-yellow-100 hover:bg-yellow-200 transition-colors"
              >
                View Bills <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* ── TODAY'S APPOINTMENTS ── */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-[#0F172A]">Today's Appointments</h2>
              <p className="text-sm text-[#1E293B]/60 mt-0.5">{dayjs().format('MMMM D, YYYY')}</p>
            </div>
            {todayAppts.length === 0 ? (
              <div className="px-6 py-10 text-center">
                <CalendarCheck className="w-10 h-10 text-[#1E293B]/20 mx-auto mb-3" />
                <p className="text-[#1E293B]/60 font-medium">No appointments today — enjoy your day! 😊</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-50 bg-gray-50/50">
                      <th className="text-left py-3.5 px-4 font-medium text-[#1E293B]/60">Time</th>
                      <th className="text-left py-3.5 px-4 font-medium text-[#1E293B]/60">Patient</th>
                      <th className="text-left py-3.5 px-4 font-medium text-[#1E293B]/60">Doctor</th>
                      <th className="text-left py-3.5 px-4 font-medium text-[#1E293B]/60">Treatment</th>
                      <th className="text-center py-3.5 px-4 font-medium text-[#1E293B]/60">Status</th>
                      <th className="text-right py-3.5 px-4 font-medium text-[#1E293B]/60">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {todayAppts.map((a) => {
                      const time = a.scheduled_at || a.appointment_time || '';
                      const timeStr = time ? dayjs(time).format('h:mm A') : '--';
                      const patientName = a.patient?.name || a.patient?.first_name || `Patient #${a.patient_id}`;
                      const doctorName = a.doctor?.name || `Doctor #${a.doctor_id}`;
                      return (
                        <tr key={a.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-2">
                              <Clock className="w-3.5 h-3.5 text-[#1E293B]/40" />
                              <span className="font-medium text-[#0F172A]">{timeStr}</span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="font-medium text-[#0F172A]">{patientName}</span>
                          </td>
                          <td className="py-3.5 px-4 text-[#1E293B]/70">{doctorName}</td>
                          <td className="py-3.5 px-4 text-[#1E293B]/70">--</td>
                          <td className="py-3.5 px-4 text-center"><StatusBadge status={a.status} /></td>
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => navigate(`/appointments#${a.id}`)}
                                className="p-1.5 rounded-lg hover:bg-gray-100 text-[#1E293B]/50 hover:text-[#0EA5E9] transition-colors"
                                title="View"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </button>
                              {a.status === 'scheduled' && (
                                <>
                                  <button
                                    className="p-1.5 rounded-lg hover:bg-green-50 text-[#1E293B]/50 hover:text-green-600 transition-colors"
                                    title="Complete"
                                  >
                                    <CheckCircle className="w-4 h-4" />
                                  </button>
                                  <button
                                    className="p-1.5 rounded-lg hover:bg-red-50 text-[#1E293B]/50 hover:text-red-500 transition-colors"
                                    title="Cancel"
                                  >
                                    <XCircle className="w-4 h-4" />
                                  </button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* ── QUICK ACTIONS ── */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {quickActions.map((action) => (
              <button
                key={action.label}
                onClick={() => navigate(action.href, action.state ? { state: action.state } : undefined)}
                className="flex flex-col items-center gap-2 px-4 py-5 rounded-xl text-sm font-medium transition-all border border-gray-100 bg-white hover:shadow-md hover:-translate-y-0.5"
              >
                <div className={cn('w-11 h-11 rounded-xl flex items-center justify-center', action.color)}>
                  <action.icon className="w-5 h-5" />
                </div>
                <span className="text-[#1E293B] text-xs sm:text-sm">{action.label}</span>
              </button>
            ))}
          </div>

          {/* ── RECENT PATIENTS + DOCTOR PERFORMANCE ── */}
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Recent Patients */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-[#0F172A]">Recent Patients</h2>
                <button
                  onClick={() => navigate('/patients')}
                  className="text-sm font-medium text-[#0EA5E9] hover:text-[#0284C7] transition-colors"
                >
                  View All Patients →
                </button>
              </div>
              {recentPatients.length === 0 ? (
                <div className="px-6 py-8 text-center text-sm text-[#1E293B]/50">
                  No patients added yet.
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {recentPatients.map((p) => (
                    <div key={p.id} className="px-6 py-3.5 flex items-center justify-between hover:bg-gray-50/50 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-[#0EA5E9]/10 flex items-center justify-center text-sm font-medium text-[#0EA5E9]">
                          {(p.name || p.first_name || '?').charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-[#0F172A]">{p.name || p.first_name || 'Unknown'}</p>
                          <p className="text-xs text-[#1E293B]/50">{p.phone || '—'}</p>
                        </div>
                      </div>
                      <span className="text-xs text-[#1E293B]/40">
                        {p.created_at ? dayjs(p.created_at).format('MMM D') : '—'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Doctor Performance */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-100">
                <h2 className="text-lg font-semibold text-[#0F172A]">Doctor Performance</h2>
                <p className="text-sm text-[#1E293B]/60 mt-0.5">This month</p>
              </div>
              {doctorPerformance.length === 0 ? (
                <div className="px-6 py-8 text-center text-sm text-[#1E293B]/50">
                  No doctor data yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-50 bg-gray-50/50">
                        <th className="text-left py-3 px-4 font-medium text-[#1E293B]/60">Doctor</th>
                        <th className="text-center py-3 px-4 font-medium text-[#1E293B]/60">Appts</th>
                        <th className="text-center py-3 px-4 font-medium text-[#1E293B]/60">Completed</th>
                        <th className="text-right py-3 px-4 font-medium text-[#1E293B]/60">Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {doctorPerformance.map((row) => (
                        <tr key={row.doctor_id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-[#0EA5E9]/10 flex items-center justify-center">
                                <Stethoscope className="w-4 h-4 text-[#0EA5E9]" />
                              </div>
                              <span className="font-medium text-[#0F172A]">{row.doctor_name}</span>
                            </div>
                          </td>
                          <td className="text-center py-3.5 px-4 tabular-nums">{row.appointments_count}</td>
                          <td className="text-center py-3.5 px-4 tabular-nums">{row.completed_appointments}</td>
                          <td className="text-right py-3.5 px-4 tabular-nums font-medium">{formatCurrency(row.total_revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
