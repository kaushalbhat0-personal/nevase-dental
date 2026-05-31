import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, ChevronRight, Search, Stethoscope, Tag } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { doctorsApi } from '../../services';
import type { Doctor, PublicTenantDiscovery } from '../../types';
import { formatDoctorName } from '../../utils';
import { POPULAR_SPECIALIZATIONS } from '../../constants/patient';

type Result =
  | { type: 'doctor'; id: string; label: string; sub: string }
  | { type: 'clinic'; id: string; label: string; sub: string }
  | { type: 'spec'; label: string };

type PatientSearchComboboxProps = {
  className?: string;
  inputClassName?: string;
  /** Preloaded for instant results on home. */
  tenants?: PublicTenantDiscovery[];
  allDoctors?: Doctor[];
};

const DEBOUNCE_MS = 200;

function typeLabel(t: PublicTenantDiscovery): string {
  if (t.organization_label) return t.organization_label;
  if (t.type === 'individual') return 'Individual practice';
  if (t.type === 'organization') return 'Organization';
  return t.type;
}

export function PatientSearchCombobox({
  className,
  inputClassName,
  tenants: tenantsProp = [],
  allDoctors: allDoctorsProp,
}: PatientSearchComboboxProps) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [doctors, setDoctors] = useState<Doctor[] | null>(allDoctorsProp ?? null);
  const [loading, setLoading] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setDoctors(allDoctorsProp ?? null);
  }, [allDoctorsProp]);

  const ensureDoctors = useCallback(async () => {
    if (doctors != null) return;
    setLoading(true);
    try {
      const list = await doctorsApi.getAll();
      setDoctors(list);
    } catch {
      setDoctors([]);
    } finally {
      setLoading(false);
    }
  }, [doctors]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const narrow = (q || '').trim().toLowerCase();

  const results = useMemo((): Result[] => {
    const out: Result[] = [];
    const dlist = doctors ?? [];
    if (narrow) {
      for (const d of dlist) {
        const name = (d.name || '').toLowerCase();
        const spec = (d.specialization || d.specialty || '').toLowerCase();
        if (name.includes(narrow) || spec.includes(narrow)) {
          out.push({
            type: 'doctor',
            id: String(d.id),
            label: formatDoctorName(d),
            sub: d.specialization || d.specialty || 'Specialist',
          });
        }
        if (out.length >= 6) break;
      }
      for (const t of tenantsProp) {
        if (out.length >= 10) break;
        if ((t.name || '').toLowerCase().includes(narrow)) {
          out.push({ type: 'clinic', id: t.id, label: t.name, sub: typeLabel(t) });
        }
      }
      for (const s of POPULAR_SPECIALIZATIONS) {
        if (s.toLowerCase().includes(narrow)) {
          out.push({ type: 'spec', label: s });
        }
        if (out.length >= 12) break;
      }
    } else {
      POPULAR_SPECIALIZATIONS.slice(0, 4).forEach((label) => out.push({ type: 'spec', label }));
    }
    return out;
  }, [narrow, doctors, tenantsProp]);

  const onInputChange = (v: string) => {
    setQ(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (v.trim()) void ensureDoctors();
    }, DEBOUNCE_MS);
  };

  const goResult = (r: Result) => {
    setOpen(false);
    if (r.type === 'doctor') {
      navigate(`/patient/doctor/${r.id}`);
      return;
    }
    if (r.type === 'clinic') {
      navigate(`/patient/clinic/${r.id}`, { state: { tenantName: r.label } });
      return;
    }
    navigate('/patient/doctors', { state: { initialSearch: r.label, browseAllDoctors: true } });
  };

  return (
    <div ref={rootRef} className={cn('relative w-full', className)}>
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <Input
          value={q}
          onChange={(e) => onInputChange(e.target.value)}
          onFocus={() => {
            setOpen(true);
            void ensureDoctors();
          }}
          placeholder="Search doctors, clinics, specializations…"
          className={cn('h-10 rounded-xl border-border/80 bg-white pl-9 pr-3 shadow-sm transition-shadow', open && 'ring-2 ring-primary/20', inputClassName)}
          aria-label="Search care"
          autoComplete="off"
        />
      </div>
      {open && (
        <div
          className="absolute left-0 right-0 z-50 mt-1 max-h-[min(70vh,420px)] overflow-y-auto rounded-2xl border border-border/80 bg-white py-2 shadow-lg shadow-black/10 ring-1 ring-black/5 transition-opacity duration-200"
          role="listbox"
        >
          {loading && <p className="px-4 py-2 text-sm text-muted-foreground">Loading…</p>}
          {!loading && results.length === 0 && (
            <p className="px-4 py-3 text-sm text-muted-foreground">
              {narrow ? 'No quick matches. Try the doctors list.' : 'Type to find doctors and clinics.'}
            </p>
          )}
          {!loading &&
            results.map((r, i) => (
              <button
                key={`${r.type}-${'id' in r ? r.id : r.label}-${i}`}
                type="button"
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors hover:bg-primary/5"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => goResult(r)}
              >
                {r.type === 'doctor' && <Stethoscope className="h-4 w-4 shrink-0 text-primary" aria-hidden />}
                {r.type === 'clinic' && <Building2 className="h-4 w-4 shrink-0 text-primary" aria-hidden />}
                {r.type === 'spec' && <Tag className="h-4 w-4 shrink-0 text-[#22c55e]" aria-hidden />}
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium text-foreground">{r.label}</span>
                  {r.type !== 'spec' && <span className="block truncate text-xs text-muted-foreground">{r.sub}</span>}
                </span>
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
