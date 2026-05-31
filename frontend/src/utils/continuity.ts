/**
 * continuity.ts — continuity-of-care calculators from existing encounter data.
 *
 * ALL functions are PURE and derive from existing aggregate data only.
 * NO persistence, NO AI, NO predictions.
 */

import dayjs from 'dayjs';
import type { EncounterCard } from '../types';

// ═════════════════════════════════════════════════════════════════════════════
// PRIMARY DOCTOR
// ═════════════════════════════════════════════════════════════════════════════

export interface PrimaryDoctor {
  doctorId: string;
  name: string;
  specialization: string | null;
  visitCount: number;
  lastVisit: string | null;
}

/**
 * Get the most frequently visited doctor from encounter history.
 */
export function getPrimaryDoctor(encounters: EncounterCard[]): PrimaryDoctor | null {
  if (encounters.length === 0) return null;

  const doctorMap = new Map<
    string,
    { name: string; specialization: string | null; count: number; lastVisit: string | null }
  >();

  for (const enc of encounters) {
    const existing = doctorMap.get(enc.doctor_id) ?? {
      name: enc.doctor_name,
      specialization: enc.doctor_specialization,
      count: 0,
      lastVisit: null as string | null,
    };
    existing.count += 1;
    // Track most recent visit
    if (
      enc.appointment_time &&
      (!existing.lastVisit || enc.appointment_time > existing.lastVisit)
    ) {
      existing.lastVisit = enc.appointment_time;
    }
    doctorMap.set(enc.doctor_id, existing);
  }

  // Find doctor with highest visit count
  let primary: PrimaryDoctor | null = null;
  for (const [doctorId, info] of doctorMap) {
    if (!primary || info.count > primary.visitCount) {
      primary = {
        doctorId,
        name: info.name,
        specialization: info.specialization,
        visitCount: info.count,
        lastVisit: info.lastVisit,
      };
    }
  }

  return primary;
}

// ═════════════════════════════════════════════════════════════════════════════
// CARE STREAK
// ═════════════════════════════════════════════════════════════════════════════

export interface CareStreak {
  /** Number of consecutive months with at least one visit */
  consecutiveMonths: number;
  /** Start of the streak */
  startDate: string | null;
  /** End of the streak (most recent visit) */
  endDate: string | null;
  /** Total visits in the streak period */
  totalVisits: number;
}

/**
 * Calculate the current care streak (consecutive months with visits).
 */
export function getCareStreak(encounters: EncounterCard[]): CareStreak {
  if (encounters.length === 0) {
    return { consecutiveMonths: 0, startDate: null, endDate: null, totalVisits: 0 };
  }

  // Sort by date ascending
  const sorted = [...encounters]
    .filter((e) => !!e.appointment_time)
    .sort((a, b) => (a.appointment_time ?? '').localeCompare(b.appointment_time ?? ''));

  if (sorted.length === 0) {
    return { consecutiveMonths: 0, startDate: null, endDate: null, totalVisits: 0 };
  }

  // Get unique months with visits
  const monthsSet = new Set<string>();
  for (const enc of sorted) {
    monthsSet.add(dayjs(enc.appointment_time).format('YYYY-MM'));
  }

  const uniqueMonths = Array.from(monthsSet).sort();
  const now = dayjs().format('YYYY-MM');

  // Count consecutive months from most recent backwards
  let streak = 0;
  let currentIdx = uniqueMonths.length - 1;

  while (currentIdx >= 0) {
    const expectedMonth =
      streak === 0
        ? now
        : dayjs(uniqueMonths[currentIdx + 1])
            .subtract(1, 'month')
            .format('YYYY-MM');

    if (uniqueMonths[currentIdx] === expectedMonth || uniqueMonths[currentIdx] === now) {
      streak += 1;
      currentIdx -= 1;
    } else {
      break;
    }
  }

  const streakMonths = uniqueMonths.slice(-streak);

  return {
    consecutiveMonths: streak,
    startDate: streakMonths.length > 0 ? dayjs(streakMonths[0]).startOf('month').toISOString() : null,
    endDate: sorted[sorted.length - 1]?.appointment_time ?? null,
    totalVisits: sorted.filter((e) => {
      const m = dayjs(e.appointment_time).format('YYYY-MM');
      return streakMonths.includes(m);
    }).length,
  };
}

// ═════════════════════════════════════════════════════════════════════════════
// RECENT SPECIALTY HISTORY
// ═════════════════════════════════════════════════════════════════════════════

export interface SpecialtyVisit {
  specialization: string;
  visitCount: number;
  lastVisit: string | null;
}

/**
 * Get list of specialties visited recently, sorted by frequency.
 */
export function getRecentSpecialtyHistory(
  encounters: EncounterCard[],
  limit: number = 5,
): SpecialtyVisit[] {
  const specialtyMap = new Map<
    string,
    { count: number; lastVisit: string | null }
  >();

  for (const enc of encounters) {
    const spec = enc.doctor_specialization ?? 'General';
    const existing = specialtyMap.get(spec) ?? { count: 0, lastVisit: null as string | null };
    existing.count += 1;
    if (
      enc.appointment_time &&
      (!existing.lastVisit || enc.appointment_time > existing.lastVisit)
    ) {
      existing.lastVisit = enc.appointment_time;
    }
    specialtyMap.set(spec, existing);
  }

  return Array.from(specialtyMap.entries())
    .map(([specialization, info]) => ({
      specialization,
      visitCount: info.count,
      lastVisit: info.lastVisit,
    }))
    .sort((a, b) => b.visitCount - a.visitCount)
    .slice(0, limit);
}

// ═════════════════════════════════════════════════════════════════════════════
// VISIT FREQUENCY BY DOCTOR
// ═════════════════════════════════════════════════════════════════════════════

export interface DoctorVisitFrequency {
  doctorId: string;
  name: string;
  specialization: string | null;
  visitCount: number;
  lastVisit: string | null;
}

/**
 * Get visit frequency per doctor, sorted by count descending.
 */
export function getVisitFrequencyByDoctor(
  encounters: EncounterCard[],
): DoctorVisitFrequency[] {
  const doctorMap = new Map<
    string,
    { name: string; specialization: string | null; count: number; lastVisit: string | null }
  >();

  for (const enc of encounters) {
    const existing = doctorMap.get(enc.doctor_id) ?? {
      name: enc.doctor_name,
      specialization: enc.doctor_specialization,
      count: 0,
      lastVisit: null as string | null,
    };
    existing.count += 1;
    if (
      enc.appointment_time &&
      (!existing.lastVisit || enc.appointment_time > existing.lastVisit)
    ) {
      existing.lastVisit = enc.appointment_time;
    }
    doctorMap.set(enc.doctor_id, existing);
  }

  return Array.from(doctorMap.entries())
    .map(([doctorId, info]) => ({
      doctorId,
      name: info.name,
      specialization: info.specialization,
      visitCount: info.count,
      lastVisit: info.lastVisit,
    }))
    .sort((a, b) => b.visitCount - a.visitCount);
}

// ═════════════════════════════════════════════════════════════════════════════
// ACTIVE MEDICATIONS FROM ENCOUNTERS
// ═════════════════════════════════════════════════════════════════════════════

export interface ActiveMedication {
  medicineName: string;
  dosage: string | null;
  frequency: string | null;
  prescribedBy: string;
  prescribedDate: string | null;
}

/**
 * Get the most recent unique medications from encounter prescriptions.
 * This is derived from encounter card data (prescriptions_count) and
 * would ideally use full prescription data from the aggregate.
 * For timeline cards, we return a simplified view.
 */
export function getActiveMedicationsFromEncounters(
  encounters: EncounterCard[],
  limit: number = 5,
): ActiveMedication[] {
  // EncounterCard only has prescriptions_count, not individual medicines.
  // For full medication details, use the workspace aggregate or encounter detail.
  // This returns a count-based summary.
  const meds: ActiveMedication[] = [];

  for (const enc of encounters) {
    if (enc.prescriptions_count > 0) {
      meds.push({
        medicineName: `${enc.prescriptions_count} medicine${enc.prescriptions_count > 1 ? 's' : ''}`,
        dosage: null,
        frequency: null,
        prescribedBy: enc.doctor_name,
        prescribedDate: enc.appointment_time,
      });
    }
  }

  return meds.slice(0, limit);
}

// ═════════════════════════════════════════════════════════════════════════════
// UPCOMING FOLLOW-UP
// ═════════════════════════════════════════════════════════════════════════════

export interface UpcomingFollowUp {
  appointmentId: string;
  doctorName: string;
  followUpDate: string;
  followUpNotes: string | null;
  isOverdue: boolean;
}

/**
 * Get the next upcoming follow-up from encounters.
 */
export function getUpcomingFollowUp(encounters: EncounterCard[]): UpcomingFollowUp | null {
  const now = dayjs();

  const followUps = encounters
    .filter((e) => !!e.follow_up_date)
    .map((e) => ({
      appointmentId: e.appointment_id,
      doctorName: e.doctor_name,
      followUpDate: e.follow_up_date!,
      followUpNotes: e.follow_up_notes,
      isOverdue: dayjs(e.follow_up_date).isBefore(now),
    }))
    .sort((a, b) => {
      // Overdue first, then by date ascending
      if (a.isOverdue && !b.isOverdue) return -1;
      if (!a.isOverdue && b.isOverdue) return 1;
      return a.followUpDate.localeCompare(b.followUpDate);
    });

  return followUps[0] ?? null;
}

// ═════════════════════════════════════════════════════════════════════════════
// LAST COMPLETED VISIT
// ═════════════════════════════════════════════════════════════════════════════

export interface LastCompletedVisit {
  appointmentId: string;
  doctorName: string;
  specialization: string | null;
  date: string;
  diagnosis: string | null;
}

/**
 * Get the most recent completed visit.
 */
export function getLastCompletedVisit(
  encounters: EncounterCard[],
): LastCompletedVisit | null {
  const completed = encounters
    .filter((e) => e.status === 'completed' && !!e.appointment_time)
    .sort((a, b) => (b.appointment_time ?? '').localeCompare(a.appointment_time ?? ''));

  if (completed.length === 0) return null;

  const last = completed[0]!;
  return {
    appointmentId: last.appointment_id,
    doctorName: last.doctor_name,
    specialization: last.doctor_specialization,
    date: last.appointment_time!,
    diagnosis: last.diagnosis,
  };
}
