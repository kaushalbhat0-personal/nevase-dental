/**
 * Patient Communication Center API client.
 *
 * Phase P2 — Patient Communication Center.
 *
 * Architecture:
 *   These endpoints compose existing NotificationEvent data into a patient-friendly
 *   communication center view. They enforce strict patient-scoped access and NEVER
 *   expose provider delivery internals or audit metadata.
 *
 *   NotificationEvent remains the source-of-truth.
 *   Communication delivery remains infrastructure-level.
 *   Patient UI CONSUMES communication aggregates — it does not own delivery workflows.
 */

import { api } from './api';
import type {
  CommunicationPreferencesRead,
  CommunicationPreferencesUpdate,
  CommunicationTimelineResponse,
  PatientCommunicationAggregate,
  ReminderListResponse,
} from '../types';

export const patientCommunicationsApi = {
  /**
   * Get the full Patient Communication Aggregate for the authenticated patient.
   * GET /patient/communications
   */
  getAggregate: async (): Promise<PatientCommunicationAggregate> => {
    const response = await api.get<PatientCommunicationAggregate>(
      '/patient/communications'
    );
    return response.data;
  },

  /**
   * Get paginated communication cards for the patient timeline.
   * GET /patient/communications/timeline
   */
  getTimeline: async (
    params?: { skip?: number; limit?: number }
  ): Promise<CommunicationTimelineResponse> => {
    const response = await api.get<CommunicationTimelineResponse>(
      '/patient/communications/timeline',
      { params }
    );
    return response.data;
  },

  /**
   * Get reminders grouped by urgency for the patient.
   * GET /patient/communications/reminders
   */
  getReminders: async (): Promise<ReminderListResponse> => {
    const response = await api.get<ReminderListResponse>(
      '/patient/communications/reminders'
    );
    return response.data;
  },

  /**
   * Get the unread notification count for the patient.
   * GET /patient/communications/unread-count
   */
  getUnreadCount: async (): Promise<{ unread_count: number }> => {
    const response = await api.get<{ unread_count: number }>(
      '/patient/communications/unread-count'
    );
    return response.data;
  },

  /**
   * Mark a notification event as read by the patient.
   * PUT /patient/communications/{eventId}/read
   */
  markAsRead: async (eventId: string): Promise<void> => {
    await api.put(`/patient/communications/${eventId}/read`);
  },

  /**
   * Get communication preferences for the authenticated patient.
   * GET /patient/communications/preferences
   */
  getPreferences: async (): Promise<CommunicationPreferencesRead> => {
    const response = await api.get<CommunicationPreferencesRead>(
      '/patient/communications/preferences'
    );
    return response.data;
  },

  /**
   * Update communication preferences for the authenticated patient.
   * PUT /patient/communications/preferences
   */
  updatePreferences: async (
    data: CommunicationPreferencesUpdate
  ): Promise<CommunicationPreferencesRead> => {
    const response = await api.put<CommunicationPreferencesRead>(
      '/patient/communications/preferences',
      data
    );
    return response.data;
  },
};
