/**
 * preparationChecklist.ts — static/generic visit preparation checklist items.
 *
 * These are GENERIC preparedness reminders, NOT medical recommendations.
 * No AI, no personalization, no clinical advice.
 *
 * ALL functions are PURE. Items are static and predefined.
 */

// ═════════════════════════════════════════════════════════════════════════════
// TYPES
// ═════════════════════════════════════════════════════════════════════════════

export interface PreparationChecklistItem {
  id: string;
  label: string;
  description: string | null;
  category: 'documents' | 'medication' | 'preparation' | 'logistics';
  /** Whether this item is always shown vs. conditionally shown */
  alwaysShow: boolean;
}

// ═════════════════════════════════════════════════════════════════════════════
// STATIC CHECKLIST ITEMS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Generic preparation checklist items.
 * These are STATIC and GENERIC — no medical recommendations.
 */
export const genericPreparationItems: PreparationChecklistItem[] = [
  {
    id: 'prev-reports',
    label: 'Bring previous reports',
    description: 'Lab reports, scans, or documents from your last visit',
    category: 'documents',
    alwaysShow: true,
  },
  {
    id: 'medicines-list',
    label: 'Bring your current medicines list',
    description: 'A list of medicines you are currently taking',
    category: 'medication',
    alwaysShow: true,
  },
  {
    id: 'insurance-card',
    label: 'Bring your insurance card',
    description: 'Insurance information if applicable',
    category: 'documents',
    alwaysShow: true,
  },
  {
    id: 'id-proof',
    label: 'Bring a valid ID',
    description: 'Government-issued ID for registration',
    category: 'documents',
    alwaysShow: true,
  },
  {
    id: 'arrive-early',
    label: 'Arrive 15 minutes early',
    description: 'Gives you time to complete any paperwork',
    category: 'logistics',
    alwaysShow: true,
  },
  {
    id: 'questions-list',
    label: 'Write down your questions',
    description: 'Things you want to discuss with your doctor',
    category: 'preparation',
    alwaysShow: true,
  },
  {
    id: 'fasting-check',
    label: 'Check if fasting is needed',
    description: 'Some tests may require fasting — check with your clinic',
    category: 'preparation',
    alwaysShow: true,
  },
  {
    id: 'continue-medicines',
    label: 'Continue your regular medicines',
    description: 'Unless your doctor advised otherwise',
    category: 'medication',
    alwaysShow: true,
  },
  {
    id: 'payment-method',
    label: 'Payment method',
    description: 'Check with your clinic about accepted payment methods',
    category: 'logistics',
    alwaysShow: true,
  },
  {
    id: 'transport',
    label: 'Plan your transport',
    description: 'Check traffic and parking options before you leave',
    category: 'logistics',
    alwaysShow: true,
  },
];

// ═════════════════════════════════════════════════════════════════════════════
// CATEGORY LABELS
// ═════════════════════════════════════════════════════════════════════════════

export function getCategoryLabel(category: PreparationChecklistItem['category']): string {
  switch (category) {
    case 'documents': return 'Documents to Bring';
    case 'medication': return 'Medication';
    case 'preparation': return 'Preparation';
    case 'logistics': return 'Logistics';
    default: return 'Other';
  }
}

export function getCategoryIcon(category: PreparationChecklistItem['category']): string {
  switch (category) {
    case 'documents': return 'FileText';
    case 'medication': return 'Pill';
    case 'preparation': return 'ClipboardList';
    case 'logistics': return 'MapPin';
    default: return 'CheckCircle2';
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// GROUPED ITEMS
// ═════════════════════════════════════════════════════════════════════════════

export interface GroupedChecklist {
  category: PreparationChecklistItem['category'];
  label: string;
  icon: string;
  items: PreparationChecklistItem[];
}

/**
 * Get checklist items grouped by category.
 */
export function getGroupedChecklist(): GroupedChecklist[] {
  const categories: PreparationChecklistItem['category'][] = [
    'documents',
    'medication',
    'preparation',
    'logistics',
  ];

  return categories.map((category) => ({
    category,
    label: getCategoryLabel(category),
    icon: getCategoryIcon(category),
    items: genericPreparationItems.filter((item) => item.category === category),
  }));
}

/**
 * Calm, reassuring header message for the preparation checklist.
 */
export const preparationHeaderMessage =
  'A little preparation helps you make the most of your visit. Here are some things to consider.';

/**
 * Calm footer message.
 */
export const preparationFooterMessage =
  'These are general reminders. Your doctor may give you specific instructions — please follow their advice.';
