import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import { Calendar, Loader2 } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { appointmentsApi } from '../../services';
import type { Appointment } from '../../types';
import { formatAppointmentDoctorName } from '../../utils';
import { formatAppointmentDateTimeWithZoneLabel } from '../../utils/doctorSchedule';
import { ErrorState } from '../../components/common';
import { BOOKING_DATA_REFRESH_EVENT } from '../../constants/booking';
import { PATIENT_BOOKING_PENDING_STORAGE_KEY } from '../../constants/patient';
import { DISPLAY_TIMEZONE } from '../../constants/time';

dayjs.extend(utc);

type TabKey = 'upcoming' | 'past';

function appointmentTime(a: Appointment): string | undefined {
  return a.appointment_time || a.scheduled_at;
}

function doctorLabel(a: Appointment): string {
  const n = formatAppointmentDoctorName(a);
  if (n !== '-') return n;
  return a.doctor_id != null ? `Doctor #${a.doctor_id}` : 'Doctor';
}

/** Later entries win (so server rows replace same id after refetch). */
function dedupeById(rows: Appointment[]): Appointment[] {
  const map = new Map<string, Appointment>();
  for (const r of rows) {
    map.set(String(r.id), r);
  }
  return [...map.values()];
}

function readPendingBookedAppointment(
  location: ReturnType<typeof useLocation>
): { booked: Appointment | null; hadRouterState: boolean } {
  const fromState = (location.state as { seedAppointment?: Appointment } | null)?.seedAppointment;
  if (fromState) {
    try {
      sessionStorage.removeItem(PATIENT_BOOKING_PENDING_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    return { booked: fromState, hadRouterState: true };
  }
  try {
    const raw = sessionStorage.getItem(PATIENT_BOOKING_PENDING_STORAGE_KEY);
    if (!raw) return { booked: null, hadRouterState: false };
    const parsed = JSON.parse(raw) as Appointment;
    sessionStorage.removeItem(PATIENT_BOOKING_PENDING_STORAGE_KEY);
    return { booked: parsed, hadRouterState: false };
  } catch {
    try {
      sessionStorage.removeItem(PATIENT_BOOKING_PENDING_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    return { booked: null, hadRouterState: false };
  }
}

function toOptimisticPendingRow(booked: Appointment): Appointment {
  return { ...booked, status: 'pending' };
}

export function PatientAppointments() {
  const location = useLocation();
  const navigate = useNavigate();
  const [tab, setTab] = useState<TabKey>('upcoming');
  const [rows, setRows] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasLoadedOnceRef = useRef(false);
  const preferInlineAfterSeedRef = useRef(false);

  const loadFromServer = useCallback(async () => {
    setError(null);
    const inlineOnly = preferInlineAfterSeedRef.current;
    preferInlineAfterSeedRef.current = false;

    if (hasLoadedOnceRef.current || inlineOnly) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const list = await appointmentsApi.getAll({ limit: 100 });
      const deduped = dedupeById(list);
      setRows(deduped);
      hasLoadedOnceRef.current = true;
    } catch {
      setError('Unable to load appointments.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useLayoutEffect(() => {
    const { booked, hadRouterState } = readPendingBookedAppointment(location);
    if (!booked) return;
    preferInlineAfterSeedRef.current = true;
    const optimistic = toOptimisticPendingRow(booked);
    setRows((prev) => {
      const without = prev.filter((a) => String(a.id) !== String(optimistic.id));
      return dedupeById([optimistic, ...without]);
    });
    if (hadRouterState) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.state, location.pathname, navigate]);

  useEffect(() => {
    void loadFromServer();
  }, [location.pathname, location.key, loadFromServer]);

  useEffect(() => {
    const onBookingRefresh = () => {
      console.log('[REFETCH_TRIGGERED] patientAppointments');
      void loadFromServer();
    };
    window.addEventListener(BOOKING_DATA_REFRESH_EVENT, onBookingRefresh);
    return () => window.removeEventListener(BOOKING_DATA_REFRESH_EVENT, onBookingRefresh);
  }, [loadFromServer]);

  const { upcoming, past } = useMemo(() => {
    const now = dayjs.utc();
    const upcomingList: Appointment[] = [];
    const pastList: Appointment[] = [];
    for (const a of rows) {
      const t = appointmentTime(a);
      const dt = t ? dayjs.utc(t) : null;
      const isPast =
        a.status === 'pending'
          ? false
          : !dt || dt.isBefore(now) || a.status === 'cancelled' || a.status === 'completed';
      if (isPast) pastList.push(a);
      else upcomingList.push(a);
    }
    upcomingList.sort(
      (a, b) => dayjs.utc(appointmentTime(a)!).valueOf() - dayjs.utc(appointmentTime(b)!).valueOf()
    );
    pastList.sort(
      (a, b) => dayjs.utc(appointmentTime(b)!).valueOf() - dayjs.utc(appointmentTime(a)!).valueOf()
    );
    return { upcoming: upcomingList, past: pastList };
  }, [rows]);

  const shown = tab === 'upcoming' ? upcoming : past;
  const showInitialSkeleton = loading && rows.length === 0;

  if (error) {
    return <ErrorState title="Appointments" description={error} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Appointments</h1>
        <p className="text-muted-foreground text-sm mt-1">Your upcoming visits and history.</p>
      </div>

      <div className="relative -mx-1 sm:mx-0">
        <div
          className="pointer-events-none absolute left-0 top-0 z-10 h-full w-5 bg-gradient-to-r from-background to-transparent md:hidden"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute right-0 top-0 z-10 h-full w-5 bg-gradient-to-l from-background to-transparent md:hidden"
          aria-hidden
        />
        <div className="-mx-1 flex flex-nowrap items-center gap-2 overflow-x-auto border-b border-border px-1 pb-2 [scrollbar-width:none] md:flex-wrap md:overflow-visible md:px-0 [&::-webkit-scrollbar]:hidden">
          <Button variant={tab === 'upcoming' ? 'default' : 'ghost'} size="sm" onClick={() => setTab('upcoming')}>
            Upcoming ({upcoming.length})
          </Button>
          <Button variant={tab === 'past' ? 'default' : 'ghost'} size="sm" onClick={() => setTab('past')}>
            Past ({past.length})
          </Button>
          {refreshing && rows.length > 0 && (
            <span className="ml-auto inline-flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground md:ml-auto">
              <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" aria-hidden />
              Updating…
            </span>
          )}
        </div>
      </div>

      {showInitialSkeleton ? (
        <div className="space-y-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardContent>
                <div className="h-5 w-48 rounded-md bg-muted animate-pulse mb-2" />
                <div className="h-4 w-64 rounded-md bg-muted animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : rows.length === 0 ? (
        <Card className="border-dashed">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <Calendar className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle className="text-base pt-2">No appointments yet</CardTitle>
            <CardDescription>
              When you book with a doctor, your visits will show up here.
            </CardDescription>
            <div className="flex justify-center pt-4">
              <Button
                type="button"
                onClick={() => navigate('/patient/doctors', { state: { browseAllDoctors: true } })}
              >
                Book your first appointment
              </Button>
            </div>
          </CardHeader>
        </Card>
      ) : shown.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">
          {tab === 'upcoming' ? 'No upcoming appointments.' : 'No past appointments in your history.'}
        </p>
      ) : (
        <ul className="space-y-6">
          {shown.map((a) => {
            const t = appointmentTime(a);
            const isPending = a.status === 'pending';
            return (
              <Card
                key={String(a.id)}
                className={isPending ? 'opacity-80' : undefined}
                aria-busy={isPending}
                aria-disabled={isPending}
                data-pending={isPending || undefined}
              >
                <CardContent
                  className={
                    isPending
                      ? 'pt-6 flex flex-wrap items-start justify-between gap-3 pointer-events-none select-none'
                      : 'pt-6 flex flex-wrap items-start justify-between gap-3'
                  }
                >
                  <div>
                    <p className="font-medium">{doctorLabel(a)}</p>
                    <p className="text-sm text-muted-foreground">
                      {t ? formatAppointmentDateTimeWithZoneLabel(t, DISPLAY_TIMEZONE) : 'Time TBD'}
                    </p>
                    {a.notes && <p className="text-xs text-muted-foreground mt-1 max-w-md">{a.notes}</p>}
                  </div>
                  <Badge
                    variant={
                      a.status === 'cancelled'
                        ? 'destructive'
                        : a.status === 'pending'
                          ? 'outline'
                          : 'secondary'
                    }
                    className="capitalize"
                  >
                    {a.status === 'pending' ? 'Confirming…' : a.status}
                  </Badge>
                </CardContent>
              </Card>
            );
          })}
        </ul>
      )}
    </div>
  );
}
