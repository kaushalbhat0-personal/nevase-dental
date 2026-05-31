/**
 * Patient Health Workspace API client.
 *
 * These endpoints compose existing domain data into a patient-friendly workspace.
 * They enforce strict patient-scoped access and NEVER expose SOAP/doctor-only fields.
 *
 * Architecture:
 *   - Appointment remains the encounter anchor
 *   - No separate Encounter table exists
 *   - Patient workspace is READ-ORIENTED (doctor workflows mutate)
 *   - Patient identity is resolved from current_user (never from request params)
 */

import { api } from './api';
import type {
  EncounterCard,
  FollowUpSummary,
  PatientHealthWorkspaceAggregate,
  VitalsSnapshot,
} from '../types';

export const patientWorkspaceApi = {
  /**
   * Get the full Patient Health Workspace aggregate for the authenticated patient.
   * GET /patient/workspace
   */
  getWorkspace: async (): Promise<PatientHealthWorkspaceAggregate> => {
    const response = await api.get<PatientHealthWorkspaceAggregate>(
      '/patient/workspace'
    );
    return response.data;
  },

  /**
   * Get paginated encounter cards for the patient timeline.
   * GET /patient/workspace/encounters
   */
  getEncounters: async (
    params?: { skip?: number; limit?: number }
  ): Promise<EncounterCard[]> => {
    const response = await api.get<EncounterCard[]>('/patient/workspace/encounters', {
      params,
    });
    return response.data;
  },

  /**
   * Get chronological vitals history for the patient.
   * GET /patient/workspace/vitals
   */
  getVitalsHistory: async (): Promise<VitalsSnapshot[]> => {
    const response = await api.get<VitalsSnapshot[]>('/patient/workspace/vitals');
    return response.data;
  },

  /**
   * Get follow-up summary for the patient.
   * GET /patient/workspace/follow-ups
   */
  getFollowUps: async (): Promise<FollowUpSummary> => {
    const response = await api.get<FollowUpSummary>('/patient/workspace/follow-ups');
    return response.data;
  },
};
