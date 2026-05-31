import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { useDoctorAppointmentsView, useBilling, useModalFocusTrap } from '../../hooks';
import { useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import { ErrorState, EmptyState } from '../../components/common';
import { DayCalendar } from '../../components/doctor/calendar/DayCalendar';
import { DISPLAY_TIMEZONE } from '../../constants/time';
import { formatAppointmentDateTimeWithZoneLabel } from '../../utils/doctorSchedule';
import { billingApi } from '../../services';
import type { Appointment, Bill } from '../../types';

type Tab = 'upcoming' | 'past';

function apptStatusBadgeVariant(
  s: Appointment['status']
): 'default' | 'secondary' | 'outline' | 'destructive' {
  if (s === 'completed') return 'secondary';
  if (s === 'cancelled') return 'destructive';
  if (s === 'scheduled' || s === 'pending') return 'default';
  return 'outline';
}

function billCoversAppointment(bills: Bill[], appt: Appointment): boolean {
  const aid = String(appt.id);
  return bills.some((b) => b.appointment_id && String(b.appointment_id) === aid);
}

export function DoctorAppointmentsPage() {
  const [tab, setTab] = useState<Tab>('upcoming');
  const {
    listAppointments: appointments,
    calendarAppointments,
    patients,
    loading,
    error,
    refetch,
  } = useDoctorAppointmentsView(tab);
  const { bills, loading: billsLoading, refetch: refetchBills } = useBilling();
  const { isIndependent, selfDoctor, isReadOnly } = useDoctorWorkspace();
  const location = useLocation();
  const navigate = useNavigate();
  const calendarRef = useRef<HTMLDivElement>(null);
  const scheduleFocusRef = useRef(false);
  const [bookPatientId, setBookPatientId] = useState<string | null>(null);
  const [billDialogAppt, setBillDialogAppt] = useState<Appointment | null>(null);
  const [billAmount, setBillAmount] = useState('');
  const [billDescription, setBillDescription] = useState('');
  const [billSubmitting, setBillSubmitting] = useState(false);
  const billDialogRef = useRef<HTMLDivElement>(null);

  useModalFocusTrap(billDialogRef, Boolean(billDialogAppt));

  const list = appointments;

  const showMobileBookingBar =
    isIndependent && selfDoctor != null && selfDoctor.has_availability_windows !== false;

  const clearApptPageNavState = useCallback(() => {
    if (
      location.state &&
      typeof location.state === 'object' &&
      ('openSchedule' in location.state || 'bookPatientId' in location.state)
    ) {
      navigate(
        { pathname: location.pathname, search: location.search, hash: location.hash },
        { replace: true, state: {} }
      );
    }
  }, [location.hash, location.pathname, location.search, location.state, navigate]);

  useEffect(() => {
    if (location.pathname !== '/doctor/appointments') {
      return;
    }
    if (tab === 'past') {
      return;
    }
    const st = location.state as { openSchedule?: boolean; bookPatientId?: string } | null;
    if (st?.bookPatientId) {
      setBookPatientId(String(st.bookPatientId));
    }
    const shouldScroll = Boolean(st?.openSchedule || st?.bookPatientId);
    if (shouldScroll && isIndependent && !scheduleFocusRef.current) {
      scheduleFocusRef.current = true;
      const id = window.setTimeout(() => {
        calendarRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 150);
      clearApptPageNavState();
      return () => clearTimeout(id);
    }
    if (st && typeof st === 'object' && ('openSchedule' in st || 'bookPatientId' in st)) {
      clearApptPageNavState();
    }
  }, [location.pathname, location.state, isIndependent, clearApptPageNavState, tab]);

  const scrollToCalendar = () => {
    calendarRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const closeBillDialog = useCallback(() => {
    setBillDialogAppt(null);
    setBillAmount('');
    setBillDescription('');
  }, []);

  const submitBillFromAppointment = useCallback(async () => {
    if (!billDialogAppt) return;
    const pid = billDialogAppt.patient_id != null ? String(billDialogAppt.patient_id) : '';
    if (!pid) {
      toast.error('Cannot bill: patient missing');
      return;
    }
    const n = parseFloat(billAmount);
    if (Number.isNaN(n) || n <= 0) {
      toast.error('Enter a valid amount');
      return;
    }
    setBillSubmitting(true);
    try {
      await billingApi.create({
        patient_id: pid,
        appointment_id: String(billDialogAppt.id),
        amount: n,
        currency: 'INR',
        description: billDescription.trim() || undefined,
      });
      toast.success('Bill created');
      closeBillDialog();
      void refetchBills();
      void refetch();
    } catch (e) {
      const msg =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not create bill')
          : 'Could not create bill';
      toast.error(msg, { duration: 5000 });
    } finally {
      setBillSubmitting(false);
    }
  }, [billDialogAppt, billAmount, billDescription, closeBillDialog, refetch, refetchBills]);

  if (error) {
    return <ErrorState title="Could not load appointments" description="" error={error} onRetry={refetch} />;
  }

  return (
    <div
      className={cn(
        'space-y-6',
        /* Reserve space for DayCalendar fixed mobile CTA (~h-12 + bar padding + safe area) */
        showMobileBookingBar && 'pb-24 md:pb-0'
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Appointments</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isReadOnly
              ? 'Upcoming and past visits assigned to you (read only).'
              : 'Your calendar and visit list. All times in IST.'}
          </p>
        </div>
        {isIndependent && selfDoctor && selfDoctor.has_availability_windows !== false && (
          <Button type="button" size="sm" variant="secondary" onClick={scrollToCalendar}>
            Jump to schedule
          </Button>
        )}
      </div>

      {isIndependent && selfDoctor?.has_availability_windows === false && (
        <p className="text-sm text-muted-foreground rounded-lg border border-border px-3 py-2">
          Set your weekly availability in <strong>Availability</strong> before booking from the calendar.
        </p>
      )}

      {selfDoctor && selfDoctor.has_availability_windows !== false && (
        <div ref={calendarRef}>
          <Card>
            <CardHeader>
              <CardTitle>Day schedule</CardTitle>
              <CardDescription>
                {isIndependent
                  ? 'Click a green slot to book. Booked, past, and busy blocks are not selectable.'
                  : 'Published slot times in your organization (read only).'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DayCalendar
                doctorId={String(selfDoctor.id)}
                isInteractive={isIndependent}
                patients={patients}
                appointments={calendarAppointments}
                bookPatientId={bookPatientId}
                hasAvailabilityWindows={selfDoctor.has_availability_windows}
                doctorTimeZone={DISPLAY_TIMEZONE}
                onBooked={async () => {
                  await refetch();
                }}
              />
            </CardContent>
          </Card>
        </div>
      )}

      <div className="flex gap-2">
        <Button
          type="button"
          variant={tab === 'upcoming' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setTab('upcoming')}
          className={cn(tab === 'upcoming' && 'shadow-sm')}
        >
          Upcoming
        </Button>
        <Button type="button" variant={tab === 'past' ? 'default' : 'outline'} size="sm" onClick={() => setTab('past')}>
          Past
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {!loading && list.length === 0 && (
        <EmptyState
          title={tab === 'upcoming' ? 'No upcoming appointments' : 'No past appointments'}
          description={
            tab === 'upcoming'
              ? 'Your list will show here; book from the schedule above when slots are open.'
              : 'Completed, cancelled, and overdue visits that still need completion appear here.'
          }
        />
      )}

      {!loading &&
        list.map((a) => {
          const pid = a.patient_id != null ? String(a.patient_id) : '';
          const pName =
            patients.find((p) => String(p.id) === pid)?.name || a.patient?.name || 'Patient';
          const showCreateBill =
            tab === 'past' &&
            isIndependent &&
            !isReadOnly &&
            a.status === 'completed' &&
            !billsLoading &&
            !billCoversAppointment(bills, a);
          return (
            <Card key={String(a.id)} id={`appt-${a.id}`} className="scroll-mt-4 transition-all hover:shadow-lg">
              <CardContent className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <div className="min-w-0 space-y-1">
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
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {formatAppointmentDateTimeWithZoneLabel(
                      a.appointment_time || a.scheduled_at || '',
                      DISPLAY_TIMEZONE
                    )}
                  </span>
                  <div>
                    <Link
                      to={`/doctor/appointments/${a.id}`}
                      className="text-xs font-medium text-primary hover:underline"
                    >
                      {a.status === 'completed' ? 'View Encounter' : 'Start Encounter'}
                    </Link>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  {showCreateBill && (
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        if (!a.patient_id) {
                          toast.error('Cannot bill: patient missing');
                          return;
                        }
                        setBillDialogAppt(a);
                        setBillAmount('');
                        setBillDescription('');
                      }}
                    >
                      Create bill
                    </Button>
                  )}
                  <Badge variant={apptStatusBadgeVariant(a.status)} className="capitalize shrink-0">
                    {a.status}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          );
        })}

      {billDialogAppt && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="presentation"
          onClick={() => !billSubmitting && closeBillDialog()}
        >
          <div
            ref={billDialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="appt-bill-title"
            className="w-full max-w-md rounded-xl border border-border bg-card text-foreground shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-border px-4 py-3">
              <h2 id="appt-bill-title" className="text-lg font-semibold">
                New bill
              </h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                For this completed visit — amount in INR.
              </p>
            </div>
            <div className="space-y-3 px-4 py-4">
              <div>
                <p className="text-xs font-medium text-muted-foreground">Visit</p>
                <p className="text-sm mt-1">
                  {formatAppointmentDateTimeWithZoneLabel(
                    billDialogAppt.appointment_time || billDialogAppt.scheduled_at || '',
                    DISPLAY_TIMEZONE
                  )}
                </p>
              </div>
              <div>
                <label htmlFor="appt-bill-amt" className="text-xs font-medium text-muted-foreground">
                  Amount
                </label>
                <Input
                  id="appt-bill-amt"
                  type="number"
                  min="0"
                  step="0.01"
                  className="mt-1"
                  value={billAmount}
                  onChange={(e) => setBillAmount(e.target.value)}
                  disabled={billSubmitting}
                />
              </div>
              <div>
                <label htmlFor="appt-bill-desc" className="text-xs font-medium text-muted-foreground">
                  Description (optional)
                </label>
                <Input
                  id="appt-bill-desc"
                  className="mt-1"
                  value={billDescription}
                  onChange={(e) => setBillDescription(e.target.value)}
                  disabled={billSubmitting}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-border px-4 py-3">
              <Button type="button" variant="outline" onClick={closeBillDialog} disabled={billSubmitting}>
                Cancel
              </Button>
              <Button type="button" onClick={() => void submitBillFromAppointment()} disabled={billSubmitting}>
                {billSubmitting ? 'Creating…' : 'Create bill'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
