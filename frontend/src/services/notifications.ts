/**
 * Notification API service — Phase 3D Communication Infrastructure.
 *
 * Provides API client methods for:
 * - Notification history
 * - Delivery status tracking
 * - Failed message management
 * - Communication template CRUD
 * - Template preview
 * - Resend actions
 * - Dashboard stats
 */

import { api } from './api';

// ── Types ───────────────────────────────────────────────────────────────────

export interface NotificationEvent {
  id: string;
  event_type: string;
  tenant_id: string;
  patient_id: string | null;
  doctor_id: string | null;
  appointment_id: string | null;
  bill_id: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface NotificationEventList {
  items: NotificationEvent[];
  total: number;
  skip: number;
  limit: number;
}

export interface NotificationDelivery {
  id: string;
  notification_event_id: string;
  channel: string;
  status: string;
  recipient: string;
  sent_at: string | null;
  failed_at: string | null;
  provider_response: Record<string, unknown> | null;
  retry_count: number;
  error_message: string | null;
  next_retry_at: string | null;
  created_at: string;
}

export interface NotificationDeliveryList {
  items: NotificationDelivery[];
  total: number;
  skip: number;
  limit: number;
}

export interface CommunicationTemplate {
  id: string;
  tenant_id: string | null;
  template_type: string;
  channel: string;
  subject: string | null;
  body: string;
  locale: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CommunicationTemplateList {
  items: CommunicationTemplate[];
  total: number;
  skip: number;
  limit: number;
}

export interface CommunicationTemplateCreate {
  template_type: string;
  channel: string;
  subject?: string | null;
  body: string;
  locale?: string;
  is_active?: boolean;
}

export interface CommunicationTemplateUpdate {
  subject?: string | null;
  body?: string | null;
  locale?: string | null;
  is_active?: boolean | null;
}

export interface TemplatePreviewRequest {
  template_id?: string | null;
  template_type?: string | null;
  channel?: string | null;
  test_context: Record<string, string>;
}

export interface TemplatePreviewResponse {
  subject: string | null;
  body: string;
  template_type: string;
  channel: string;
}

export interface CommunicationDashboardStats {
  total_notifications: number;
  total_sent: number;
  total_failed: number;
  total_pending: number;
  success_rate: number;
  by_channel: Record<string, number>;
  by_type: Record<string, number>;
}

export interface ReminderSettings {
  twenty_four_hour_enabled: boolean;
  two_hour_enabled: boolean;
  follow_up_enabled: boolean;
  reminder_channels: string[];
}

// ── API Methods ─────────────────────────────────────────────────────────────

const BASE = '/communications';

/**
 * Fetch notification events for the current tenant.
 */
export async function fetchNotifications(
  params: {
    skip?: number;
    limit?: number;
    event_type?: string;
    patient_id?: string;
  } = {}
): Promise<NotificationEventList> {
  const query = new URLSearchParams();
  if (params.skip !== undefined) query.set('skip', String(params.skip));
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.event_type) query.set('event_type', params.event_type);
  if (params.patient_id) query.set('patient_id', params.patient_id);

  const qs = query.toString();
  const response = await api.get<NotificationEventList>(
    `${BASE}/notifications${qs ? `?${qs}` : ''}`
  );
  return response.data;
}

/**
 * Fetch a single notification event by ID.
 */
export async function fetchNotificationDetail(
  eventId: string
): Promise<NotificationEvent> {
  const response = await api.get<NotificationEvent>(
    `${BASE}/notifications/${eventId}`
  );
  return response.data;
}

/**
 * Fetch delivery records for a notification event.
 */
export async function fetchDeliveryStatus(
  eventId: string
): Promise<NotificationDeliveryList> {
  const response = await api.get<NotificationDeliveryList>(
    `${BASE}/notifications/${eventId}/deliveries`
  );
  return response.data;
}

/**
 * Fetch failed deliveries for the current tenant.
 */
export async function fetchFailedDeliveries(
  params: { skip?: number; limit?: number } = {}
): Promise<NotificationDeliveryList> {
  const query = new URLSearchParams();
  if (params.skip !== undefined) query.set('skip', String(params.skip));
  if (params.limit !== undefined) query.set('limit', String(params.limit));

  const qs = query.toString();
  const response = await api.get<NotificationDeliveryList>(
    `${BASE}/deliveries/failed${qs ? `?${qs}` : ''}`
  );
  return response.data;
}

/**
 * Resend a failed delivery.
 */
export async function resendNotification(
  deliveryId: string,
  channel?: string
): Promise<{ status: string; delivery_id: string }> {
  const response = await api.post<{ status: string; delivery_id: string }>(
    `${BASE}/deliveries/${deliveryId}/resend`,
    channel ? { delivery_id: deliveryId, channel } : {}
  );
  return response.data;
}

/**
 * Fetch communication templates for the current tenant.
 */
export async function fetchTemplates(
  params: { skip?: number; limit?: number } = {}
): Promise<CommunicationTemplateList> {
  const query = new URLSearchParams();
  if (params.skip !== undefined) query.set('skip', String(params.skip));
  if (params.limit !== undefined) query.set('limit', String(params.limit));

  const qs = query.toString();
  const response = await api.get<CommunicationTemplateList>(
    `${BASE}/templates${qs ? `?${qs}` : ''}`
  );
  return response.data;
}

/**
 * Fetch a single communication template by ID.
 */
export async function fetchTemplate(
  templateId: string
): Promise<CommunicationTemplate> {
  const response = await api.get<CommunicationTemplate>(
    `${BASE}/templates/${templateId}`
  );
  return response.data;
}

/**
 * Create a new communication template.
 */
export async function createTemplate(
  data: CommunicationTemplateCreate
): Promise<CommunicationTemplate> {
  const response = await api.post<CommunicationTemplate>(
    `${BASE}/templates`,
    data
  );
  return response.data;
}

/**
 * Update an existing communication template.
 */
export async function updateTemplate(
  templateId: string,
  data: CommunicationTemplateUpdate
): Promise<CommunicationTemplate> {
  const response = await api.put<CommunicationTemplate>(
    `${BASE}/templates/${templateId}`,
    data
  );
  return response.data;
}

/**
 * Delete a communication template.
 */
export async function deleteTemplate(templateId: string): Promise<void> {
  await api.delete(`${BASE}/templates/${templateId}`);
}

/**
 * Preview a rendered template with test data.
 */
export async function previewTemplate(
  request: TemplatePreviewRequest
): Promise<TemplatePreviewResponse> {
  const response = await api.post<TemplatePreviewResponse>(
    `${BASE}/templates/preview`,
    request
  );
  return response.data;
}

/**
 * Fetch available template placeholders.
 */
export async function fetchPlaceholders(): Promise<
  Record<string, string>
> {
  const response = await api.get<Record<string, string>>(
    `${BASE}/templates/placeholders`
  );
  return response.data;
}

/**
 * Fetch communication dashboard stats.
 */
export async function fetchCommunicationDashboardStats(): Promise<CommunicationDashboardStats> {
  const response = await api.get<CommunicationDashboardStats>(
    `${BASE}/dashboard/stats`
  );
  return response.data;
}

/**
 * Fetch reminder settings.
 */
export async function fetchReminderSettings(): Promise<ReminderSettings> {
  const response = await api.get<ReminderSettings>(
    `${BASE}/reminder-settings`
  );
  return response.data;
}

/**
 * Update reminder settings.
 */
export async function updateReminderSettings(
  settings: ReminderSettings
): Promise<ReminderSettings> {
  const response = await api.put<ReminderSettings>(
    `${BASE}/reminder-settings`,
    settings
  );
  return response.data;
}

/**
 * Manually trigger reminder generation (admin only).
 */
export async function triggerReminders(): Promise<{
  status: string;
  results: Record<string, number>;
}> {
  const response = await api.post<{
    status: string;
    results: Record<string, number>;
  }>(`${BASE}/reminders/trigger`);
  return response.data;
}
