import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { ArrowLeft, Calendar, FileText, IndianRupee, User } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button, buttonVariants } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { EmptyState, ErrorState } from '../../components/common';
import { useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import { DISPLAY_TIMEZONE } from '../../constants/time';
import {
  appointmentCalendarDayYmd,
  formatSlotTimeWithZoneLabel,
  relativeCalendarDayTitleInZone,
} from '../../utils/doctorSchedule';
import { appointmentsApi, billingApi, patientsApi } from '../../services';
import { Textarea } from '@/components/ui/textarea';
import type { Appointment, Bill, Patient, VisitAggregate } from '../../types';

type Section = 'activity' | 'bills' | 'info';

/**
 * Timeline is visit-centric.
 * One clinical encounter renders as one VisitAggregate card,
 * even if billing/inventory metadata exists.
 *
 * TODO: Future extensions for Phase 2 clinical features:
 * - Add prescriptions to VisitAggregate display
 * - Add vitals to VisitAggregate display
 * - Add attachments to VisitAggregate display
 * - Add follow-up plans to VisitAggregate display
 * - Add AI visit summaries
 */
type TimelineItem =
  | {
      id: string;
      kind: 'visit';
      at: number;
      dayKey: string;
      iso: string;
      /** VisitAggregate: appointment + attached metadata (bill, inventory, prescriptions, etc.) */
      visit: VisitAggregate;
    }
  | {
      id: string;
      kind: 'bill-only';
      at: number;
      dayKey: string;
      iso: string;
      bill: Bill;
    };

function appointmentTime(a: Appointment): number {
  const t = a.appointment_time || a.scheduled_at;
  return t ? new Date(t).getTime() : 0;
}

function kindPriority(k: TimelineItem['kind']): number {
  return k === 'visit' ? 0 : 1;
}

function formatRelativePast(iso: string | undefined): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '—';
  const diff = Date.now() - t;
  const days = Math.floor(diff / 86_400_000);
  if (days < 0) return '—';
  if (days === 0) return 'Today';
  if (days === 1) return '1 day ago';
  return `${days} days ago`;
}

function apptCanAct(s: Appointment['status']): boolean {
  return s === 'scheduled' || s === 'pending';
}

function apptStatusVariant(
  s: Appointment['status']
): 'default' | 'secondary' | 'outline' | 'destructive' {
  if (s === 'completed') return 'secondary';
  if (s === 'cancelled') return 'destructive';
  if (s === 'scheduled' || s === 'pending') return 'default';
  return 'outline';
}

function billStatusLabel(status: Bill['status']): { label: string; className: string } {
  if (status === 'paid') {
    return {
      label: 'Paid',
      className: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200',
    };
  }
  if (status === 'unpaid') {
    return { label: 'Unpaid', className: 'border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200' };
  }
  return { label: status, className: '' };
}

function HeaderLoadingSkeleton() {
  return (
    <div className="flex h-full min-h-0 flex-col justify-between" aria-hidden>
      <div className="h-4 w-24 animate-pulse rounded bg-muted" />
      <div className="min-w-0 flex-1 space-y-2 py-1">
        <div className="h-5 w-48 max-w-full rounded-md bg-muted animate-pulse" />
        <div className="h-4 w-40 max-w-full rounded-md bg-muted animate-pulse" />
      </div>
      <div className="flex gap-2 pt-1">
        <div className="h-8 flex-1 rounded-md bg-muted animate-pulse" />
        <div className="h-8 flex-1 rounded-md bg-muted animate-pulse" />
      </div>
    </div>
  );
}

function getScrollParent(from: HTMLElement | null): HTMLElement | Window | null {
  let el: HTMLElement | null = from?.parentElement ?? null;
  while (el && el !== document.body) {
    const { overflowY } = getComputedStyle(el);
    if (overflowY === 'auto' || overflowY === 'scroll') return el;
    el = el.parentElement;
  }
  return typeof window !== 'undefined' ? window : null;
}

const lerp = (start: number, end: number, t: number) => start + (end - start) * t;

export function DoctorPatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isIndependent, isReadOnly } = useDoctorWorkspace();
  const pageRootRef = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(0);
  const [ready, setReady] = useState(false);
  const [section, setSection] = useState<Section>('activity');
  const [patient, setPatient] = useState<Patient | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<'forbidden' | 'notfound' | 'other' | null>(null);
  const [rowBusyKey, setRowBusyKey] = useState<string | null>(null);
  const [notesDraft, setNotesDraft] = useState('');
  const [notesSaving, setNotesSaving] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setLoadError(null);
    setPatient(null);
    setAppointments([]);
    setBills([]);
    try {
      // Future: single GET /patients/{id}/summary could replace the parallel fetches below.
      const [p, apts, bls] = await Promise.all([
        patientsApi.getById(id),
        appointmentsApi.getAll({ patient_id: id, skip: 0, limit: 100 }),
        billingApi.getAll({ patient_id: id, skip: 0, limit: 100 }),
      ]);
      setPatient(p);
      setAppointments(apts);
      setBills(bls);
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 403) {
        setLoadError('forbidden');
      } else if (axios.isAxiosError(e) && e.response?.status === 404) {
        setLoadError('notfound');
      } else {
        setLoadError('other');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setNotesDraft(patient?.clinical_notes ?? '');
  }, [patient?.id, patient?.clinical_notes]);

  useLayoutEffect(() => {
    const root = pageRootRef.current;
    if (!root) {
      setReady(true);
      return;
    }
    const scrollTarget = getScrollParent(root);
    if (!scrollTarget) {
      setReady(true);
      return;
    }

    const readY = () =>
      scrollTarget === window ? window.scrollY : (scrollTarget as HTMLElement).scrollTop;

    const threshold = 100;
    const y = readY();
    setProgress(Math.min(Math.max(y / threshold, 0), 1));
    setReady(true);
  }, [id]);

  useEffect(() => {
    const root = pageRootRef.current;
    if (!root) return;
    const scrollTarget = getScrollParent(root);
    if (!scrollTarget) return;

    const readY = () =>
      scrollTarget === window ? window.scrollY : (scrollTarget as HTMLElement).scrollTop;

    const threshold = 100;

    const handleScroll = () => {
      const y = readY();
      const p = Math.min(Math.max(y / threshold, 0), 1);
      setProgress(p);
    };

    scrollTarget.addEventListener('scroll', handleScroll, { passive: true });
    return () => scrollTarget.removeEventListener('scroll', handleScroll);
  }, [id]);

  const stats = useMemo(() => {
    const completed = appointments.filter((a) => a.status === 'completed');
    const visitTimes = completed
      .map((a) => a.appointment_time || a.scheduled_at)
      .filter(Boolean) as string[];
    const lastVisitIso =
      visitTimes.length > 0
        ? visitTimes.reduce((best, cur) => (new Date(cur) > new Date(best) ? cur : best), visitTimes[0])
        : null;
    return {
      totalVisits: completed.length,
      lastVisitLabel: lastVisitIso ? formatRelativePast(lastVisitIso) : '—',
    };
  }, [appointments]);

  const outstandingBills = useMemo(
    () => bills.filter((b) => b.status === 'unpaid'),
    [bills]
  );

  /**
   * Build visit-centric timeline.
   * Each appointment becomes one VisitAggregate card.
   * Bills are attached to their appointment visits, not shown separately.
   */
  const { timelineByDay, dayOrder } = useMemo(() => {
    const items: TimelineItem[] = [];
    const processedBillIds = new Set<string>();

    // Build VisitAggregate for each appointment (visit-centric grouping)
    for (const a of appointments) {
      const raw = a.appointment_time || a.scheduled_at;
      const t = appointmentTime(a);
      if (!raw || !t) continue;
      const dayKey = appointmentCalendarDayYmd(raw, DISPLAY_TIMEZONE);
      if (!dayKey) continue;

      // Find attached bill for this appointment
      const bill = bills.find((b) =>
        b.appointment_id && String(b.appointment_id) === String(a.id)
      );

      if (bill) {
        processedBillIds.add(String(bill.id));
      }

      // Create VisitAggregate: appointment + attached metadata
      const visitAggregate: VisitAggregate = {
        appointment: a,
        bill: bill || null,
        inventoryUsage: a.inventory_usages,
      };

      items.push({
        id: `visit-${a.id}`,
        kind: 'visit',
        at: t,
        dayKey,
        iso: raw,
        visit: visitAggregate,
      });
    }

    // Add orphaned bills (bills without appointments) as separate timeline items
    for (const b of bills) {
      if (processedBillIds.has(String(b.id))) continue;

      const raw = b.created_at || b.updated_at;
      const t = raw ? new Date(raw).getTime() : 0;
      if (!raw || !t) continue;
      const dayKey = appointmentCalendarDayYmd(raw, DISPLAY_TIMEZONE);
      if (!dayKey) continue;

      items.push({
        id: `bill-${b.id}`,
        kind: 'bill-only',
        at: t,
        dayKey,
        iso: raw,
        bill: b,
      });
    }
    
    const byDay = new Map<string, TimelineItem[]>();
    for (const it of items) {
      if (!byDay.has(it.dayKey)) byDay.set(it.dayKey, []);
      byDay.get(it.dayKey)!.push(it);
    }
    for (const [, arr] of byDay) {
      arr.sort((x, y) => {
        if (y.at !== x.at) return y.at - x.at;
        return kindPriority(x.kind) - kindPriority(y.kind);
      });
    }
    const order = Array.from(byDay.keys()).sort((a, b) => b.localeCompare(a));
    return { timelineByDay: byDay, dayOrder: order };
  }, [appointments, bills]);

  if (!id) {
    return <ErrorState title="Invalid link" description="This patient page address is not valid." />;
  }

  if (loadError === 'forbidden') {
    return (
      <ErrorState
        title="Access denied"
        description="You can open patients in your organization or those linked to you by appointment. If this looks wrong, ask an administrator."
      />
    );
  }

  if (loadError === 'notfound' && !loading) {
    return (
      <ErrorState
        title="Patient not found"
        description="This ID does not match a record you can see, or it was removed."
        onRetry={() => void load()}
      />
    );
  }

  if (loadError === 'other' && !loading) {
    return (
      <ErrorState
        title="Could not load patient"
        description="We could not load this record. The network may have failed — try again."
        onRetry={() => void load()}
      />
    );
  }

  const contactLine = [patient?.phone, patient?.email].filter(Boolean).join(' · ');

  const goBook = () => {
    if (!id) return;
    navigate('/doctor/appointments', { state: { openSchedule: true, bookPatientId: id } });
  };

  const goCreateBill = () => {
    if (!id) return;
    navigate('/doctor/bills', { state: { openCreateBill: true, billPatientId: id } });
  };

  const canMutate = isIndependent && !isReadOnly;

  const openEncounter = (apptId: string) => {
    navigate(`/doctor/appointments/${apptId}`);
  };

  const cancelAppointment = async (apptId: string) => {
    const key = `a-${apptId}`;
    setRowBusyKey(key);
    try {
      await appointmentsApi.update(apptId, { status: 'cancelled' });
      toast.success('Appointment cancelled');
      await load();
    } catch (e) {
      const msg =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not cancel')
          : 'Could not cancel appointment';
      toast.error(msg);
    } finally {
      setRowBusyKey(null);
    }
  };

  const markBillPaid = async (billId: string) => {
    const key = `b-${billId}`;
    setRowBusyKey(key);
    try {
      await billingApi.pay(billId);
      toast.success('Marked as paid');
      await load();
    } catch (e) {
      const msg =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not update bill')
          : 'Could not mark bill paid';
      toast.error(msg);
    } finally {
      setRowBusyKey(null);
    }
  };

  /** Save persistent patient context notes (NOT visit-specific clinical notes). */
  const savePatientContextNotes = async () => {
    if (!id || !patient) return;
    setNotesSaving(true);
    try {
      const updated = await patientsApi.update(id, { clinical_notes: notesDraft.trim() || null });
      setPatient(updated);
      toast.success('Patient context saved');
    } catch (e) {
      const msg =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not save')
          : 'Could not save patient context';
      toast.error(msg);
    } finally {
      setNotesSaving(false);
    }
  };

  const showActions = isIndependent && !isReadOnly;
  const inHeaderSkeleton = loading && !patient;
  /** Expanded header needs extra height when actions/skeleton rows exist */
  const headerExpandedNeedsTallRow = showActions || inHeaderSkeleton;
  const scrollProgress = ready ? progress : 0;
  /** While the header skeleton shows, stay fully expanded (same as old `!collapsed || inHeaderSkeleton`) */
  const t = inHeaderSkeleton ? 0 : scrollProgress;

  const expandedHeight = headerExpandedNeedsTallRow ? 184 : 132;
  const height = lerp(expandedHeight, 56, t);
  const nameSize = lerp(18, 15, t);
  const buttonScale = lerp(1, 0.85, t);
  const expandedOpacity = 1 - t;
  const collapsedOpacity = t;
  const layerTransition =
    'transform 0.1s linear, opacity 0.1s linear';

  return (
    <div ref={pageRootRef} className="min-h-full bg-muted/30">
      <div className="mx-auto max-w-md">
        <div
          className="sticky top-0 z-30 border-b border-border/80 backdrop-blur bg-white/80 supports-[backdrop-filter]:bg-white/70 dark:bg-background/80 dark:supports-[backdrop-filter]:bg-background/70 shadow-sm dark:shadow-black/10"
          style={{
            height: `${height}px`,
            transition: 'height 0.1s linear',
          }}
        >
          <div className="relative h-full overflow-hidden">
            {/* Expanded */}
            <div
              className="absolute inset-0 flex flex-col justify-between px-4 py-3"
              style={{
                opacity: expandedOpacity,
                transform: `translateY(${lerp(0, -10, t)}px)`,
                transition: layerTransition,
                pointerEvents: expandedOpacity < 0.02 ? 'none' : 'auto',
              }}
            >
              {inHeaderSkeleton ? (
                <HeaderLoadingSkeleton />
              ) : (
                <>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Link
                      to="/doctor/patients"
                      className={cn(
                        buttonVariants({ variant: 'ghost', size: 'sm' }),
                        '-ml-2 h-8 gap-1.5 px-2 text-muted-foreground'
                      )}
                    >
                      <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
                      Patients
                    </Link>
                  </div>

                  <div className="min-w-0">
                    <div
                      className="truncate font-semibold tracking-tight text-foreground"
                      style={{ fontSize: `${nameSize}px` }}
                    >
                      {patient?.name || 'Patient'}
                    </div>
                    <div className="truncate text-sm text-muted-foreground">
                      {contactLine || 'No phone or email on file'}
                    </div>
                  </div>

                  {showActions ? (
                    <div
                      className="flex gap-2 pt-1"
                      style={{
                        transform: `scale(${buttonScale})`,
                        transition: 'transform 0.1s linear',
                        transformOrigin: 'center bottom',
                      }}
                    >
                      <Button type="button" size="sm" className="flex-1" onClick={goBook}>
                        Book appointment
                      </Button>
                      <Button type="button" size="sm" variant="outline" className="flex-1" onClick={goCreateBill}>
                        Create bill
                      </Button>
                    </div>
                  ) : (
                    <div className="shrink-0" aria-hidden />
                  )}
                </>
              )}
            </div>

            {/* Collapsed — compact */}
            <div
              className="absolute inset-0 flex items-center justify-between px-4"
              style={{
                opacity: collapsedOpacity,
                transform: `translateY(${lerp(10, 0, t)}px)`,
                transition: layerTransition,
                pointerEvents: collapsedOpacity < 0.02 ? 'none' : 'auto',
              }}
            >
              <div className="flex min-w-0 flex-1 items-center gap-2">
                <Link
                  to="/doctor/patients"
                  className={cn(
                    buttonVariants({ variant: 'ghost', size: 'icon' }),
                    'h-8 w-8 shrink-0 rounded-full text-muted-foreground'
                  )}
                  aria-label="Back to patients"
                >
                  <ArrowLeft className="h-5 w-5" aria-hidden />
                </Link>
                <span
                  className="max-w-[140px] truncate font-medium text-foreground"
                  style={{ fontSize: `${nameSize}px` }}
                >
                  {patient?.name || 'Patient'}
                </span>
              </div>
              {showActions ? (
                <div
                  className="flex shrink-0 gap-2"
                  style={{
                    transform: `scale(${buttonScale})`,
                    transition: 'transform 0.1s linear',
                  }}
                >
                  <Button
                    type="button"
                    className="h-8 shrink-0 rounded-full px-3 text-sm"
                    onClick={goBook}
                  >
                    Book
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="h-8 shrink-0 rounded-full border px-3 text-sm"
                    onClick={goCreateBill}
                  >
                    Bill
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="space-y-6 px-4 py-4 pb-24">
      {!loading && patient && (
        <div className="flex flex-col gap-4">
          <Card className="flex flex-col gap-3">
            <div className="text-sm text-muted-foreground">Total visits</div>
            <div className="text-lg font-semibold tabular-nums">{stats.totalVisits}</div>
          </Card>
          <Card className="flex flex-col gap-3">
            <div className="text-sm text-muted-foreground">Last visit</div>
            <div className="text-lg font-semibold">{stats.lastVisitLabel}</div>
          </Card>
          <Card className="flex flex-col gap-3">
            <div className="text-sm text-muted-foreground">Outstanding bills</div>
            {outstandingBills.length === 0 ? (
              <div className="text-sm text-muted-foreground">No bills</div>
            ) : (
              <ul className="flex flex-col gap-2">
                {outstandingBills.map((b) => (
                  <li key={String(b.id)} className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-lg font-semibold tabular-nums">
                      {b.currency} {Number(b.amount).toFixed(0)}
                    </span>
                    <Link
                      to={`/doctor/bills/${b.id}`}
                      className="text-sm text-primary font-medium hover:underline shrink-0"
                    >
                      View bill
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}

      {!loading && (
        <div className="flex flex-wrap gap-2 border-b border-border pb-3">
          {(
            [
              { key: 'activity' as const, label: 'Activity', icon: Calendar },
              { key: 'bills' as const, label: 'Bills', icon: FileText },
              { key: 'info' as const, label: 'Basic info', icon: User },
            ] as const
          ).map(({ key, label, icon: Icon }) => (
            <Button
              key={key}
              type="button"
              size="sm"
              variant={section === key ? 'default' : 'outline'}
              onClick={() => setSection(key)}
              className={cn('gap-1.5', section === key && 'shadow-sm')}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden />
              {label}
            </Button>
          ))}
        </div>
      )}

      {!loading && section === 'activity' && (
        <div className="flex flex-col gap-4">
          {patient && (
            <Card className="rounded-xl border bg-white p-4 shadow-md relative z-0">
              <CardHeader className="pb-2 px-0 pt-0">
                <CardTitle className="text-base">Patient Context Notes</CardTitle>
                <CardDescription>Persistent context across all visits (not visit-specific)</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 px-0 pb-0">
                {canMutate ? (
                  <>
                    <Textarea
                      value={notesDraft}
                      onChange={(e) => setNotesDraft(e.target.value)}
                      placeholder="e.g. Chronic conditions, allergies, ongoing medications, family history..."
                      disabled={notesSaving}
                      className="min-h-[88px] resize-y"
                    />
                    <div className="flex justify-end">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => void savePatientContextNotes()}
                        disabled={notesSaving || notesDraft === (patient.clinical_notes ?? '')}
                      >
                        {notesSaving ? 'Saving…' : 'Save context'}
                      </Button>
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-foreground/90 whitespace-pre-wrap rounded-md border border-border/60 bg-muted/20 px-3 py-2 min-h-[4.5rem]">
                    {patient.clinical_notes?.trim() ? patient.clinical_notes : 'No patient context on file.'}
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {dayOrder.length === 0 && (
            <EmptyState
              title="No appointments yet"
              description="When you schedule visits or add bills, they will appear on this timeline."
              action={
                isIndependent && !isReadOnly
                  ? { label: 'Book first appointment', onClick: goBook }
                  : undefined
              }
            />
          )}

          {dayOrder.length > 0 && (
            <div className="flex flex-col gap-4">
              {dayOrder.map((dayKey, dayIdx) => {
                const list = timelineByDay.get(dayKey) ?? [];
                const sampleIso = list[0]?.iso;
                return (
                  <div
                    key={dayKey}
                    className={cn(dayIdx > 0 && 'border-t border-border/50 pt-4')}
                  >
                    <h2 className="text-lg font-semibold tracking-tight text-foreground border-b border-border/60 pb-2 mb-4">
                      {sampleIso ? relativeCalendarDayTitleInZone(sampleIso, DISPLAY_TIMEZONE) : ''}
                    </h2>
                    <ul className="space-y-3">
                      {list.map((it) => {
                        if (it.kind === 'visit') {
                          const a = it.visit.appointment;
                          const b = it.visit.bill;
                          const inv = it.visit.inventoryUsage;
                          const canCompleteOrCancel = canMutate && apptCanAct(a.status);
                          const st = b ? billStatusLabel(b.status) : null;

                          return (
                            <li
                              key={it.id}
                              className="flex gap-3 text-sm rounded-lg border border-border/60 bg-card/30 px-3 py-2.5"
                            >
                              <div
                                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                                aria-hidden
                              >
                                <Calendar className="h-4 w-4" />
                              </div>
                              <div className="min-w-0 flex-1 space-y-1.5">
                                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                                  <p className="text-muted-foreground tabular-nums">
                                    <span className="font-medium text-foreground">
                                      {formatSlotTimeWithZoneLabel(
                                        a.appointment_time || a.scheduled_at || '',
                                        DISPLAY_TIMEZONE
                                      )}
                                    </span>
                                    <span className="mx-1.5 text-border">·</span>
                                    <span className="text-foreground">Visit</span>{' '}
                                    <Badge
                                      variant={apptStatusVariant(a.status)}
                                      className="capitalize align-middle ml-0.5"
                                    >
                                      {a.status}
                                    </Badge>
                                  </p>
                                  <div className="flex flex-wrap gap-x-3 gap-y-1 shrink-0">
                                    <Link
                                      to={`/doctor/appointments/${a.id}`}
                                      className="text-primary text-xs font-medium hover:underline"
                                    >
                                      View encounter
                                    </Link>
                                  </div>
                                </div>

                                {/*
                                  Clinical encounter documentation hierarchy (clinical-first):
                                  1. Diagnosis (most important clinical output)
                                  2. Treatment summary (what was done)
                                  3. Clinical notes (detailed observations)
                                  4. Medicines used (inventory)
                                  5. Bill summary (secondary, visually lighter)
                                */}
                                {(a.diagnosis || a.treatment_summary || a.clinical_notes) && (
                                  <div className="space-y-1 text-xs text-muted-foreground border-t border-border/50 pt-2">
                                    {a.diagnosis && (
                                      <p><span className="font-medium text-foreground">Diagnosis:</span> {a.diagnosis}</p>
                                    )}
                                    {a.treatment_summary && (
                                      <p><span className="font-medium text-foreground">Treatment:</span> {a.treatment_summary}</p>
                                    )}
                                    {a.clinical_notes && (
                                      <p><span className="font-medium text-foreground">Clinical notes:</span> {a.clinical_notes}</p>
                                    )}
                                    {/* DEPRECATED: completion_notes preserved for backward compatibility */}
                                    {a.completion_notes && (
                                      <p><span className="font-medium text-foreground">Notes (legacy):</span> {a.completion_notes}</p>
                                    )}
                                  </div>
                                )}

                                {/* Show inventory usage if available */}
                                {a.status === 'completed' && inv && inv.length > 0 && (
                                  <div className="text-xs text-muted-foreground">
                                    <p className="font-medium text-foreground">Medicines given:</p>
                                    <ul className="list-disc pl-4 mt-1 space-y-0.5">
                                      {inv.map((u) => (
                                        <li key={u.item_id}>
                                          {u.item_name || 'Item'} × {u.quantity}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {/* Bill summary - visually lighter, secondary */}
                                {b && (
                                  <div className="flex items-center gap-2 text-xs border-t border-border/30 pt-2">
                                    <IndianRupee className="h-3 w-3 text-muted-foreground" />
                                    <span className="text-muted-foreground">
                                      {b.currency} {Number(b.amount).toFixed(0)}
                                    </span>
                                    <Badge
                                      variant="outline"
                                      className={cn('capitalize text-[0.65rem] py-0', st?.className)}
                                    >
                                      {st?.label}
                                    </Badge>
                                    <Link
                                      to={`/doctor/bills/${b.id}`}
                                      className="text-primary font-medium hover:underline ml-auto"
                                    >
                                      View bill
                                    </Link>
                                  </div>
                                )}
                                
                                {canCompleteOrCancel && (
                                  <div className="flex flex-wrap gap-2">
                                    <Button
                                      type="button"
                                      variant="secondary"
                                      size="sm"
                                      className="h-7 text-xs"
                                      disabled={rowBusyKey === it.id}
                                      onClick={() => openEncounter(String(a.id))}
                                    >
                                      Start Encounter
                                    </Button>
                                    <Button
                                      type="button"
                                      variant="outline"
                                      size="sm"
                                      className="h-7 text-xs"
                                      disabled={rowBusyKey === it.id}
                                      onClick={() => void cancelAppointment(String(a.id))}
                                    >
                                      Cancel
                                    </Button>
                                  </div>
                                )}
                              </div>
                            </li>
                          );
                        }
                        
                        // Bill-only card (for bills without appointments)
                        const b = it.bill;
                        const st = billStatusLabel(b.status);
                        const canPay = canMutate && b.status === 'unpaid';
                        return (
                          <li
                            key={it.id}
                            className="flex gap-3 text-sm rounded-lg border border-border/60 bg-card/30 px-3 py-2.5"
                          >
                            <div
                              className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-500/10 text-amber-800 dark:text-amber-300"
                              aria-hidden
                            >
                              <IndianRupee className="h-4 w-4" />
                            </div>
                            <div className="min-w-0 flex-1 space-y-1.5">
                              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                                <p className="text-muted-foreground tabular-nums">
                                  <span className="font-medium text-foreground">
                                    {formatSlotTimeWithZoneLabel(it.iso, DISPLAY_TIMEZONE)}
                                  </span>
                                  <span className="mx-1.5 text-border">·</span>
                                  <span className="text-foreground font-medium">
                                    {b.currency} {Number(b.amount).toFixed(0)}
                                  </span>
                                  <span className="text-muted-foreground"> — Bill</span>{' '}
                                  <Badge
                                    variant="outline"
                                    className={cn('capitalize align-middle text-[0.7rem] py-0', st.className)}
                                  >
                                    {st.label}
                                  </Badge>
                                </p>
                                <div className="flex flex-wrap gap-x-3 gap-y-1 shrink-0">
                                  <Link
                                    to={`/doctor/bills/${b.id}`}
                                    className="text-primary text-xs font-medium hover:underline"
                                  >
                                    View bill
                                  </Link>
                                </div>
                              </div>
                              {canPay && (
                                <div className="flex flex-wrap gap-2">
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="secondary"
                                    className="h-7 text-xs"
                                    disabled={rowBusyKey === it.id}
                                    onClick={() => void markBillPaid(String(b.id))}
                                  >
                                    {rowBusyKey === it.id ? '…' : 'Mark as paid'}
                                  </Button>
                                </div>
                              )}
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {!loading && section === 'bills' && (
        <div className="flex flex-col gap-4">
          {bills.length === 0 && (
            <EmptyState
              title="No bills yet"
              description="Create a bill from a scheduled visit, or use Create bill to start from this patient."
              action={
                isIndependent && !isReadOnly
                  ? { label: 'Create bill', onClick: goCreateBill }
                  : undefined
              }
            />
          )}
          {bills.length > 0 &&
            bills.map((b) => {
              const st = billStatusLabel(b.status);
              const appt = b.appointment_id
                ? appointments.find((x) => String(x.id) === String(b.appointment_id))
                : undefined;
              const apptTime = appt
                ? formatSlotTimeWithZoneLabel(
                    appt.appointment_time || appt.scheduled_at || '',
                    DISPLAY_TIMEZONE
                  )
                : null;
              return (
                <Card key={String(b.id)}>
                  <CardContent className="flex flex-wrap items-start justify-between gap-3 text-sm">
                    <div className="space-y-1 min-w-0">
                      <p className="font-medium tabular-nums">
                        {b.currency} {Number(b.amount).toFixed(2)}
                      </p>
                      {b.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2">{b.description}</p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        <Link to={`/doctor/bills/${b.id}`} className="text-primary font-medium hover:underline">
                          View bill
                        </Link>
                        {b.appointment_id && (
                          <>
                            {' · '}
                            <Link
                              to={`/doctor/appointments/${b.appointment_id}`}
                              className="text-primary hover:underline"
                            >
                              {apptTime ? `Encounter (${apptTime})` : 'View encounter'}
                            </Link>
                          </>
                        )}
                      </p>
                    </div>
                    <Badge
                      variant="outline"
                      className={cn('shrink-0', st.className)}
                    >
                      {st.label}
                    </Badge>
                  </CardContent>
                </Card>
              );
            })}
        </div>
      )}

      {!loading && section === 'info' && (
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
              <CardDescription>Demographics and contact details on file</CardDescription>
            </CardHeader>
            <CardContent className="text-sm space-y-3 max-w-md">
            <div className="grid grid-cols-[8rem_1fr] gap-2">
              <span className="text-muted-foreground">Name</span>
              <span>{patient?.name || '—'}</span>
              <span className="text-muted-foreground">Age</span>
              <span>{patient?.age != null ? patient.age : '—'}</span>
              <span className="text-muted-foreground">Gender</span>
              <span>{patient?.gender || '—'}</span>
              <span className="text-muted-foreground">Phone</span>
              <span>{patient?.phone || '—'}</span>
              <span className="text-muted-foreground">Email</span>
              <span className="break-all">{patient?.email || '—'}</span>
            </div>
            {patient?.medical_history && (
              <div className="pt-2 border-t border-border">
                <p className="text-xs font-medium text-muted-foreground mb-1">Notes</p>
                <p className="whitespace-pre-wrap text-foreground/90">{patient.medical_history}</p>
              </div>
            )}
          </CardContent>
        </Card>
        </div>
      )}
        </div>
      </div>
    </div>
  );
}
