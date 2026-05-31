import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import { DISPLAY_TIMEZONE } from '../constants/time';

dayjs.extend(utc);
dayjs.extend(timezone);

/**
 * Calendar YYYY-MM-DD for an instant (default: now) in the display zone.
 * Prefer `calendarTodayYmdInZone` for "today" and `appointmentCalendarDayYmd` for API ISO strings.
 */
export function ymdInTimeZone(_iana: string, d?: Date): string {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  const ms = d != null ? d.getTime() : dayjs.utc().valueOf();
  try {
    return dayjs.utc(ms).tz(tz).format('YYYY-MM-DD');
  } catch {
    return dayjs.utc(ms).format('YYYY-MM-DD');
  }
}

/** Today's calendar date in the display zone from the current instant (UTC-safe). */
export function calendarTodayYmdInZone(_iana: string): string {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  try {
    return dayjs.utc().tz(tz).format('YYYY-MM-DD');
  } catch {
    return dayjs.utc().format('YYYY-MM-DD');
  }
}

/** Today's YYYY-MM-DD in a specific IANA zone (e.g. doctor schedule). */
export function ymdNowInIana(iana: string | undefined | null): string {
  const tz = (iana && iana.trim()) || DISPLAY_TIMEZONE;
  try {
    return dayjs.utc().tz(tz).format('YYYY-MM-DD');
  } catch {
    return calendarTodayYmdInZone('');
  }
}

/** Add calendar days in *iana* (anchor at local noon to avoid DST edge issues). */
export function ymdAddDaysInIana(ymd: string, iana: string | undefined | null, deltaDays: number): string {
  const tz = (iana && iana.trim()) || DISPLAY_TIMEZONE;
  try {
    const anchor = dayjs.tz(`${ymd}T12:00:00`, tz);
    if (!anchor.isValid()) {
      return addDaysYmd(ymd, DISPLAY_TIMEZONE, deltaDays);
    }
    return anchor.add(deltaDays, 'day').format('YYYY-MM-DD');
  } catch {
    return addDaysYmd(ymd, DISPLAY_TIMEZONE, deltaDays);
  }
}

export function addDaysYmd(ymd: string, _iana: string, deltaDays: number): string {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  const anchor = dayjs.tz(`${ymd} 12:00:00`, tz);
  if (!anchor.isValid()) {
    const fallback = dayjs.utc(`${ymd}T12:00:00Z`);
    return fallback.isValid() ? fallback.add(deltaDays, 'day').format('YYYY-MM-DD') : ymd;
  }
  return anchor.add(deltaDays, 'day').format('YYYY-MM-DD');
}

/** True 9:00 → 17:00 window for that calendar day in the zone (DST-safe total length). */
export function getCalendarViewWindow(
  dateYmd: string,
  _iana: string,
  startWall = '09:00',
  endWall = '17:00'
): { viewStart: Dayjs; viewEnd: Dayjs; totalMinutes: number } {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  const viewStart = dayjs.tz(`${dateYmd} ${startWall}`, tz);
  const viewEnd = dayjs.tz(`${dateYmd} ${endWall}`, tz);
  const raw = viewEnd.diff(viewStart, 'minute', true);
  const totalMinutes = Math.max(1 / 60, raw);
  return { viewStart, viewEnd, totalMinutes };
}

function later(a: Dayjs, b: Dayjs): Dayjs {
  return a.isAfter(b) ? a : b;
}

function earlier(a: Dayjs, b: Dayjs): Dayjs {
  return a.isBefore(b) ? a : b;
}

export type SlotBlockInViewResult = {
  clippedOut: boolean;
  topPct: number;
  heightPct: number;
  visualStart: Dayjs;
  visualEnd: Dayjs;
};

/** Map a slot (UTC ISO + duration) into the 9–17 view; uses real instants, not fixed 480 min. */
export function slotBlockInView(
  iso: string,
  durationMinutes: number,
  viewStart: Dayjs,
  viewEnd: Dayjs,
  totalMinutes: number
): SlotBlockInViewResult {
  const slotStart = dayjs.utc(iso);
  const slotEnd = slotStart.add(durationMinutes, 'minute');
  const clipStart = later(slotStart, viewStart);
  const clipEnd = earlier(slotEnd, viewEnd);
  if (!clipStart.isBefore(clipEnd)) {
    return {
      clippedOut: true,
      topPct: 0,
      heightPct: 0,
      visualStart: clipStart,
      visualEnd: clipEnd,
    };
  }
  const topMin = clipStart.diff(viewStart, 'minute', true);
  const heightMin = clipEnd.diff(clipStart, 'minute', true);
  return {
    clippedOut: false,
    topPct: (topMin / totalMinutes) * 100,
    heightPct: (heightMin / totalMinutes) * 100,
    visualStart: clipStart,
    visualEnd: clipEnd,
  };
}

/** Position of "now" in the same view (0–100), or null if outside the window. */
export function nowLinePercentInView(
  dateYmd: string,
  doctorTodayYmd: string,
  viewStart: Dayjs,
  viewEnd: Dayjs,
  totalMinutes: number
): number | null {
  if (dateYmd !== doctorTodayYmd) return null;
  const now = dayjs.utc();
  if (now.isBefore(viewStart) || now.isAfter(viewEnd)) return null;
  const m = now.diff(viewStart, 'minute', true);
  return (m / totalMinutes) * 100;
}

/** Every wall hour 9…17 that falls in [viewStart, viewEnd] with % from view top. */
export function listHourGridTicks(
  dateYmd: string,
  _iana: string,
  viewStart: Dayjs,
  viewEnd: Dayjs,
  totalMinutes: number
): { hour: number; label: string; topPct: number }[] {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  const out: { hour: number; label: string; topPct: number }[] = [];
  for (let h = 9; h <= 17; h += 1) {
    const t = dayjs.tz(`${dateYmd} ${String(h).padStart(2, '0')}:00:00`, tz);
    if (t.isBefore(viewStart, 'minute')) continue;
    if (t.isAfter(viewEnd, 'minute')) break;
    const min = t.diff(viewStart, 'minute', true);
    const topPct = (min / totalMinutes) * 100;
    out.push({ hour: h, label: t.format('h:mm A'), topPct });
  }
  return out;
}

/** Minutes from local midnight in the display zone for the UTC instant `iso` (slot start from API). */
export function wallMinutesInZone(iso: string, _iana: string): number {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  try {
    const x = dayjs.utc(iso).tz(tz);
    return x.hour() * 60 + x.minute() + x.second() / 60;
  } catch {
    const x = dayjs.utc(iso);
    if (!x.isValid()) return 0;
    return x.hour() * 60 + x.minute() + x.second() / 60;
  }
}

/** Short timezone label for a wall time (e.g. IST). Uses the instant for DST correctness. */
export function timeZoneAbbreviation(_iana: string, refMs?: number): string {
  void _iana;
  const z = DISPLAY_TIMEZONE;
  const ref = refMs != null && !Number.isNaN(refMs) ? refMs : dayjs.utc().valueOf();
  try {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: z, timeZoneName: 'short' }).formatToParts(
      new Date(ref)
    );
    return parts.find((p) => p.type === 'timeZoneName')?.value ?? z.replace(/_/g, ' ');
  } catch {
    return z.replace(/_/g, ' ');
  }
}

/** Calendar YYYY-MM-DD in the display zone for a UTC instant from the API. */
export function appointmentCalendarDayYmd(iso: string, _iana: string): string {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  const u = dayjs.utc(iso);
  if (!u.isValid()) return '';
  try {
    return u.tz(tz).format('YYYY-MM-DD');
  } catch {
    return u.format('YYYY-MM-DD');
  }
}

/** Calendar YYYY-MM-DD for a UTC ISO instant in a specific IANA zone (e.g. doctor schedule). */
export function calendarDayYmdForInstantInZone(iso: string, iana: string | null | undefined): string {
  const tz = (iana && iana.trim()) || DISPLAY_TIMEZONE;
  const u = dayjs.utc(iso);
  if (!u.isValid()) return '';
  try {
    return u.tz(tz).format('YYYY-MM-DD');
  } catch {
    return u.format('YYYY-MM-DD');
  }
}

/** Format a slot start for display (API times are UTC). */
export function formatSlotTime(iso: string, _iana: string): string {
  void _iana;
  if (!iso?.trim()) return '—';
  const tz = DISPLAY_TIMEZONE;
  try {
    return dayjs.utc(iso).tz(tz).format('h:mm A');
  } catch {
    return '—';
  }
}

export function formatSlotTimeWithZoneLabel(iso: string, _iana: string): string {
  void _iana;
  if (!iso?.trim()) return '—';
  return formatSlotTime(iso, DISPLAY_TIMEZONE);
}

export function formatSlotDateTimeLine(iso: string, _iana: string): string {
  void _iana;
  if (!iso?.trim()) return '—';
  const tz = DISPLAY_TIMEZONE;
  try {
    return dayjs.utc(iso).tz(tz).format('ddd, MMM D — h:mm A');
  } catch {
    return '—';
  }
}

/** Longer line for lists: date and time in IST (no separate zone badge). */
export function formatAppointmentDateTimeWithZoneLabel(iso: string, _iana: string): string {
  void _iana;
  if (!iso?.trim()) return '—';
  return formatSlotDateTimeLine(iso, DISPLAY_TIMEZONE);
}

/**
 * "Today" / "Yesterday" / long date for grouping headings, using the display calendar
 * (not the browser's local date).
 */
export function relativeCalendarDayHeadingInZone(iso: string, _iana: string): string {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  try {
    const d = dayjs.utc(iso).tz(tz);
    const todayYmd = calendarTodayYmdInZone(DISPLAY_TIMEZONE);
    const ymd = d.format('YYYY-MM-DD');
    const yestYmd = addDaysYmd(todayYmd, DISPLAY_TIMEZONE, -1);
    if (ymd === todayYmd) return 'Today';
    if (ymd === yestYmd) return 'Yesterday';
    return d.format('dddd, MMMM D, YYYY');
  } catch {
    return 'Unknown date';
  }
}

export function relativeCalendarDayTitleInZone(iso: string, iana: string): string {
  const h = relativeCalendarDayHeadingInZone(iso, iana);
  if (h === 'Today') return 'TODAY';
  if (h === 'Yesterday') return 'YESTERDAY';
  return h;
}

/** Footnote for schedule views (India-first; no UTC or IANA parenthetical). */
export function formatTimeZoneCaption(_iana?: string): string {
  void _iana;
  return 'All times in IST';
}

export function formatNextAvailablePhrase(
  iso: string,
  _slotDayYmd: string,
  _doctorTodayYmd: string,
  _iana: string
): string {
  void _slotDayYmd;
  void _doctorTodayYmd;
  void _iana;
  const todayYmd = calendarTodayYmdInZone(DISPLAY_TIMEZONE);
  const slotDayYmd = appointmentCalendarDayYmd(iso, DISPLAY_TIMEZONE);
  const time = formatSlotTime(iso, DISPLAY_TIMEZONE);
  if (slotDayYmd === todayYmd) return `Today at ${time}`;
  if (addDaysYmd(todayYmd, DISPLAY_TIMEZONE, 1) === slotDayYmd) return `Tomorrow at ${time}`;
  try {
    const day = dayjs.utc(iso).tz(DISPLAY_TIMEZONE).format('ddd, MMM D');
    return `${day} at ${time}`;
  } catch {
    return time;
  }
}

/** @deprecated use listHourGridTicks; kept for any imports */
export function formatHourLabelForDate(hour: number, dateYmd: string, _iana: string): string {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  const pad = (n: number) => String(n).padStart(2, '0');
  const s = `${dateYmd} ${pad(hour)}:00:00`;
  try {
    return dayjs.tz(s, tz).format('h:mm A');
  } catch {
    return dayjs.tz(`${dateYmd} ${pad(hour)}:00:00`, DISPLAY_TIMEZONE).format('h:mm A');
  }
}

export function isSlotInPast(isoStart: string, selectedYmd: string, doctorTodayYmd: string): boolean {
  if (selectedYmd < doctorTodayYmd) return true;
  if (selectedYmd > doctorTodayYmd) return false;
  const t = dayjs.utc(isoStart);
  if (!t.isValid()) return true;
  return t.valueOf() <= Date.now();
}

/** Compare UTC slot instant to clock now (for booking validation). */
export function isSlotInstantInThePast(isoStart: string): boolean {
  const t = dayjs.utc(isoStart);
  if (!t.isValid()) return true;
  return t.valueOf() <= Date.now();
}

export function isSlotInstantInTheFuture(isoStart: string): boolean {
  const t = dayjs.utc(isoStart);
  if (!t.isValid()) return false;
  return t.valueOf() > Date.now();
}

/** "Now" as minutes from midnight in the display zone. */
export function nowWallMinutes(_iana: string): number {
  void _iana;
  const tz = DISPLAY_TIMEZONE;
  try {
    const x = dayjs.utc().tz(tz);
    return x.hour() * 60 + x.minute() + x.second() / 60;
  } catch {
    const x = dayjs.utc();
    return x.hour() * 60 + x.minute() + x.second() / 60;
  }
}

function isYmd(s: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(s) && dayjs.utc(`${s}T12:00:00Z`).isValid();
}

export function parseAndClampDateParam(raw: string | null, minYmd: string): string | null {
  if (!raw || !isYmd(raw)) return null;
  if (raw < minYmd) return minYmd;
  return raw;
}

/**
 * Canonical UTC instant key aligned with backend `normalize_appointment_time_utc`
 * (second and sub-second parts zeroed). Use for slot identity in UI state merges.
 */
export function slotKey(iso: string): string {
  return dayjs.utc(iso).second(0).millisecond(0).toISOString();
}

/** Milliseconds since epoch for a UTC slot start ISO string. */
export function slotInstantUtcMs(iso: string): number {
  return dayjs.utc(iso).valueOf();
}

export function dedupeDoctorSlots<T extends { start: string }>(slots: T[]): T[] {
  const m = new Map<string, T>();
  for (const s of slots) {
    m.set(slotKey(s.start), s);
  }
  return [...m.values()].sort((a, b) => slotKey(a.start).localeCompare(slotKey(b.start)));
}

/** Pure overlap lane assignment for interval scheduling (ms since epoch). */
export function assignOverlapLanesPure(
  intervals: { start: number; end: number }[]
): { lane: number; laneCount: number }[] {
  const sorted = [...intervals].sort((a, b) => a.start - b.start || a.end - b.end);
  const laneEnds: number[] = [];
  const laneByIndex: number[] = [];
  for (const s of sorted) {
    let lane = laneEnds.findIndex((end) => end <= s.start);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(s.end);
    } else {
      laneEnds[lane] = s.end;
    }
    laneByIndex.push(lane);
  }
  const laneCount = Math.max(1, laneEnds.length);
  return laneByIndex.map((lane) => ({ lane, laneCount }));
}
