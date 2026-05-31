import type { DoctorAvailabilityWindow } from '../types';

/** Stable ordering for one doctor's windows (day then start). */
export function sortAvailabilityWindows(windows: DoctorAvailabilityWindow[]): DoctorAvailabilityWindow[] {
  return windows
    .slice()
    .sort((a, b) =>
      a.day_of_week !== b.day_of_week
        ? a.day_of_week - b.day_of_week
        : a.start_time.localeCompare(b.start_time)
    );
}

/** API times as "HH:MM:SS" or "HH:MM" — same calendar day, minutes from midnight. */
export function timeToMinutes(t: string): number {
  const s = t.trim().slice(0, 8);
  const [h, m, sec] = s.split(':').map((x) => parseInt(x, 10));
  if (Number.isNaN(h) || Number.isNaN(m)) return 0;
  const extra = Number.isNaN(sec) ? 0 : sec / 60;
  return h * 60 + m + extra;
}

function rangesOverlapMinutes(a0: number, a1: number, b0: number, b1: number): boolean {
  return a0 < b1 && b0 < a1;
}

/** Count slot starts in [start, end) matching the backend iteration (no fractional slots). */
export function countBookableSlotsInWindow(startTime: string, endTime: string, slotMinutes: number): number {
  if (!Number.isFinite(slotMinutes) || slotMinutes <= 0) return 0;
  const a = timeToMinutes(startTime);
  const b = timeToMinutes(endTime);
  if (a >= b) return 0;
  let n = 0;
  let cur = a;
  while (cur < b) {
    if (cur + slotMinutes > b) break;
    n += 1;
    cur += slotMinutes;
  }
  return n;
}

/** True if [start,end) overlaps another window on the same day (server rules). */
export function windowOverlapsExisting(
  day: number,
  startTime: string,
  endTime: string,
  others: DoctorAvailabilityWindow[],
  excludeId?: string
): boolean {
  const a0 = timeToMinutes(startTime);
  const a1 = timeToMinutes(endTime);
  if (a0 >= a1) return true;
  for (const w of others) {
    if (w.day_of_week !== day) continue;
    if (excludeId && String(w.id) === String(excludeId)) continue;
    if (rangesOverlapMinutes(a0, a1, timeToMinutes(w.start_time), timeToMinutes(w.end_time))) {
      return true;
    }
  }
  return false;
}

export function toApiTime(hhmm: string): string {
  const t = hhmm.trim();
  if (t.length === 5) return `${t}:00`;
  return t;
}

export function formatTimeShort(isoish: string): string {
  return isoish.slice(0, 5);
}

export const AVAILABILITY_WEEKDAYS: { dow: number; short: string; label: string }[] = [
  { dow: 0, short: 'Mon', label: 'Monday' },
  { dow: 1, short: 'Tue', label: 'Tuesday' },
  { dow: 2, short: 'Wed', label: 'Wednesday' },
  { dow: 3, short: 'Thu', label: 'Thursday' },
  { dow: 4, short: 'Fri', label: 'Friday' },
  { dow: 5, short: 'Sat', label: 'Saturday' },
  { dow: 6, short: 'Sun', label: 'Sunday' },
];
