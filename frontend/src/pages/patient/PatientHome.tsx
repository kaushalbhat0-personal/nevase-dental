/**
 * Today's Care Dashboard — Phase P3 Daily Care Dashboard + Adherence Experience.
 *
 * Transforms the patient home page from a discovery-focused page into a
 * daily care engagement platform. The dashboard is composed of 5 sections:
 *
 * 1. Medicines Due Today — adherence tracking with large touch targets
 * 2. Upcoming Care — next appointment, follow-ups, unread communications
 * 3. Continue Care — recent doctors, prescriptions for continuity
 * 4. Health Timeline Preview — last 3 encounter preview cards
 * 5. Quick Actions — action shortcuts
 *
 * CRITICAL:
 * - Patient access is strictly scoped to their own data
 * - Prescription data is NEVER mutated through this aggregate
 * - Adherence actions affect tracking ONLY
 * - No shadow adherence systems are created
 */

import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileText,
  MessageSquare,
  Pill,
  Timer,
  XCircle,
  AlertTriangle,
  Sparkles,
  User,
  Activity,
  Bell,
  CalendarPlus,
  Stethoscope,
} from 'lucide-react';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { dailyCareApi, type DailyCareDashboardAggregate } from '../../services/dailyCare';
import { medicationScheduleApi } from '../../services/medicationSchedule';
import { ErrorState } from '../../components/common';
import { Skeleton } from '@/components/ui/skeleton';
import { PageSection } from '@/components/ui/page-section';

// ═════════════════════════════════════════════════════════════════════════════
// Skeleton Loading
// ═════════════════════════════════════════════════════════════════════════════

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Sticky Today Header */}
      <div className="sticky top-0 z-20 -mx-4 border-b border-border/50 bg-background/95 px-4 py-3 backdrop-blur-md sm:mx-0 sm:rounded-2xl sm:border sm:shadow-sm">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-2 h-4 w-72" />
      </div>

      {/* Medicines Due Today Skeleton */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-44" />
        <div className="grid gap-3 sm:grid-cols-2">
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
        </div>
      </div>

      {/* Upcoming Care Skeleton */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-36" />
        <Skeleton className="h-24 rounded-2xl" />
      </div>

      {/* Continue Care Skeleton */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <div className="flex gap-3 overflow-x-auto">
          <Skeleton className="h-28 w-56 shrink-0 rounded-2xl" />
          <Skeleton className="h-28 w-56 shrink-0 rounded-2xl" />
        </div>
      </div>

      {/* Quick Actions Skeleton */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-28" />
        <div className="grid grid-cols-3 gap-3">
          <Skeleton className="h-20 rounded-2xl" />
          <Skeleton className="h-20 rounded-2xl" />
          <Skeleton className="h-20 rounded-2xl" />
        </div>
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// Medication Card
// ═════════════════════════════════════════════════════════════════════════════

interface MedicationCardProps {
  medicineName: string;
  dosage: string | null;
  frequency: string | null;
  instructions: string | null;
  adherenceStatus: 'pending' | 'taken' | 'skipped' | 'snoozed';
  scheduleId: string;
  scheduledTime: string | null;
  onMarkTaken: (scheduleId: string) => void;
  onMarkSkipped: (scheduleId: string) => void;
  onSnooze: (scheduleId: string) => void;
}

function MedicationCard({
  medicineName,
  dosage,
  frequency,
  instructions,
  adherenceStatus,
  scheduleId,
  scheduledTime,
  onMarkTaken,
  onMarkSkipped,
  onSnooze,
}: MedicationCardProps) {
  const isCompleted = adherenceStatus === 'taken';
  const isSkipped = adherenceStatus === 'skipped';
  const isSnoozed = adherenceStatus === 'snoozed';
  const isPending = adherenceStatus === 'pending';

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl border p-4 transition-all duration-300',
        isCompleted && 'border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20',
        isSkipped && 'border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/20',
        isSnoozed && 'border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20',
        isPending && 'border-border bg-card shadow-sm hover:shadow-md'
      )}
    >
      {/* Completion state indicator */}
      {isCompleted && (
        <div className="absolute right-3 top-3">
          <CheckCircle2 className="h-6 w-6 text-green-500" aria-label="Taken" />
        </div>
      )}
      {isSkipped && (
        <div className="absolute right-3 top-3">
          <XCircle className="h-6 w-6 text-amber-500" aria-label="Skipped" />
        </div>
      )}
      {isSnoozed && (
        <div className="absolute right-3 top-3">
          <Timer className="h-6 w-6 text-blue-500" aria-label="Snoozed" />
        </div>
      )}

      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex h-12 w-12 shrink-0 items-center justify-center rounded-xl',
            isCompleted && 'bg-green-100 dark:bg-green-900/30',
            isSkipped && 'bg-amber-100 dark:bg-amber-900/30',
            isSnoozed && 'bg-blue-100 dark:bg-blue-900/30',
            isPending && 'bg-primary/10'
          )}
        >
          <Pill
            className={cn(
              'h-6 w-6',
              isCompleted && 'text-green-600 dark:text-green-400',
              isSkipped && 'text-amber-600 dark:text-amber-400',
              isSnoozed && 'text-blue-600 dark:text-blue-400',
              isPending && 'text-primary'
            )}
          />
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-foreground truncate">{medicineName}</h3>
          {dosage && <p className="text-sm text-muted-foreground">{dosage}</p>}
          {frequency && <p className="text-xs text-muted-foreground">{frequency}</p>}
          {scheduledTime && (
            <p className="mt-1 text-xs font-medium text-primary">
              <Clock className="mr-1 inline h-3 w-3" />
              {scheduledTime}
            </p>
          )}
          {instructions && (
            <p className="mt-1 text-xs italic text-muted-foreground">{instructions}</p>
          )}
        </div>
      </div>

      {/* Action buttons — large touch targets */}
      {isPending && (
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={() => onMarkTaken(scheduleId)}
            className="flex-1 min-h-[44px] rounded-xl bg-green-500 px-3 text-sm font-medium text-white transition active:scale-95 hover:bg-green-600 touch-manipulation"
          >
            <CheckCircle2 className="mr-1.5 inline h-4 w-4" />
            Mark Taken
          </button>
          <button
            type="button"
            onClick={() => onMarkSkipped(scheduleId)}
            className="flex-1 min-h-[44px] rounded-xl bg-amber-100 px-3 text-sm font-medium text-amber-700 transition active:scale-95 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400 touch-manipulation"
          >
            <XCircle className="mr-1.5 inline h-4 w-4" />
            Skip
          </button>
          <button
            type="button"
            onClick={() => onSnooze(scheduleId)}
            className="flex min-h-[44px] items-center justify-center rounded-xl bg-muted px-3 text-sm font-medium text-muted-foreground transition active:scale-95 hover:bg-muted/80 touch-manipulation"
          >
            <Timer className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Completed state */}
      {isCompleted && (
        <div className="mt-3">
          <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Taken
          </p>
        </div>
      )}

      {/* Skipped state */}
      {isSkipped && (
        <div className="mt-3">
          <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Skipped
          </p>
        </div>
      )}

      {/* Snoozed state */}
      {isSnoozed && (
        <div className="mt-3">
          <p className="text-xs text-blue-600 dark:text-blue-400 flex items-center gap-1">
            <Timer className="h-3 w-3" />
            Snoozed
          </p>
        </div>
      )}
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// Adherence Progress Bar
// ═════════════════════════════════════════════════════════════════════════════

function AdherenceProgressBar({
  taken,
  total,
  rate,
  streak,
}: {
  taken: number;
  total: number;
  rate: number;
  streak: number;
}) {
  const percentage = Math.round(rate * 100);
  const colorClass =
    percentage >= 80
      ? 'bg-green-500'
      : percentage >= 50
        ? 'bg-amber-500'
        : 'bg-red-500';

  return (
    <div className="rounded-2xl border border-border/80 bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">Today's Adherence</p>
          <p className="text-2xl font-bold text-foreground">{percentage}%</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground">
            {taken} / {total} taken
          </p>
          {streak > 0 && (
            <p className="mt-1 text-xs font-medium text-primary flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              {streak} day streak
            </p>
          )}
        </div>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full transition-all duration-500', colorClass)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// Main Dashboard Component
// ═════════════════════════════════════════════════════════════════════════════

export function PatientHome() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<DailyCareDashboardAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Load dashboard data ──────────────────────────────────────────────────
  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await dailyCareApi.getDashboard();
      setDashboard(data);
    } catch {
      setError('Could not load your daily care dashboard. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // ── Adherence actions ────────────────────────────────────────────────────
  const handleMarkTaken = useCallback(
    async (scheduleId: string) => {
      try {
        await medicationScheduleApi.recordAdherence(scheduleId, {
          action: 'taken',
          scheduled_time: null,
        });
        await loadDashboard();
      } catch {
        // Silently handle
      }
    },
    [loadDashboard]
  );

  const handleMarkSkipped = useCallback(
    async (scheduleId: string) => {
      try {
        await medicationScheduleApi.recordAdherence(scheduleId, {
          action: 'skipped',
          scheduled_time: null,
        });
        await loadDashboard();
      } catch {
        // Silently handle
      }
    },
    [loadDashboard]
  );

  const handleSnooze = useCallback(
    async (scheduleId: string) => {
      try {
        await medicationScheduleApi.recordAdherence(scheduleId, {
          action: 'snoozed',
          scheduled_time: null,
        });
        await loadDashboard();
      } catch {
        // Silently handle
      }
    },
    [loadDashboard]
  );

  // ── Error state ──────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="space-y-4">
        <ErrorState title="Dashboard unavailable" description={error} />
        <button
          type="button"
          onClick={loadDashboard}
          className="mx-auto block rounded-xl bg-primary px-6 py-2 text-sm font-medium text-primary-foreground"
        >
          Try Again
        </button>
      </div>
    );
  }

  // ── Loading state ────────────────────────────────────────────────────────
  if (loading || !dashboard) {
    return <DashboardSkeleton />;
  }

  const { medicines_due_today, upcoming_care, continue_care, health_timeline_preview, quick_actions } = dashboard;

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 pb-8">
      {/* ═══════════════════════════════════════════════════════════════════
          Sticky Today Header
          ═══════════════════════════════════════════════════════════════════ */}
      <div className="sticky top-0 z-20 -mx-4 border-b border-border/50 bg-background/95 px-4 py-3 backdrop-blur-md transition-shadow duration-200 sm:mx-0 sm:rounded-2xl sm:border sm:shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              Today's Care
            </h1>
            <p className="text-sm text-muted-foreground">
              {new Date().toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {upcoming_care.unread_communications > 0 && (
              <Link
                to="/patient/messages"

                className="relative flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary"
              >
                <Bell className="h-5 w-5" />
                <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                  {upcoming_care.unread_communications > 9 ? '9+' : upcoming_care.unread_communications}
                </span>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 1 — Medicines Due Today
          ═══════════════════════════════════════════════════════════════════ */}
      <PageSection
        title="Medicines Due Today"
        description={
          medicines_due_today.total_due > 0
            ? `${medicines_due_today.pending_count} pending · ${medicines_due_today.taken_count} taken`
            : 'No medications scheduled for today'
        }
        className="animate-in fade-in duration-300"
        action={
          medicines_due_today.total_due > 0 ? (
            <Link
              to="/patient/care/medicines"

              className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'gap-1 text-primary')}
            >
              View All
              <ChevronRight className="h-4 w-4" />
            </Link>
          ) : undefined
        }
      >
        {/* Adherence Progress */}
        {medicines_due_today.total_due > 0 && (
          <div className="mb-3">
            <AdherenceProgressBar
              taken={medicines_due_today.taken_count}
              total={medicines_due_today.total_due}
              rate={medicines_due_today.adherence_rate_today}
              streak={medicines_due_today.current_streak_days}
            />
          </div>
        )}

        {/* Due Now — highest urgency */}
        {medicines_due_today.due_now.length > 0 && (
          <div className="mb-3">
            <div className="mb-2 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
              <p className="text-xs font-semibold uppercase tracking-wide text-red-600 dark:text-red-400">
                Due Now
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {medicines_due_today.due_now.map((med) => (
                <MedicationCard
                  key={`${med.schedule_id}-${med.scheduled_time || 'now'}`}
                  medicineName={med.medicine_name}
                  dosage={med.dosage}
                  frequency={med.frequency}
                  instructions={med.instructions}
                  adherenceStatus={med.adherence_status}
                  scheduleId={med.schedule_id}
                  scheduledTime={med.scheduled_time}
                  onMarkTaken={handleMarkTaken}
                  onMarkSkipped={handleMarkSkipped}
                  onSnooze={handleSnooze}
                />
              ))}
            </div>
          </div>
        )}

        {/* Overdue */}
        {medicines_due_today.overdue.length > 0 && (
          <div className="mb-3">
            <div className="mb-2 flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">
                Overdue
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {medicines_due_today.overdue.map((med) => (
                <MedicationCard
                  key={`${med.schedule_id}-${med.scheduled_time || 'overdue'}`}
                  medicineName={med.medicine_name}
                  dosage={med.dosage}
                  frequency={med.frequency}
                  instructions={med.instructions}
                  adherenceStatus={med.adherence_status}
                  scheduleId={med.schedule_id}
                  scheduledTime={med.scheduled_time}
                  onMarkTaken={handleMarkTaken}
                  onMarkSkipped={handleMarkSkipped}
                  onSnooze={handleSnooze}
                />
              ))}
            </div>
          </div>
        )}

        {/* Upcoming */}
        {medicines_due_today.upcoming.length > 0 && (
          <div className="mb-3">
            <div className="mb-2 flex items-center gap-2">
              <Clock className="h-3.5 w-3.5 text-blue-500" />
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">
                Upcoming
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {medicines_due_today.upcoming.map((med) => (
                <MedicationCard
                  key={`${med.schedule_id}-${med.scheduled_time || 'upcoming'}`}
                  medicineName={med.medicine_name}
                  dosage={med.dosage}
                  frequency={med.frequency}
                  instructions={med.instructions}
                  adherenceStatus={med.adherence_status}
                  scheduleId={med.schedule_id}
                  scheduledTime={med.scheduled_time}
                  onMarkTaken={handleMarkTaken}
                  onMarkSkipped={handleMarkSkipped}
                  onSnooze={handleSnooze}
                />
              ))}
            </div>
          </div>
        )}

        {/* Completed */}
        {medicines_due_today.completed.length > 0 && (
          <div>
            <div className="mb-2 flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
              <p className="text-xs font-semibold uppercase tracking-wide text-green-600 dark:text-green-400">
                Completed
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {medicines_due_today.completed.map((med) => (
                <MedicationCard
                  key={`${med.schedule_id}-${med.scheduled_time || 'completed'}`}
                  medicineName={med.medicine_name}
                  dosage={med.dosage}
                  frequency={med.frequency}
                  instructions={med.instructions}
                  adherenceStatus={med.adherence_status}
                  scheduleId={med.schedule_id}
                  scheduledTime={med.scheduled_time}
                  onMarkTaken={handleMarkTaken}
                  onMarkSkipped={handleMarkSkipped}
                  onSnooze={handleSnooze}
                />
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {medicines_due_today.total_due === 0 && (
          <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 p-6 text-center">
            <Pill className="mx-auto h-8 w-8 text-muted-foreground/50" />
            <p className="mt-2 text-sm text-muted-foreground">No medications scheduled for today.</p>
            <Link
              to="/patient/care/timeline"

              className="mt-3 inline-block text-sm font-medium text-primary hover:underline"
            >
              View your health timeline
            </Link>
          </div>
        )}
      </PageSection>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 2 — Upcoming Care
          ═══════════════════════════════════════════════════════════════════ */}
      <PageSection
        title="Upcoming Care"
        description="Your next appointments and tasks"
        className="animate-in fade-in duration-300"
      >
        <div className="space-y-3">
          {/* Next Appointment */}
          {upcoming_care.next_appointment ? (
            <Link
              to={`/patient/care/encounters/${upcoming_care.next_appointment.id}`}

              className="block rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/5 to-background p-4 transition hover:shadow-md"
            >
              <div className="flex items-start gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
                  <Calendar className="h-6 w-6 text-primary" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold uppercase tracking-wide text-primary/80">Next Appointment</p>
                  <h3 className="mt-1 font-semibold text-foreground">
                    {upcoming_care.next_appointment.doctor_name}
                  </h3>
                  {upcoming_care.next_appointment.doctor_specialization && (
                    <p className="text-sm text-muted-foreground">
                      {upcoming_care.next_appointment.doctor_specialization}
                    </p>
                  )}
                  <p className="mt-1 text-sm font-medium text-foreground">
                    {new Date(upcoming_care.next_appointment.appointment_time).toLocaleDateString('en-US', {
                      weekday: 'short',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                  {upcoming_care.next_appointment.clinic_name && (
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {upcoming_care.next_appointment.clinic_name}
                    </p>
                  )}
                </div>
                <ChevronRight className="mt-2 h-5 w-5 shrink-0 text-muted-foreground" />
              </div>
            </Link>
          ) : (
            <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 p-4 text-center">
              <p className="text-sm text-muted-foreground">No upcoming appointments.</p>
              <Link
              to="/patient/discover"

                className="mt-2 inline-block text-sm font-medium text-primary hover:underline"
              >
                Book an appointment
              </Link>
            </div>
          )}

          {/* Overdue Follow-ups */}
          {upcoming_care.overdue_follow_ups.length > 0 && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-4 dark:border-amber-800 dark:bg-amber-950/20">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
                  {upcoming_care.overdue_follow_ups.length} Overdue Follow-up{upcoming_care.overdue_follow_ups.length > 1 ? 's' : ''}
                </p>
              </div>
              <div className="mt-2 space-y-2">
                {upcoming_care.overdue_follow_ups.slice(0, 3).map((fu) => (
                  <div key={fu.appointment_id} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{fu.doctor_name}</span>
                    <span className="text-xs text-amber-600">
                      Due {new Date(fu.follow_up_date).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
              <Link
                to="/patient/care/follow-ups"

                className="mt-3 inline-block text-sm font-medium text-primary hover:underline"
              >
                View all follow-ups
              </Link>
            </div>
          )}

          {/* Upcoming Follow-ups */}
          {upcoming_care.upcoming_follow_ups.length > 0 && (
            <div className="rounded-2xl border border-border/80 bg-card p-4 shadow-sm">
              <p className="text-sm font-semibold text-foreground">Upcoming Follow-ups</p>
              <div className="mt-2 space-y-2">
                {upcoming_care.upcoming_follow_ups.slice(0, 3).map((fu) => (
                  <div key={fu.appointment_id} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{fu.doctor_name}</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(fu.follow_up_date).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Unread Communications */}
          {upcoming_care.unread_communications > 0 && (
            <Link
              to="/patient/messages"

              className="flex items-center gap-3 rounded-2xl border border-border/80 bg-card p-4 shadow-sm transition hover:shadow-md"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <MessageSquare className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground">Unread Messages</p>
                <p className="text-xs text-muted-foreground">
                  {upcoming_care.unread_communications} unread communication{upcoming_care.unread_communications > 1 ? 's' : ''}
                </p>
              </div>
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                {upcoming_care.unread_communications}
              </span>
            </Link>
          )}
        </div>
      </PageSection>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 3 — Continue Care
          ═══════════════════════════════════════════════════════════════════ */}
      <PageSection
        title="Continue Care"
        description="Pick up where you left off"
        className="animate-in fade-in duration-300"
      >
        <div className="space-y-3">
          {/* Recent Doctors */}
          {continue_care.recent_doctors.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Recent Doctors
              </p>
              <div className="flex gap-3 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {continue_care.recent_doctors.map((doc) => (
                  <button
                    key={doc.doctor_id}
                    type="button"
                    onClick={() => navigate(`/patient/discover/doctor/${doc.doctor_id}`)}

                    className="w-48 shrink-0 rounded-2xl border border-border/80 bg-card p-4 text-left shadow-sm transition hover:shadow-md"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                      <User className="h-5 w-5 text-primary" />
                    </div>
                    <p className="mt-2 font-medium text-foreground truncate">{doc.doctor_name}</p>
                    {doc.specialization && (
                      <p className="text-xs text-muted-foreground truncate">{doc.specialization}</p>
                    )}
                    {doc.last_visit && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Last visit: {new Date(doc.last_visit).toLocaleDateString()}
                      </p>
                    )}
                    <span className="mt-2 inline-block text-xs font-medium text-primary">
                      Rebook
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Recent Prescriptions */}
          {continue_care.recent_prescriptions.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Recent Prescriptions
              </p>
              <div className="space-y-2">
                {continue_care.recent_prescriptions.slice(0, 3).map((rx) => (
                  <Link
                    key={rx.prescription_id}
                    to="/patient/profile/documents"

                    className="flex items-center gap-3 rounded-xl border border-border/60 bg-card p-3 transition hover:shadow-sm"
                  >
                    <FileText className="h-5 w-5 shrink-0 text-primary" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground truncate">
                        {rx.doctor_name ? `Prescription from ${rx.doctor_name}` : 'Prescription'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {rx.medicine_count} medicine{rx.medicine_count !== 1 ? 's' : ''} · {new Date(rx.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {continue_care.recent_doctors.length === 0 && continue_care.recent_prescriptions.length === 0 && (
            <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 p-6 text-center">
              <Activity className="mx-auto h-8 w-8 text-muted-foreground/50" />
              <p className="mt-2 text-sm text-muted-foreground">
                No recent care activity. Book your first appointment to get started.
              </p>
              <Link
                to="/patient/discover"

                className="mt-3 inline-block text-sm font-medium text-primary hover:underline"
              >
                Find a doctor
              </Link>
            </div>
          )}
        </div>
      </PageSection>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 4 — Health Timeline Preview
          ═══════════════════════════════════════════════════════════════════ */}
      {health_timeline_preview.recent_cards.length > 0 && (
        <PageSection
          title="Health Timeline"
          description={`${health_timeline_preview.total_encounters} total encounters`}
          className="animate-in fade-in duration-300"
          action={
            <Link
              to="/patient/care/timeline"

              className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'gap-1 text-primary')}
            >
              View All
              <ChevronRight className="h-4 w-4" />
            </Link>
          }
        >
          <div className="space-y-3">
            {health_timeline_preview.recent_cards.map((card) => (
              <Link
                key={card.appointment_id}
              to={`/patient/care/encounters/${card.appointment_id}`}

                className="flex items-start gap-3 rounded-2xl border border-border/80 bg-card p-4 shadow-sm transition hover:shadow-md"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
                  <Stethoscope className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground truncate">{card.doctor_name}</p>
                  {card.doctor_specialization && (
                    <p className="text-xs text-muted-foreground">{card.doctor_specialization}</p>
                  )}
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {new Date(card.appointment_time).toLocaleDateString()}
                  </p>
                  {card.diagnosis && (
                    <p className="mt-1 text-xs text-foreground/80 line-clamp-1">{card.diagnosis}</p>
                  )}
                </div>
                <ChevronRight className="mt-2 h-4 w-4 shrink-0 text-muted-foreground" />
              </Link>
            ))}
          </div>
        </PageSection>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 5 — Quick Actions
          ═══════════════════════════════════════════════════════════════════ */}
      <PageSection
        title="Quick Actions"
        description="Common tasks"
        className="animate-in fade-in duration-300"
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {quick_actions.actions.map((action) => {
            if (action.is_future) {
              return (
                <div
                  key={action.id}
                  className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border/60 bg-muted/20 p-4 text-center opacity-60"
                  title="Coming soon"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted">
                    <span className="text-lg text-muted-foreground">+</span>
                  </div>
                  <span className="text-xs font-medium text-muted-foreground">{action.label}</span>
                </div>
              );
            }
            return (
              <Link
                key={action.id}
                to={action.route}
                className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-border/80 bg-card p-4 text-center shadow-sm transition hover:shadow-md active:scale-95 touch-manipulation"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                  {action.icon === 'CalendarPlus' && <CalendarPlus className="h-5 w-5 text-primary" />}
                  {action.icon === 'FileText' && <FileText className="h-5 w-5 text-primary" />}
                  {action.icon === 'MessageSquare' && <MessageSquare className="h-5 w-5 text-primary" />}
                  {action.icon === 'Pill' && <Pill className="h-5 w-5 text-primary" />}
                  {action.icon === 'Activity' && <Activity className="h-5 w-5 text-primary" />}
                  {action.icon === 'Clock' && <Clock className="h-5 w-5 text-primary" />}
                  {action.icon === 'User' && <User className="h-5 w-5 text-primary" />}
                  {action.icon === 'Calendar' && <Calendar className="h-5 w-5 text-primary" />}
                  {action.icon === 'Bell' && <Bell className="h-5 w-5 text-primary" />}
                  {action.icon === 'Stethoscope' && <Stethoscope className="h-5 w-5 text-primary" />}
                  {action.icon === 'Timeline' && <Activity className="h-5 w-5 text-primary" />}
                  {action.icon === 'Upload' && <FileText className="h-5 w-5 text-primary" />}
                  {action.icon === 'ShoppingCart' && <CalendarPlus className="h-5 w-5 text-primary" />}
                  {action.icon === 'Users' && <User className="h-5 w-5 text-primary" />}

                </div>
                <span className="text-xs font-medium text-foreground">{action.label}</span>
                {action.description && (
                  <span className="text-[10px] text-muted-foreground">{action.description}</span>
                )}
              </Link>
            );
          })}
        </div>
      </PageSection>
    </div>
  );
}
