/**
 * PatientDiscover — Practo-like exploration area.
 *
 * Separate from personal care flows.
 * Contains:
 * - Search
 * - Specialties grid
 * - Nearby doctors
 * - Clinics
 * - Availability
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Stethoscope,
  Heart,
  Brain,
  Eye,
  Bone,
  Baby,
  Activity,
  MapPin,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { publicDiscoveryApi, doctorsApi } from '../../services';
import type { PublicTenantDiscovery, Doctor } from '../../types';
import { formatDoctorName } from '../../utils';
import { Skeleton } from '@/components/ui/skeleton';
import { DoctorRowCard } from '../../components/patient/DoctorRowCard';
import { mockRatingFromId, mockReviewCountFromId } from '@/lib/patient/mockDoctorPresentation';
import { doctorAvailabilityPresentation } from '@/lib/patient/doctorAvailabilityPresentation';
import { doctorDiscoverySortScore } from '@/lib/patient/doctorDiscoveryRanking';

// ── Specialties ──────────────────────────────────────────────────────────────

interface Specialty {
  key: string;
  label: string;
  icon: React.ElementType;
  color: string;
}

const specialties: Specialty[] = [
  { key: 'general', label: 'General Physician', icon: Stethoscope, color: 'bg-blue-100 text-blue-600' },
  { key: 'cardiology', label: 'Cardiology', icon: Heart, color: 'bg-red-100 text-red-600' },
  { key: 'neurology', label: 'Neurology', icon: Brain, color: 'bg-purple-100 text-purple-600' },
  { key: 'ophthalmology', label: 'Ophthalmology', icon: Eye, color: 'bg-teal-100 text-teal-600' },
  { key: 'orthopedics', label: 'Orthopedics', icon: Bone, color: 'bg-amber-100 text-amber-600' },
  { key: 'pediatrics', label: 'Pediatrics', icon: Baby, color: 'bg-pink-100 text-pink-600' },
  { key: 'dermatology', label: 'Dermatology', icon: Activity, color: 'bg-green-100 text-green-600' },
  { key: 'ent', label: 'ENT', icon: Stethoscope, color: 'bg-indigo-100 text-indigo-600' },
];

// ── Skeleton ─────────────────────────────────────────────────────────────────

function DiscoverSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <Skeleton className="h-12 w-full rounded-xl" />
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-2xl" />
        ))}
      </div>
      <Skeleton className="h-6 w-32" />
      <Skeleton className="h-28 rounded-2xl" />
      <Skeleton className="h-28 rounded-2xl" />
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export function PatientDiscover() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [tenants, setTenants] = useState<PublicTenantDiscovery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tList, docList] = await Promise.all([
        publicDiscoveryApi.listTenants(),
        doctorsApi.getAll({ only_verified: true, limit: 50, include_availability_hint: true }),
      ]);
      setTenants(tList);
      setDoctors(docList);
    } catch {
      setError('Unable to load discovery data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter doctors by search
  const filteredDoctors = useMemo(() => {
    if (!searchQuery.trim()) return doctors;
    const q = searchQuery.toLowerCase();
    return doctors.filter((d) => {
      const name = (d.name || '').toLowerCase();
      const spec = (d.specialization || d.specialty || '').toLowerCase();
      return name.includes(q) || spec.includes(q);
    });
  }, [doctors, searchQuery]);

  // Rank doctors for display
  const rankedDoctors = useMemo(() => {
    return [...filteredDoctors].sort((a, b) => doctorDiscoverySortScore(b) - doctorDiscoverySortScore(a));
  }, [filteredDoctors]);

  // Top 5 for quick display
  const topDoctors = useMemo(() => rankedDoctors.slice(0, 5), [rankedDoctors]);

  if (error) {
    return (
      <div className="space-y-4 pb-24">
        <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 p-8 text-center">
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" size="sm" onClick={loadData} className="mt-4 rounded-xl">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-24">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
          Discover
        </h1>
        <p className="text-sm text-muted-foreground">
          Find doctors and clinics near you
        </p>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search doctors, specialties, clinics…"
          className="h-12 w-full rounded-2xl border-border/80 pl-11 text-base shadow-sm transition-shadow focus:shadow-md"
          aria-label="Search doctors and clinics"
        />
      </div>

      {loading ? (
        <DiscoverSkeleton />
      ) : (
        <>
          {/* Specialties Grid */}
          <section className="space-y-3">
            <h2 className="text-base font-semibold text-foreground">Browse by Specialty</h2>
            <div className="grid grid-cols-4 gap-3">
              {specialties.map(({ key, label, icon: Icon, color }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    setSearchQuery(label);
                  }}
                  className="flex flex-col items-center gap-1.5 rounded-2xl border border-border/60 bg-card p-3 shadow-sm transition hover:shadow-md active:scale-95 touch-manipulation"
                >
                  <div className={cn('flex h-10 w-10 items-center justify-center rounded-xl', color)}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="text-[10px] font-medium text-foreground text-center leading-tight">
                    {label}
                  </span>
                </button>
              ))}
            </div>
          </section>

          {/* Nearby Clinics */}
          {tenants.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-base font-semibold text-foreground">Nearby Clinics</h2>
              <div className="flex gap-3 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {tenants.slice(0, 6).map((tenant) => (
                  <button
                    key={tenant.id}
                    type="button"
                    onClick={() => navigate(`/patient/discover/clinic/${tenant.id}`, { state: { tenantName: tenant.name } })}
                    className="w-44 shrink-0 rounded-2xl border border-border/80 bg-card p-4 text-left shadow-sm transition hover:shadow-md"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                      <MapPin className="h-5 w-5 text-primary" />
                    </div>
                    <p className="mt-2 text-sm font-medium text-foreground truncate">{tenant.name}</p>
                    <p className="text-xs text-muted-foreground">{tenant.organization_label}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{tenant.doctor_count} doctor{tenant.doctor_count !== 1 ? 's' : ''}</p>
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Top Doctors */}
          {topDoctors.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-base font-semibold text-foreground">
                {searchQuery.trim() ? 'Search Results' : 'Top Doctors'}
              </h2>
              <div className="space-y-3">
                {topDoctors.map((d) => {
                  const spec = d.specialization || d.specialty || 'Specialist';
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
                      showVerifiedBadge={d.verification_status === 'approved'}
                      primaryLabel="Book Appointment"
                      onPrimary={() =>
                        navigate(`/patient/discover/doctor/${d.id}`, {
                          state: { focusBooking: true },
                        })
                      }
                      onCardClick={() =>
                        navigate(`/patient/discover/doctor/${d.id}`)
                      }
                    />
                  );
                })}
              </div>
            </section>
          )}

          {/* Empty state */}
          {!loading && doctors.length === 0 && (
            <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 p-8 text-center">
              <Stethoscope className="mx-auto h-10 w-10 text-muted-foreground/50" />
              <p className="mt-3 text-sm text-muted-foreground">
                No doctors available for discovery right now.
              </p>
            </div>
          )}

          {!loading && doctors.length > 0 && topDoctors.length === 0 && searchQuery.trim() && (
            <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 p-8 text-center">
              <Search className="mx-auto h-10 w-10 text-muted-foreground/50" />
              <p className="mt-3 text-sm text-muted-foreground">
                No doctors match "{searchQuery}". Try a different search term.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
