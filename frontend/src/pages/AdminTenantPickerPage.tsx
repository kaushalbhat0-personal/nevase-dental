import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Loader2 } from 'lucide-react';
import { tenantsApi } from '../services';
import type { Tenant } from '../types';
import { setActiveTenantId, clearActiveTenantId } from '../utils/tenantIdForRequest';

export default function AdminTenantPickerPage() {
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    clearActiveTenantId();
    async function fetch() {
      try {
        const data = await tenantsApi.getAll();
        setTenants(data);
      } catch {
        setError('Failed to load organizations');
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  function selectTenant(t: Tenant) {
    setActiveTenantId(t.id);
    navigate('/admin/dashboard');
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#0EA5E9]/10 mb-4">
            <Building2 className="w-8 h-8 text-[#0EA5E9]" />
          </div>
          <h1 className="text-2xl font-bold text-[#0F172A]">Select Organization</h1>
          <p className="mt-2 text-[#1E293B]/60">Choose an organization to manage</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-[#0EA5E9]" />
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <p className="text-red-500 mb-4">{error}</p>
            <button onClick={() => window.location.reload()} className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] transition-colors">Retry</button>
          </div>
        ) : tenants.length === 0 ? (
          <div className="text-center py-8 bg-white rounded-2xl border border-gray-100 shadow-sm">
            <p className="text-[#1E293B]/60 mb-4">No organizations found</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tenants.map((t) => (
              <button
                key={t.id}
                onClick={() => selectTenant(t)}
                className="w-full text-left bg-white rounded-2xl p-5 border border-gray-100 shadow-sm hover:shadow-md hover:border-[#0EA5E9]/30 transition-all"
              >
                <p className="font-semibold text-[#0F172A]">{t.name}</p>
                <p className="text-sm text-[#1E293B]/60 mt-0.5 capitalize">{t.type}</p>
                {t.address && <p className="text-xs text-[#1E293B]/40 mt-1">{t.address}</p>}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
