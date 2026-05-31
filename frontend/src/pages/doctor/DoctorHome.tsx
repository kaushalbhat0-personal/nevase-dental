import { useCallback, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button, buttonVariants } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { useAppointments, useModalFocusTrap, usePatients } from '../../hooks';
import { useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import { useAppMode } from '../../contexts/AppModeContext';
import { useAuth } from '../../hooks/useAuth';
import { isDoctorOnlyRole } from '../../utils/roles';
import { isDoctorVerificationApproved } from '../../utils/doctorVerification';
import { isIndividualTenantUser } from '../../utils/tenantMode';
import { ErrorState } from '../../components/common';
import { tenantsApi } from '../../services/tenants';
import type { Appointment } from '../../types';
import { UserPlus, CalendarPlus, Receipt, Building2 } from 'lucide-react';
import { DISPLAY_TIMEZONE } from '../../constants/time';
import {
  appointmentCalendarDayYmd,
  calendarTodayYmdInZone,
  formatSlotTimeWithZoneLabel,
  slotInstantUtcMs,
} from '../../utils/doctorSchedule';

function apiErrorMessage(e: unknown, fallback: string): string {
  if (!axios.isAxiosError(e) || !e.response?.data || typeof e.response.data !== 'object') {
    return fallback;
  }
  const d = (e.response.data as { detail?: unknown }).detail;
  if (d == null) return fallback;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .join(' ');
  }
  return String(d);
}

function isAppointmentToday(a: Appointment): boolean {
  const t = a.appointment_time || a.scheduled_at;
  if (!t) return false;
  return (
    appointmentCalendarDayYmd(t, DISPLAY_TIMEZONE) === calendarTodayYmdInZone(DISPLAY_TIMEZONE)
  );
}

export function DoctorHome() {
  const navigate = useNavigate();
  const { user, patchUser, refreshUser } = useAuth();
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const practiceDataEnabled = isDoctorVerificationApproved(user, token);
  const { setMode } = useAppMode();
  const { selfDoctor, loading: workspaceLoading, refetch: refetchWorkspace } = useDoctorWorkspace();
  const isIndividualDoctor = isIndividualTenantUser(user);
  const showUpgradeToClinic =
    isIndividualDoctor && isDoctorOnlyRole(user, token) && !workspaceLoading;
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [clinicName, setClinicName] = useState('');
  const [upgradeSubmitting, setUpgradeSubmitting] = useState(false);
  const [upgradeError, setUpgradeError] = useState<string | null>(null);
  const upgradeDialogRef = useRef<HTMLDivElement>(null);
  useModalFocusTrap(upgradeDialogRef, upgradeOpen);
  const openUpgrade = useCallback(() => {
    setUpgradeError(null);
    setClinicName('');
    setUpgradeOpen(true);
  }, []);
  const closeUpgrade = useCallback(() => {
    if (upgradeSubmitting) return;
    setUpgradeOpen(false);
    setUpgradeError(null);
  }, [upgradeSubmitting]);
  const confirmUpgrade = useCallback(async () => {
    const name = clinicName.trim();
    if (!name) {
      setUpgradeError('Enter a clinic name');
      return;
    }
    setUpgradeSubmitting(true);
    setUpgradeError(null);
    try {
      const data = await tenantsApi.upgradeToOrganization({ clinic_name: name });
      patchUser({
        roles: data.roles,
        is_owner: true,
      });
      setMode('admin');
      await refreshUser();
      void refetchWorkspace();
      setUpgradeOpen(false);
      setClinicName('');
      toast("You're now running a clinic 🎉", { icon: '✨', duration: 4500 });
      navigate('/admin/dashboard', { replace: true });
    } catch (e) {
      setUpgradeError(apiErrorMessage(e, 'Could not upgrade your practice'));
    } finally {
      setUpgradeSubmitting(false);
    }
  }, [clinicName, navigate, patchUser, refreshUser, refetchWorkspace, setMode]);
  const { appointments, loading: aptLoading, error: aptError, refetch: refetchApt } = useAppointments(
    undefined,
    practiceDataEnabled
  );
  const { patients, loading: patLoading, error: patError, refetch: refetchPat } = usePatients(
    undefined,
    practiceDataEnabled
  );

  const loading = aptLoading || patLoading;
  const error = aptError || patError;

  const todaysAppointments = useMemo(
    () => appointments.filter((a) => isAppointmentToday(a)),
    [appointments]
  );

  const upcoming = useMemo(() => {
    const t = Date.now();
    return appointments.filter((a) => {
      const at = a.appointment_time || a.scheduled_at;
      return at && slotInstantUtcMs(at) >= t && a.status === 'scheduled';
    }).length;
  }, [appointments]);

  if (error) {
    return (
      <ErrorState
        title="Could not load overview"
        description="Try again in a moment."
        error={error}
        onRetry={() => {
          void refetchApt();
          void refetchPat();
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {isIndividualDoctor
            ? 'A snapshot of your practice today — add care and billing as you go.'
            : 'A snapshot of patients and visits associated with you in this organization.'}
        </p>
      </div>

      {showUpgradeToClinic && (
        <Card className="border-primary/20 bg-gradient-to-r from-sky-50/80 to-emerald-50/50 dark:from-sky-950/30 dark:to-emerald-950/20">
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
            <div className="flex gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Building2 className="h-5 w-5" aria-hidden />
              </div>
              <div>
                <CardTitle className="text-base">Grow your practice</CardTitle>
                <CardDescription className="text-sm leading-relaxed max-w-prose">
                  Add more doctors, manage staff, and run your clinic.
                </CardDescription>
              </div>
            </div>
            <Button type="button" onClick={openUpgrade} disabled={workspaceLoading}>
              Upgrade to Clinic
            </Button>
          </CardHeader>
        </Card>
      )}

      {upgradeOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="presentation"
          onClick={closeUpgrade}
        >
          <div
            ref={upgradeDialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="upgrade-clinic-title"
            className="w-full max-w-md rounded-xl border border-border bg-card text-foreground shadow-lg outline-none p-0"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-border px-4 py-3">
              <h2 id="upgrade-clinic-title" className="text-lg font-semibold">
                Upgrade to Clinic
              </h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                This turns your individual practice into a clinic organization. You can invite staff
                and add more doctors.
              </p>
            </div>
            <div className="space-y-3 px-4 py-4">
              {upgradeError && (
                <p className="text-sm text-destructive" role="alert">
                  {upgradeError}
                </p>
              )}
              <div>
                <label htmlFor="clinic-name" className="text-xs font-medium text-muted-foreground">
                  Clinic name
                </label>
                <Input
                  id="clinic-name"
                  className="mt-1"
                  value={clinicName}
                  onChange={(e) => {
                    setClinicName(e.target.value);
                    if (upgradeError) setUpgradeError(null);
                  }}
                  disabled={upgradeSubmitting}
                  placeholder="e.g. City Care Clinic"
                  autoComplete="organization"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-border px-4 py-3">
              <Button type="button" variant="outline" onClick={closeUpgrade} disabled={upgradeSubmitting}>
                Cancel
              </Button>
              <Button type="button" onClick={() => void confirmUpgrade()} disabled={upgradeSubmitting}>
                {upgradeSubmitting ? 'Upgrading…' : 'Confirm Upgrade'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {isIndividualDoctor && selfDoctor && (
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => navigate('/doctor/patients', { state: { openAddPatient: true } })}
            className="gap-2"
          >
            <UserPlus className="h-4 w-4" aria-hidden />
            Add patient
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => navigate('/doctor/appointments', { state: { openSchedule: true } })}
            className="gap-2"
          >
            <CalendarPlus className="h-4 w-4" aria-hidden />
            Schedule visit
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => navigate('/doctor/bills', { state: { openCreateBill: true } })}
            className="gap-2"
          >
            <Receipt className="h-4 w-4" aria-hidden />
            Create bill
          </Button>
        </div>
      )}

      {selfDoctor && (
        <Card>
          <CardHeader>
            <CardTitle>Schedule</CardTitle>
            <CardDescription>
              {isIndividualDoctor
                ? 'Book visits from the full day calendar on Appointments. This page stays a quick overview.'
                : 'Your visit list and organization schedule live on Appointments.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              to="/doctor/appointments"
              state={{ openSchedule: true }}
              className={cn(buttonVariants({ variant: 'secondary' }), 'inline-flex gap-2')}
            >
              <CalendarPlus className="h-4 w-4" aria-hidden />
              Open schedule
            </Link>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total patients</CardDescription>
            <CardTitle className="text-3xl tabular-nums">{loading ? '—' : patients.length}</CardTitle>
          </CardHeader>
          <CardContent>
            <Link to="/doctor/patients" className="text-sm text-primary hover:underline">
              View patients
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Today&apos;s appointments</CardDescription>
            <CardTitle className="text-3xl tabular-nums">{loading ? '—' : todaysAppointments.length}</CardTitle>
          </CardHeader>
          <CardContent>
            <Link to="/doctor/appointments" className="text-sm text-primary hover:underline">
              View schedule
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Upcoming scheduled</CardDescription>
            <CardTitle className="text-3xl tabular-nums">{loading ? '—' : upcoming}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">From now onward</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Today</CardTitle>
          <CardDescription>Appointments on your calendar for today</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
          {!loading && todaysAppointments.length === 0 && (
            <p className="text-sm text-muted-foreground">No appointments scheduled for today.</p>
          )}
          {!loading &&
            todaysAppointments.map((a) => {
              const pid = a.patient_id != null ? String(a.patient_id) : '';
              const pName =
                patients.find((p) => String(p.id) === pid)?.name || a.patient?.name || 'Patient';
              return (
                <div
                  key={String(a.id)}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm shadow-sm"
                >
                  <div className="min-w-0 flex-1">
                    {pid ? (
                      <Link
                        to={`/doctor/patients/${pid}`}
                        className="font-medium text-primary hover:underline truncate block"
                      >
                        {pName}
                      </Link>
                    ) : (
                      <span className="font-medium truncate block">{pName}</span>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {formatSlotTimeWithZoneLabel(
                        a.appointment_time || a.scheduled_at || '',
                        DISPLAY_TIMEZONE
                      )}
                    </span>
                  </div>
                  <span className="text-muted-foreground capitalize shrink-0">{a.status}</span>
                </div>
              );
            })}
        </CardContent>
      </Card>
    </div>
  );
}
