/**
 * TimelineEncounterCard — enhanced patient-safe encounter card for the health timeline.
 *
 * PHASE UX2: Encounter Experience + Health Memory
 *
 * Upgraded with:
 * - Category-based icon/color
 * - Calm, app-like design
 * - Better visual hierarchy
 * - Mobile-optimized touch targets
 * - Continuity connector support
 * - Reduced visual noise
 * - Smooth transitions
 *
 * CRITICAL:
 * - SOAP internal sections are NEVER exposed
 * - Doctor-only notes are NEVER exposed
 * - Audit metadata is NEVER exposed
 *
 * Design: calm, readable, mobile-first, app-like (NOT enterprise/admin)
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import {
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Download,
  FileText,
  Pill,
  Stethoscope,
  HeartPulse,
  Activity,
  Syringe,
  Microscope,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { documentsApi } from '../../services/documents';
import type { EncounterCard as EncounterCardType } from '../../types';
import { formatShortDate, getEncounterCategoryFromCard } from '../../utils/patientTimeline';
import type { EncounterCategory } from '../../utils/patientTimeline';
import toast from 'react-hot-toast';

interface TimelineEncounterCardProps {
  encounter: EncounterCardType;
}

const CATEGORY_ICONS: Record<EncounterCategory, React.ReactNode> = {
  consultation: <Stethoscope className="h-5 w-5" />,
  'follow-up': <FileText className="h-5 w-5" />,
  checkup: <HeartPulse className="h-5 w-5" />,
  emergency: <AlertTriangle className="h-5 w-5" />,
  procedure: <Syringe className="h-5 w-5" />,
  vaccination: <Syringe className="h-5 w-5" />,
  lab: <Microscope className="h-5 w-5" />,
  general: <Activity className="h-5 w-5" />,
};

const CATEGORY_ICON_BG: Record<EncounterCategory, string> = {
  consultation: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
  'follow-up': 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
  checkup: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400',
  emergency: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
  procedure: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
  vaccination: 'bg-cyan-100 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-400',
  lab: 'bg-violet-100 text-violet-600 dark:bg-violet-900/30 dark:text-violet-400',
  general: 'bg-gray-100 text-gray-600 dark:bg-gray-800/30 dark:text-gray-400',
};

export function TimelineEncounterCard({ encounter }: TimelineEncounterCardProps) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [downloadingPrescription, setDownloadingPrescription] = useState(false);
  const [downloadingSummary, setDownloadingSummary] = useState(false);

  const category = getEncounterCategoryFromCard(encounter);
  const dateLabel = encounter.appointment_time
    ? formatShortDate(encounter.appointment_time)
    : '';

  const statusVariant =
    encounter.status === 'completed'
      ? 'default'
      : encounter.status === 'cancelled'
        ? 'destructive'
        : 'secondary';

  const handleCardClick = () => {
    navigate(`/patient/encounters/${encounter.appointment_id}`);
  };

  const handleDownloadPrescription = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setDownloadingPrescription(true);
    try {
      await documentsApi.triggerPrescriptionDownload(encounter.appointment_id);
      toast.success('Prescription downloaded');
    } catch {
      toast.error('Failed to download prescription');
    } finally {
      setDownloadingPrescription(false);
    }
  };

  const handleDownloadSummary = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setDownloadingSummary(true);
    try {
      await documentsApi.triggerEncounterSummaryDownload(encounter.appointment_id);
      toast.success('Encounter summary downloaded');
    } catch {
      toast.error('Failed to download encounter summary');
    } finally {
      setDownloadingSummary(false);
    }
  };

  return (
    <Card
      className="group relative z-10 cursor-pointer rounded-2xl border border-border/60 shadow-sm transition-all hover:border-primary/20 hover:shadow-md active:scale-[0.98] touch-manipulation"
      onClick={handleCardClick}
    >
      <CardContent className="p-4 sm:p-5">
        {/* ── Header: Icon + Doctor + Date + Status ──────────────────────── */}
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ring-2 ring-white/50 dark:ring-gray-800/50',
              CATEGORY_ICON_BG[category],
            )}
          >
            {CATEGORY_ICONS[category]}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-base font-semibold text-foreground">
                  {encounter.doctor_name}
                </h3>
                {encounter.doctor_specialization && (
                  <p className="truncate text-xs text-muted-foreground/70">
                    {encounter.doctor_specialization}
                  </p>
                )}
                {encounter.clinic_name && (
                  <p className="truncate text-xs text-muted-foreground/50">
                    {encounter.clinic_name}
                  </p>
                )}
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <Badge
                  variant={statusVariant}
                  className="capitalize text-[10px] px-2 py-0"
                >
                  {encounter.status}
                </Badge>
                {dateLabel && (
                  <span className="text-[10px] text-muted-foreground/60 whitespace-nowrap">
                    {dateLabel}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ── Diagnosis (collapsible if long) ────────────────────────────── */}
        {encounter.diagnosis && (
          <div className="mt-3 rounded-xl bg-muted/40 px-3.5 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Diagnosis
            </p>
            <p className="mt-0.5 text-sm text-foreground leading-relaxed">
              {expanded || encounter.diagnosis.length <= 100
                ? encounter.diagnosis
                : `${encounter.diagnosis.slice(0, 100)}…`}
            </p>
            {encounter.diagnosis.length > 100 && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(!expanded);
                }}
                className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline touch-manipulation min-h-[28px]"
              >
                {expanded ? (
                  <>
                    Show less <ChevronUp className="h-3 w-3" />
                  </>
                ) : (
                  <>
                    Read more <ChevronDown className="h-3 w-3" />
                  </>
                )}
              </button>
            )}
          </div>
        )}

        {/* ── Treatment Summary ──────────────────────────────────────────── */}
        {encounter.treatment_summary && (
          <div className="mt-2 rounded-xl bg-muted/30 px-3.5 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Treatment
            </p>
            <p className="mt-0.5 text-sm text-foreground leading-relaxed">
              {encounter.treatment_summary.length <= 120
                ? encounter.treatment_summary
                : `${encounter.treatment_summary.slice(0, 120)}…`}
            </p>
          </div>
        )}

        {/* ── Medicines prescribed ───────────────────────────────────────── */}
        {encounter.prescriptions_count > 0 && (
          <div className="mt-2 flex items-center gap-2 rounded-xl bg-blue-50/60 px-3.5 py-2 text-sm text-blue-700 dark:bg-blue-950/20 dark:text-blue-400">
            <Pill className="h-4 w-4 shrink-0" aria-hidden />
            <span className="text-sm">
              {encounter.prescriptions_count}{' '}
              {encounter.prescriptions_count === 1 ? 'medicine' : 'medicines'}{' '}
              prescribed
            </span>
          </div>
        )}

        {/* ── Follow-up badge ────────────────────────────────────────────── */}
        {encounter.follow_up_date && (
          <div className="mt-2 flex items-center gap-2 rounded-xl bg-amber-50/60 px-3.5 py-2 text-sm text-amber-700 dark:bg-amber-950/20 dark:text-amber-400">
            <FileText className="h-4 w-4 shrink-0" aria-hidden />
            <span className="text-sm">
              Follow-up: {dayjs(encounter.follow_up_date).format('MMM D, YYYY')}
            </span>
          </div>
        )}

        {/* ── Download buttons (always visible on mobile, hover on desktop) ── */}
        <div
          className={cn(
            'mt-3 flex flex-wrap items-center gap-2',
            'sm:opacity-0 sm:group-hover:opacity-100 transition-opacity',
          )}
        >
          {encounter.has_prescription && (
            <button
              type="button"
              onClick={handleDownloadPrescription}
              disabled={downloadingPrescription}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border/50 px-3 py-1.5 text-xs font-medium text-foreground/70 hover:bg-muted/50 transition-colors disabled:opacity-50 touch-manipulation min-h-[32px]"
            >
              {downloadingPrescription ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5" />
              )}
              Prescription
            </button>
          )}
          {encounter.has_encounter_summary && (
            <button
              type="button"
              onClick={handleDownloadSummary}
              disabled={downloadingSummary}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border/50 px-3 py-1.5 text-xs font-medium text-foreground/70 hover:bg-muted/50 transition-colors disabled:opacity-50 touch-manipulation min-h-[32px]"
            >
              {downloadingSummary ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5" />
              )}
              Summary
            </button>
          )}
        </div>

        {/* ── View details link ──────────────────────────────────────────── */}
        <div className="mt-3 flex justify-end">
          <span className="inline-flex items-center gap-1 text-xs font-medium text-primary">
            View details
            <ChevronRight className="h-3 w-3" aria-hidden />
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
