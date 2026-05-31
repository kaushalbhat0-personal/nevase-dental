/**
 * DoctorOperationsView — doctor's queue, waiting patients, quick actions.
 *
 * Features:
 * - Current queue with wait indicators
 * - Active consultation display
 * - Quick actions: call next, mark ready, finish encounter
 * - Queue slot cards with patient info
 * - Tablet-optimized: large touch targets, sticky action area
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { operationsApi } from '../../services/clinicOperations';
import { queueApi } from '../../services/clinicQueue';

import type { DoctorOperationsView as DoctorViewData, DoctorQueueSlot } from '../../services/clinicOperations';
import {
  Users,
  Stethoscope,
  CheckCircle2,
  SkipForward,
  Clock,
  UserCheck,
  ClipboardCheck,
  RefreshCw,
  ArrowRight,
} from 'lucide-react';
import toast from 'react-hot-toast';

interface DoctorOperationsViewProps {
  doctorId: string;
  /** Auto-refresh interval in ms. Default 15000 (15s). Set 0 to disable. */
  refreshInterval?: number;
}

function formatWaitTime(minutes: number): string {
  if (minutes < 1) return 'Now';
  if (minutes < 60) return `${minutes}m`;
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hrs}h ${mins}m`;
}

function getWaitColor(minutes: number): string {
  if (minutes > 30) return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-950';
  if (minutes > 15) return 'text-amber-600 bg-amber-100 dark:text-amber-400 dark:bg-amber-950';
  return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800';
}

export function DoctorOperationsView({
  doctorId,
  refreshInterval = 15000,
}: DoctorOperationsViewProps) {
  const navigate = useNavigate();
  const [view, setView] = useState<DoctorViewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchView = useCallback(async () => {
    try {
      const data = await operationsApi.getDoctorView(doctorId);
      setView(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [doctorId]);

  useEffect(() => {
    void fetchView();
    if (refreshInterval > 0) {
      const interval = setInterval(fetchView, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchView, refreshInterval]);

  const handleCallNext = useCallback(async () => {
    if (!view || view.queue.length === 0) return;
    const nextSlot = view.queue[0];
    setActionLoading('call_next');
    try {
      await queueApi.callEntry(nextSlot.queue_entry_id);
      toast.success(`Called ${nextSlot.patient_name}`);
      void fetchView();
    } catch {
      toast.error('Could not call next patient');
    } finally {
      setActionLoading(null);
    }
  }, [view, fetchView]);

  const handleMarkReady = useCallback(async (slot: DoctorQueueSlot) => {
    setActionLoading(`ready_${slot.queue_entry_id}`);
    try {
      await queueApi.callEntry(slot.queue_entry_id);
      toast.success(`${slot.patient_name} marked ready`);
      void fetchView();
    } catch {
      toast.error('Could not mark ready');
    } finally {
      setActionLoading(null);
    }
  }, [fetchView]);

  const handleFinishEncounter = useCallback(async (slot: DoctorQueueSlot) => {
    setActionLoading(`finish_${slot.queue_entry_id}`);
    try {
      await queueApi.completeEntry(slot.queue_entry_id);
      toast.success(`Encounter completed for ${slot.patient_name}`);
      void fetchView();
    } catch {
      toast.error('Could not complete encounter');
    } finally {
      setActionLoading(null);
    }
  }, [fetchView]);

  if (loading && !view) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Stethoscope className="h-4 w-4 text-primary" aria-hidden />
            Your Queue
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 rounded-lg bg-muted animate-pulse" aria-hidden />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!view) return null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3 sticky top-0 bg-card z-10">
        <div className="flex items-center gap-2">
          <Stethoscope className="h-4 w-4 text-primary" aria-hidden />
          <div>
            <CardTitle className="text-base">Your Queue</CardTitle>
            <p className="text-xs text-muted-foreground">
              {view.waiting_patients_count} waiting · {view.completed_today} completed today
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => { setLoading(true); void fetchView(); }}
          disabled={loading}
          className="h-9 min-h-[36px]"
        >
          <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} aria-hidden />
          <span className="sr-only">Refresh</span>
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Current Patient */}
        {view.current_patient && (
          <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                  <Stethoscope className="h-5 w-5 text-primary" aria-hidden />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    {view.current_patient.patient_name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Dr. {view.current_patient.doctor_name} · {view.current_patient.duration_minutes}m elapsed
                  </p>
                </div>
              </div>
              <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
                In Consultation
              </Badge>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="default"
            size="lg"
            onClick={handleCallNext}
            disabled={view.queue.length === 0 || actionLoading === 'call_next'}
            className="flex-1 min-h-[48px] text-sm font-semibold"
          >
            <SkipForward className="h-5 w-5 mr-2" aria-hidden />
            {actionLoading === 'call_next' ? 'Calling...' : 'Call Next'}
          </Button>
          {view.current_patient && (
            <Button
              variant="secondary"
              size="lg"
              onClick={() => {
                const slot = view.queue.find(
                  (s) => s.appointment_id === view.current_patient?.appointment_id
                );
                if (slot) handleFinishEncounter(slot);
              }}
              disabled={actionLoading?.startsWith('finish_')}
              className="flex-1 min-h-[48px] text-sm font-semibold"
            >
              <CheckCircle2 className="h-5 w-5 mr-2" aria-hidden />
              {actionLoading?.startsWith('finish_') ? 'Completing...' : 'Finish Encounter'}
            </Button>
          )}
        </div>

        {/* Queue List */}
        {view.queue.length === 0 && (
          <div className="text-center py-8">
            <Users className="h-8 w-8 text-muted-foreground mx-auto mb-2" aria-hidden />
            <p className="text-sm text-muted-foreground">No patients in queue</p>
          </div>
        )}

        {view.queue.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Queue ({view.queue.length})
            </h4>
            {view.queue.map((slot, idx) => (
              <div
                key={slot.queue_entry_id}
                className={cn(
                  'flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-accent/50 min-h-[64px]',
                  idx === 0 && 'border-primary/20 bg-primary/5'
                )}
              >
                {/* Token Number */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-sm font-bold">
                  {slot.token_number}
                </div>

                {/* Patient Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {slot.patient_name}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
                        getWaitColor(slot.wait_time_minutes)
                      )}
                    >
                      <Clock className="h-3 w-3" aria-hidden />
                      {formatWaitTime(slot.wait_time_minutes)}
                    </span>
                    {slot.has_vitals && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-600">
                        <ClipboardCheck className="h-3 w-3" aria-hidden />
                        Vitals done
                      </span>
                    )}
                    {slot.is_ready && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-blue-600">
                        <UserCheck className="h-3 w-3" aria-hidden />
                        Ready
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-1 shrink-0">
                  {!slot.is_ready && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleMarkReady(slot)}
                      disabled={actionLoading === `ready_${slot.queue_entry_id}`}
                      className="h-9 min-h-[36px] min-w-[36px]"
                      title="Mark ready"
                    >
                      <UserCheck className="h-4 w-4" aria-hidden />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate(`/doctor/patients/${slot.patient_id}`)}
                    className="h-9 min-h-[36px] min-w-[36px]"
                    title="View patient"
                  >
                    <ArrowRight className="h-4 w-4" aria-hidden />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
