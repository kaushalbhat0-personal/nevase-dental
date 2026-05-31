import type { DoctorAvailabilityBadgeTone } from '@/components/patient/DoctorRowCard';
import { DISPLAY_TIMEZONE } from '@/constants/time';
import type { Doctor } from '@/types';
import { formatSlotTime } from '@/utils/doctorSchedule';

export function doctorAvailabilityPresentation(
  d: Pick<
    Doctor,
    'availability_status' | 'has_availability_windows' | 'next_available_slot' | 'available_today'
  >,
  options?: { displayTimeZone?: string }
): { label: string; tone: DoctorAvailabilityBadgeTone; subLabel?: string } {
  const tz = options?.displayTimeZone ?? DISPLAY_TIMEZONE;
  const st = d.availability_status;
  const subFromProfile =
    typeof d.next_available_slot === 'string' && d.next_available_slot.length > 0
      ? `Next slot: ${formatSlotTime(d.next_available_slot, tz)}`
      : undefined;

  if (d.available_today === true || st === 'available_today') {
    return { label: '🟢 Available today', tone: 'today', subLabel: subFromProfile };
  }
  if (st === 'next_available_tomorrow') {
    return { label: 'Next available tomorrow', tone: 'tomorrow', subLabel: subFromProfile };
  }
  if (d.has_availability_windows === false) return { label: 'Call clinic to book', tone: 'muted' };
  return { label: 'Check availability', tone: 'muted' };
}
