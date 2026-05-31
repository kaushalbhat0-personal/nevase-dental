/**
 * trustSignals.ts — emotional trust UX helpers.
 *
 * Calm wording, human-readable summaries, "last updated" indicators,
 * doctor continuity visibility, document verification feel.
 *
 * ALL functions are PURE. NO persistence, NO AI, NO predictions.
 */

import dayjs from 'dayjs';

// ═════════════════════════════════════════════════════════════════════════════
// CALM RELATIVE TIME
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Calm, human-friendly "last updated" label.
 * Avoids clinical/urgent language.
 */
export function calmLastUpdated(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Not yet updated';
  const now = dayjs();
  const d = dayjs(dateStr);
  const diffMinutes = now.diff(d, 'minute');
  const diffHours = now.diff(d, 'hour');
  const diffDays = now.diff(d, 'day');

  if (diffMinutes < 1) return 'Updated just now';
  if (diffMinutes < 60) return `Updated ${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `Updated ${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays === 1) return 'Updated yesterday';
  if (diffDays < 7) return `Updated ${diffDays} days ago`;
  return `Updated ${d.format('MMMM D, YYYY')}`;
}

/**
 * Calm, human-friendly "created" label.
 */
export function calmCreated(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  const d = dayjs(dateStr);
  const now = dayjs();
  const diffDays = now.diff(d, 'day');

  if (diffDays === 0) return 'Added today';
  if (diffDays === 1) return 'Added yesterday';
  if (diffDays < 30) return `Added ${diffDays} days ago`;
  return `Added ${d.format('MMMM D, YYYY')}`;
}

// ═════════════════════════════════════════════════════════════════════════════
// DOCTOR CONTINUITY
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Human-readable continuity label for a doctor relationship.
 */
export function continuityLabel(visitCount: number): string {
  if (visitCount === 0) return 'New doctor';
  if (visitCount === 1) return 'Second visit';
  if (visitCount === 2) return 'Third visit';
  if (visitCount >= 5) return 'Your regular doctor';
  return `${visitCount} visits`;
}

/**
 * Calm description of when you last saw a doctor.
 */
export function lastVisitDescription(dateStr: string | null | undefined): string {
  if (!dateStr) return 'No previous visits';
  const d = dayjs(dateStr);
  const now = dayjs();
  const diffDays = now.diff(d, 'day');

  if (diffDays === 0) return 'You saw them today';
  if (diffDays === 1) return 'You saw them yesterday';
  if (diffDays < 7) return `You saw them ${diffDays} days ago`;
  if (diffDays < 30) return `You saw them ${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? 's' : ''} ago`;
  if (diffDays < 365) return `You saw them ${Math.floor(diffDays / 30)} month${Math.floor(diffDays / 30) > 1 ? 's' : ''} ago`;
  return `Last visit ${d.format('MMMM YYYY')}`;
}

// ═════════════════════════════════════════════════════════════════════════════
// DOCUMENT VERIFICATION FEEL
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Calm label for document availability.
 */
export function documentAvailabilityLabel(
  hasDocument: boolean,
  documentType: string,
): string {
  if (hasDocument) return `${documentType} available`;
  return `${documentType} not yet generated`;
}

/**
 * Verification badge label for documents.
 */
export function documentVerificationBadge(isVerified: boolean): string {
  return isVerified ? 'Verified document' : 'Document';
}

// ═════════════════════════════════════════════════════════════════════════════
// CALM EMPTY STATE MESSAGES
// ═════════════════════════════════════════════════════════════════════════════

export const calmEmptyMessages = {
  noAppointments:
    'No upcoming appointments scheduled. When you book one, it will appear here.',
  noMedicines:
    'No active medications. Any medicines prescribed during your visits will show up here.',
  noDocuments:
    'No documents yet. After your visits, prescriptions and summaries will be available here.',
  noFamily:
    'No family members added yet. You can add dependents and trusted contacts to help manage care together.',
  noEmergencyProfile:
    'No emergency information saved yet. Adding this helps you and your family stay prepared.',
  noTrustedContacts:
    'No trusted contacts added yet. You can add family members or caregivers who help with your care.',
  noRecentCare:
    'No recent care activity. Your health journey will appear here as you visit your doctors.',
};

// ═════════════════════════════════════════════════════════════════════════════
// CARE HISTORY CONTINUITY
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Describe the care relationship duration in a calm way.
 */
export function careRelationshipDuration(
  firstVisitDate: string | null | undefined,
): string {
  if (!firstVisitDate) return '';
  const d = dayjs(firstVisitDate);
  const now = dayjs();
  const diffMonths = now.diff(d, 'month');

  if (diffMonths < 1) return 'Recently started';
  if (diffMonths < 12) return `Caring for ${diffMonths} month${diffMonths > 1 ? 's' : ''}`;
  const years = Math.floor(diffMonths / 12);
  const remainingMonths = diffMonths % 12;
  if (remainingMonths === 0) return `Caring for ${years} year${years > 1 ? 's' : ''}`;
  return `Caring for ${years} year${years > 1 ? 's' : ''} ${remainingMonths} month${remainingMonths > 1 ? 's' : ''}`;
}

// ═════════════════════════════════════════════════════════════════════════════
// HUMAN-READABLE SUMMARIES
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Calm summary of encounter count.
 */
export function encounterCountSummary(count: number): string {
  if (count === 0) return 'No visits yet';
  if (count === 1) return '1 visit';
  return `${count} visits`;
}

/**
 * Calm summary of medication count.
 */
export function medicationCountSummary(count: number): string {
  if (count === 0) return 'No active medications';
  if (count === 1) return '1 active medication';
  return `${count} active medications`;
}
