import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, type Location } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { doctorsApi, publicDiscoveryApi } from '../../services';
import { useLinkedPatient } from '../../hooks';
import { useModalFocusTrap } from '../../hooks/useModalFocusTrap';
import type { Doctor, PublicTenantDiscovery } from '../../types';
import { formatDoctorName } from '../../utils';
import { ErrorState } from '../../components/common';
import { DoctorRowCard } from '../../components/patient/DoctorRowCard';
import { PatientSearchCombobox } from '../../components/patient/PatientSearchCombobox';
import { PATIENT_CLINIC_BOOKING_SCOPE_KEY } from '../../constants/patient';
import { mockRatingFromId, mockReviewCountFromId } from '@/lib/patient/mockDoctorPresentation';
import { doctorAvailabilityPresentation } from '@/lib/patient/doctorAvailabilityPresentation';
import { doctorDiscoverySortScore } from '@/lib/patient/doctorDiscoveryRanking';
import { Skeleton } from '@/components/ui/skeleton';
import { ymdNowInIana } from '@/utils/doctorSchedule';
import { DISPLAY_TIMEZONE } from '@/constants/time';

type PatientDoctorsLocationState = {
  preselectDoctorId?: string;
  tenantId?: string;
  browseAllDoctors?: boolean;
  initialSearch?: string;
};

function readResolvedPatientBookingTenantId(loc: Location): string | undefined {
  const s = (loc.state ?? null) as PatientDoctorsLocationState | null;
  if (s?.browseAllDoctors) {
    try {
      sessionStorage.removeItem(PATIENT_CLINIC_BOOKING_SCOPE_KEY);
    } catch {
      /* ignore */
    }
    return undefined;
  }
  if (s?.tenantId != null && s.tenantId !== '') {
    try {
      sessionStorage.setItem(PATIENT_CLINIC_BOOKING_SCOPE_KEY, s.tenantId);
    } catch {
      /* ignore */
    }
    return s.tenantId;
  }
  try {
    return sessionStorage.getItem(PATIENT_CLINIC_BOOKING_SCOPE_KEY) || undefined;
  } catch {
    return undefined;
  }
}

function DoctorsListSkeleton() {
  return (
    <div className="grid gap-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-[192px] w-full rounded-2xl" />
      ))}
    </div>
  );
}

function SearchBar({
  value,
  onChange,
  id,
}: {
  value: string;
  onChange: (next: string) => void;
  id?: string;
}) {
  return (
    <div className="relative min-w-0 w-full flex-1">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search name or specialization"
        className="h-11 w-full min-w-0 rounded-xl pl-9 transition-shadow"
        aria-label="Search doctors in list"
        id={id}
      />
    </div>
  );
}

export function PatientDoctors() {
  const navigate = useNavigate();
  const location = useLocation();
  const navState = (location.state ?? null) as PatientDoctorsLocationState | null;
  const preselectDoctorId = navState?.preselectDoctorId;
  const [listQuery, setListQuery] = useState(() => navState?.initialSearch?.trim() ?? '');
  const [onlyAvailableToday, setOnlyAvailableToday] = useState(false);
  const [resolvedTenantId, setResolvedTenantId] = useState<string | undefined>(() =>
    readResolvedPatientBookingTenantId(location)
  );
  const { patientId, loading: patientLoading, error: patientError, refresh: refreshPatient } = useLinkedPatient();
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [allDoctorsForSearch, setAllDoctorsForSearch] = useState<Doctor[]>([]);
  const [tenants, setTenants] = useState<PublicTenantDiscovery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const filtersPanelRef = useRef<HTMLDivElement>(null);
  useModalFocusTrap(filtersPanelRef, filtersOpen);

  const loadSearchIndex = useCallback(async () => {
    if (allDoctorsForSearch.length > 0) return;
    try {
      const [tList, global] = await Promise.all([
        publicDiscoveryApi.listTenants(),
        doctorsApi.getAll({ only_verified: true, limit: 100 }),
      ]);
      setTenants(tList);
      setAllDoctorsForSearch(global);
    } catch {
      setAllDoctorsForSearch((d) => d);
    }
  }, [allDoctorsForSearch.length]);

  useEffect(() => {
    setResolvedTenantId(readResolvedPatientBookingTenantId(location));
  }, [location.key, location.state]);

  useEffect(() => {
    const s = navState?.initialSearch?.trim();
    if (s) setListQuery(s);
  }, [location.key, navState?.initialSearch]);

  useEffect(() => {
    if (!preselectDoctorId || patientLoading) return;
    navigate(`/patient/doctor/${preselectDoctorId}`, { replace: true, state: location.state });
  }, [preselectDoctorId, patientLoading, navigate, location.state]);

  useEffect(() => {
    if (preselectDoctorId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        if (resolvedTenantId) {
          const briefs = await publicDiscoveryApi.listTenantDoctors(resolvedTenantId);
          const list: Doctor[] = briefs.map((b) => ({
            id: b.id,
            name: b.name,
            specialization: b.specialization,
            availability_status: b.availability_status,
            available_today: b.available_today,
            next_available_slot: b.next_available_slot ?? undefined,
            has_availability_windows: true,
            rating_average: b.rating_average,
            review_count: b.review_count,
            distance_km: b.distance_km,
            slots_today_count: b.slots_today_count,
            slots_tomorrow_count: b.slots_tomorrow_count,
            metrics_are_synthetic: b.metrics_are_synthetic,
            verification_status: 'approved',
          }));
          if (!cancelled) setDoctors(list);
        } else {
          const list = await doctorsApi.getAll({
            limit: 100,
            include_availability_hint: true,
            only_verified: true,
          });
          if (!cancelled) {
            setDoctors(list);
            setAllDoctorsForSearch((prev) => (prev.length > 0 ? prev : list));
          }
        }
        void loadSearchIndex();
      } catch {
        if (!cancelled) setError('Unable to load doctors.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [resolvedTenantId, preselectDoctorId, loadSearchIndex]);

  const searchFiltered = useMemo(() => {
    const q = listQuery.toLowerCase();
    if (!q) return doctors;
    return doctors.filter((d) => {
      const name = (d.name || '').toLowerCase();
      const spec = (d.specialization || d.specialty || '').toLowerCase();
      return name.includes(q) || spec.includes(q);
    });
  }, [doctors, listQuery]);

  const rankedAll = useMemo(() => {
    return [...searchFiltered].sort((a, b) => doctorDiscoverySortScore(b) - doctorDiscoverySortScore(a));
  }, [searchFiltered]);

  const todayOnlyRanked = useMemo(
    () =>
      rankedAll.filter(
        (d) => d.available_today === true || d.availability_status === 'available_today'
      ),
    [rankedAll]
  );

  const showingTodayFallback =
    onlyAvailableToday && searchFiltered.length > 0 && todayOnlyRanked.length === 0;

  const displayDoctors = useMemo(() => {
    if (!onlyAvailableToday) return rankedAll;
    if (showingTodayFallback) return rankedAll;
    return todayOnlyRanked;
  }, [onlyAvailableToday, rankedAll, showingTodayFallback, todayOnlyRanked]);

  useEffect(() => {
    if (preselectDoctorId || loading || patientLoading) return;
    const first = displayDoctors[0];
    if (!first?.id) return;
    const ymd = ymdNowInIana(DISPLAY_TIMEZONE);
    void doctorsApi.getSlots(String(first.id), ymd).catch(() => {});
  }, [preselectDoctorId, loading, patientLoading, displayDoctors]);

  const doctorProfileState = useMemo(
    () => (resolvedTenantId ? { tenantId: resolvedTenantId } : undefined),
    [resolvedTenantId]
  );

  if (error) {
    return <ErrorState title="Could not load doctors" description={error} />;
  }

  return (
    <div className="space-y-6">
      <div className="mt-2 mb-3">
        <h1 className="text-xl font-semibold tracking-tight">Doctors</h1>
        <p className="text-xs text-muted-foreground">
          {resolvedTenantId ? 'Choose a provider at this organization' : 'Search and open a profile to book in two taps'}
        </p>
      </div>

      {patientError && (
        <p className="text-sm text-destructive" role="alert">
          {patientError}{' '}
          <button type="button" className="font-medium underline" onClick={() => void refreshPatient()}>
            Retry
          </button>
        </p>
      )}

      {!preselectDoctorId && (loading || patientLoading) && <DoctorsListSkeleton />}

      {!preselectDoctorId && !loading && !patientLoading && (
        <>
          <div className="flex flex-col gap-2">
            <div className="md:hidden">
              <PatientSearchCombobox tenants={tenants} allDoctors={allDoctorsForSearch} className="w-full min-w-0" />
            </div>
            <div className="flex min-w-0 items-center gap-2">
              <SearchBar value={listQuery} onChange={setListQuery} id="patient-doctors-search" />
              <button
                type="button"
                className="shrink-0 touch-manipulation rounded-lg px-2 py-2 text-sm font-medium text-primary hover:underline"
                onClick={() => setFiltersOpen(true)}
              >
                Filters
                {onlyAvailableToday ? (
                  <span className="ml-1 inline-flex h-1.5 w-1.5 rounded-full bg-primary align-middle" aria-hidden />
                ) : null}
              </button>
            </div>
          </div>

          {filtersOpen ? (
            <div
              className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4"
              role="presentation"
              onClick={() => setFiltersOpen(false)}
            >
              <div
                ref={filtersPanelRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="patient-doctors-filters-title"
                className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-t-2xl border border-border bg-card p-4 shadow-xl outline-none sm:rounded-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                <h2 id="patient-doctors-filters-title" className="text-lg font-semibold tracking-tight">
                  Filters
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">Narrow the list without taking space on screen.</p>
                <div className="mt-4 flex flex-col gap-3">
                  <Button
                    type="button"
                    variant={onlyAvailableToday ? 'default' : 'outline'}
                    className="h-11 w-full justify-center rounded-xl text-sm font-semibold"
                    onClick={() => setOnlyAvailableToday((v) => !v)}
                  >
                    {onlyAvailableToday ? 'Showing: available today' : 'Only available today'}
                  </Button>
                  <Button
                    type="button"
                    className="h-11 w-full rounded-xl"
                    onClick={() => setFiltersOpen(false)}
                  >
                    Done
                  </Button>
                </div>
              </div>
            </div>
          ) : null}
          {showingTodayFallback ? (
            <div
              className="rounded-xl border border-amber-500/30 bg-amber-500/[0.07] px-3 py-2 text-sm text-amber-950 dark:text-amber-100"
              role="status"
            >
              <p className="font-medium">No doctors available today</p>
              <p className="mt-0.5 text-xs opacity-90">
                Showing next available doctors — turn off the filter in Filters to see the full list.
              </p>
            </div>
          ) : null}

          <div className="grid gap-6">
            {displayDoctors.map((d) => {
              const spec = d.specialization || d.specialty || 'Specialist';
              const noAvailability = d.has_availability_windows === false;
              const blocked = !patientId || noAvailability;
              const { label: availLabel, tone: availTone, subLabel: availSub } =
                doctorAvailabilityPresentation(d);
              return (
                <DoctorRowCard
                  key={String(d.id)}
                  name={formatDoctorName(d)}
                  subtitle={spec}
                  rating={d.rating_average ?? mockRatingFromId(String(d.id))}
                  reviewCount={d.review_count ?? mockReviewCountFromId(String(d.id))}
                  distanceKm={d.distance_km}
                  metricsAreSynthetic={d.metrics_are_synthetic !== false}
                  availabilityLabel={availLabel}
                  availabilitySubLabel={availSub}
                  availabilityTone={availTone}
                  showVerifiedBadge={
                    resolvedTenantId ? true : (d.verification_status ?? null) === 'approved'
                  }
                  primaryLabel="Book Appointment"
                  onPrimary={
                    blocked
                      ? undefined
                      : () =>
                          navigate(`/patient/doctor/${d.id}`, {
                            state: { ...(doctorProfileState ?? {}), focusBooking: true },
                          })
                  }
                  onCardClick={
                    blocked
                      ? undefined
                      : () => navigate(`/patient/doctor/${d.id}`, { state: doctorProfileState })
                  }
                  className={cn(blocked && 'opacity-60')}
                />
              );
            })}
          </div>
        </>
      )}

      {!preselectDoctorId && !loading && !patientLoading && doctors.length === 0 && (
        <p className="text-sm text-muted-foreground" role="status">
          No doctors available.
        </p>
      )}

      {!preselectDoctorId &&
        !loading &&
        !patientLoading &&
        doctors.length > 0 &&
        displayDoctors.length === 0 && (
        <p className="text-sm text-muted-foreground" role="status">
          No matches for that search.
        </p>
      )}
    </div>
  );
}
