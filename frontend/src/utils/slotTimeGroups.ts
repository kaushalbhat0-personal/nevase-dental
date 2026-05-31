import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import { DISPLAY_TIMEZONE } from '../constants/time';
import type { DoctorSlot } from '../services/doctors';
import { isSlotInstantInThePast, slotKey } from './doctorSchedule';

dayjs.extend(utc);
dayjs.extend(timezone);

export type DayPart = 'morning' | 'afternoon' | 'evening';

const LABELS: Record<DayPart, string> = {
  morning: 'Morning',
  afternoon: 'Afternoon',
  evening: 'Evening',
};

export function dayPartLabel(part: DayPart): string {
  return LABELS[part];
}

function partForSlot(iso: string, tz: string): DayPart {
  const h = dayjs.utc(iso).tz(tz).hour();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}

const ORDER: DayPart[] = ['morning', 'afternoon', 'evening'];

export function groupDoctorSlotsByDayPart(
  slots: DoctorSlot[],
  tz: string = DISPLAY_TIMEZONE
): { part: DayPart; label: string; slots: DoctorSlot[] }[] {
  const map: Record<DayPart, DoctorSlot[]> = { morning: [], afternoon: [], evening: [] };
  for (const s of slots) {
    map[partForSlot(s.start, tz)].push(s);
  }
  for (const k of ORDER) {
    map[k].sort((a, b) => a.start.localeCompare(b.start));
  }
  return ORDER.map((part) => ({
    part,
    label: LABELS[part],
    slots: map[part],
  })).filter((g) => g.slots.length > 0);
}

/**
 * First future, available slot for highlighting (e.g. "Next available").
 */
export function findNextAvailableSlotKey(
  slots: DoctorSlot[],
  bookDate: string,
  doctorTodayYmd: string
): string | null {
  for (const s of slots) {
    if (!s.available) continue;
    if (bookDate === doctorTodayYmd && isSlotInstantInThePast(s.start)) continue;
    return slotKey(s.start);
  }
  return null;
}
