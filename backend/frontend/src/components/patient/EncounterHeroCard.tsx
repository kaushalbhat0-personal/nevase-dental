/**
 * EncounterHeroCard — hero header for the encounter detail page.
 *
 * Shows:
 * - Visit type badge (derived category)
 * - Doctor identity with avatar/icon and specialization
 * - Formatted date/time with weekday
 * - Visit status badge
 * - Visit continuity indicator ("Your Xth visit with Dr. Y")
 * - Timeline breadcrumb
 *
 * CRITICAL:
 * - SOAP internal sections are NEVER exposed
 * - Doctor-only notes are NEVER exposed
 * - Audit metadata is NEVER exposed
 */

import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  Stethoscope,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { EncounterDetailAggregate } from '../../types';
import type { EncounterCategory } from '../../utils/patientTimeline';
import { formatEncounterDate } from '../../utils/patientTimeline';

interface EncounterHeroCardProps {
  encounter: EncounterDetailAggregate;
  category: EncounterCategory;
  visitNumber?: number;
  totalEncounters?: number;
}

const CATEGORY_LABELS: Record<EncounterCategory, string> = {
  consultation: 'Consultation',
  'follow-up': 'Follow-up',
  checkup: 'Check-up',
  emergency: 'Emergency Visit',
  procedure: 'Procedure',
  vaccination: 'Vaccination',
  lab: 'Lab / Investigation',
  general: 'Visit',
};

const CATEGORY_COLORS: Record<EncounterCategory, string> = {
  consultation: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'follow-up': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  checkup: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  emergency: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  procedure: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  vaccination: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  lab: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  general: 'bg-gray-100 text-gray-700 dark:bg-gray-800/30 dark:text-gray-400',
};

export function EncounterHeroCard({
  encounter,
  category,
  visitNumber,
  totalEncounters,
}: EncounterHeroCardProps) {
  const navigate = useNavigate();
  const { appointment, doctor } = encounter;

  const dateLabel = appointment.appointment_time
    ? formatEncounterDate(appointment.appointment_time)
    : 'Date unknown';

  const statusVariant =
    appointment.status === 'completed'
      ? 'default'
      : appointment.status === 'cancelled'
        ? 'destructive'
        : 'secondary';

  return (
    <div className="overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card to-muted/20 shadow-sm">
      {/* ── Back button ──────────────────────────────────────────────────── */}
      <div className="px-5 pt-4">
        <button
          type="button"
          onClick={() => navigate('/patient/care/timeline')}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors touch-manipulation min-h-[36px]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to timeline
        </button>
      </div>

      {/* ── Hero content ─────────────────────────────────────────────────── */}
      <div className="p-5 pt-3">
        <div className="flex items-start gap-4">
          {/* Doctor avatar */}
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-primary/10 ring-2 ring-primary/20">
            <Stethoscope className="h-8 w-8 text-primary" aria-hidden />
          </div>

          <div className="min-w-0 flex-1 space-y-2">
            {/* Visit type badge */}
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${CATEGORY_COLORS[category]}`}
              >
                {CATEGORY_LABELS[category]}
              </span>
              <Badge
                variant={statusVariant}
                className="shrink-0 capitalize"
              >
                {appointment.status}
              </Badge>
            </div>

            {/* Doctor identity */}
            <div>
              <h1 className="text-xl font-bold text-foreground">
                {doctor?.name || 'Doctor'}
              </h1>
              {doctor?.specialization && (
                <p className="text-sm text-muted-foreground">
                  {doctor.specialization}
                </p>
              )}
            </div>

            {/* Date */}
            <div className="flex items-center gap-1.5 text-sm text-foreground/80">
              <Calendar className="h-4 w-4 text-muted-foreground" aria-hidden />
              <span className="font-medium">{dateLabel}</span>
            </div>

            {/* Continuity indicator */}
            {visitNumber && visitNumber > 0 && (
              <p className="text-xs text-muted-foreground/70 italic">
                {visitNumber === 1
                  ? 'Your first visit'
                  : `Your ${visitNumber}${getOrdinalSuffix(visitNumber)} visit`}
                {doctor?.name ? ` with ${doctor.name}` : ''}
                {totalEncounters && totalEncounters > 1
                  ? ` · ${totalEncounters} total visits`
                  : ''}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function getOrdinalSuffix(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0]!;
}
