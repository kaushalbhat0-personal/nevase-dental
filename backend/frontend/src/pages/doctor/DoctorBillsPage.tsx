import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import axios from 'axios';
import { Receipt, Plus } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAppointments, useBilling, useModalFocusTrap } from '../../hooks';
import { useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import { ErrorState, EmptyState } from '../../components/common';
import { billingApi } from '../../services';
import type { Appointment, Bill } from '../../types';
import { DISPLAY_TIMEZONE } from '../../constants/time';
import { formatAppointmentDateTimeWithZoneLabel } from '../../utils/doctorSchedule';

function patientName(map: Map<string, string>, id: string): string {
  return map.get(id) || 'Patient';
}

function billCoversAppointment(bills: Bill[], appt: Appointment): boolean {
  const aid = String(appt.id);
  return bills.some((b) => b.appointment_id && String(b.appointment_id) === aid);
}

export function DoctorBillsPage() {
  const { isIndependent, selfDoctor, isReadOnly } = useDoctorWorkspace();
  const { bills, patients: billingPatients, loading, error, refetch } = useBilling();
  const { appointments, patients, loading: aptLoading, refetch: refetchApt } = useAppointments({
    status: 'completed',
  });
  const location = useLocation();
  const navigate = useNavigate();

  const patientNameById = useMemo(() => {
    const m = new Map<string, string>();
    for (const p of billingPatients) {
      m.set(String(p.id), p.name || 'Patient');
    }
    for (const p of patients) {
      if (!m.has(String(p.id))) m.set(String(p.id), p.name || 'Patient');
    }
    return m;
  }, [billingPatients, patients]);

  const bookableAppointments = useMemo(() => {
    const selfId = selfDoctor != null ? String(selfDoctor.id) : '';
    if (!selfId) return [];
    return appointments.filter((a) => {
      if (String(a.doctor_id) !== selfId) return false;
      if (a.status === 'cancelled') return false;
      if (a.status !== 'completed') return false;
      if (billCoversAppointment(bills, a)) return false;
      return true;
    });
  }, [appointments, selfDoctor, bills]);

  const [createOpen, setCreateOpen] = useState(false);
  const [prefillBillPatientId, setPrefillBillPatientId] = useState<string | null>(null);
  const [appointmentId, setAppointmentId] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const createOpenedRef = useRef(false);

  useModalFocusTrap(dialogRef, createOpen);

  const openCreateBillModal = useCallback(() => {
    if (!bookableAppointments.some((a) => Boolean(a.patient_id))) {
      toast.error('Cannot bill: patient missing');
      return;
    }
    setPrefillBillPatientId(null);
    setCreateOpen(true);
  }, [bookableAppointments]);

  const closeCreate = useCallback(() => {
    setCreateOpen(false);
    setPrefillBillPatientId(null);
    setAppointmentId('');
    setAmount('');
    setDescription('');
    if (
      location.state &&
      typeof location.state === 'object' &&
      ('openCreateBill' in location.state || 'billPatientId' in location.state)
    ) {
      navigate(
        { pathname: location.pathname, search: location.search, hash: location.hash },
        { replace: true, state: {} }
      );
    }
  }, [location.hash, location.pathname, location.search, location.state, navigate]);

  useEffect(() => {
    const st = location.state as { openCreateBill?: boolean; billPatientId?: string } | null;
    if (st?.billPatientId) {
      setPrefillBillPatientId(String(st.billPatientId));
    }
    if (!st?.openCreateBill || !isIndependent || createOpenedRef.current) return;
    if (aptLoading) return;

    const billPid = st.billPatientId != null ? String(st.billPatientId) : null;
    const pool = billPid
      ? bookableAppointments.filter((a) => String(a.patient_id) === billPid)
      : bookableAppointments;

    if (pool.length > 0 && !pool.some((a) => Boolean(a.patient_id))) {
      toast.error('Cannot bill: patient missing');
      navigate(
        { pathname: location.pathname, search: location.search, hash: location.hash },
        { replace: true, state: {} }
      );
      return;
    }

    createOpenedRef.current = true;
    setCreateOpen(true);
  }, [
    location.state,
    location.pathname,
    location.search,
    location.hash,
    isIndependent,
    aptLoading,
    bookableAppointments,
    navigate,
  ]);

  const bookableForModal = useMemo(() => {
    if (!prefillBillPatientId) return bookableAppointments;
    return bookableAppointments.filter((a) => String(a.patient_id) === prefillBillPatientId);
  }, [bookableAppointments, prefillBillPatientId]);

  useEffect(() => {
    if (!createOpen) return;
    if (!prefillBillPatientId) return;
    const forPatient = bookableForModal;
    if (forPatient.length === 0) return;
    if (forPatient.some((a) => String(a.id) === appointmentId)) return;
    setAppointmentId(String(forPatient[0].id));
  }, [createOpen, prefillBillPatientId, bookableForModal, appointmentId]);

  const selectedAppt: Appointment | undefined = useMemo(
    () => bookableForModal.find((a) => String(a.id) === appointmentId),
    [bookableForModal, appointmentId]
  );

  const createBill = async () => {
    if (!selectedAppt || !appointmentId) {
      toast.error('Choose a visit to bill');
      return;
    }
    if (!selectedAppt.patient_id) {
      toast.error('Cannot bill: patient missing');
      return;
    }
    const n = parseFloat(amount);
    if (Number.isNaN(n) || n <= 0) {
      toast.error('Enter a valid amount');
      return;
    }
    const pid = String(selectedAppt.patient_id);
    setSubmitting(true);
    try {
      await billingApi.create({
        patient_id: pid,
        appointment_id: appointmentId,
        amount: n,
        currency: 'INR',
        description: description.trim() || undefined,
      });
      toast.success('Bill created');
      closeCreate();
      void refetch();
      void refetchApt();
    } catch (e) {
      const msg =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not create bill')
          : 'Could not create bill';
      toast.error(msg, { duration: 5000 });
    } finally {
      setSubmitting(false);
    }
  };

  if (error) {
    return <ErrorState title="Could not load bills" description="" error={error} onRetry={refetch} />;
  }

  const listLoading = loading || aptLoading;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Bills</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isReadOnly
              ? 'Bills for visits you are associated with (read only in this portal).'
              : 'Billing for your patients and visits.'}
          </p>
        </div>
        {isIndependent && bookableAppointments.length > 0 && (
          <Button
            type="button"
            size="sm"
            className="gap-2"
            onClick={() => {
              openCreateBillModal();
            }}
          >
            <Plus className="h-4 w-4" aria-hidden />
            Create bill
          </Button>
        )}
      </div>

      {isIndependent && selfDoctor && bookableAppointments.length === 0 && !listLoading && (
        <p className="text-sm text-muted-foreground rounded-lg border border-border px-3 py-2">
          Bill completed visits that do not have a charge yet. Visits you have already billed are not listed here.
        </p>
      )}

      {listLoading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {!listLoading && bills.length === 0 && (
        <EmptyState
          title="No bills"
          description="Bills tied to your appointments appear here."
          icon={Receipt}
        />
      )}

      {!listLoading && bills.length > 0 && (
        <div className="space-y-3">
          {bills.map((b) => (
            <Card key={b.id} id={b.id ? `bill-${b.id}` : undefined}>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 text-sm">
                <div className="min-w-0 flex-1">
                  <Link
                    to={`/doctor/bills/${b.id}`}
                    className="font-medium text-primary hover:underline block"
                  >
                    {b.currency} {Number(b.amount).toFixed(2)}
                  </Link>
                  <Link
                    to={`/doctor/patients/${b.patient_id}`}
                    className="text-sm text-muted-foreground hover:text-foreground hover:underline mt-0.5 block"
                  >
                    {patientName(patientNameById, String(b.patient_id))}
                  </Link>
                  {b.description && (
                    <p className="text-xs text-muted-foreground truncate max-w-md mt-1">{b.description}</p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs capitalize text-muted-foreground">{b.status}</p>
                  <Link
                    to={`/doctor/bills/${b.id}`}
                    className="text-xs font-medium text-primary hover:underline mt-1 inline-block"
                  >
                    Open
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {createOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="presentation"
          onClick={() => !submitting && closeCreate()}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-bill-title"
            className="w-full max-w-md rounded-xl border border-border bg-card text-foreground shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-border px-4 py-3">
              <h2 id="create-bill-title" className="text-lg font-semibold">
                New bill
              </h2>
              <p className="text-sm text-muted-foreground mt-0.5">Tie the charge to a completed visit you own.</p>
            </div>
            <div className="space-y-3 px-4 py-4">
              <div>
                <label htmlFor="bill-appt" className="text-xs font-medium text-muted-foreground">
                  Visit
                </label>
                <select
                  id="bill-appt"
                  className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground"
                  value={appointmentId}
                  onChange={(e) => setAppointmentId(e.target.value)}
                  disabled={submitting}
                >
                  <option value="">Select appointment</option>
                  {bookableForModal.map((a) => (
                    <option key={String(a.id)} value={String(a.id)}>
                      {formatAppointmentDateTimeWithZoneLabel(
                        a.appointment_time || a.scheduled_at || '',
                        DISPLAY_TIMEZONE
                      )}{' '}
                      — {patientName(patientNameById, String(a.patient_id))}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="bill-amt" className="text-xs font-medium text-muted-foreground">
                  Amount
                </label>
                <Input
                  id="bill-amt"
                  type="number"
                  min="0"
                  step="0.01"
                  className="mt-1"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  disabled={submitting}
                />
              </div>
              <div>
                <label htmlFor="bill-desc" className="text-xs font-medium text-muted-foreground">
                  Description (optional)
                </label>
                <Input
                  id="bill-desc"
                  className="mt-1"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={submitting}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-border px-4 py-3">
              <Button type="button" variant="outline" onClick={closeCreate} disabled={submitting}>
                Cancel
              </Button>
              <Button type="button" onClick={() => void createBill()} disabled={submitting}>
                {submitting ? 'Creating…' : 'Create bill'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
