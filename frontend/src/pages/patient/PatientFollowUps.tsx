/**
 * PatientFollowUps — follow-up tracking for the patient workspace.
 *
 * Surfaces:
 * - upcoming follow-ups
 * - overdue follow-ups
 * - follow-up instructions
 *
 * Future hooks for:
 * - reminder automation
 * - AI follow-up summaries
 * - care plans
 */

import { useCallback, useEffect, useState } from 'react';
import dayjs from 'dayjs';
import {
  AlertTriangle,
  Calendar,
  CalendarCheck,
  Stethoscope,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { patientWorkspaceApi } from '../../services/patientWorkspace';
import type { FollowUpItem, FollowUpSummary } from '../../types';
import { ErrorState } from '../../components/common';

export function PatientFollowUps() {
  const [followUps, setFollowUps] = useState<FollowUpSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFollowUps = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await patientWorkspaceApi.getFollowUps();
      setFollowUps(data);
    } catch {
      setError('Unable to load follow-up information.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadFollowUps();
  }, [loadFollowUps]);

  if (error) {
    return <ErrorState title="Follow-ups" description={error} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Follow-ups</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Stay on track with your care plan.
        </p>
      </div>

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-28 rounded-2xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : !followUps || (followUps.total_upcoming === 0 && followUps.total_overdue === 0) ? (
        <Card className="border-dashed">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
              <CalendarCheck className="h-7 w-7 text-primary" />
            </div>
            <CardTitle className="text-lg pt-3">No follow-ups scheduled</CardTitle>
            <CardDescription className="max-w-sm mx-auto">
              You don't have any upcoming or overdue follow-up appointments.
              Your doctor will schedule follow-ups as needed.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          {/* ── Overdue Follow-ups ──────────────────────────────────────────── */}
          {followUps.total_overdue > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-5 w-5 text-red-500" aria-hidden />
                <h2 className="text-base font-semibold text-red-600 dark:text-red-400">
                  Overdue ({followUps.total_overdue})
                </h2>
              </div>
              <div className="space-y-3">
                {followUps.overdue.map((item) => (
                  <FollowUpCard key={item.appointment_id} item={item} overdue />
                ))}
              </div>
            </div>
          )}

          {/* ── Upcoming Follow-ups ─────────────────────────────────────────── */}
          {followUps.total_upcoming > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Calendar className="h-5 w-5 text-primary" aria-hidden />
                <h2 className="text-base font-semibold text-foreground">
                  Upcoming ({followUps.total_upcoming})
                </h2>
              </div>
              <div className="space-y-3">
                {followUps.upcoming.map((item) => (
                  <FollowUpCard key={item.appointment_id} item={item} />
                ))}
              </div>
            </div>
          )}

          {/* TODO: Phase 2 — Reminder automation
           * <FollowUpReminderSettings />
           * <FollowUpNotificationPreferences />
           */}

          {/* TODO: Phase 2 — AI follow-up summaries
           * <AiFollowUpSummary />
           */}

          {/* TODO: Phase 2 — Care plans
           * <CarePlanTimeline />
           */}
        </>
      )}
    </div>
  );
}

function FollowUpCard({ item, overdue }: { item: FollowUpItem; overdue?: boolean }) {
  return (
    <Card
      className={`rounded-2xl border shadow-sm ${
        overdue
          ? 'border-red-200 bg-red-50/30 dark:border-red-800/30 dark:bg-red-950/10'
          : 'border-border/60'
      }`}
    >
      <CardContent className="p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <div
            className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ring-1 ${
              overdue
                ? 'bg-red-100 ring-red-200 dark:bg-red-900/20 dark:ring-red-800/30'
                : 'bg-primary/10 ring-primary/15'
            }`}
          >
            <Stethoscope
              className={`h-6 w-6 ${
                overdue ? 'text-red-500' : 'text-primary'
              }`}
              aria-hidden
            />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-base font-semibold text-foreground">
                  {item.doctor_name}
                </h3>
                {item.doctor_specialization && (
                  <p className="truncate text-xs text-muted-foreground/70">
                    {item.doctor_specialization}
                  </p>
                )}
              </div>
              {overdue && (
                <Badge variant="destructive" className="shrink-0">
                  Overdue
                </Badge>
              )}
            </div>

            <div className="mt-2 flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" aria-hidden />
              <span className="font-medium text-foreground">
                {dayjs(item.follow_up_date).format('MMMM D, YYYY')}
              </span>
            </div>

            {item.follow_up_notes && (
              <p className="mt-2 text-sm text-muted-foreground">
                {item.follow_up_notes}
              </p>
            )}

            <p className="mt-1.5 text-xs text-muted-foreground/60">
              From visit on{' '}
              {dayjs(item.appointment_time).format('MMM D, YYYY')}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
