import { useEffect, useState } from 'react';
import { publicDiscoveryApi } from '../../services/publicDiscovery';
import type { PublicTenantDoctorBrief, PublicTenantDiscovery } from '../../types';
import DoctorCard from '../../components/public/DoctorCard';

export default function DoctorsPage() {
  const [doctors, setDoctors] = useState<PublicTenantDoctorBrief[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchDoctors() {
      setLoading(true);
      setError(null);

      try {
        const tenants: PublicTenantDiscovery[] = await publicDiscoveryApi.listTenants();
        if (cancelled) return;

        if (tenants.length === 0) {
          setDoctors([]);
          setLoading(false);
          return;
        }

        const tenant = tenants[0];
        const result = await publicDiscoveryApi.listTenantDoctors(tenant.id);
        if (cancelled) return;

        setDoctors(result);
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load doctors');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchDoctors();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="bg-gradient-to-br from-sky-50 via-white to-white py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-sm font-semibold text-[#0EA5E9] tracking-widest uppercase mb-3">
            Our Team
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold text-[#0F172A]">
            Meet Our Specialists
          </h1>
          <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">
            Experienced dental professionals dedicated to your smile
          </p>
        </div>
      </section>

      {/* Doctor cards */}
      <section className="py-16 sm:py-24 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4">
          {loading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-2xl p-8 animate-pulse">
                  <div className="w-28 h-28 mx-auto mb-5 rounded-full bg-gray-200" />
                  <div className="h-5 w-32 mx-auto bg-gray-200 rounded" />
                  <div className="h-4 w-24 mx-auto mt-3 bg-gray-200 rounded-full" />
                  <div className="h-4 w-20 mx-auto mt-4 bg-gray-200 rounded" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="text-center py-16">
              <p className="text-red-500 mb-4">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-3 rounded-xl text-sm font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] transition-colors"
              >
                Retry
              </button>
            </div>
          ) : doctors.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-[#1E293B]/60 text-lg">No doctors listed yet. Check back soon!</p>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {doctors.map((doctor) => (
                <DoctorCard key={doctor.id} doctor={doctor} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 sm:py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Ready to Book?</h2>
          <p className="mt-4 text-lg text-[#1E293B]/60 max-w-xl mx-auto">
            Choose your preferred date and time — we'll confirm within minutes.
          </p>
          <div className="mt-8">
            <a
              href={`https://wa.me/918805606018?text=Hi%2C%20I%20want%20to%20book%20an%20appointment`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-base font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] shadow-lg shadow-[#0EA5E9]/25 transition-all hover:shadow-xl hover:scale-[1.02]"
            >
              Book Appointment
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
