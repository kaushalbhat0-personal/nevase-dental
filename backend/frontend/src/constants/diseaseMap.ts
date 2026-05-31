/**
 * Maps common symptom / disease shortcuts to specialization search terms for GET /doctors?specialization=...
 * (substring match on doctor.specialization).
 */
export const DISEASE_SPECIALIZATION_MAP = {
  fever: 'general physician',
  skin: 'dermatology',
  dental: 'dentist',
} as const;

export type DiseaseKey = keyof typeof DISEASE_SPECIALIZATION_MAP;

/** Labels shown on home “Common diseases” chips. */
export const COMMON_DISEASES: { key: DiseaseKey; label: string }[] = [
  { key: 'fever', label: 'Fever & cold' },
  { key: 'skin', label: 'Skin issues' },
  { key: 'dental', label: 'Dental' },
];
