import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import axios from 'axios';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { usePatients, useModalFocusTrap } from '../../hooks';
import { useAuth } from '../../hooks/useAuth';
import { useAppMode } from '../../contexts/AppModeContext';
import { useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import { getActiveTenantId } from '../../utils/tenantIdForRequest';
import { ErrorState, EmptyState } from '../../components/common';
import { patientsApi } from '../../services';
import { UserPlus } from 'lucide-react';

export function DoctorPatientsPage() {
  const { user } = useAuth();
  const { resolvedMode } = useAppMode();
  const { isIndependent, isReadOnly, selfDoctor } = useDoctorWorkspace();
  const { patients, loading, error, refetch } = usePatients();
  const location = useLocation();
  const navigate = useNavigate();
  const [addOpen, setAddOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ name: '', age: '', gender: '', phone: '' });
  const dialogRef = useRef<HTMLDivElement>(null);
  const openedFromStateRef = useRef(false);

  useModalFocusTrap(dialogRef, addOpen);

  const closeAdd = useCallback(() => {
    setAddOpen(false);
    setForm({ name: '', age: '', gender: '', phone: '' });
    if (location.state && typeof location.state === 'object' && 'openAddPatient' in location.state) {
      navigate({ pathname: location.pathname, search: location.search, hash: location.hash }, { replace: true, state: {} });
    }
  }, [location.hash, location.pathname, location.search, location.state, navigate]);

  useEffect(() => {
    const st = location.state as { openAddPatient?: boolean } | null;
    if (st?.openAddPatient && isIndependent && !openedFromStateRef.current) {
      openedFromStateRef.current = true;
      setAddOpen(true);
    }
  }, [location.state, isIndependent]);

  const submitAdd = async () => {
    const name = form.name.trim();
    const age = parseInt(form.age, 10);
    if (!name) {
      toast.error('Name is required');
      return;
    }
    if (Number.isNaN(age) || age < 0) {
      toast.error('Enter a valid age');
      return;
    }
    if (!form.gender.trim()) {
      toast.error('Gender is required');
      return;
    }
    if (!form.phone.trim()) {
      toast.error('Phone is required');
      return;
    }
    setSubmitting(true);
    try {
      await patientsApi.create({
        name,
        age,
        gender: form.gender.trim(),
        phone: form.phone.trim(),
      });
      toast.success('Patient created');
      closeAdd();
      void refetch();
    } catch (e) {
      const detail =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not create patient')
          : 'Could not create patient';
      toast.error(detail, { duration: 5000 });
    } finally {
      setSubmitting(false);
    }
  };

  if (error) {
    return (
      <ErrorState
        title="Could not load patients"
        description="Patients linked to you through care or appointments."
        error={error}
        onRetry={refetch}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Patients</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isReadOnly
              ? 'Patients you are scheduled with or who appear in your assigned care (read only).'
              : 'Patients you have seen or are scheduled with.'}
          </p>
        </div>
        {isIndependent && (
          <Button type="button" size="sm" className="gap-2" onClick={() => setAddOpen(true)}>
            <UserPlus className="h-4 w-4" aria-hidden />
            Add patient
          </Button>
        )}
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {!loading && patients.length === 0 && (
        <EmptyState
          title="No patients found"
          description={`scope: ${resolvedMode} · tenant: ${getActiveTenantId() ?? 'none'} · doctor: ${user?.doctor_id ?? (selfDoctor?.id != null ? String(selfDoctor.id) : 'none')}. Book a visit or add a patient when your practice allows it.`}
        />
      )}

      {!loading && patients.length > 0 && (
        <div className="grid gap-3">
          {patients.map((p) => (
            <Link key={String(p.id)} to={`/doctor/patients/${p.id}`} className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <Card className="transition-all hover:shadow-lg hover:bg-muted/40">
                <CardContent className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium text-foreground">{p.name || 'Patient'}</p>
                    <p className="text-xs text-muted-foreground">
                      {[p.age != null ? `${p.age} yrs` : null, p.gender, p.phone].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {addOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="presentation"
          onClick={() => !submitting && closeAdd()}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-patient-title"
            className="w-full max-w-md rounded-xl border border-border bg-card text-foreground shadow-lg outline-none p-0"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-border px-4 py-3">
              <h2 id="add-patient-title" className="text-lg font-semibold">
                Add patient
              </h2>
              <p className="text-sm text-muted-foreground mt-0.5">Creates a record for your practice.</p>
            </div>
            <div className="space-y-3 px-4 py-4">
              <div>
                <label htmlFor="p-name" className="text-xs font-medium text-muted-foreground">
                  Full name
                </label>
                <Input
                  id="p-name"
                  className="mt-1"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  disabled={submitting}
                  autoComplete="name"
                />
              </div>
              <div>
                <label htmlFor="p-age" className="text-xs font-medium text-muted-foreground">
                  Age
                </label>
                <Input
                  id="p-age"
                  type="number"
                  min={0}
                  className="mt-1"
                  value={form.age}
                  onChange={(e) => setForm((f) => ({ ...f, age: e.target.value }))}
                  disabled={submitting}
                />
              </div>
              <div>
                <label htmlFor="p-gender" className="text-xs font-medium text-muted-foreground">
                  Gender
                </label>
                <Input
                  id="p-gender"
                  className="mt-1"
                  value={form.gender}
                  onChange={(e) => setForm((f) => ({ ...f, gender: e.target.value }))}
                  disabled={submitting}
                />
              </div>
              <div>
                <label htmlFor="p-phone" className="text-xs font-medium text-muted-foreground">
                  Phone
                </label>
                <Input
                  id="p-phone"
                  className="mt-1"
                  value={form.phone}
                  onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                  disabled={submitting}
                  autoComplete="tel"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-border px-4 py-3">
              <Button type="button" variant="outline" onClick={closeAdd} disabled={submitting}>
                Cancel
              </Button>
              <Button type="button" onClick={() => void submitAdd()} disabled={submitting}>
                {submitting ? 'Saving…' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
