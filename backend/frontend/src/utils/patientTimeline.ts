/**
 * patientTimeline.ts — encounter display formatters, timeline grouping,
 * category detection, and derived health insights.
 *
 * ALL functions are PURE and derive from existing aggregate data only.
 * NO persistence, NO AI, NO diagnosis, NO predictions.
 *
 * CRITICAL:
 * - Insights are observational only
 * - Categories are keyword-based, NOT ML/NLP
 * - No health scoring or risk assessment
 */

import dayjs from 'dayjs';
import type { EncounterCard, EncounterDetailAggregate } from '../types';

// ═════════════════════════════════════════════════════════════════════════════
// ENCOUNTER CATEGORY
// ═════════════════════════════════════════════════════════════════════════════

export type EncounterCategory =
  | 'consultation'
  | 'follow-up'
  | 'checkup'
  | 'emergency'
  | 'procedure'
  | 'vaccination'
  | 'lab'
  | 'general';

const CATEGORY_KEYWORDS: Record<EncounterCategory, string[]> = {
  consultation: ['consultation', 'consult', 'new visit', 'first visit', 'initial'],
  'follow-up': ['follow-up', 'followup', 'follow up', 'review', 'revisit'],
  checkup: ['checkup', 'check-up', 'check up', 'annual', 'routine', 'physical', 'wellness', 'preventive'],
  emergency: ['emergency', 'urgent', 'acute', 'severe'],
  procedure: ['procedure', 'surgery', 'operation', 'dressing', 'injection', 'infusion'],
  vaccination: ['vaccination', 'vaccine', 'immunization', 'shot', 'booster'],
  lab: ['lab', 'test', 'investigation', 'scan', 'x-ray', 'blood work', 'pathology'],
  general: [],
};

/**
 * Derive an encounter category from diagnosis and treatment_summary text.
 * Uses simple keyword matching — NOT ML/NLP.
 * Falls back to 'general' when no keywords match.
 */
export function getEncounterCategory(
  diagnosis: string | null | undefined,
  treatmentSummary: string | null | undefined,
): EncounterCategory {
  const text = [diagnosis ?? '', treatmentSummary ?? '']
    .join(' ')
    .toLowerCase()
    .trim();

  if (!text) return 'general';

  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    if (category === 'general') continue;
    if (keywords.some((kw) => text.includes(kw))) {
      return category as EncounterCategory;
    }
  }

  return 'general';
}

/**
 * Get encounter category from an EncounterCard.
 */
export function getEncounterCategoryFromCard(
  card: EncounterCard,
): EncounterCategory {
  return getEncounterCategory(card.diagnosis, card.treatment_summary);
}

/**
 * Get encounter category from an EncounterDetailAggregate.
 */
export function getEncounterCategoryFromDetail(
  detail: EncounterDetailAggregate,
): EncounterCategory {
  return getEncounterCategory(
    detail.appointment.diagnosis,
    detail.appointment.treatment_summary,
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// DATE FORMATTING
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Calm, readable date formatting for encounter display.
 * E.g. "Monday, March 15 · 10:30 AM"
 */
export function formatEncounterDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Date unknown';
  const d = dayjs(dateStr);
  return d.format('dddd, MMMM D · h:mm A');
}

/**
 * Short date for timeline cards.
 * E.g. "Mar 15, 2026"
 */
export function formatShortDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  return dayjs(dateStr).format('MMM D, YYYY');
}

/**
 * Relative date for continuity display.
 * E.g. "2 months ago", "Last week", "Yesterday"
 */
export function formatRelativeDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  const now = dayjs();
  const d = dayjs(dateStr);
  const diffDays = now.diff(d, 'day');

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? 's' : ''} ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} month${Math.floor(diffDays / 30) > 1 ? 's' : ''} ago`;
  return `${Math.floor(diffDays / 365)} year${Math.floor(diffDays / 365) > 1 ? 's' : ''} ago`;
}

// ═════════════════════════════════════════════════════════════════════════════
// TIMELINE GROUPING
// ═════════════════════════════════════════════════════════════════════════════

export interface YearGroup {
  year: number;
  label: string;
  months: MonthGroup[];
  totalEncounters: number;
}

export interface MonthGroup {
  key: string; // "YYYY-MM"
  label: string; // "March 2026"
  items: EncounterCard[];
}

/**
 * Group encounters by year → month, sorted newest first.
 */
export function groupEncountersByYearMonth(
  encounters: EncounterCard[],
): YearGroup[] {
  const yearMap = new Map<number, Map<string, EncounterCard[]>>();

  for (const enc of encounters) {
    if (!enc.appointment_time) continue;
    const d = dayjs(enc.appointment_time);
    const year = d.year();
    const monthKey = d.format('YYYY-MM');

    if (!yearMap.has(year)) {
      yearMap.set(year, new Map());
    }
    const monthMap = yearMap.get(year)!;
    if (!monthMap.has(monthKey)) {
      monthMap.set(monthKey, []);
    }
    monthMap.get(monthKey)!.push(enc);
  }

  // Sort years descending
  const sortedYears = Array.from(yearMap.entries()).sort(
    ([a], [b]) => b - a,
  );

  return sortedYears.map(([year, monthMap]) => {
    const sortedMonths = Array.from(monthMap.entries()).sort(([a], [b]) =>
      b.localeCompare(a),
    );

    const months: MonthGroup[] = sortedMonths.map(([key, items]) => ({
      key,
      label: items[0]?.appointment_time
        ? dayjs(items[0].appointment_time).format('MMMM YYYY')
        : key,
      items,
    }));

    const totalEncounters = months.reduce((sum, m) => sum + m.items.length, 0);

    return {
      year,
      label: String(year),
      months,
      totalEncounters,
    };
  });
}

// ═════════════════════════════════════════════════════════════════════════════
// DERIVED HEALTH INSIGHTS (observational only)
// ═════════════════════════════════════════════════════════════════════════════

export interface HealthInsight {
  type: 'visit_frequency' | 'bp_trend' | 'follow_up_status' | 'care_streak' | 'specialty_diversity';
  message: string;
  icon: string; // lucide icon name
  priority: 'high' | 'medium' | 'low';
}

/**
 * Derive observational health insights from encounter data.
 *
 * CRITICAL:
 * - Insights are observational only
 * - NO diagnostic statements
 * - NO treatment recommendations
 * - NO predictions
 * - NO health scoring
 */
export function deriveHealthInsights(
  encounters: EncounterCard[],
): HealthInsight[] {
  const insights: HealthInsight[] = [];

  if (encounters.length === 0) return insights;

  // ── Visit frequency per doctor ──────────────────────────────────────────
  const doctorCounts = new Map<string, { name: string; count: number }>();
  for (const enc of encounters) {
    const key = enc.doctor_id;
    const existing = doctorCounts.get(key) ?? {
      name: enc.doctor_name,
      count: 0,
    };
    existing.count += 1;
    doctorCounts.set(key, existing);
  }

  for (const [, { name, count }] of doctorCounts) {
    if (count >= 3) {
      insights.push({
        type: 'visit_frequency',
        message: `You visited Dr. ${name} ${count} times`,
        icon: 'User',
        priority: count >= 5 ? 'high' : 'medium',
      });
    }
  }

  // ── BP trend (observational comparison only) ────────────────────────────
  const encountersWithBP = encounters.filter(
    (e) => e.diagnosis?.toLowerCase().includes('bp') ||
           e.diagnosis?.toLowerCase().includes('blood pressure') ||
           e.treatment_summary?.toLowerCase().includes('bp') ||
           e.treatment_summary?.toLowerCase().includes('blood pressure'),
  );
  if (encountersWithBP.length >= 2) {
    insights.push({
      type: 'bp_trend',
      message: `Blood pressure was discussed in your last ${encountersWithBP.length} visits`,
      icon: 'Activity',
      priority: 'medium',
    });
  }

  // ── Follow-up completion ────────────────────────────────────────────────
  const completedFollowUps = encounters.filter(
    (e) => e.follow_up_date && e.status === 'completed',
  );
  if (completedFollowUps.length > 0) {
    insights.push({
      type: 'follow_up_status',
      message: `${completedFollowUps.length} follow-up${completedFollowUps.length > 1 ? 's' : ''} completed`,
      icon: 'CheckCircle2',
      priority: 'low',
    });
  }

  // ── Care streak (recent activity) ───────────────────────────────────────
  const recentEncounters = encounters.filter((e) => {
    if (!e.appointment_time) return false;
    return dayjs().diff(dayjs(e.appointment_time), 'month') <= 6;
  });
  if (recentEncounters.length >= 3) {
    insights.push({
      type: 'care_streak',
      message: `${recentEncounters.length} visits in the last 6 months`,
      icon: 'Sparkles',
      priority: 'medium',
    });
  }

  // ── Specialty diversity ─────────────────────────────────────────────────
  const specialties = new Set(
    encounters
      .map((e) => e.doctor_specialization)
      .filter((s): s is string => !!s),
  );
  if (specialties.size >= 3) {
    insights.push({
      type: 'specialty_diversity',
      message: `You've consulted ${specialties.size} different specialties`,
      icon: 'Stethoscope',
      priority: 'low',
    });
  }

  return insights;
}

// ═════════════════════════════════════════════════════════════════════════════
// VISIT COUNT HELPERS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get the visit number for a specific doctor (1-indexed).
 */
export function getVisitNumberForDoctor(
  encounters: EncounterCard[],
  doctorId: string,
): number {
  return encounters.filter((e) => e.doctor_id === doctorId).length;
}

/**
 * Get total encounter count.
 */
export function getTotalEncounterCount(encounters: EncounterCard[]): number {
  return encounters.length;
}

/**
 * Get the most recent encounter date.
 */
export function getMostRecentEncounterDate(
  encounters: EncounterCard[],
): string | null {
  if (encounters.length === 0) return null;
  const sorted = [...encounters].sort((a, b) =>
    (b.appointment_time ?? '').localeCompare(a.appointment_time ?? ''),
  );
  return sorted[0]?.appointment_time ?? null;
}
