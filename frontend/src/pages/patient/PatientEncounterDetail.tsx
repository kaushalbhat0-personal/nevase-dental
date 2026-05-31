/**
 * PatientEncounterDetail — enhanced encounter detail page.
 *
 * PHASE UX2: Encounter Experience + Health Memory
 *
 * Upgraded with:
 * - Hero encounter header
 * - Visit type badge
 * - Doctor continuity card
 * - Timeline breadcrumbs
 * - Better prescription grouping
 * - Visit summary sections
 * - "Care provided" visual grouping
 * - Follow-up status card
 * - Document quick actions
 * - Sticky mobile actions
 * - Calm spacing and typography
 *
 * CRITICAL:
 * - SOAP internal sections are NEVER exposed
 * - Doctor-only notes are NEVER exposed
 * - Audit metadata is NEVER exposed
 *
 * Allowed:
 * - diagnosis
 * - treatment summary
 * - vitals
 * - prescriptions
 * - follow-up instructions
 * - visit date/time
 * - doctor identity
 */

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import {
  Download,
  FileText,
  HeartPulse,
  Pill,
  Thermometer,
  Activity,
  Weight,
  Ruler,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { encountersApi } from '../../services/appointments';
import { documentsApi } from '../../services/documents';
import type { EncounterDetailAggregate } from '../../types';
import { ErrorState } from '../../components/common';
import { EncounterHeroCard } from '../../components/patient/EncounterHeroCard';
import { EncounterJourneySection } from '../../components/patient/EncounterJourneySection';
import { getEncounterCategoryFromDetail } from '../../utils/patientTimeline';
import toast from 'react-hot-toast';

export function PatientEncounterDetail() {
  const { appointmentId } = useParams<{ appointmentId: string }>();
  const [encounter, setEncounter] = useState<EncounterDetailAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingPrescription, setDownloadingPrescription] = useState(false);
  const [downloadingSummary, setDownloadingSummary] = useState(false);

  useEffect(() => {
    if (!appointmentId) {
      setError('No appointment specified.');
      setLoading(false);
      return;
    }

    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await encountersApi.getById(appointmentId);
        if (!cancelled) setEncounter(data);
      } catch {
        if (!cancelled) setError('Unable to load encounter details.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [appointmentId]);

  const category = useMemo(
    () => (encounter ? getEncounterCategoryFromDetail(encounter) : 'general'),
    [encounter],
  );

  const handleDownloadPrescription = async () => {
    if (!appointmentId) return;
    setDownloadingPrescription(true);
    try {
      await documentsApi.triggerPrescriptionDownload(appointmentId);
      toast.success('Prescription downloaded');
    } catch {
      toast.error('Failed to download prescription');
    } finally {
      setDownloadingPrescription(false);
    }
  };

  const handleDownloadSummary = async () => {
    if (!appointmentId) return;
    setDownloadingSummary(true);
    try {
      await documentsApi.triggerEncounterSummaryDownload(appointmentId);
      toast.success('Encounter summary downloaded');
    } catch {
      toast.error('Failed to download encounter summary');
    } finally {
      setDownloadingSummary(false);
    }
  };

  if (error) {
    return <ErrorState title="Encounter Details" description={error} />;
  }

  if (loading) {
    return (
      <div className="space-y-5 px-0 sm:px-0">
        <Skeleton className="h-48 w-full rounded-2xl" />
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-24 w-full rounded-2xl" />
        <Skeleton className="h-40 w-full rounded-2xl" />
      </div>
    );
  }

  if (!encounter) {
    return <ErrorState title="Not Found" description="This encounter could not be found." />;
  }

  const { appointment, vitals, prescriptions } = encounter;
  const hasPrescriptions = (prescriptions?.length ?? 0) > 0;
  const hasVitals = vitals && Object.values(vitals).some((v) => v != null && v !== '');
  const hasFollowUp = !!appointment.follow_up_date;
  const documentCount = (appointment.status === 'completed' ? 1 : 0) + (hasPrescriptions ? 1 : 0);

  return (
    <div className="pb-24 sm:pb-8">
      {/* ── Hero header ──────────────────────────────────────────────────── */}
      <EncounterHeroCard
        encounter={encounter}
        category={category}
        visitNumber={encounter.timeline_context?.previous_visit_count ?? 0}
        totalEncounters={(encounter.timeline_context?.previous_visit_count ?? 0) + 1}
      />

      {/* ── Visit Journey ────────────────────────────────────────────────── */}
      <div className="mt-5">
        <EncounterJourneySection
          encounter={encounter}
          documentCount={documentCount}
        />
      </div>

      {/* ── Care Provided — Diagnosis + Treatment ────────────────────────── */}
      {(appointment.diagnosis || appointment.treatment_summary) && (
        <div className="mt-5 rounded-2xl border border-border/60 bg-card shadow-sm">
          <div className="px-5 pt-4 pb-3">
            <div className="flex items-center gap-2">
              <HeartPulse className="h-4 w-4 text-primary" aria-hidden />
              <h2 className="text-sm font-semibold text-foreground">Care Provided</h2>
            </div>
          </div>
          <div className="divide-y divide-border/40 px-5 pb-5">
            {appointment.diagnosis && (
              <div className="py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                  Diagnosis
                </p>
                <p className="text-sm text-foreground/90 leading-relaxed">
                  {appointment.diagnosis}
                </p>
              </div>
            )}
            {appointment.treatment_summary && (
              <div className="py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                  Treatment Summary
                </p>
                <p className="text-sm text-foreground/90 leading-relaxed">
                  {appointment.treatment_summary}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Vitals ────────────────────────────────────────────────────────── */}
      {hasVitals && (
        <div className="mt-5 rounded-2xl border border-border/60 bg-card shadow-sm">
          <div className="px-5 pt-4 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" aria-hidden />
              <h2 className="text-sm font-semibold text-foreground">Vitals</h2>
            </div>
          </div>
          <div className="px-5 pb-5">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {vitals!.bp_systolic != null && vitals!.bp_diastolic != null && (
                <div className="rounded-xl bg-muted/30 px-3.5 py-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Activity className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                      BP
                    </p>
                  </div>
                  <p className="text-lg font-bold text-foreground">
                    {vitals!.bp_systolic}/{vitals!.bp_diastolic}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">mmHg</span>
                  </p>
                </div>
              )}
              {vitals!.pulse != null && (
                <div className="rounded-xl bg-muted/30 px-3.5 py-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <HeartPulse className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                      Pulse
                    </p>
                  </div>
                  <p className="text-lg font-bold text-foreground">
                    {vitals!.pulse}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">bpm</span>
                  </p>
                </div>
              )}
              {vitals!.temperature != null && (
                <div className="rounded-xl bg-muted/30 px-3.5 py-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Thermometer className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                      Temp
                    </p>
                  </div>
                  <p className="text-lg font-bold text-foreground">
                    {vitals!.temperature}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">°F</span>
                  </p>
                </div>
              )}
              {vitals!.spo2 != null && (
                <div className="rounded-xl bg-muted/30 px-3.5 py-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Activity className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                      SpO₂
                    </p>
                  </div>
                  <p className="text-lg font-bold text-foreground">
                    {vitals!.spo2}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">%</span>
                  </p>
                </div>
              )}
              {vitals!.weight != null && (
                <div className="rounded-xl bg-muted/30 px-3.5 py-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Weight className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                      Weight
                    </p>
                  </div>
                  <p className="text-lg font-bold text-foreground">
                    {vitals!.weight}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">kg</span>
                  </p>
                </div>
              )}
              {vitals!.bmi != null && (
                <div className="rounded-xl bg-muted/30 px-3.5 py-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Ruler className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                      BMI
                    </p>
                  </div>
                  <p className="text-lg font-bold text-foreground">
                    {vitals!.bmi}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">kg/m²</span>
                  </p>
                </div>
              )}
            </div>
            {vitals!.notes && (
              <p className="mt-3 text-xs text-muted-foreground">{vitals!.notes}</p>
            )}
          </div>
        </div>
      )}

      {/* ── Prescriptions ────────────────────────────────────────────────── */}
      {hasPrescriptions && (
        <div className="mt-5 rounded-2xl border border-border/60 bg-card shadow-sm">
          <div className="px-5 pt-4 pb-3">
            <div className="flex items-center gap-2">
              <Pill className="h-4 w-4 text-primary" aria-hidden />
              <h2 className="text-sm font-semibold text-foreground">Prescriptions</h2>
            </div>
          </div>
          <div className="px-5 pb-5">
            <div className="space-y-3">
              {prescriptions!.map((rx) => (
                <div key={rx.id}>
                  {rx.notes && (
                    <p className="mb-2 text-sm text-muted-foreground">{rx.notes}</p>
                  )}
                  <div className="divide-y divide-border/50 rounded-xl border border-border/50">
                    {rx.items.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex flex-col gap-1 px-3.5 py-3 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div>
                          <p className="text-sm font-medium text-foreground">
                            {item.medicine_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {[item.dosage, item.frequency, item.duration]
                              .filter(Boolean)
                              .join(' · ')}
                          </p>
                        </div>
                        {item.instructions && (
                          <p className="text-xs text-muted-foreground/70 italic">
                            {item.instructions}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Follow-up ────────────────────────────────────────────────────── */}
      {hasFollowUp && (
        <div className="mt-5 rounded-2xl border border-amber-200/60 bg-amber-50/30 shadow-sm dark:border-amber-800/30 dark:bg-amber-950/10">
          <div className="px-5 pt-4 pb-3">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-amber-600 dark:text-amber-400" aria-hidden />
              <h2 className="text-sm font-semibold text-amber-700 dark:text-amber-400">
                Follow-up Scheduled
              </h2>
            </div>
          </div>
          <div className="px-5 pb-5">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-100 dark:bg-amber-900/30">
                <FileText className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {dayjs(appointment.follow_up_date).format('dddd, MMMM D, YYYY')}
                </p>
                {appointment.follow_up_notes && (
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {appointment.follow_up_notes}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Document quick actions ───────────────────────────────────────── */}
      {(hasPrescriptions || appointment.status === 'completed') && (
        <div className="mt-5 rounded-2xl border border-border/60 bg-card shadow-sm">
          <div className="px-5 pt-4 pb-3">
            <div className="flex items-center gap-2">
              <Download className="h-4 w-4 text-primary" aria-hidden />
              <h2 className="text-sm font-semibold text-foreground">Documents</h2>
            </div>
          </div>
          <div className="px-5 pb-5">
            <div className="space-y-2">
              {hasPrescriptions && (
                <button
                  type="button"
                  onClick={handleDownloadPrescription}
                  disabled={downloadingPrescription}
                  className="flex w-full items-center gap-3 rounded-xl border border-border/50 px-4 py-3 text-left transition-colors hover:bg-muted/30 active:bg-muted/50 disabled:opacity-50 touch-manipulation min-h-[48px]"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-950/20">
                    <Pill className="h-4 w-4 text-blue-500" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">Prescription</p>
                    <p className="text-xs text-muted-foreground">Download PDF</p>
                  </div>
                  {downloadingPrescription ? (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  ) : (
                    <Download className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
              )}
              {appointment.status === 'completed' && (
                <button
                  type="button"
                  onClick={handleDownloadSummary}
                  disabled={downloadingSummary}
                  className="flex w-full items-center gap-3 rounded-xl border border-border/50 px-4 py-3 text-left transition-colors hover:bg-muted/30 active:bg-muted/50 disabled:opacity-50 touch-manipulation min-h-[48px]"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 dark:bg-emerald-950/20">
                    <FileText className="h-4 w-4 text-emerald-500" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">Encounter Summary</p>
                    <p className="text-xs text-muted-foreground">Download PDF</p>
                  </div>
                  {downloadingSummary ? (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  ) : (
                    <Download className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Sticky mobile actions ────────────────────────────────────────── */}
      {(hasPrescriptions || appointment.status === 'completed') && (
        <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-border/60 bg-background/95 backdrop-blur-lg pb-safe-or-4 sm:hidden">
          <div className="flex gap-2 px-4 py-3">
            {hasPrescriptions && (
              <Button
                variant="default"
                className="flex-1 rounded-xl text-sm"
                onClick={handleDownloadPrescription}
                disabled={downloadingPrescription}
              >
                {downloadingPrescription ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                Prescription
              </Button>
            )}
            {appointment.status === 'completed' && (
              <Button
                variant="outline"
                className="flex-1 rounded-xl text-sm"
                onClick={handleDownloadSummary}
                disabled={downloadingSummary}
              >
                {downloadingSummary ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <FileText className="mr-2 h-4 w-4" />
                )}
                Summary
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
