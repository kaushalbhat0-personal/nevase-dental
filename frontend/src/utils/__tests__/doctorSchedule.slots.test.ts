import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  appointmentCalendarDayYmd,
  assignOverlapLanesPure,
  dedupeDoctorSlots,
  formatNextAvailablePhrase,
  formatSlotTime,
  slotKey,
} from '../doctorSchedule';

describe('slotKey', () => {
  it('zeros sub-second noise to match backend minute boundaries', () => {
    const a = '2035-06-15T10:00:00.007Z';
    const b = '2035-06-15T10:00:00.000Z';
    expect(slotKey(a)).toBe(slotKey(b));
  });

  it('is stable across DST-style ISO strings (UTC normalization)', () => {
    const winter = '2026-01-15T15:30:00+00:00';
    expect(slotKey(winter)).toBe('2026-01-15T15:30:00.000Z');
  });
});

describe('formatSlotTime', () => {
  it('renders API instant in IST (12:00 UTC → 5:30 PM IST)', () => {
    expect(formatSlotTime('2035-06-15T12:00:00.000Z', 'Asia/Kolkata')).toBe('5:30 PM');
  });

  it('maps late UTC evening to next calendar day midnight IST (regression)', () => {
    expect(formatSlotTime('2026-04-23T18:30:00.000Z', 'UTC')).toBe('12:00 AM');
  });
});

describe('appointmentCalendarDayYmd', () => {
  it('uses IST calendar day (UTC evening → next day in Asia/Kolkata)', () => {
    expect(appointmentCalendarDayYmd('2026-04-23T18:30:00.000Z', 'Asia/Kolkata')).toBe('2026-04-24');
  });

  it('ignores a non-IST profile zone and still uses IST for the calendar day', () => {
    expect(appointmentCalendarDayYmd('2026-04-23T18:30:00.000Z', 'America/New_York')).toBe('2026-04-24');
  });
});

describe('formatNextAvailablePhrase', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('says Today when slot instant maps to IST calendar today', () => {
    vi.setSystemTime(new Date('2026-04-24T10:00:00.000Z'));
    const iso = '2026-04-24T03:30:00.000Z';
    const slotDay = appointmentCalendarDayYmd(iso, 'Asia/Kolkata');
    expect(slotDay).toBe('2026-04-24');
    expect(formatNextAvailablePhrase(iso, slotDay, '2026-04-24', 'Asia/Kolkata')).toMatch(/^Today at /);
  });

  it('says Tomorrow when slot is the next IST calendar day', () => {
    vi.setSystemTime(new Date('2026-04-23T10:00:00.000Z'));
    const iso = '2026-04-24T03:30:00.000Z';
    const slotDay = appointmentCalendarDayYmd(iso, 'Asia/Kolkata');
    expect(formatNextAvailablePhrase(iso, slotDay, '2026-04-23', 'Asia/Kolkata')).toMatch(/^Tomorrow at /);
  });
});

describe('dedupeDoctorSlots', () => {
  it('merges rows that differ only by sub-second start', () => {
    const rows = [
      { start: '2035-06-15T10:00:00.100Z', available: true },
      { start: '2035-06-15T10:00:00.900Z', available: false },
    ];
    const out = dedupeDoctorSlots(rows);
    expect(out).toHaveLength(1);
    expect(out[0].available).toBe(false);
  });
});

describe('assignOverlapLanesPure', () => {
  it('uses three lanes when three intervals mutually overlap', () => {
    const placed = assignOverlapLanesPure([
      { start: 0, end: 30 },
      { start: 10, end: 40 },
      { start: 20, end: 50 },
    ]);
    expect(placed.map((p) => p.lane)).toEqual([0, 1, 2]);
    expect(placed.every((p) => p.laneCount === 3)).toBe(true);
  });

  it('reuses a lane when the interval starts after that lane ends', () => {
    const placed = assignOverlapLanesPure([
      { start: 0, end: 10 },
      { start: 12, end: 18 },
      { start: 15, end: 25 },
    ]);
    expect(placed.map((p) => p.lane)).toEqual([0, 0, 1]);
    expect(placed.every((p) => p.laneCount === 2)).toBe(true);
  });
});
