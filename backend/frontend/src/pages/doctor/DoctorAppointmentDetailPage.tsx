import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Calendar, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button, buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { appointmentsApi, billingApi } from '../../services';
import { ErrorState } from '../../components/common';
import { DISPLAY_TIMEZONE } from '../../constants/time';
import { formatAppointmentDateTimeWithZoneLabel } from '../../utils/doctorSchedule';
import { useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import { useActiveWorkspace } from '../../workspace/useActiveWorkspace';
import { useAuth } from '../../hooks/useAuth';
import type { Appointment, Bill } from '../../types';


function statusVariant(
  s: Appointment['status']
): 'default' | 'secondary' | 'outline' | 'destructive' {
  if (s === 'completed') return 'secondary';
  if (s === 'cancelled') return 'destructive';
  if (s === 'scheduled' || s === 'pending') return 'default';
  return 'outline';
}

export function DoctorAppointmentDetailPage() {
  const { appointmentId } = useParams<{ appointmentId: string }>();
  const navigate = useNavigate();
  const { isIndependent, isReadOnly } = useDoctorWorkspace();
  const { user } = useAuth();
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const { isClinician, hasClinicianCapability } = useActiveWorkspace(user, token);
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [linkedBill, setLinkedBill] = useState<Bill | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);


  useEffect(() => {
    if (!appointmentId) {
      setError('Missing appointment');
      setLoading(false);
      return;
    }
    let cancelled = false;
    setError(null);
    setLoading(true);
    void (async () => {
      try {
        const a = await appointmentsApi.getById(appointmentId);
        if (cancelled) return;
        setAppointment(a);
        if (a.id) {
          const forAppt = await billingApi.getAll({ appointment_id: String(a.id), limit: 5 });
          if (!cancelled && forAppt.length > 0) {
            setLinkedBill(forAppt[0] ?? null);
          } else {
            setLinkedBill(null);
          }
        }
      } catch {
        if (!cancelled) setError('Could not load this visit.');
        setAppointment(null);
        setLinkedBill(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [appointmentId, retryKey]);

  // Clinical actions require: clinician capability (doctor role, normalized doctor role,
  // or linked Doctor record) + write access + scheduled status.
  // Workspace context does NOT block clinical actions — a tenant doctor in the Finance
  // workspace can still start encounters because clinician capability exists.
  const canStartEncounter =
    hasClinicianCapability && isIndependent && !isReadOnly && appointment?.status === 'scheduled';

  const handleEncounterNavigation = useCallback(() => {
    if (!appointmentId) return;
    navigate(`/doctor/appointments/${appointmentId}`);
  }, [appointmentId, navigate]);


  if (error && !loading) {
    return (
      <div className="space-y-4">
        <BackBar />
        <ErrorState
          title="Visit not found"
          description="It may have been removed or you may not have access."
          error={error}
          onRetry={() => setRetryKey((k) => k + 1)}
        />
      </div>
    );
  }

  if (loading || !appointment) {
    return (
      <div className="space-y-4">
        <BackBar />
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  const pid = appointment.patient_id != null ? String(appointment.patient_id) : '';

  const encounterActionLabel =
    appointment.status === 'completed'
      ? 'View Encounter'
      : 'Start Encounter';

  return (
    <div className="space-y-6" id={appointmentId ? `appt-${appointmentId}` : undefined}>
      <BackBar />
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Visit</h1>
        <p className="text-sm text-muted-foreground mt-1">Appointment details</p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center gap-2 justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" aria-hidden />
              {formatAppointmentDateTimeWithZoneLabel(
                appointment.appointment_time || appointment.scheduled_at || '',
                DISPLAY_TIMEZONE
              )}
            </CardTitle>
            <Badge variant={statusVariant(appointment.status)} className="capitalize">
              {appointment.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          {pid && (
            <p>
              <span className="text-muted-foreground">Patient: </span>
              <Link to={`/doctor/patients/${pid}`} className="text-primary font-medium hover:underline">
                Open patient
              </Link>
            </p>
          )}
          {linkedBill && (
            <p>
              <span className="text-muted-foreground">Bill: </span>
              <Link
                to={`/doctor/bills/${linkedBill.id}`}
                className="text-primary font-medium hover:underline"
              >
                {linkedBill.currency} {Number(linkedBill.amount).toFixed(2)} ({linkedBill.status})
              </Link>
            </p>
          )}
          {/*
            Clinical encounter documentation hierarchy:
            1. Diagnosis (most important clinical output)
            2. Treatment summary (what was done)
            3. Clinical notes (detailed observations)
            Billing information is shown secondary.
          */}
          {appointment.diagnosis && (
            <p className="text-muted-foreground border-t border-border pt-2 mt-2">
              <span className="font-medium text-foreground">Diagnosis: </span>
              {appointment.diagnosis}
            </p>
          )}
          {appointment.treatment_summary && (
            <p className="text-muted-foreground border-t border-border pt-2 mt-2">
              <span className="font-medium text-foreground">Treatment: </span>
              {appointment.treatment_summary}
            </p>
          )}
          {appointment.clinical_notes && (
            <p className="text-muted-foreground border-t border-border pt-2 mt-2">
              <span className="font-medium text-foreground">Clinical notes: </span>
              {appointment.clinical_notes}
            </p>
          )}
          {/* DEPRECATED: completion_notes preserved for backward compatibility */}
          {appointment.completion_notes && (
            <p className="text-muted-foreground border-t border-border pt-2 mt-2">
              <span className="font-medium text-foreground">Notes (legacy): </span>
              {appointment.completion_notes}
            </p>
          )}
          {appointment.status === 'completed' &&
            appointment.inventory_usages &&
            appointment.inventory_usages.length > 0 && (
              <div className="border-t border-border pt-2 mt-2 space-y-1.5">
                <p className="font-medium text-foreground text-sm">Medicines given</p>
                <ul className="list-disc pl-5 space-y-0.5">
                  {appointment.inventory_usages.map((u) => (
                    <li key={u.item_id}>
                      {u.item_name || 'Item'}{' '}
                      <span className="text-muted-foreground">× {u.quantity}</span>
                    </li>
                  ))}
                </ul>
                {appointment.inventory_materials_selling_total != null &&
                  Number(appointment.inventory_materials_selling_total) > 0 && (
                    <p className="text-sm text-muted-foreground pt-0.5">
                      Total medicines (selling):{' '}
                      <span className="font-medium text-foreground tabular-nums">
                        ₹{Number(appointment.inventory_materials_selling_total).toFixed(2)}
                      </span>
                    </p>
                  )}
              </div>
            )}
          {canStartEncounter && (
            <div className="pt-2">
              <Button
                type="button"
                size="sm"
                onClick={handleEncounterNavigation}
              >
                {encounterActionLabel}
              </Button>
            </div>
          )}
          {/* Workspace context banner — shown when user has clinician capability but wrong workspace */}
          {!isClinician && hasClinicianCapability && appointment?.status === 'scheduled' && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 mt-3">
              <div className="flex items-center gap-2">
                <ArrowRight className="h-4 w-4 shrink-0" />
                <span>
                  Switch to{' '}
                  <span className="font-medium">Clinician workspace</span> to start this encounter.
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>

  );
}

function BackBar() {
  return (
    <div>
      <Link
        to="/doctor/appointments"
        className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), '-ml-2 gap-1.5 h-8 text-muted-foreground')}
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        Appointments
      </Link>
    </div>
  );
}
