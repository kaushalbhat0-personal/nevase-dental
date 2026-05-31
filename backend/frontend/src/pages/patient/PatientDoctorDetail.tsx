import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import axios from 'axios';
import { buttonVariants } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { doctorsApi, publicDiscoveryApi, type DoctorScheduleDay, type DoctorSlot } from '../../services';
import type { Doctor, PublicDoctorProfile } from '../../types';
import { useLinkedPatient } from '../../hooks';
import { usePatientDoctorBookingPanel } from '../../hooks/patient/usePatientDoctorBookingPanel';
import { ErrorState } from '../../components/common';
import { formatDoctorName } from '../../utils';
import { DoctorSlotPicker } from '../../components/patient/DoctorSlotPicker';
import {
  DoctorProfileAbout,
  DoctorProfileAvailabilitySummary,
  DoctorProfileClinic,
  DoctorProfileHero,
  DoctorProfileNextAvailableBanner,
} from '../../components/patient/DoctorPublicProfileBlocks';
import {
  appointmentCalendarDayYmd,
  calendarDayYmdForInstantInZone,
  formatNextAvailablePhrase,
  formatSlotTimeWithZoneLabel,
  isSlotInstantInTheFuture,
  relativeCalendarDayHeadingInZone,
} from '../../utils/doctorSchedule';
import { DISPLAY_TIMEZONE } from '../../constants/time';
import { ymdAddDaysInIana, ymdNowInIana } from '../../utils/doctorSchedule';
import { PATIENT_BOOKING_PENDING_STORAGE_KEY, PATIENT_CLINIC_BOOKING_SCOPE_KEY } from '../../constants/patient';
import { Button } from '@/components/ui/button';

function publicToBookingDoctor(p: PublicDoctorProfile): Doctor {
  return {
    id: p.id,
    name: p.full_name,
    specialization: p.specialization,
    experience_years: p.experience,
    verification_status: p.verification_status,
    verified: p.verified,
    has_availability_windows: p.has_availability_windows,
    timezone: p.timezone,
  };
}

function ProfileSkeleton() {
  return (
    <div className="pb-28">
      <div className="mx-auto max-w-md space-y-6 px-4">
        <div className="flex items-start gap-2">
          <div className="h-10 w-10 shrink-0 animate-pulse rounded-xl bg-muted" />
          <div className="min-w-0 flex-1 space-y-6">
            <div className="mb-4 space-y-4 rounded-2xl border-2 border-primary/10 bg-muted/40 p-4">
              <div className="h-3 w-28 animate-pulse rounded bg-muted" />
              <div className="h-9 w-full max-w-sm animate-pulse rounded-lg bg-muted" />
              <div className="h-4 w-40 animate-pulse rounded bg-muted" />
            </div>
            <div className="rounded-xl border border-border/80 bg-card p-4 shadow-md relative z-0">
              <div className="flex items-center gap-4">
                <div className="h-16 w-16 shrink-0 animate-pulse rounded-xl bg-muted" />
                <div className="flex-1 space-y-4">
                  <div className="h-5 w-48 max-w-full animate-pulse rounded-md bg-muted" />
                  <div className="h-4 w-40 max-w-full animate-pulse rounded-md bg-muted" />
                  <div className="h-4 w-56 max-w-full animate-pulse rounded-md bg-muted" />
                  <div className="h-12 w-full animate-pulse rounded-xl bg-muted" />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="space-y-4 rounded-xl border border-border/60 p-4 shadow-md relative z-0">
          <div className="h-4 w-32 animate-pulse rounded bg-muted" />
          <div className="h-16 w-full animate-pulse rounded-lg bg-muted" />
          <div className="h-3 w-full animate-pulse rounded bg-muted" />
        </div>
        <div className="h-20 animate-pulse rounded-2xl bg-muted/80" />
        <div className="space-y-3 rounded-xl border border-border/60 p-4 shadow-md relative z-0">
          <div className="h-4 w-28 animate-pulse rounded bg-muted" />
          <div className="h-12 w-2/3 max-w-sm animate-pulse rounded-xl bg-muted" />
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-10 w-[4.5rem] animate-pulse rounded-xl bg-muted" />
            ))}
          </div>
        </div>
      </div>
      <div
        className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/80 px-4 pt-3 backdrop-blur-sm"
        style={{ paddingBottom: 'max(12px, env(safe-area-inset-bottom))' }}
      >
        <div className="mx-auto max-w-md">
          <div className="h-12 w-full animate-pulse rounded-xl bg-muted" />
        </div>
      </div>
    </div>
  );
}

export function PatientDoctorDetail() {
  const { id, doctorId } = useParams<{ id?: string; doctorId?: string }>();
  const rawParam = doctorId ?? id;
  const navigate = useNavigate();
  const location = useLocation();
  const { state: routeState } = location;
  const tenantFromRoute = (routeState as { tenantId?: string; focusBooking?: boolean } | null)?.tenantId;
  const focusBookingFromRoute = Boolean(
    (routeState as { focusBooking?: boolean } | null)?.focusBooking
  );
  const bookingSectionRef = useRef<HTMLElement>(null);
  const clearedFocusBookingRef = useRef(false);

  const { patientId, loading: patientLoading, error: patientError, refresh: refreshPatient } = useLinkedPatient();
  const [publicDoctor, setPublicDoctor] = useState<PublicDoctorProfile | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [avLoading, setAvLoading] = useState(false);
  const [avError, setAvError] = useState<string | null>(null);
  const [todayYmd, setTodayYmd] = useState('');
  const [tomorrowYmd, setTomorrowYmd] = useState('');
  const [summaryDay, setSummaryDay] = useState<DoctorScheduleDay | null>(null);
  const [tomorrowSlots, setTomorrowSlots] = useState<DoctorSlot[]>([]);
  const [nextAfterNoSlots, setNextAfterNoSlots] = useState<DoctorSlot | null>(null);
  const [nextAfterNoSlotsLoading, setNextAfterNoSlotsLoading] = useState(false);

  const bookingDoctor = useMemo(
    () => (publicDoctor ? publicToBookingDoctor(publicDoctor) : null),
    [publicDoctor]
  );

  const booking = usePatientDoctorBookingPanel(
    patientId,
    bookingDoctor,
    () => {},
    (created) => {
      try {
        sessionStorage.setItem(PATIENT_BOOKING_PENDING_STORAGE_KEY, JSON.stringify(created));
      } catch {
        /* */
      }
      navigate('/patient/appointments', { state: { seedAppointment: created } });
    },
    publicDoctor?.timezone ?? null
  );

  useEffect(() => {
    if (tenantFromRoute) {
      try {
        sessionStorage.setItem(PATIENT_CLINIC_BOOKING_SCOPE_KEY, tenantFromRoute);
      } catch {
        /* */
      }
    }
  }, [tenantFromRoute]);

  useEffect(() => {
    if (!rawParam) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setLoadError(null);
      setPublicDoctor(null);
      try {
        const p = await publicDiscoveryApi.getDoctor(rawParam);
        if (!cancelled) setPublicDoctor(p);
      } catch (e) {
        if (axios.isCancel(e)) return;
        if (axios.isAxiosError(e) && e.response?.status === 404) {
          if (!cancelled) {
            setLoadError('This doctor is not available for booking.');
            setPublicDoctor(null);
          }
        } else if (!cancelled) {
          setLoadError('Could not load this doctor.');
          setPublicDoctor(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [rawParam]);

  useEffect(() => {
    clearedFocusBookingRef.current = false;
  }, [location.key]);

  useEffect(() => {
    if (!focusBookingFromRoute || clearedFocusBookingRef.current) return;
    if (!publicDoctor || loading || patientLoading) return;
    clearedFocusBookingRef.current = true;
    const blockedHere = !patientId || publicDoctor.has_availability_windows === false;
    const t = window.setTimeout(() => {
      if (!blockedHere) {
        bookingSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      navigate(
        { pathname: location.pathname, hash: location.hash },
        {
          replace: true,
          state: tenantFromRoute ? { tenantId: tenantFromRoute } : undefined,
        }
      );
    }, 120);
    return () => clearTimeout(t);
  }, [
    focusBookingFromRoute,
    publicDoctor,
    loading,
    patientLoading,
    patientId,
    navigate,
    location.pathname,
    location.hash,
    tenantFromRoute,
  ]);

  useEffect(() => {
    if (!publicDoctor) return;
    const tz = publicDoctor.timezone;
    const t0 = ymdNowInIana(tz);
    const t1 = ymdAddDaysInIana(t0, tz, 1);
    setTodayYmd(t0);
    setTomorrowYmd(t1);
    let cancelled = false;
    (async () => {
      setAvLoading(true);
      setAvError(null);
      setSummaryDay(null);
      setTomorrowSlots([]);
      try {
        const [day, tom] = await Promise.all([
          doctorsApi.getScheduleDay(publicDoctor.id, t0, { fromYmd: t0, skipSlotsCache: true }),
          doctorsApi.getSlots(publicDoctor.id, t1, { skipCache: true }),
        ]);
        if (cancelled) return;
        setSummaryDay(day);
        setTomorrowSlots(tom);
      } catch {
        if (!cancelled) setAvError('Could not load availability.');
      } finally {
        if (!cancelled) setAvLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [publicDoctor?.id, publicDoctor?.timezone]);

  useEffect(() => {
    if (!publicDoctor || !patientId) {
      setNextAfterNoSlots(null);
      setNextAfterNoSlotsLoading(false);
      return;
    }
    if (booking.slotsLoading || booking.slotsError) return;
    if (booking.slots.length > 0) {
      setNextAfterNoSlots(null);
      setNextAfterNoSlotsLoading(false);
      return;
    }
    if (!booking.bookDate) return;
    const tz = publicDoctor.timezone;
    const fromNextDay = ymdAddDaysInIana(booking.bookDate, tz, 1);
    let cancelled = false;
    (async () => {
      setNextAfterNoSlotsLoading(true);
      setNextAfterNoSlots(null);
      try {
        const n = await doctorsApi.getNextAvailable(String(publicDoctor.id), fromNextDay, { horizonDays: 21 });
        if (!cancelled) setNextAfterNoSlots(n);
      } catch {
        if (!cancelled) setNextAfterNoSlots(null);
      } finally {
        if (!cancelled) setNextAfterNoSlotsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [
    publicDoctor,
    patientId,
    booking.slots.length,
    booking.slotsLoading,
    booking.slotsError,
    booking.bookDate,
  ]);

  const schedulePreviewSlots = useMemo(
    () => [...(summaryDay?.slots ?? []), ...tomorrowSlots],
    [summaryDay?.slots, tomorrowSlots]
  );
  const todaySlotsQuick = useMemo(
    () =>
      schedulePreviewSlots.filter(
        (s) => calendarDayYmdForInstantInZone(s.start, publicDoctor?.timezone) === todayYmd
      ),
    [schedulePreviewSlots, publicDoctor?.timezone, todayYmd]
  );
  const tomorrowSlotsQuick = useMemo(
    () =>
      schedulePreviewSlots.filter(
        (s) => calendarDayYmdForInstantInZone(s.start, publicDoctor?.timezone) === tomorrowYmd
      ),
    [schedulePreviewSlots, publicDoctor?.timezone, tomorrowYmd]
  );

  if (!rawParam) {
    return <ErrorState title="Missing doctor" description="Go back to search for a provider." />;
  }

  if (loadError) {
    return <ErrorState title="Doctor not available" description={loadError} />;
  }

  if (loading || !publicDoctor) {
    return <ProfileSkeleton />;
  }

  if (publicDoctor.verification_status !== 'approved') {
    return <ErrorState title="Doctor not available" description="This provider is not on the public network." />;
  }

  const name = formatDoctorName(bookingDoctor!);
  const blocked =
    !patientId || publicDoctor.has_availability_windows === false;

  const showSlotsSkeleton =
    Boolean(booking.bookDate) &&
    Boolean(patientId) &&
    booking.slotsLoading &&
    booking.slots.length === 0 &&
    !booking.slotsError;

  return (
    <div className="pb-28">
      <div className="mx-auto max-w-md space-y-6 px-4">
        <div className="flex items-start gap-2">
          <Link
            to="/patient/doctors"
            state={{ browseAllDoctors: true }}
            className={cn(buttonVariants({ variant: 'ghost', size: 'icon' }), 'mt-0.5 shrink-0 -ml-2 rounded-xl')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div className="min-w-0 flex-1">
            <div className="mb-4">
              <DoctorProfileNextAvailableBanner
                doctor={publicDoctor}
                profileSlotIso={publicDoctor.next_available_slot ?? null}
                scheduleNext={summaryDay?.next_available ?? null}
                todayYmd={todayYmd}
                doctorTodayYmd={booking.doctorTodayYmd}
                todaySlots={todaySlotsQuick}
                loading={avLoading}
              />
            </div>
            <DoctorProfileHero doctor={publicDoctor} />
          </div>
        </div>

        {patientError && (
          <p className="text-sm text-destructive" role="alert">
            {patientError}{' '}
            <button type="button" className="font-medium underline" onClick={() => void refreshPatient()}>
              Retry
            </button>
          </p>
        )}

        <DoctorProfileAbout doctor={publicDoctor} />
        <DoctorProfileClinic doctor={publicDoctor} />

        <DoctorProfileAvailabilitySummary
          loading={avLoading}
          error={avError}
          todayYmd={todayYmd}
          tomorrowYmd={tomorrowYmd}
          todaySlots={todaySlotsQuick}
          tomorrowSlots={tomorrowSlotsQuick}
          selectedStart={booking.selectedSlotStart}
          onPickSlot={(iso, ymd) => {
            booking.setBookDate(ymd);
            booking.setSelectedSlotStart(iso);
          }}
          onScrollToBooking={
            blocked
              ? undefined
              : () => bookingSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }
        />

        {blocked && (
          <p className="text-sm text-amber-800" role="status">
            {publicDoctor.has_availability_windows === false
              ? 'This doctor has not set online hours yet. Try another provider or call the clinic.'
              : 'Connect your profile to book.'}
          </p>
        )}

        {!blocked && !patientLoading && (
          <section
            ref={bookingSectionRef}
            id="patient-booking"
            className="scroll-mt-6 space-y-6"
          >
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Pick a time</h2>
            <ul className="mt-2 flex flex-col gap-1 text-xs text-muted-foreground sm:flex-row sm:flex-wrap sm:gap-x-5">
              <li>✔ Instant booking</li>
              <li>✔ No waiting time</li>
              <li>✔ Confirmed appointment</li>
            </ul>
          </div>
          {nextAfterNoSlotsLoading && !booking.slotsLoading && booking.slots.length === 0 ? (
            <p className="text-sm text-muted-foreground" role="status">
              Finding next opening…
            </p>
          ) : null}
          <Input
            id="book-date"
            type="date"
            min={booking.doctorTodayYmd}
            className="h-11 rounded-xl"
            value={booking.bookDate}
            onChange={(e) => booking.setBookDate(e.target.value)}
            disabled={!patientId || booking.submitting}
          />
          {booking.slotsError && (
            <p className="text-sm text-destructive" role="alert">
              {booking.slotsError}
            </p>
          )}
          {showSlotsSkeleton && (
            <div className="space-y-3" aria-busy aria-label="Loading available times">
              <div className="h-3 w-40 animate-pulse rounded bg-muted" />
              <div className="grid grid-cols-3 gap-2">
                {Array.from({ length: 9 }).map((_, i) => (
                  <div key={i} className="min-h-[48px] animate-pulse rounded-xl bg-muted" />
                ))}
              </div>
            </div>
          )}
          {!showSlotsSkeleton &&
            booking.bookDate &&
            patientId &&
            !booking.slotsLoading &&
            !booking.slotsError &&
            booking.slots.length === 0 && (
              <div className="space-y-3 rounded-xl border border-border/80 bg-card p-4 shadow-md relative z-0" role="status">
                <p className="text-sm font-medium text-foreground">No slots on this day</p>
                {!nextAfterNoSlotsLoading && nextAfterNoSlots?.start && (
                  <>
                    <p className="text-base font-semibold text-foreground">
                      Next available:{' '}
                      {formatNextAvailablePhrase(
                        nextAfterNoSlots.start,
                        appointmentCalendarDayYmd(nextAfterNoSlots.start, DISPLAY_TIMEZONE),
                        booking.doctorTodayYmd,
                        DISPLAY_TIMEZONE
                      )}
                    </p>
                    <Button
                      type="button"
                      variant="secondary"
                      className="h-11 w-full rounded-xl"
                      onClick={() => {
                        const y = appointmentCalendarDayYmd(
                          nextAfterNoSlots.start,
                          DISPLAY_TIMEZONE
                        );
                        booking.setBookDate(y);
                      }}
                    >
                      {(() => {
                        const h = relativeCalendarDayHeadingInZone(
                          nextAfterNoSlots.start,
                          DISPLAY_TIMEZONE
                        );
                        if (h === 'Tomorrow') return 'View tomorrow’s slots';
                        if (h === 'Today') return 'View today’s slots';
                        return `View slots — ${h}`;
                      })()}
                    </Button>
                  </>
                )}
                {!nextAfterNoSlotsLoading && !nextAfterNoSlots?.start && (
                  <p className="text-sm text-muted-foreground">
                    Try another date or check back—openings are released as the schedule updates.
                  </p>
                )}
              </div>
            )}
          {!showSlotsSkeleton &&
            booking.bookDate &&
            patientId &&
            !booking.slotsLoading &&
            booking.slots.length > 0 && (
            <>
              <DoctorSlotPicker
                slots={booking.slots}
                bookDate={booking.bookDate}
                doctorTodayYmd={booking.doctorTodayYmd}
                selectedSlotStart={booking.selectedSlotStart}
                onSelect={booking.setSelectedSlotStart}
                disabled={booking.submitting}
                nextAvailableKey={booking.nextAvailableKey}
              />
              {booking.selectedSlotStart && isSlotInstantInTheFuture(booking.selectedSlotStart) ? (
                <p className="rounded-xl border border-emerald-500/25 bg-emerald-500/[0.06] px-3 py-2.5 text-sm font-medium text-emerald-900 dark:text-emerald-100">
                  You&apos;ll be seen at{' '}
                  {formatSlotTimeWithZoneLabel(booking.selectedSlotStart, DISPLAY_TIMEZONE)}
                  <span className="font-normal opacity-90">
                    {' '}
                    (
                    {relativeCalendarDayHeadingInZone(
                      booking.selectedSlotStart,
                      DISPLAY_TIMEZONE
                    ).toLowerCase()}
                    ).
                  </span>
                </p>
              ) : null}
            </>
          )}
          </section>
        )}
      </div>

      <div
        className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 px-4 pt-3 shadow-[0_-4px_24px_rgba(0,0,0,0.08)] backdrop-blur-sm"
        style={{ paddingBottom: 'max(12px, env(safe-area-inset-bottom))' }}
      >
        <div className="mx-auto max-w-md">
          <Button
            type="button"
            className="h-12 w-full min-h-[48px] text-base font-semibold"
            disabled={!booking.stickyBookEnabled}
            onClick={() => booking.setConfirmOpen(true)}
          >
            Book Appointment
          </Button>
        </div>
      </div>

      {booking.confirmOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4"
          role="presentation"
          aria-busy={booking.submitting}
          onClick={() => {
            if (!booking.submitting) booking.closeConfirmOnly();
          }}
        >
          <div
            ref={booking.dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="book-appt-title-detail"
            className="w-full max-w-md rounded-t-xl border border-border bg-card text-foreground shadow-lg outline-none sm:rounded-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-border px-4 py-3">
              <h2 id="book-appt-title-detail" className="text-lg font-semibold">
                Confirm
              </h2>
            </div>
            <div className="space-y-4 px-4 py-4">
              <p className="text-sm">
                <span className="font-medium">{name}</span>
                <br />
                <span className="text-muted-foreground">
                  {booking.bookDate} ·{' '}
                  {booking.selectedSlotStart
                    ? formatSlotTimeWithZoneLabel(booking.selectedSlotStart, DISPLAY_TIMEZONE)
                    : '—'}
                </span>
              </p>
              <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
                <Button
                  type="button"
                  variant="outline"
                  className="min-h-[48px] w-full rounded-xl sm:w-auto"
                  onClick={booking.closeConfirmOnly}
                  disabled={booking.submitting}
                >
                  Back
                </Button>
                <Button
                  type="button"
                  className="min-h-[48px] w-full rounded-xl sm:w-auto"
                  onClick={() => void booking.confirmBooking()}
                  disabled={booking.submitting || !booking.bookingReady}
                >
                  {booking.submitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                      Booking…
                    </>
                  ) : (
                    'Confirm'
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
