/**
 * Patient Medicines Page — medication schedule management.
 *
 * Displays all medication schedules for the patient with adherence tracking.
 * This is a READ-ONLY view of prescription-derived schedules.
 * Patients CANNOT edit prescription data through this page.
 */

import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Pill,
  CheckCircle2,
  XCircle,
  Timer,
  Clock,
  ArrowLeft,
  Sparkles,
} from 'lucide-react';

import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { medicationScheduleApi, type MedicationScheduleRead, type TodayAdherenceSummary } from '../../services/medicationSchedule';
import { ErrorState } from '../../components/common';
import { Skeleton } from '@/components/ui/skeleton';

function MedicinesSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-24 rounded-2xl" />
      <Skeleton className="h-24 rounded-2xl" />
      <Skeleton className="h-24 rounded-2xl" />
    </div>
  );
}

export function PatientMedicines() {
  const [schedules, setSchedules] = useState<MedicationScheduleRead[]>([]);
  const [summary, setSummary] = useState<TodayAdherenceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [listRes, summaryData] = await Promise.all([
        medicationScheduleApi.listSchedules({ active_only: true, limit: 100 }),
        medicationScheduleApi.getAdherenceSummary(),
      ]);
      setSchedules(listRes.items);
      setSummary(summaryData);
    } catch {
      setError('Could not load your medications. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (error) {
    return (
      <div className="space-y-4">
        <ErrorState title="Medications unavailable" description={error} />
        <button
          type="button"
          onClick={loadData}
          className="mx-auto block rounded-xl bg-primary px-6 py-2 text-sm font-medium text-primary-foreground"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (loading) {
    return <MedicinesSkeleton />;
  }

  const adherenceRate = summary ? Math.round(summary.adherence_rate_today * 100) : 0;

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to="/patient/home"
          className={cn(buttonVariants({ variant: 'ghost', size: 'icon' }), 'h-9 w-9')}
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">My Medicines</h1>
          <p className="text-sm text-muted-foreground">
            {schedules.length} active schedule{schedules.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* Adherence Summary */}
      {summary && summary.total_due_today > 0 && (
        <div className="rounded-2xl border border-border/80 bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">Today's Adherence</p>
              <p className="text-2xl font-bold text-foreground">{adherenceRate}%</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">
                {summary.taken_today} / {summary.total_due_today} taken
              </p>
              {summary.current_streak_days > 0 && (
                <p className="mt-1 text-xs font-medium text-primary flex items-center gap-1">
                  <Sparkles className="h-3 w-3" />
                  {summary.current_streak_days} day streak
                </p>
              )}
            </div>
          </div>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                adherenceRate >= 80 ? 'bg-green-500' : adherenceRate >= 50 ? 'bg-amber-500' : 'bg-red-500'
              )}
              style={{ width: `${adherenceRate}%` }}
            />
          </div>
        </div>
      )}

      {/* Schedule List */}
      {schedules.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 p-8 text-center">
          <Pill className="mx-auto h-10 w-10 text-muted-foreground/50" />
          <p className="mt-3 text-sm text-muted-foreground">
            No active medication schedules. Medications appear here once a doctor prescribes them and you create a schedule.
          </p>
          <Link
            to="/patient/timeline"
            className="mt-4 inline-block text-sm font-medium text-primary hover:underline"
          >
            View your health timeline
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((schedule) => {
            const rate = schedule.adherence_rate != null ? Math.round(schedule.adherence_rate * 100) : null;
            return (
              <div
                key={schedule.id}
                className="rounded-2xl border border-border/80 bg-card p-4 shadow-sm transition hover:shadow-md"
              >
                <div className="flex items-start gap-3">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
                    <Pill className="h-6 w-6 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-foreground">{schedule.medicine_name}</h3>
                    {schedule.dosage && (
                      <p className="text-sm text-muted-foreground">{schedule.dosage}</p>
                    )}
                    {schedule.frequency && (
                      <p className="text-xs text-muted-foreground">{schedule.frequency}</p>
                    )}
                    {schedule.instructions && (
                      <p className="mt-1 text-xs italic text-muted-foreground">{schedule.instructions}</p>
                    )}
                    {schedule.reminder_times.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {schedule.reminder_times.map((time) => (
                          <span
                            key={time}
                            className="inline-flex items-center gap-1 rounded-full bg-primary/5 px-2 py-0.5 text-[10px] font-medium text-primary"
                          >
                            <Clock className="h-2.5 w-2.5" />
                            {time}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  {rate != null && (
                    <div className="text-right shrink-0">
                      <p className="text-lg font-bold text-foreground">{rate}%</p>
                      <p className="text-[10px] text-muted-foreground">adherence</p>
                    </div>
                  )}
                </div>

                {/* Status badges */}
                <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3 text-green-500" />
                    {schedule.taken_count} taken
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <XCircle className="h-3 w-3 text-amber-500" />
                    {schedule.skipped_count} skipped
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Timer className="h-3 w-3 text-blue-500" />
                    {schedule.total_doses} total
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
