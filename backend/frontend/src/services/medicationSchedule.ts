/**
 * Medication Schedule API service — adherence tracking layer.
 *
 * Provides access to PatientMedicationSchedule which is DERIVED from
 * Prescription + PrescriptionItem. It is a reminder/adherence layer ONLY.
 * Prescription remains the canonical source-of-truth.
 *
 * CRITICAL:
 * - Patient access is strictly scoped to their own data
 * - Prescription data is NEVER mutated through these endpoints
 * - Adherence actions affect tracking ONLY
 * - No shadow adherence systems are created
 */

import { api } from './api';

// ═════════════════════════════════════════════════════════════════════════════
// Types
// ═════════════════════════════════════════════════════════════════════════════

export interface MedicationScheduleRead {
  id: string;
  medicine_name: string;
  dosage: string | null;
  frequency: string | null;
  duration: string | null;
  instructions: string | null;
  start_date: string;
  end_date: string | null;
  reminder_times: string[];
  taken_count: number;
  skipped_count: number;
  total_doses: number;
  is_active: boolean;
  status: string;
  adherence_rate: number | null;
  prescription_id: string;
  prescription_item_id: string;
  created_at: string;
}

export interface AdherenceActionPayload {
  action: 'taken' | 'skipped' | 'snoozed';
  scheduled_time: string | null;
}

export interface AdherenceActionResponse {
  schedule: MedicationScheduleRead;
  message: string;
}

export interface TodayAdherenceSummary {
  total_due_today: number;
  taken_today: number;
  skipped_today: number;
  pending_today: number;
  adherence_rate_today: number;
  current_streak_days: number;
  longest_streak_days: number;
  week_adherence_rate: number;
}

export interface MedicationScheduleListResponse {
  items: MedicationScheduleRead[];
  total: number;
  skip: number;
  limit: number;
}

export interface MedicationScheduleCreatePayload {
  prescription_item_id: string;
  start_date: string;
  end_date?: string | null;
  reminder_times?: string[];
}

export interface MedicationScheduleUpdatePayload {
  reminder_times?: string[];
  is_active?: boolean;
  status?: 'active' | 'paused' | 'completed';
}

// ═════════════════════════════════════════════════════════════════════════════
// API calls
// ═════════════════════════════════════════════════════════════════════════════

export const medicationScheduleApi = {
  /**
   * Derive a medication schedule from a prescription item.
   * Prescription data is snapshotted and becomes immutable.
   */
  deriveSchedule: async (data: MedicationScheduleCreatePayload): Promise<MedicationScheduleRead> => {
    const response = await api.post('/patient/medications/derive', data);
    return response.data;
  },

  /**
   * Derive schedules for all items in a prescription.
   * Skips items that already have schedules.
   */
  deriveSchedulesForPrescription: async (prescriptionId: string): Promise<MedicationScheduleRead[]> => {
    const response = await api.post(`/patient/medications/derive/${prescriptionId}`);
    return response.data;
  },

  /**
   * List medication schedules for the current patient.
   */
  listSchedules: async (params?: {
    skip?: number;
    limit?: number;
    active_only?: boolean;
    status_filter?: string;
  }): Promise<MedicationScheduleListResponse> => {
    const response = await api.get('/patient/medications', { params });
    return response.data;
  },

  /**
   * Get medications due today.
   */
  getDueMedications: async (): Promise<MedicationScheduleRead[]> => {
    const response = await api.get('/patient/medications/due');
    return response.data;
  },

  /**
   * Get today's adherence summary.
   */
  getAdherenceSummary: async (): Promise<TodayAdherenceSummary> => {
    const response = await api.get('/patient/medications/summary');
    return response.data;
  },

  /**
   * Get a single medication schedule by ID.
   */
  getSchedule: async (scheduleId: string): Promise<MedicationScheduleRead> => {
    const response = await api.get(`/patient/medications/${scheduleId}`);
    return response.data;
  },

  /**
   * Record an adherence action (taken/skipped/snoozed).
   * These actions affect adherence tracking ONLY.
   * They NEVER modify the Prescription or PrescriptionItem rows.
   */
  recordAdherence: async (
    scheduleId: string,
    action: AdherenceActionPayload
  ): Promise<AdherenceActionResponse> => {
    const response = await api.post(`/patient/medications/${scheduleId}/adherence`, action);
    return response.data;
  },

  /**
   * Update a medication schedule (patient-safe fields only).
   * Patients can ONLY update reminder_times, is_active, and status.
   */
  updateSchedule: async (
    scheduleId: string,
    updates: MedicationScheduleUpdatePayload
  ): Promise<MedicationScheduleRead> => {
    const response = await api.patch(`/patient/medications/${scheduleId}`, updates);
    return response.data;
  },
};
