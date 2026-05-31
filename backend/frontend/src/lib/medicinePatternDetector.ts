/**
 * Simple heuristic to detect likely medicine instructions in free-text notes.
 * Intentionally simple and low-risk - only triggers on clear patterns.
 */
// Lightweight structural type for Appointment fields used in this utility
interface MedicineDetectionAppointment {
  clinical_notes?: string | null;
  subjective_notes?: string | null;
  objective_notes?: string | null;
  assessment_notes?: string | null;
  plan_notes?: string | null;
  diagnosis?: string | null;
  treatment_summary?: string | null;
  inventory_usages?: any[] | null;
  prescriptions?: any[] | null;
}

export function containsLikelyMedicineInstructions(text: string): boolean {
  if (!text || typeof text !== 'string') return false;
  
  const lowerText = text.toLowerCase().trim();
  if (lowerText.length < 3) return false; // Too short to be meaningful
  
  // Simple patterns that strongly suggest medicine instructions
  const medicinePatterns = [
    // Dosage patterns: number followed by mg/ml/tablet/capsule etc.
    /\d+\s*(mg|ml|tablet|tablets|capsule|capsules|gm|grams?|iu|units?)\b/,
    // Frequency patterns
    /\b(once|twice|thrice|daily|daily\.|bd|tds|qid|od|hs|pc|ac)\b/i,
    // Common medicine instruction phrases
    /\b(after food|before food|with food|empty stomach)\b/i,
    /\b(take|apply|use)\s+\d+\s*(mg|ml|tablet|capsule)\b/i
  ];
  
  return medicinePatterns.some(pattern => pattern.test(lowerText));
}

/**
 * Check if any notes fields contain likely medicine instructions
 */
export function hasMedicineLikeNotes(appointment: MedicineDetectionAppointment): boolean {
  const noteFields = [
    appointment.clinical_notes,
    appointment.subjective_notes,
    appointment.objective_notes,
    appointment.assessment_notes,
    appointment.plan_notes,
    appointment.diagnosis,
    appointment.treatment_summary
  ];
  
  return noteFields.some((field): field is string => 
    field != null && typeof field === 'string' && containsLikelyMedicineInstructions(field)
  );
}

/**
 * Check if structured medicine items exist (inventory usages or prescriptions)
 */
export function hasStructuredMedicines(appointment: MedicineDetectionAppointment): boolean {
  const hasInventoryUsages = !!(appointment.inventory_usages && 
    Array.isArray(appointment.inventory_usages) && 
    appointment.inventory_usages.length > 0);
    
  const hasPrescriptions = !!(appointment.prescriptions && 
    Array.isArray(appointment.prescriptions) && 
    appointment.prescriptions.length > 0);
    
  return hasInventoryUsages || hasPrescriptions;
}