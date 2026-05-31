/**
 * trustAndFamily.ts — API client for trust & family features.
 *
 * Emergency profile CRUD, trusted contacts, dependent linkage.
 * Minimal backend calls — most data is presentational.
 */

import { api } from './api';
import type {
  EmergencyProfile,
  EmergencyProfileUpdate,
  TrustedContact,
  DependentProfile,
  CaregiverAccess,
  HealthSummaryMetadata,
  PatientTrustAggregate,
} from '../types';

// ═════════════════════════════════════════════════════════════════════════════
// EMERGENCY PROFILE
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get the patient's emergency profile.
 */
export async function getEmergencyProfile(): Promise<EmergencyProfile> {
  const response = await api.get('/patient/emergency-profile');
  return response.data;
}

/**
 * Update the patient's emergency profile.
 */
export async function updateEmergencyProfile(
  data: EmergencyProfileUpdate,
): Promise<EmergencyProfile> {
  const response = await api.put('/patient/emergency-profile', data);
  return response.data;
}

// ═════════════════════════════════════════════════════════════════════════════
// TRUSTED CONTACTS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get all trusted contacts for the patient.
 */
export async function getTrustedContacts(): Promise<TrustedContact[]> {
  const response = await api.get('/patient/trusted-contacts');
  return response.data;
}

/**
 * Update trusted contacts list.
 */
export async function updateTrustedContacts(
  contacts: TrustedContact[],
): Promise<TrustedContact[]> {
  const response = await api.put('/patient/trusted-contacts', { contacts });
  return response.data;
}

// ═════════════════════════════════════════════════════════════════════════════
// DEPENDENTS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get all dependents for the patient.
 */
export async function getDependents(): Promise<DependentProfile[]> {
  const response = await api.get('/patient/dependents');
  return response.data;
}

// ═════════════════════════════════════════════════════════════════════════════
// CAREGIVERS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get all caregivers who have access to this patient's data.
 */
export async function getCaregivers(): Promise<CaregiverAccess[]> {
  const response = await api.get('/patient/caregivers');
  return response.data;
}

// ═════════════════════════════════════════════════════════════════════════════
// HEALTH SUMMARY
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get metadata about the downloadable health summary.
 */
export async function getHealthSummaryMetadata(): Promise<HealthSummaryMetadata> {
  const response = await api.get('/documents/health-summary/meta');
  return response.data;
}

/**
 * Download the consolidated health summary PDF.
 */
export async function downloadHealthSummary(): Promise<Blob> {
  const response = await api.get('/documents/health-summary/download', {
    responseType: 'blob',
  });
  return response.data;
}

// ═════════════════════════════════════════════════════════════════════════════
// TRUST AGGREGATE
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get all trust & family data in a single call.
 */
export async function getPatientTrustAggregate(): Promise<PatientTrustAggregate> {
  const response = await api.get('/patient/trust-aggregate');
  return response.data;
}
