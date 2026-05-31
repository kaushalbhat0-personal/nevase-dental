/**
 * Encounter Workspace Components
 * 
 * Reusable sections for the clinical encounter workspace.
 * These components form the building blocks of the Encounter Workspace UI,
 * designed for Phase 2 clinical feature extensibility.
 * 
 * Architecture principles:
 * - Clinical-first hierarchy (diagnosis > treatment > notes > medicines > billing)
 * - Mobile-responsive design
 * - Section-based organization for future extensibility
 * - No role-based authorization (capability-based only)
 */

export { EncounterHeaderSection } from './EncounterHeaderSection';
export { EncounterClinicalSection } from './EncounterClinicalSection';
export { EncounterMedicationSection } from './EncounterMedicationSection';
export { EncounterBillingSection } from './EncounterBillingSection';
export { EncounterTimelineSection } from './EncounterTimelineSection';
export { EncounterVitalsSection } from './EncounterVitalsSection';
export { EncounterSOAPSection } from './EncounterSOAPSection';
export { EncounterPrescriptionsSection } from './EncounterPrescriptionsSection';
export { EncounterFollowUpSection } from './EncounterFollowUpSection';

// Future extension exports (Phase 2):
// export { EncounterAttachmentsSection } from './EncounterAttachmentsSection';
// export { EncounterSoapNotesSection } from './EncounterSoapNotesSection';
// export { EncounterAiSummarySection } from './EncounterAiSummarySection';
