import { useEffect, useState } from 'react';
import { Shield, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import { doctorsApi } from '../services';
import type { Doctor } from '../types';

export default function AdminDoctorVerificationsPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        const data = await doctorsApi.getAll({ limit: 100, include_availability_hint: false });
        setDoctors(data);
      } catch {
        setError('Failed to load doctors');
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  const statusIcon = (s: string | null | undefined) => {
    switch (s) {
      case 'approved': return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'rejected': return <XCircle className="w-5 h-5 text-red-500" />;
      case 'pending': return <Clock className="w-5 h-5 text-amber-500" />;
      default: return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Shield className="w-6 h-6 text-[#0EA5E9]" />
          <h1 className="text-2xl font-bold text-[#0F172A]">Doctor Verifications</h1>
        </div>
        <p className="text-[#1E293B]/60">Review and manage marketplace verification status for doctors</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-[#0EA5E9]" />
        </div>
      ) : error ? (
        <div className="text-center py-8 bg-white rounded-2xl border border-gray-100 shadow-sm">
          <p className="text-red-500 mb-4">{error}</p>
          <button onClick={() => window.location.reload()} className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] transition-colors">Retry</button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          {doctors.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-[#1E293B]/60">No doctors found</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {doctors.map((d) => (
                <div key={String(d.id)} className="flex items-center gap-4 p-5 hover:bg-[#F8FAFC] transition-colors">
                  <div className="w-10 h-10 rounded-full bg-[#0EA5E9]/10 flex items-center justify-center text-sm font-semibold text-[#0EA5E9]">
                    {d.name?.charAt(0) || '?'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-[#0F172A] truncate">{d.name}</p>
                    <p className="text-sm text-[#1E293B]/60 truncate">{d.specialization || d.specialty} &middot; {d.tenant_name || 'No clinic'}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {statusIcon(d.verification_status)}
                    <span className="text-sm capitalize text-[#1E293B]/70">{d.verification_status || 'draft'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
