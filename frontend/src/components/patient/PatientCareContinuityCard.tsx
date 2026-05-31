/**
 * PatientCareContinuityCard — continuity-of-care summary card.
 *
 * PRESENTATIONAL ONLY. No new tables.
 * All data is derived from existing encounter aggregates.
 *
 * Shows:
 * - Primary recurring doctor
 * - Recent care streak
 * - Active medications
 * - Upcoming follow-up
 * - Last completed visit
 * - Recent specialty history
 *
 * CRITICAL:
 * - SOAP internal sections are NEVER exposed
 * - Doctor-only notes are NEVER exposed
 * - Audit metadata is NEVER exposed
 */

import { Link } from 'react-router-dom';
import {
  Calendar,
  CheckCircle2,
  ChevronRight,
  Pill,
  Sparkles,
  Stethoscope,
  User,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PrimaryDoctor, CareStreak, UpcomingFollowUp, LastCompletedVisit, SpecialtyVisit } from '../../utils/continuity';
import { formatRelativeDate, formatShortDate } from '../../utils/patientTimeline';

interface PatientCareContinuityCardProps {
  primaryDoctor: PrimaryDoctor | null;
  careStreak: CareStreak;
  upcomingFollowUp: UpcomingFollowUp | null;
  lastCompletedVisit: LastCompletedVisit | null;
  specialtyHistory: SpecialtyVisit[];
  activeMedicationCount: number;
  className?: string;
}

export function PatientCareContinuityCard({
  primaryDoctor,
  careStreak,
  upcomingFollowUp,
  lastCompletedVisit,
  specialtyHistory,
  activeMedicationCount,
  className,
}: PatientCareContinuityCardProps) {
  const hasData = primaryDoctor || careStreak.consecutiveMonths > 0 || upcomingFollowUp || lastCompletedVisit;

  if (!hasData) return null;

  return (
    <div className={cn('rounded-2xl border border-border/60 bg-gradient-to-br from-card to-muted/10 shadow-sm', className)}>
      <div className="px-5 pt-4 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" aria-hidden />
          <h2 className="text-sm font-semibold text-foreground">Your Care Continuity</h2>
        </div>
      </div>

      <div className="divide-y divide-border/40 px-5 pb-4">
        {/* Primary Doctor */}
        {primaryDoctor && (
          <div className="flex items-center gap-3 py-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <User className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground truncate">
                {primaryDoctor.name}
              </p>
              <p className="text-xs text-muted-foreground">
                {primaryDoctor.specialization ?? 'Doctor'}
                {' · '}
                {primaryDoctor.visitCount} visit{primaryDoctor.visitCount > 1 ? 's' : ''}
              </p>
            </div>
            {primaryDoctor.lastVisit && (
              <span className="text-xs text-muted-foreground/60 shrink-0">
                Last {formatRelativeDate(primaryDoctor.lastVisit)}
              </span>
            )}
          </div>
        )}

        {/* Care Streak */}
        {careStreak.consecutiveMonths > 0 && (
          <div className="flex items-center gap-3 py-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 dark:bg-emerald-950/20">
              <Sparkles className="h-5 w-5 text-emerald-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground">
                {careStreak.consecutiveMonths === 1
                  ? 'Active this month'
                  : `${careStreak.consecutiveMonths}-month care streak`}
              </p>
              <p className="text-xs text-muted-foreground">
                {careStreak.totalVisits} visit{careStreak.totalVisits > 1 ? 's' : ''} in this period
              </p>
            </div>
          </div>
        )}

        {/* Active Medications */}
        {activeMedicationCount > 0 && (
          <div className="flex items-center gap-3 py-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 dark:bg-blue-950/20">
              <Pill className="h-5 w-5 text-blue-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground">
                {activeMedicationCount} active medication{activeMedicationCount > 1 ? 's' : ''}
              </p>
              <p className="text-xs text-muted-foreground">
                From your recent visits
              </p>
            </div>
            <Link
              to="/patient/care/medicines"
              className="shrink-0 text-xs font-medium text-primary hover:underline"
            >
              View
            </Link>
          </div>
        )}

        {/* Upcoming Follow-up */}
        {upcomingFollowUp && (
          <div className="flex items-center gap-3 py-3">
            <div
              className={cn(
                'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
                upcomingFollowUp.isOverdue
                  ? 'bg-red-50 dark:bg-red-950/20'
                  : 'bg-amber-50 dark:bg-amber-950/20',
              )}
            >
              <Calendar
                className={cn(
                  'h-5 w-5',
                  upcomingFollowUp.isOverdue
                    ? 'text-red-500'
                    : 'text-amber-500',
                )}
              />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground truncate">
                {upcomingFollowUp.isOverdue ? 'Overdue follow-up' : 'Upcoming follow-up'}
              </p>
              <p className="text-xs text-muted-foreground">
                {upcomingFollowUp.doctorName}
                {' · '}
                {formatShortDate(upcomingFollowUp.followUpDate)}
              </p>
            </div>
            <Link
              to="/patient/care/follow-ups"
              className="shrink-0 text-xs font-medium text-primary hover:underline"
            >
              Details
            </Link>
          </div>
        )}

        {/* Last Completed Visit */}
        {lastCompletedVisit && (
          <div className="flex items-center gap-3 py-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-green-50 dark:bg-green-950/20">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground truncate">
                Last visit completed
              </p>
              <p className="text-xs text-muted-foreground">
                {lastCompletedVisit.doctorName}
                {' · '}
                {formatRelativeDate(lastCompletedVisit.date)}
              </p>
            </div>
            <Link
              to={`/patient/care/encounters/${lastCompletedVisit.appointmentId}`}
              className="shrink-0 text-xs font-medium text-primary hover:underline"
            >
              View
            </Link>
          </div>
        )}

        {/* Specialty History */}
        {specialtyHistory.length > 0 && (
          <div className="flex items-center gap-3 py-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-purple-50 dark:bg-purple-950/20">
              <Stethoscope className="h-5 w-5 text-purple-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground">Specialties visited</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {specialtyHistory.slice(0, 3).map((spec) => (
                  <span
                    key={spec.specialization}
                    className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                  >
                    {spec.specialization}
                  </span>
                ))}
                {specialtyHistory.length > 3 && (
                  <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                    +{specialtyHistory.length - 3} more
                  </span>
                )}
              </div>
            </div>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/40" />
          </div>
        )}
      </div>
    </div>
  );
}
