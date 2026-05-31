import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { buttonVariants } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { publicDiscoveryApi } from '../../services';
import type { PublicTenantDoctorBrief } from '../../types';
import { ErrorState } from '../../components/common';
import { cn } from '@/lib/utils';
import { DoctorRowCard } from '../../components/patient/DoctorRowCard';
import { mockRatingFromId, mockReviewCountFromId } from '@/lib/patient/mockDoctorPresentation';
import { doctorAvailabilityPresentation } from '@/lib/patient/doctorAvailabilityPresentation';
import type { Doctor } from '@/types';

export function PatientClinicDoctors() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const tenantName = (location.state as { tenantName?: string } | null)?.tenantName;

  const [doctors, setDoctors] = useState<PublicTenantDoctorBrief[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tenantId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const list = await publicDiscoveryApi.listTenantDoctors(tenantId);
        if (!cancelled) setDoctors(list);
      } catch {
        if (!cancelled) setError('Could not load providers for this organization.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tenantId]);

  if (!tenantId) {
    return <ErrorState title="Missing clinic" description="Go back to home and pick an organization." />;
  }

  if (error) {
    return <ErrorState title="Something went wrong" description={error} />;
  }

  const title = tenantName || 'Clinic';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link
          to="/patient/home"
          aria-label="Back to home"
          className={cn(buttonVariants({ variant: 'ghost', size: 'icon' }), 'shrink-0 -ml-2 rounded-xl')}
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold tracking-tight">{title}</h1>
          <p className="text-xs text-muted-foreground">Choose a doctor to book</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Doctors</CardTitle>
          <CardDescription>All active providers at this location</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <ul className="space-y-6" aria-hidden>
              {Array.from({ length: 4 }).map((_, i) => (
                <li key={i}>
                  <Skeleton className="h-[192px] w-full rounded-2xl" />
                </li>
              ))}
            </ul>
          ) : doctors.length === 0 ? (
            <p className="text-sm text-muted-foreground">No doctors listed yet.</p>
          ) : (
            <ul className="space-y-6">
              {doctors.map((d) => {
                const asDoc: Doctor = {
                  id: d.id,
                  name: d.name,
                  specialization: d.specialization,
                  availability_status: d.availability_status,
                  available_today: d.available_today,
                  next_available_slot: d.next_available_slot ?? undefined,
                  has_availability_windows: true,
                };
                const { label: availLabel, tone: availTone, subLabel: availSub } =
                  doctorAvailabilityPresentation(asDoc);
                return (
                <li key={d.id}>
                  <DoctorRowCard
                    name={d.name}
                    subtitle={d.specialization}
                    rating={d.rating_average ?? mockRatingFromId(d.id)}
                    reviewCount={d.review_count ?? mockReviewCountFromId(d.id)}
                    distanceKm={d.distance_km}
                    metricsAreSynthetic={d.metrics_are_synthetic !== false}
                    showVerifiedBadge
                    availabilityLabel={availLabel}
                    availabilitySubLabel={availSub}
                    availabilityTone={availTone}
                    primaryLabel="Book Appointment"
                    onPrimary={() =>
                      navigate(`/patient/doctor/${d.id}`, { state: { tenantId, focusBooking: true } })
                    }
                    onCardClick={() => navigate(`/patient/doctor/${d.id}`, { state: { tenantId } })}
                  />
                </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
