/**
 * PatientHealthTimeline — enhanced longitudinal health memory.
 *
 * PHASE UX2: Encounter Experience + Health Memory
 *
 * Enhanced with:
 * - Sticky month headers
 * - Timeline continuity feel
 * - Visual encounter progression
 * - Encounter category icons
 * - Search/filter capability
 * - Empty states with guidance
 * - Better grouping by year/month
 * - Reduced visual noise
 * - Smooth mobile transitions
 * - Lightweight derived insights (observational only)
 *
 * CRITICAL:
 * - SOAP internal sections are NEVER exposed
 * - Doctor-only notes are NEVER exposed
 * - Audit metadata is NEVER exposed
 * - Insights are observational only, NOT diagnostic
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Calendar,
  HeartPulse,
  Search,
  Sparkles,
  X,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { TimelineEncounterCard } from '../../components/patient/TimelineEncounterCard';
import { PatientCareContinuityCard } from '../../components/patient/PatientCareContinuityCard';
import { patientWorkspaceApi } from '../../services/patientWorkspace';
import type { EncounterCard } from '../../types';
import { ErrorState } from '../../components/common';
import {
  groupEncountersByYearMonth,
  deriveHealthInsights,
} from '../../utils/patientTimeline';
import {
  getPrimaryDoctor,
  getCareStreak,
  getUpcomingFollowUp,
  getLastCompletedVisit,
  getRecentSpecialtyHistory,
} from '../../utils/continuity';

export function PatientHealthTimeline() {
  const [encounters, setEncounters] = useState<EncounterCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showInsights, setShowInsights] = useState(true);

  const loadEncounters = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await patientWorkspaceApi.getEncounters({ limit: 100 });
      setEncounters(data);
    } catch {
      setError('Unable to load your health timeline. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadEncounters();
  }, [loadEncounters]);

  // ── Filter by search query ──────────────────────────────────────────────
  const filteredEncounters = useMemo(() => {
    if (!searchQuery.trim()) return encounters;

    const q = searchQuery.toLowerCase().trim();
    return encounters.filter(
      (enc) =>
        enc.doctor_name?.toLowerCase().includes(q) ||
        enc.diagnosis?.toLowerCase().includes(q) ||
        enc.treatment_summary?.toLowerCase().includes(q) ||
        enc.clinic_name?.toLowerCase().includes(q) ||
        enc.doctor_specialization?.toLowerCase().includes(q),
    );
  }, [encounters, searchQuery]);

  // ── Group by year → month ───────────────────────────────────────────────
  const yearGroups = useMemo(
    () => groupEncountersByYearMonth(filteredEncounters),
    [filteredEncounters],
  );

  // ── Derived insights (observational only) ───────────────────────────────
  const insights = useMemo(() => deriveHealthInsights(encounters), [encounters]);

  // ── Continuity data ─────────────────────────────────────────────────────
  const primaryDoctor = useMemo(() => getPrimaryDoctor(encounters), [encounters]);
  const careStreak = useMemo(() => getCareStreak(encounters), [encounters]);
  const upcomingFollowUp = useMemo(() => getUpcomingFollowUp(encounters), [encounters]);
  const lastCompletedVisit = useMemo(() => getLastCompletedVisit(encounters), [encounters]);
  const specialtyHistory = useMemo(() => getRecentSpecialtyHistory(encounters), [encounters]);
  const activeMedicationCount = useMemo(
    () => encounters.reduce((sum, e) => sum + e.prescriptions_count, 0),
    [encounters],
  );

  if (error) {
    return <ErrorState title="Health Timeline" description={error} />;
  }

  return (
    <div className="space-y-6 pb-8">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <HeartPulse className="h-5 w-5 text-primary" aria-hidden />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Your Health Timeline
          </h1>
        </div>
        <p className="text-sm text-muted-foreground">
          A chronological record of your visits and care.
        </p>
      </div>

      {/* ── Continuity Card ──────────────────────────────────────────────── */}
      {!loading && encounters.length > 0 && (
        <PatientCareContinuityCard
          primaryDoctor={primaryDoctor}
          careStreak={careStreak}
          upcomingFollowUp={upcomingFollowUp}
          lastCompletedVisit={lastCompletedVisit}
          specialtyHistory={specialtyHistory}
          activeMedicationCount={activeMedicationCount}
        />
      )}

      {/* ── Insights (observational only) ─────────────────────────────────── */}
      {!loading && insights.length > 0 && showInsights && (
        <div className="rounded-2xl border border-primary/20 bg-primary/5 shadow-sm">
          <div className="flex items-center justify-between px-5 pt-4 pb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" aria-hidden />
              <h2 className="text-sm font-semibold text-foreground">Your Care Insights</h2>
            </div>
            <button
              type="button"
              onClick={() => setShowInsights(false)}
              className="text-muted-foreground/50 hover:text-muted-foreground transition-colors touch-manipulation min-h-[36px] min-w-[36px] flex items-center justify-center"
              aria-label="Dismiss insights"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="px-5 pb-4">
            <div className="space-y-2">
              {insights.map((insight, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 rounded-xl bg-background/60 px-3.5 py-2.5"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <HeartPulse className="h-4 w-4 text-primary" />
                  </div>
                  <p className="text-sm text-foreground/80">{insight.message}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Search ────────────────────────────────────────────────────────── */}
      {!loading && encounters.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" aria-hidden />
          <Input
            type="text"
            placeholder="Search visits by doctor, diagnosis, or clinic…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="rounded-2xl border-border/60 pl-10 text-sm h-12 bg-card"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-muted-foreground transition-colors touch-manipulation min-h-[36px] min-w-[36px] flex items-center justify-center"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}

      {/* ── Loading state ─────────────────────────────────────────────────── */}
      {loading ? (
        <div className="space-y-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-5">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 shrink-0 rounded-2xl bg-muted animate-pulse" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-40 rounded-md bg-muted animate-pulse" />
                    <div className="h-3 w-28 rounded-md bg-muted animate-pulse" />
                  </div>
                </div>
                <div className="mt-3 h-16 rounded-xl bg-muted/40 animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredEncounters.length === 0 && searchQuery ? (
        /* ── No search results ──────────────────────────────────────────── */
        <Card className="border-dashed">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-muted/50">
              <Search className="h-7 w-7 text-muted-foreground" />
            </div>
            <CardTitle className="text-lg pt-3">No results found</CardTitle>
            <CardDescription className="max-w-sm mx-auto">
              No visits match "{searchQuery}". Try a different search term.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : encounters.length === 0 ? (
        /* ── Empty state ────────────────────────────────────────────────── */
        <Card className="border-dashed">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
              <HeartPulse className="h-7 w-7 text-primary" />
            </div>
            <CardTitle className="text-lg pt-3">No visits yet</CardTitle>
            <CardDescription className="max-w-sm mx-auto">
              Your health timeline will start filling up after your first visit with a doctor.
              Each visit will appear here as a complete record of your care.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        /* ── Timeline ───────────────────────────────────────────────────── */
        <div className="space-y-8">
          {yearGroups.map((yearGroup) => (
            <div key={yearGroup.year}>
              {/* Year header */}
              <div className="sticky top-0 z-10 -mx-4 bg-background/95 px-4 py-2 backdrop-blur-md sm:mx-0 sm:px-0">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" aria-hidden />
                  <h2 className="text-lg font-semibold text-foreground">
                    {yearGroup.label}
                  </h2>
                  <span className="text-xs text-muted-foreground/50">
                    {yearGroup.totalEncounters} visit{yearGroup.totalEncounters !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="mt-1 h-px bg-gradient-to-r from-primary/20 to-transparent" />
              </div>

              {/* Months */}
              <div className="mt-4 space-y-6">
                {yearGroup.months.map((monthGroup) => (
                  <div key={monthGroup.key} className="space-y-3">
                    {/* Month header */}
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-primary/40" aria-hidden />
                      <h3 className="text-sm font-medium text-muted-foreground">
                        {monthGroup.label}
                      </h3>
                      <span className="text-xs text-muted-foreground/40">
                        {monthGroup.items.length} visit{monthGroup.items.length !== 1 ? 's' : ''}
                      </span>
                    </div>

                    {/* Encounter cards */}
                    <div className="space-y-3">
                      {monthGroup.items.map((enc, idx) => (
                        <div key={enc.appointment_id} className="relative">
                          {/* Continuity connector (not for last item) */}
                          {idx < monthGroup.items.length - 1 && (
                            <div
                              className="absolute left-[23px] top-[60px] bottom-[-8px] w-px bg-border/40 z-0"
                              aria-hidden
                            />
                          )}
                          <TimelineEncounterCard encounter={enc} />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {encounters.length >= 100 && (
            <p className="text-center text-xs text-muted-foreground">
              Showing the most recent 100 visits.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
