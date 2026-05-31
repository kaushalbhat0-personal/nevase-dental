import { api } from './api';
import type { Appointment } from '../types';

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export interface QueueEntry {
  id: string;
  appointment_id: string;
  tenant_id: string;
  doctor_id: string;
  patient_id: string;
  queue_date: string;
  token_number: number;
  queue_status: 'waiting' | 'in_room' | 'completed' | 'skipped';
  priority: number;
  room_number: string | null;
  entered_at: string;
  called_at: string | null;
  completed_at: string | null;
  created_by: string;
  patient_name: string;
  doctor_name: string;
  appointment_time: string | null;
}

export interface QueueDashboard {
  total_waiting: number;
  total_in_room: number;
  total_completed_today: number;
  entries: QueueEntry[];
}

export interface QueuePosition {
  token_number: number;
  position: number;
  waiting_count_before: number;
  estimated_wait_minutes: number;
}

export interface WalkInData {
  patient_id: string;
  doctor_id: string;
}

export interface RescheduleData {
  new_time: string;
}

export interface VitalsData {
  temperature?: number | null;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  pulse?: number | null;
  respiratory_rate?: number | null;
  spo2?: number | null;
  weight?: number | null;
  height?: number | null;
  notes?: string | null;
}

export interface RoomAssignment {
  room_number: string;
}

export interface PrepChecklistUpdate {
  [key: string]: boolean | string | number | null;
}

// ──────────────────────────────────────────────────────────────────────────────
// Queue API
// ──────────────────────────────────────────────────────────────────────────────

export const queueApi = {
  /** Get today's queue (optionally filtered by doctor) */
  getToday: async (doctorId?: string): Promise<QueueEntry[]> => {
    const params: Record<string, string> = {};
    if (doctorId) params.doctor_id = doctorId;
    const response = await api.get<QueueEntry[]>('/queue/today', { params });
    return response.data;
  },

  /** Get front desk queue dashboard with counts */
  getFrontDesk: async (): Promise<QueueDashboard> => {
    const response = await api.get<QueueDashboard>('/queue/today/front-desk');
    return response.data;
  },

  /** Get queue position and wait estimation */
  getPosition: async (appointmentId: string): Promise<QueuePosition> => {
    const response = await api.get<QueuePosition>(`/queue/${appointmentId}/position`);
    return response.data;
  },

  /** Mark queue entry as called */
  callEntry: async (entryId: string): Promise<QueueEntry> => {
    const response = await api.post<QueueEntry>(`/queue/${entryId}/call`);
    return response.data;
  },

  /** Mark queue entry as completed */
  completeEntry: async (entryId: string): Promise<QueueEntry> => {
    const response = await api.post<QueueEntry>(`/queue/${entryId}/complete`);
    return response.data;
  },

  /** Skip queue entry */
  skipEntry: async (entryId: string): Promise<QueueEntry> => {
    const response = await api.post<QueueEntry>(`/queue/${entryId}/skip`);
    return response.data;
  },

  /** Assign room to queue entry */
  assignRoom: async (entryId: string, roomNumber: string): Promise<QueueEntry> => {
    const response = await api.put<QueueEntry>(`/queue/${entryId}/room`, {
      room_number: roomNumber,
    });
    return response.data;
  },

  /** Update prep checklist */
  updatePrepChecklist: async (
    entryId: string,
    checklist: PrepChecklistUpdate
  ): Promise<QueueEntry> => {
    const response = await api.put<QueueEntry>(
      `/queue/${entryId}/prep-check`,
      checklist
    );
    return response.data;
  },
};

// ──────────────────────────────────────────────────────────────────────────────
// Front Desk API
// ──────────────────────────────────────────────────────────────────────────────

export const frontDeskApi = {
  /** Mark appointment as arrived */
  markArrived: async (appointmentId: string): Promise<Appointment> => {
    const response = await api.post<Appointment>(
      `/appointments/${appointmentId}/arrive`
    );
    return response.data;
  },

  /** Check in patient */
  checkIn: async (appointmentId: string): Promise<Appointment> => {
    const response = await api.post<Appointment>(
      `/appointments/${appointmentId}/check-in`
    );
    return response.data;
  },

  /** Cancel appointment */
  cancel: async (appointmentId: string): Promise<Appointment> => {
    const response = await api.post<Appointment>(
      `/appointments/${appointmentId}/cancel`
    );
    return response.data;
  },

  /** Mark no-show */
  markNoShow: async (appointmentId: string): Promise<Appointment> => {
    const response = await api.post<Appointment>(
      `/appointments/${appointmentId}/no-show`
    );
    return response.data;
  },

  /** Create walk-in appointment */
  createWalkIn: async (data: WalkInData): Promise<Appointment> => {
    const response = await api.post<Appointment>('/appointments/walk-in', data);
    return response.data;
  },

  /** Reschedule appointment */
  reschedule: async (
    appointmentId: string,
    data: RescheduleData
  ): Promise<Appointment> => {
    const response = await api.post<Appointment>(
      `/appointments/${appointmentId}/reschedule`,
      data
    );
    return response.data;
  },
};

// ──────────────────────────────────────────────────────────────────────────────
// Nurse Workflow API
// ──────────────────────────────────────────────────────────────────────────────

export const nurseWorkflowApi = {
  /** Mark vitals completed */
  markVitalsCompleted: async (
    appointmentId: string,
    vitals?: VitalsData
  ): Promise<Appointment> => {
    const response = await api.post<Appointment>(
      `/appointments/${appointmentId}/vitals-complete`,
      vitals ?? {}
    );
    return response.data;
  },

  /** Send patient to doctor queue */
  sendToDoctor: async (appointmentId: string): Promise<Appointment> => {
    const response = await api.post<Appointment>(
      `/appointments/${appointmentId}/send-to-doctor`
    );
    return response.data;
  },

  /** Assign room to appointment */
  assignRoom: async (
    appointmentId: string,
    roomNumber: string
  ): Promise<QueueEntry> => {
    const response = await api.put<QueueEntry>(
      `/appointments/${appointmentId}/room`,
      { room_number: roomNumber }
    );
    return response.data;
  },
};
