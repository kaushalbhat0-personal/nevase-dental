import { api } from './api';
import { safeArray } from '../utils';
import type { Appointment, EncounterDetailAggregate } from '../types';

export interface CreateAppointmentData {
  patient_id: string;
  doctor_id: string;
  appointment_time: string;
  notes?: string;
}

export interface AppointmentFilters {
  doctor_id?: string;
  patient_id?: string;
  status?: 'scheduled' | 'completed' | 'cancelled' | 'pending';
  /** `past` = completed/cancelled or overdue scheduled; `upcoming` = future scheduled. */
  type?: 'past' | 'upcoming';
  skip?: number;
  limit?: number;
}

export const appointmentsApi = {
  getById: async (id: string): Promise<Appointment> => {
    const response = await api.get<Appointment>(`/appointments/${id}`);
    return response.data;
  },
  getAll: async (filters?: AppointmentFilters): Promise<Appointment[]> => {
    try {
      const params: Record<string, string | number | undefined> = {
        skip: 0,
        limit: 100,
        ...filters,
      };

      const response = await api.get('/appointments', { params });
      // Debug log in development
      if (import.meta.env.DEV) {
        console.log('[appointmentsApi.getAll] Response:', response.data);
      }
      // Safe array extraction - handles { data: [...] } or direct array
      return safeArray<Appointment>(response.data);
    } catch (error) {
      console.error('[appointmentsApi.getAll] Error:', error);
      throw error;
    }
  },
  create: async (
    appointment: CreateAppointmentData,
    options?: { idempotencyKey?: string; signal?: AbortSignal }
  ): Promise<{ appointment: Appointment; idempotentReplay: boolean }> => {
    try {
      const idempotencyKey = options?.idempotencyKey ?? crypto.randomUUID();
      const response = await api.post('/appointments', appointment, {
        headers: { 'Idempotency-Key': idempotencyKey },
        signal: options?.signal,
      });
      const idempotentReplay = String(
        (response.headers as { 'x-idempotent-replay'?: string })['x-idempotent-replay'] ?? ''
      ) === '1';
      return { appointment: response.data, idempotentReplay };
    } catch (error) {
      console.error('[appointmentsApi.create] Error:', error);
      throw error;
    }
  },
  update: async (
    id: string,
    payload: Partial<{
      status: 'scheduled' | 'completed' | 'cancelled';
      patient_id: string;
      doctor_id: string;
      appointment_time: string;
    }>
  ): Promise<Appointment> => {
    const response = await api.put(`/appointments/${id}`, payload);
    return response.data;
  },
  /**
   * Mark an appointment as completed.
   * Note: completion_notes is deprecated and ignored by the backend. Use clinical_notes instead.
   */
  markCompleted: async (
    id: string,
    payload?: {
      /** @deprecated Use clinical_notes instead. Kept for backward compatibility. */
      completion_notes?: string | null;
      /** Clinical observations/treatment documentation for this visit (preferred). */
      clinical_notes?: string | null;
      /** Primary and differential diagnoses. */
      diagnosis?: string | null;
      /** Treatment provided, medications prescribed, follow-up plan. */
      treatment_summary?: string | null;
      items?: { item_id: string; quantity: number }[];
      prescriptions?: {
        notes?: string | null;
        items: Array<{
          medicine_name: string;
          dosage?: string | null;
          frequency?: string | null;
          duration?: string | null;
          instructions?: string | null;
        }>;
      }[];
      vitals?: {
        temperature?: number | null;
        bp_systolic?: number | null;
        bp_diastolic?: number | null;
        pulse?: number | null;
        respiratory_rate?: number | null;
        spo2?: number | null;
        weight?: number | null;
        height?: number | null;
        bmi?: number | null;
        notes?: string | null;
      } | null;
      follow_up_date?: string | null;
      follow_up_notes?: string | null;
      generate_bill?: boolean;
      bill_consultation_amount?: number | string;
    },
    options?: { idempotencyKey?: string }
  ): Promise<{ appointment: Appointment; idempotentReplay: boolean }> => {
    const idempotencyKey = options?.idempotencyKey ?? crypto.randomUUID();
    const response = await api.post<Appointment>(
      `/appointments/${id}/mark-completed`,
      payload ?? {},
      {
        headers: { 'Idempotency-Key': idempotencyKey },
      }
    );
    const idempotentReplay =
      String(
        (response.headers as { 'x-idempotent-replay'?: string })['x-idempotent-replay'] ?? ''
      ) === '1';
    return { appointment: response.data, idempotentReplay };
  },
  delete: async (id: string): Promise<void> => {
    try {
      await api.delete(`/appointments/${id}`);
    } catch (error) {
      console.error('[appointmentsApi.delete] Error:', error);
      throw error;
    }
  },
};

/**
 * Encounters API — canonical encounter aggregate endpoint.
 *
 * GET /encounters/{appointment_id}
 *
 * Returns the full EncounterDetailAggregate in a single response.
 * This is the SINGLE canonical source for encounter workspace rendering.
 */
export const encountersApi = {
  /**
   * Get the full encounter aggregate for the given appointment.
   * Replaces the previous pattern of assembling multiple requests client-side.
   */
  getById: async (appointmentId: string): Promise<EncounterDetailAggregate> => {
    const response = await api.get<EncounterDetailAggregate>(
      `/encounters/${appointmentId}`
    );
    return response.data;
  },
};
