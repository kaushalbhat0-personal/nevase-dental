/**
 * familyHelpers.ts — family/dependent display helpers.
 *
 * Relationship label mapping, dependent display helpers,
 * "shared with" indicator logic.
 *
 * ALL functions are PURE. NO persistence, NO auth delegation.
 */

// ═════════════════════════════════════════════════════════════════════════════
// RELATIONSHIP LABELS
// ═════════════════════════════════════════════════════════════════════════════

export type RelationshipType =
  | 'self'
  | 'spouse'
  | 'child'
  | 'parent'
  | 'sibling'
  | 'grandparent'
  | 'grandchild'
  | 'other_family'
  | 'friend'
  | 'caregiver'
  | 'legal_guardian'
  | 'other';

const relationshipLabels: Record<RelationshipType, string> = {
  self: 'Self',
  spouse: 'Spouse',
  child: 'Child',
  parent: 'Parent',
  sibling: 'Sibling',
  grandparent: 'Grandparent',
  grandchild: 'Grandchild',
  other_family: 'Family Member',
  friend: 'Friend',
  caregiver: 'Caregiver',
  legal_guardian: 'Legal Guardian',
  other: 'Other',
};

const relationshipIcons: Record<RelationshipType, string> = {
  self: 'User',
  spouse: 'Heart',
  child: 'Baby',
  parent: 'Users',
  sibling: 'Users',
  grandparent: 'Users',
  grandchild: 'Baby',
  other_family: 'Users',
  friend: 'UserPlus',
  caregiver: 'HeartHandshake',
  legal_guardian: 'Shield',
  other: 'User',
};

/**
 * Get human-readable relationship label.
 */
export function getRelationshipLabel(relationship: RelationshipType | string): string {
  return relationshipLabels[relationship as RelationshipType] ?? relationship ?? 'Other';
}

/**
 * Get icon name for a relationship type.
 */
export function getRelationshipIcon(relationship: RelationshipType | string): string {
  return relationshipIcons[relationship as RelationshipType] ?? 'User';
}

/**
 * Get all available relationship types for selection.
 */
export function getRelationshipOptions(): Array<{ value: RelationshipType; label: string }> {
  return Object.entries(relationshipLabels).map(([value, label]) => ({
    value: value as RelationshipType,
    label,
  }));
}

// ═════════════════════════════════════════════════════════════════════════════
// AGE GROUP LABELS
// ═════════════════════════════════════════════════════════════════════════════

export type AgeGroup = 'infant' | 'child' | 'teen' | 'adult' | 'senior';

export function getAgeGroup(age: number | null | undefined): AgeGroup | null {
  if (age === null || age === undefined) return null;
  if (age < 2) return 'infant';
  if (age < 13) return 'child';
  if (age < 20) return 'teen';
  if (age < 65) return 'adult';
  return 'senior';
}

export function getAgeGroupLabel(ageGroup: AgeGroup | null): string {
  switch (ageGroup) {
    case 'infant': return 'Infant';
    case 'child': return 'Child';
    case 'teen': return 'Teen';
    case 'adult': return 'Adult';
    case 'senior': return 'Senior';
    default: return '';
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// "SHARED WITH" INDICATORS
// ═════════════════════════════════════════════════════════════════════════════

export interface SharedWithInfo {
  contactId: string;
  name: string;
  relationship: string;
  /** What is shared: 'appointments' | 'medications' | 'documents' | 'all' */
  sharedItems: Array<'appointments' | 'medications' | 'documents' | 'all'>;
}

/**
 * Get a human-readable summary of what is shared with a contact.
 */
export function getSharedWithSummary(sharedItems: SharedWithInfo['sharedItems']): string {
  if (sharedItems.length === 0) return 'Nothing shared';
  if (sharedItems.includes('all')) return 'Full access';

  const labels: string[] = [];
  if (sharedItems.includes('appointments')) labels.push('appointments');
  if (sharedItems.includes('medications')) labels.push('medications');
  if (sharedItems.includes('documents')) labels.push('documents');

  if (labels.length === 1) return `Shared: ${labels[0]}`;
  if (labels.length === 2) return `Shared: ${labels[0]} and ${labels[1]}`;
  return `Shared: ${labels.slice(0, -1).join(', ')}, and ${labels[labels.length - 1]}`;
}

// ═════════════════════════════════════════════════════════════════════════════
// DEPENDENT DISPLAY HELPERS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get a display label for a dependent's age.
 */
export function dependentAgeLabel(age: number | null | undefined): string {
  if (age === null || age === undefined) return '';
  if (age < 1) return `${Math.round(age * 12)} months old`;
  if (age === 1) return '1 year old';
  return `${age} years old`;
}

/**
 * Get a calm, family-friendly label for a dependent.
 */
export function dependentDisplayLabel(
  name: string,
  relationship: string,
  age: number | null | undefined,
): string {
  const ageLabel = dependentAgeLabel(age);
  const relLabel = getRelationshipLabel(relationship);
  if (ageLabel) return `${name}, ${relLabel.toLowerCase()}, ${ageLabel}`;
  return `${name}, ${relLabel.toLowerCase()}`;
}

/**
 * Get a family-aware contextual greeting.
 */
export function familyAwareGreeting(
  hasDependents: boolean,
  dependentName?: string | null,
): string {
  if (!hasDependents || !dependentName) return "Today's Care";
  return `Caring for ${dependentName}`;
}

/**
 * Get a family-aware appointment label.
 */
export function familyAwareAppointmentLabel(
  isDependent: boolean,
  dependentName?: string | null,
  doctorName?: string | null,
): string {
  if (isDependent && dependentName) {
    return `${dependentName}'s visit with ${doctorName ?? 'doctor'}`;
  }
  return `Your visit with ${doctorName ?? 'doctor'}`;
}

/**
 * Get a family-aware medication reminder label.
 */
export function familyAwareMedicationLabel(
  isDependent: boolean,
  dependentName?: string | null,
  medicineName?: string | null,
): string {
  if (isDependent && dependentName) {
    return `${dependentName}'s ${medicineName ?? 'medication'}`;
  }
  return medicineName ?? 'Medication';
}
