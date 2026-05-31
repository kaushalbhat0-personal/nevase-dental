import type { Doctor } from '@/types';

/** Higher = show first. Mirrors list conversion priorities (today > soon > verified). */
export function doctorDiscoverySortScore(d: Doctor): number {
  const avToday = d.available_today === true || d.availability_status === 'available_today';
  const nextSoon =
    avToday ||
    d.availability_status === 'next_available_tomorrow' ||
    (typeof d.next_available_slot === 'string' && d.next_available_slot.length > 0);
  const verified = (d.verification_status ?? '') === 'approved';
  return (avToday ? 50 : 0) + (nextSoon ? 30 : 0) + (verified ? 20 : 0);
}
