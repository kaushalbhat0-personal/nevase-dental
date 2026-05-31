import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { LayoutGrid, List, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import {
  appointmentsApi,
  doctorsApi,
  invalidateDoctorSlotsClientCache,
  shouldSyncSlotsCrossTab,
  SLOTS_CROSS_TAB_BROADCAST,
  type DoctorSlot,
} from '../../../services';
import type { Appointment, Patient } from '../../../types';
import { DISPLAY_TIMEZONE } from '../../../constants/time';
import {
  addDaysYmd,
  appointmentCalendarDayYmd,
  calendarTodayYmdInZone,
  dedupeDoctorSlots,
  formatNextAvailablePhrase,
  formatSlotTime,
  formatTimeZoneCaption,
  getCalendarViewWindow,
  isSlotInPast,
  listHourGridTicks,
  nowLinePercentInView,
  parseAndClampDateParam,
  slotBlockInView,
  slotInstantUtcMs,
  slotKey,
} from '../../../utils/doctorSchedule';
import { BookingModal } from './BookingModal';
import { SwipeableSlotActions } from './SwipeableSlotActions';

const CALENDAR_VIEW_STORAGE_KEY = 'calendar_view';
type CalendarViewMode = 'grid' | 'list';

type PlacedSlot = {
  slot: DoctorSlot;
  topPct: number;
  heightPct: number;
  clippedOut: boolean;
  lane: number;
  laneCount: number;
};

function assignPlacementLanes(
  sorted: DoctorSlot[],
  viewStart: import('dayjs').Dayjs,
  viewEnd: import('dayjs').Dayjs,
  totalMinutes: number
): PlacedSlot[] {
  const laneEnds: number[] = [];
  const out: PlacedSlot[] = [];
  for (const s of sorted) {
    const dur = s.duration_minutes ?? 30;
    const t0 = slotInstantUtcMs(s.start);
    const t1 = t0 + dur * 60_000;
    const block = slotBlockInView(s.start, dur, viewStart, viewEnd, totalMinutes);
    if (block.clippedOut) {
      out.push({
        slot: s,
        topPct: 0,
        heightPct: 0,
        clippedOut: true,
        lane: 0,
        laneCount: 1,
      });
      continue;
    }
    let lane = laneEnds.findIndex((end) => end <= t0);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(t1);
    } else {
      laneEnds[lane] = t1;
    }
    out.push({
      slot: s,
      topPct: block.topPct,
      heightPct: block.heightPct,
      clippedOut: false,
      lane,
      laneCount: Math.max(1, laneEnds.length),
    });
  }
  const maxLanes = out.reduce((m, p) => (p.clippedOut ? m : Math.max(m, p.laneCount)), 1);
  return out.map((p) => (p.clippedOut ? p : { ...p, laneCount: maxLanes }));
}

function placeSlotsInView(slots: DoctorSlot[], viewStart: import('dayjs').Dayjs, viewEnd: import('dayjs').Dayjs, totalMinutes: number): PlacedSlot[] {
  const sorted = dedupeDoctorSlots(slots).sort((a, b) => slotKey(a.start).localeCompare(slotKey(b.start)));
  return assignPlacementLanes(sorted, viewStart, viewEnd, totalMinutes);
}

function slotTimeRangeMs(s: DoctorSlot): { t0: number; t1: number } {
  const dur = s.duration_minutes ?? 30;
  const t0 = slotInstantUtcMs(s.start);
  return { t0, t1: t0 + dur * 60_000 };
}

/** Overlapping slots in the same time band, ordered by lane (for Left/Right focus). */
function overlapLaneKeys(placed: PlacedSlot[], currentKey: string): string[] {
  const p =
    placed.find((x) => !x.clippedOut && slotKey(x.slot.start) === currentKey) ??
    placed.find((x) => slotKey(x.slot.start) === currentKey);
  if (!p) return [currentKey];
  const { t0, t1 } = slotTimeRangeMs(p.slot);
  return placed
    .filter((q) => !q.clippedOut)
    .filter((q) => {
      const r = slotTimeRangeMs(q.slot);
      return t0 < r.t1 && t1 > r.t0;
    })
    .sort((a, b) => a.lane - b.lane)
    .map((g) => slotKey(g.slot.start));
}

function useIsDesktop() {
  const [desktop, setDesktop] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia('(min-width: 768px)').matches : true
  );
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)');
    const f = () => setDesktop(mq.matches);
    mq.addEventListener('change', f);
    f();
    return () => mq.removeEventListener('change', f);
  }, []);
  return desktop;
}

function CalendarGridSkeleton() {
  return (
    <div className="flex min-h-[28rem] gap-0 rounded-lg border border-border bg-muted/20 p-0 overflow-hidden" aria-hidden>
      <div className="w-12 shrink-0 space-y-6 border-r border-border py-2 pr-2 pl-1">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-3 w-8 rounded bg-muted animate-pulse" />
        ))}
      </div>
      <div className="flex-1 space-y-3 p-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-16 w-full rounded-md bg-muted animate-pulse" />
        ))}
      </div>
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-hidden>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="min-h-[64px] w-full rounded-xl border border-border bg-muted/40 animate-pulse p-4" />
      ))}
    </div>
  );
}

export interface DayCalendarProps {
  doctorId: string | null;
  isInteractive: boolean;
  patients: Patient[];
  /** Matched to slot starts for patient name and Complete/Cancel on the day list. */
  appointments?: Appointment[];
  /** When set, booking flow pre-selects this patient in the modal. */
  bookPatientId?: string | null;
  hasAvailabilityWindows?: boolean;
  /** @deprecated Ignored; UI always displays Asia/Kolkata (IST). */
  doctorTimeZone?: string;
  onBooked?: () => void | Promise<void>;
  className?: string;
}

export function DayCalendar({
  doctorId,
  isInteractive,
  patients,
  appointments = [],
  bookPatientId = null,
  hasAvailabilityWindows,
  doctorTimeZone: _doctorTimeZone,
  onBooked,
  className,
}: DayCalendarProps) {
  const tz = DISPLAY_TIMEZONE;
  const isDesktop = useIsDesktop();
  const [searchParams, setSearchParams] = useSearchParams();
  const [slots, setSlots] = useState<DoctorSlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fullDayTimeOff, setFullDayTimeOff] = useState<boolean | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedStart, setSelectedStart] = useState<string | null>(null);
  const [nowTick, setNowTick] = useState(0);
  const [bookingBusy, setBookingBusy] = useState(false);
  const [nextAvailSlot, setNextAvailSlot] = useState<DoctorSlot | null | undefined>(undefined);
  const [nextAvailLoading, setNextAvailLoading] = useState(false);
  const [viewMode, setViewMode] = useState<CalendarViewMode>(() => {
    if (typeof window === 'undefined') return 'grid';
    return window.localStorage.getItem(CALENDAR_VIEW_STORAGE_KEY) === 'list' ? 'list' : 'grid';
  });

  const dayLoadIdRef = useRef(0);
  const dayLoadAbortRef = useRef<AbortController | null>(null);
  const slotBtnRefs = useRef<Map<string, HTMLElement | null>>(new Map());

  useEffect(() => {
    try {
      window.localStorage.setItem(CALENDAR_VIEW_STORAGE_KEY, viewMode);
    } catch {
      /* quota / disabled */
    }
  }, [viewMode]);

  const doctorTodayYmd = useMemo(() => {
    void nowTick;
    return calendarTodayYmdInZone(tz);
  }, [tz, nowTick]);

  const nextAvail = useMemo(() => {
    if (nextAvailSlot === undefined) return undefined;
    if (hasAvailabilityWindows === false) return undefined;
    if (!nextAvailSlot || !nextAvailSlot.available) return null;
    const dayYmd = appointmentCalendarDayYmd(nextAvailSlot.start, tz);
    if (isSlotInPast(nextAvailSlot.start, dayYmd, doctorTodayYmd)) return null;
    return {
      label: formatNextAvailablePhrase(nextAvailSlot.start, dayYmd, doctorTodayYmd, tz),
      dayYmd,
    };
  }, [nextAvailSlot, hasAvailabilityWindows, tz, doctorTodayYmd]);

  const minYmd = doctorTodayYmd;
  const date = useMemo(() => {
    const raw = searchParams.get('date');
    return parseAndClampDateParam(raw, minYmd) ?? minYmd;
  }, [searchParams, minYmd, tz]);

  const setDateParam = useCallback(
    (d: string) => {
      setSearchParams(
        (prev) => {
          const p = new URLSearchParams(prev);
          p.set('date', d);
          return p;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  useEffect(() => {
    if (!searchParams.get('date')) {
      setSearchParams(
        (prev) => {
          const p = new URLSearchParams(prev);
          p.set('date', minYmd);
          return p;
        },
        { replace: true }
      );
    }
  }, [searchParams, setSearchParams, minYmd]);

  const { viewStart, viewEnd, totalMinutes } = useMemo(() => getCalendarViewWindow(date, tz), [date, tz]);
  const hourTicks = useMemo(
    () => listHourGridTicks(date, tz, viewStart, viewEnd, totalMinutes),
    [date, tz, viewStart, viewEnd, totalMinutes]
  );

  const isToday = date === doctorTodayYmd;

  useEffect(() => {
    if (!doctorId) return;
    const id = window.setInterval(() => setNowTick((n) => n + 1), 30_000);
    return () => window.clearInterval(id);
  }, [doctorId]);

  const nowLinePct = useMemo(
    () => nowLinePercentInView(date, doctorTodayYmd, viewStart, viewEnd, totalMinutes),
    [date, doctorTodayYmd, viewStart, viewEnd, totalMinutes, nowTick]
  );

  const applyNextFromResponse = useCallback(
    (slot: DoctorSlot | null) => {
      if (hasAvailabilityWindows === false) {
        setNextAvailSlot(undefined);
        setNextAvailLoading(false);
        return;
      }
      if (!slot || !slot.available) {
        setNextAvailSlot(null);
        setNextAvailLoading(false);
        return;
      }
      setNextAvailSlot(slot);
      setNextAvailLoading(false);
    },
    [hasAvailabilityWindows]
  );

  const loadDaySchedule = useCallback(
    async (opts?: { skipSlotsCache?: boolean }) => {
      if (!doctorId) return;
      if (hasAvailabilityWindows === false) {
        setNextAvailSlot(undefined);
        setNextAvailLoading(false);
      } else {
        setNextAvailLoading(true);
      }
      const reqId = ++dayLoadIdRef.current;
      dayLoadAbortRef.current?.abort();
      const ac = new AbortController();
      dayLoadAbortRef.current = ac;
      setLoading(true);
      setError(null);
      const fromYmd = calendarTodayYmdInZone(tz);
      try {
        const data = await doctorsApi.getScheduleDay(doctorId, date, {
          fromYmd,
          horizonDays: 14,
          signal: ac.signal,
          skipSlotsCache: opts?.skipSlotsCache,
        });
        if (reqId !== dayLoadIdRef.current) return;
        if (ac.signal.aborted) return;
        setSlots(dedupeDoctorSlots(data.slots));
        setFullDayTimeOff(data.full_day_time_off);
        applyNextFromResponse(data.next_available);
      } catch (e) {
        if (axios.isCancel(e)) return;
        if (ac.signal.aborted) return;
        if (reqId !== dayLoadIdRef.current) return;
        setError('Could not load slots for this day.');
        setSlots([]);
        if (hasAvailabilityWindows !== false) {
          setNextAvailSlot(null);
        }
        setNextAvailLoading(false);
      } finally {
        if (!ac.signal.aborted && reqId === dayLoadIdRef.current) {
          setLoading(false);
        }
      }
    },
    [doctorId, date, tz, hasAvailabilityWindows, applyNextFromResponse]
  );

  useEffect(() => {
    if (!doctorId) {
      setSlots([]);
      setLoading(false);
      setFullDayTimeOff(null);
      return;
    }
    void loadDaySchedule();
    return () => dayLoadAbortRef.current?.abort();
  }, [doctorId, date, loadDaySchedule]);

  useEffect(() => {
    if (!doctorId) return;
    const onBroadcast = () => {
      if (!shouldSyncSlotsCrossTab()) return;
      void loadDaySchedule();
    };
    window.addEventListener(SLOTS_CROSS_TAB_BROADCAST, onBroadcast);
    return () => window.removeEventListener(SLOTS_CROSS_TAB_BROADCAST, onBroadcast);
  }, [doctorId, loadDaySchedule]);

  const placed = useMemo(
    () => placeSlotsInView(slots, viewStart, viewEnd, totalMinutes),
    [slots, viewStart, viewEnd, totalMinutes]
  );

  const onBookingSuccess = useCallback(
    async (bookedStart?: string) => {
      const canon = bookedStart ? slotKey(bookedStart) : null;
      if (canon) {
        setSlots((prev) =>
          prev.map((s) => (slotKey(s.start) === canon ? { ...s, available: false } : s))
        );
      }
      if (!doctorId) return;
      invalidateDoctorSlotsClientCache(doctorId, date);
      await Promise.resolve(onBooked?.());
      void loadDaySchedule({ skipSlotsCache: true });
    },
    [doctorId, date, onBooked, loadDaySchedule]
  );

  const sortedSlots = useMemo(
    () => dedupeDoctorSlots(slots).sort((a, b) => slotKey(a.start).localeCompare(slotKey(b.start))),
    [slots]
  );

  const apptBySlotKey = useMemo(() => {
    const m = new Map<string, Appointment>();
    if (!doctorId) return m;
    for (const a of appointments) {
      if (String(a.doctor_id) !== String(doctorId)) continue;
      const raw = a.appointment_time || a.scheduled_at;
      if (!raw) continue;
      if (appointmentCalendarDayYmd(raw, tz) !== date) continue;
      m.set(slotKey(raw), a);
    }
    return m;
  }, [appointments, doctorId, date, tz]);

  const navigate = useNavigate();
  const [apptActionBusy, setApptActionBusy] = useState<string | null>(null);

  const onCancelAppt = useCallback(
    async (apptId: string) => {
      setApptActionBusy(apptId);
      try {
        await appointmentsApi.update(apptId, { status: 'cancelled' });
        toast.success('Appointment cancelled');
        onBooked?.();
        void loadDaySchedule({ skipSlotsCache: true });
      } catch {
        toast.error('Could not cancel');
      } finally {
        setApptActionBusy(null);
      }
    },
    [onBooked, loadDaySchedule]
  );

  const openNewAppointment = useCallback(() => {
    if (bookingBusy) return;
    const first = sortedSlots.find(
      (s) => s.available && !isSlotInPast(s.start, date, doctorTodayYmd)
    );
    if (first) {
      setSelectedStart(slotKey(first.start));
      setModalOpen(true);
    } else {
      toast.error('No open slots on this day. Try another date.');
    }
  }, [sortedSlots, date, doctorTodayYmd, bookingBusy]);

  const navSlotKeys = useMemo(() => sortedSlots.map((s) => slotKey(s.start)), [sortedSlots]);

  const focusNeighborSlot = useCallback(
    (fromKey: string, delta: number) => {
      const keys = navSlotKeys;
      const n = keys.length;
      if (n === 0) return;
      const idx = keys.indexOf(fromKey);
      if (idx < 0) return;
      const next = keys[(idx + delta + n) % n];
      slotBtnRefs.current.get(next)?.focus();
    },
    [navSlotKeys]
  );

  const focusNeighborLane = useCallback(
    (fromKey: string, delta: 1 | -1) => {
      const group = overlapLaneKeys(placed, fromKey);
      if (group.length === 0) return;
      const idx = group.indexOf(fromKey);
      if (idx < 0) return;
      const n = group.length;
      const next = group[(idx + delta + n) % n];
      slotBtnRefs.current.get(next)?.focus();
    },
    [placed]
  );

  const focusFirstSlot = useCallback(() => {
    const keys = navSlotKeys;
    if (keys.length === 0) return;
    slotBtnRefs.current.get(keys[0])?.focus();
  }, [navSlotKeys]);

  const focusLastSlot = useCallback(() => {
    const keys = navSlotKeys;
    if (keys.length === 0) return;
    slotBtnRefs.current.get(keys[keys.length - 1])?.focus();
  }, [navSlotKeys]);

  const shiftDate = (delta: number) => {
    setDateParam(addDaysYmd(date, tz, delta));
  };

  const showGrid = isDesktop && viewMode === 'grid';

  if (!doctorId) {
    return (
      <div
        className={cn('rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground', className)}
      >
        Set up your doctor profile to see the schedule.
      </div>
    );
  }

  if (hasAvailabilityWindows === false) {
    return (
      <div className={cn('rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm text-foreground', className)}>
        <p className="font-medium">No availability is configured</p>
        <p className="mt-1 text-muted-foreground">
          Add your weekly hours under <strong>Availability</strong> to publish bookable time slots.
        </p>
      </div>
    );
  }

  const renderSlotButton = (p: PlacedSlot) => {
    if (p.clippedOut) return null;
    const k = slotKey(p.slot.start);
    const past = isSlotInPast(p.slot.start, date, doctorTodayYmd);
    const selected = Boolean(modalOpen && selectedStart != null && slotKey(selectedStart) === k);
    const disabled = !p.slot.available || !isInteractive || past || bookingBusy;
    const { lane, laneCount } = p;
    const colPct = 100 / laneCount;
    const gutter = 0.5;
    return (
      <button
        key={k}
        type="button"
        data-testid="doctor-schedule-slot"
        ref={(el) => {
          if (el) slotBtnRefs.current.set(k, el);
          else slotBtnRefs.current.delete(k);
        }}
        style={{
          top: `${p.topPct}%`,
          height: `${Math.max(p.heightPct, 3)}%`,
          left: `calc(${lane * colPct}% + ${gutter}%)`,
          width: `calc(${colPct}% - ${gutter * 2}%)`,
        }}
        className={cn(
          'absolute z-10 box-border flex min-h-[1.5rem] flex-col items-stretch justify-center overflow-hidden rounded-md border px-2 py-0.5 text-left text-sm font-semibold tabular-nums transition-colors',
          past &&
            'cursor-not-allowed border border-gray-200 bg-gray-100 text-gray-400',
          !past && !p.slot.available && 'border border-red-200 bg-red-50 text-red-900',
          !past && p.slot.available && !selected &&
            'cursor-pointer border border-emerald-200 bg-emerald-50 text-emerald-900 hover:bg-emerald-100',
          !past && p.slot.available && selected && 'z-[15] border border-primary bg-primary text-white shadow-sm hover:bg-primary/90',
          isInteractive && p.slot.available && !past && !bookingBusy && 'active:scale-[0.99]'
        )}
        disabled={disabled}
        onClick={() => {
          if (modalOpen) return;
          if (bookingBusy) return;
          if (!isInteractive || !p.slot.available) return;
          if (past) return;
          setSelectedStart(k);
          setModalOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Home') {
            e.preventDefault();
            focusFirstSlot();
            return;
          }
          if (e.key === 'End') {
            e.preventDefault();
            focusLastSlot();
            return;
          }
          if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault();
            focusNeighborSlot(k, e.key === 'ArrowDown' ? 1 : -1);
            return;
          }
          if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
            e.preventDefault();
            focusNeighborLane(k, e.key === 'ArrowRight' ? 1 : -1);
          }
        }}
        aria-disabled={disabled}
      >
        <span className="font-semibold tabular-nums">{formatSlotTime(p.slot.start, tz)}</span>
        <span
          className={cn(
            'truncate text-[10px] leading-tight sm:text-xs',
            !past && p.slot.available && selected && 'text-white/80',
            !past && p.slot.available && !selected && 'text-emerald-800/90',
            !past && !p.slot.available && 'text-red-800/90',
            past && 'text-gray-500'
          )}
        >
          {past ? 'Past' : p.slot.available ? 'Available' : 'Booked'}
        </span>
      </button>
    );
  };

  const slotNavKeyHandler = (k: string) => (e: KeyboardEvent) => {
    if (e.key === 'Home') {
      e.preventDefault();
      focusFirstSlot();
      return;
    }
    if (e.key === 'End') {
      e.preventDefault();
      focusLastSlot();
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      focusNeighborSlot(k, e.key === 'ArrowDown' ? 1 : -1);
      return;
    }
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      focusNeighborLane(k, e.key === 'ArrowRight' ? 1 : -1);
    }
  };

  const listSlotCard = (s: DoctorSlot) => {
    const k = slotKey(s.start);
    const past = isSlotInPast(s.start, date, doctorTodayYmd);
    const selected = Boolean(modalOpen && selectedStart != null && slotKey(selectedStart) === k);
    const appt = apptBySlotKey.get(k);
    const pid = appt?.patient_id != null ? String(appt.patient_id) : '';
    const pName =
      (pid && patients.find((p) => String(p.id) === pid)?.name) ||
      appt?.patient?.name ||
      (appt && !s.available ? 'Patient' : '');

    const overdueNeedsAction = Boolean(
      past &&
        appt &&
        (appt.status === 'scheduled' || appt.status === 'pending')
    );
    let statusLabel: string;
    if (overdueNeedsAction) statusLabel = 'Needs completion';
    else if (past) statusLabel = 'Past';
    else if (s.available) statusLabel = 'Available';
    else if (appt?.status === 'completed') statusLabel = 'Completed';
    else if (appt?.status === 'cancelled') statusLabel = 'Cancelled';
    else statusLabel = 'Booked';

    const showCompleteCancel =
      isInteractive && appt && (appt.status === 'scheduled' || appt.status === 'pending');

    const listCardBaseClass = cn(
      'w-full rounded-xl border p-4 text-left transition-colors min-h-[44px] flex flex-col gap-3 sm:min-h-[64px]',
      past && !overdueNeedsAction && 'cursor-not-allowed border border-gray-200 bg-gray-100 text-gray-400',
      overdueNeedsAction && 'border border-amber-200 bg-amber-50 text-amber-950',
      !past && s.available && !selected && 'border border-emerald-200 bg-emerald-50 text-emerald-900 hover:bg-emerald-100',
      !past && s.available && selected && 'z-[1] border border-primary bg-primary text-white shadow-sm hover:bg-primary/90',
      !past && !s.available && appt?.status !== 'completed' && appt?.status !== 'cancelled' && 'border border-red-200 bg-red-50 text-red-900',
      !past && !s.available && appt?.status === 'completed' && 'border border-gray-200 bg-gray-100 text-gray-500',
      !past && !s.available && appt?.status === 'cancelled' && 'border border-red-200 bg-red-50 text-red-800',
      !past && !s.available && !appt && 'border border-red-200 bg-red-50 text-red-900'
    );

    const cardShell = (opts: {
      interactive: boolean;
      children: ReactNode;
      className?: string;
    }) => {
      const base = listCardBaseClass;

      if (opts.interactive) {
        return (
          <button
            key={k}
            type="button"
            data-testid="doctor-schedule-slot"
            ref={(el) => {
              if (el) slotBtnRefs.current.set(k, el);
              else slotBtnRefs.current.delete(k);
            }}
            className={cn(base, opts.className, isInteractive && !bookingBusy && 'active:scale-[0.99]')}
            disabled={!isInteractive || past || bookingBusy}
            onClick={() => {
              if (modalOpen || bookingBusy || !isInteractive || past) return;
              setSelectedStart(k);
              setModalOpen(true);
            }}
            onKeyDown={slotNavKeyHandler(k)}
            aria-disabled={!isInteractive || past || bookingBusy}
          >
            {opts.children}
          </button>
        );
      }

      return (
        <div
          key={k}
          data-testid="doctor-schedule-slot"
          ref={(el) => {
            if (el) slotBtnRefs.current.set(k, el);
            else slotBtnRefs.current.delete(k);
          }}
          role="listitem"
          tabIndex={showCompleteCancel ? 0 : -1}
          className={cn(base, opts.className)}
          onKeyDown={showCompleteCancel ? slotNavKeyHandler(k) : undefined}
        >
          {opts.children}
        </div>
      );
    };

    const body = (
      <>
        <div className="min-w-0 space-y-1">
          <p
            className={cn(
              'text-sm font-semibold tabular-nums leading-tight sm:text-xl sm:font-bold',
              selected && 'text-white'
            )}
          >
            {formatSlotTime(s.start, tz)}
          </p>
          {pName ? (
            pid ? (
              <Link
                to={`/doctor/patients/${pid}`}
                className={cn(
                  'text-base font-medium hover:underline truncate block',
                  selected ? 'text-white' : 'text-primary'
                )}
                onClick={(e) => e.stopPropagation()}
              >
                {pName}
              </Link>
            ) : (
              <p className={cn('text-base font-medium truncate', selected && 'text-white')}>{pName}</p>
            )
          ) : null}
          <p className={cn('text-sm capitalize', selected ? 'text-white/80' : 'text-muted-foreground')}>
            {statusLabel}
          </p>
        </div>
        {showCompleteCancel && appt && (
          <div className="flex w-full gap-2">
            <Button
              type="button"
              className="min-h-[44px] flex-1 bg-emerald-600 text-white hover:bg-emerald-700"
              disabled={apptActionBusy != null}
              onClick={() => navigate(`/doctor/appointments/${String(appt.id)}`)}
            >
              Open Encounter
            </Button>
            <Button
              type="button"
              variant="outline"
              className="min-h-[44px] flex-1 border-red-500/60 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
              disabled={apptActionBusy != null}
              onClick={() => void onCancelAppt(String(appt.id))}
            >
              Cancel
            </Button>
          </div>
        )}
      </>
    );

    if (!past && s.available && isInteractive) {
      return cardShell({ interactive: true, children: body });
    }

    if (showCompleteCancel && appt) {
      return (
        <SwipeableSlotActions
          key={k}
          ref={(el) => {
            if (el) slotBtnRefs.current.set(k, el);
            else slotBtnRefs.current.delete(k);
          }}
          dataTestId="doctor-schedule-slot"
          swipeEnabled={!isDesktop}
          disabled={apptActionBusy != null}
          className={listCardBaseClass}
          onKeyDown={slotNavKeyHandler(k)}
          onComplete={() => {
            navigate(`/doctor/appointments/${String(appt.id)}`);
          }}
          onCancel={() => {
            void onCancelAppt(String(appt.id));
          }}
        >
          {body}
        </SwipeableSlotActions>
      );
    }

    return cardShell({ interactive: false, children: body });
  };

  const canGoYesterday = date > minYmd;

  return (
    <div className={cn('space-y-3', isInteractive && 'pb-24 md:pb-3', className)}>
      {doctorId && hasAvailabilityWindows && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/20 px-3 py-2 text-sm">
          {nextAvailLoading && (
            <>
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" aria-hidden />
              <span className="text-muted-foreground">Finding next open slot…</span>
            </>
          )}
          {!nextAvailLoading && nextAvail && (
            <span>
              <span className="text-muted-foreground">Next available: </span>
              <span className="font-medium text-foreground">{nextAvail.label}</span>
            </span>
          )}
          {!nextAvailLoading && nextAvail === null && (
            <span className="text-muted-foreground">No free slots in the next 14 days (check time off and hours).</span>
          )}
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div className="grid grid-cols-3 gap-2 w-full sm:w-auto sm:max-w-md">
          <Button
            type="button"
            variant="outline"
            className="min-h-[44px] sm:min-h-9"
            onClick={() => shiftDate(-1)}
            disabled={!canGoYesterday}
          >
            Yesterday
          </Button>
          <Button
            type="button"
            variant={isToday ? 'default' : 'outline'}
            className="min-h-[44px] sm:min-h-9"
            onClick={() => setDateParam(minYmd)}
          >
            Today
          </Button>
          <Button type="button" variant="outline" className="min-h-[44px] sm:min-h-9" onClick={() => shiftDate(1)}>
            Tomorrow
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Input
            type="date"
            className="h-10 sm:h-8 w-full sm:w-auto min-w-0 sm:min-w-[10rem] text-sm"
            value={date}
            min={minYmd}
            onChange={(e) => setDateParam(e.target.value)}
          />
          {isDesktop && (
            <div className="flex items-center gap-0.5 rounded-md border border-border p-0.5" role="group" aria-label="Calendar view">
              <Button
                type="button"
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-7 gap-1 px-2"
                onClick={() => setViewMode('grid')}
                aria-pressed={viewMode === 'grid'}
              >
                <LayoutGrid className="h-3.5 w-3.5" aria-hidden />
                Grid
              </Button>
              <Button
                type="button"
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-7 gap-1 px-2"
                onClick={() => setViewMode('list')}
                aria-pressed={viewMode === 'list'}
              >
                <List className="h-3.5 w-3.5" aria-hidden />
                List
              </Button>
            </div>
          )}
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{formatTimeZoneCaption(tz)}</p>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {loading && (showGrid ? <CalendarGridSkeleton /> : <ListSkeleton />)}

      {!loading && !error && slots.length === 0 && (
        <div
          className={cn(
            'flex min-h-[10rem] flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground',
            fullDayTimeOff ? 'bg-muted/25' : 'bg-muted/10'
          )}
          role="status"
        >
          <p className="font-medium text-foreground">
            {fullDayTimeOff ? 'Doctor is unavailable on this day' : 'No time slots for this day'}
          </p>
          <p className="text-muted-foreground max-w-sm">
            {fullDayTimeOff
              ? 'Full-day time off is blocking this date. Pick another day or update the calendar.'
              : 'Your weekly hours may not include this weekday, or time off and other blocks are covering the day. Pick another date or update availability.'}
          </p>
        </div>
      )}

      {!loading && !error && slots.length > 0 && !showGrid && (
        <div className="flex flex-col gap-3" role="list" aria-label="Appointment slots">
          {sortedSlots.map((s) => listSlotCard(s))}
        </div>
      )}

      {!loading && !error && slots.length > 0 && showGrid && (
        <div
          className={cn(
            'flex gap-0 overflow-hidden rounded-lg border border-border bg-background',
            fullDayTimeOff && 'bg-muted/20'
          )}
        >
          <div className="w-12 shrink-0 select-none border-r border-border py-0 text-right text-[10px] leading-none text-muted-foreground sm:text-xs">
            <div className="relative min-h-[28rem] w-full" style={{ height: 'min(70vh, 32rem)' }}>
              {hourTicks.map((t) => (
                <div key={t.hour} className="absolute right-1 -translate-y-1/2" style={{ top: `${t.topPct}%` }}>
                  {t.label}
                </div>
              ))}
            </div>
          </div>
          <div className="relative min-h-[28rem] min-w-0 flex-1" style={{ height: 'min(70vh, 32rem)' }}>
            {hourTicks.slice(1).map((t) => (
              <div
                key={`g-${t.hour}`}
                className="pointer-events-none absolute right-0 left-0 z-0 border-t border-border/60"
                style={{ top: `${t.topPct}%` }}
              />
            ))}
            {nowLinePct != null && (
              <div
                className="pointer-events-none absolute left-0 right-0 z-20 border-t-2 border-primary"
                style={{ top: `${nowLinePct}%` }}
                role="presentation"
                title="Current time"
              />
            )}
            {nowLinePct != null && (
              <div
                className="pointer-events-none absolute -left-1 z-20 size-2 rounded-full bg-primary"
                style={{ top: `calc(${nowLinePct}% - 4px)` }}
                aria-hidden
              />
            )}
            {placed.filter((p) => !p.clippedOut).map((p) => renderSlotButton(p))}
          </div>
        </div>
      )}

      {isInteractive && (
        <BookingModal
          open={modalOpen}
          onClose={() => {
            setModalOpen(false);
            setSelectedStart(null);
            setBookingBusy(false);
          }}
          slotStart={selectedStart}
          doctorId={doctorId}
          patients={patients}
          defaultPatientId={bookPatientId}
          onSuccess={onBookingSuccess}
          timeZone={tz}
          onSubmittingChange={setBookingBusy}
        />
      )}

      {isInteractive && (
        <div
          className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background px-4 py-3 shadow-[0_-4px_24px_rgba(0,0,0,0.06)] md:hidden"
          style={{ paddingBottom: 'max(12px, env(safe-area-inset-bottom))' }}
        >
          <Button
            type="button"
            className="h-12 w-full rounded-xl text-base font-semibold"
            onClick={openNewAppointment}
          >
            + New Appointment
          </Button>
        </div>
      )}
    </div>
  );
}
