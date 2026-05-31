/**
 * Daily Care Dashboard API service — Phase P3 Daily Care Dashboard + Adherence Experience.
 *
 * Provides access to the DailyCareDashboardAggregate which composes existing
 * domain data into a patient-friendly Today's Care Dashboard.
 *
 * CRITICAL:
 * - Patient access is strictly scoped to their own data
 * - Prescription data is NEVER mutated through this aggregate
 * - Adherence actions affect tracking ONLY
 * - No shadow adherence systems are created
 */

import { api } from './api';

// ═════════════════════════════════════════════════════════════════════════════
// Types
// ═════════════════════════════════════════════════════════════════════════════

export interface MedicationDueItem {
  schedule_id: string;
  medicine_name: string;
  dosage: string | null;
  frequency: string | null;
  instructions: string | null;
  reminder_times: string[];
  adherence_status: 'pending' | 'taken' | 'skipped' | 'snoozed';
  scheduled_time: string | null;
  prescription_id: string;
  prescription_item_id: string;
}

export interface MedicinesDueToday {
  due_now: MedicationDueItem[];
  upcoming: MedicationDueItem[];
  overdue: MedicationDueItem[];
  completed: MedicationDueItem[];
  total_due: number;
  taken_count: number;
  skipped_count: number;
  pending_count: number;
  adherence_rate_today: number;
  current_streak_days: number;
  longest_streak_days: number;
  week_adherence_rate: number;
}

export interface UpcomingAppointmentBrief {
  id: string;
  appointment_time: string;
  doctor_name: string;
  doctor_specialization: string | null;
  clinic_name: string | null;
  status: string;
}

export interface FollowUpBrief {
  appointment_id: string;
  doctor_name: string;
  follow_up_date: string;
  follow_up_notes: string | null;
  is_overdue: boolean;
}

export interface UpcomingCare {
  next_appointment: UpcomingAppointmentBrief | null;
  upcoming_follow_ups: FollowUpBrief[];
  overdue_follow_ups: FollowUpBrief[];
  unread_communications: number;
  pending_care_tasks: number;
}

export interface RecentDoctorBrief {
  doctor_id: string;
  doctor_name: string;
  specialization: string | null;
  clinic_name: string | null;
  last_visit: string | null;
  has_prescription: boolean;
}

export interface RecentPrescriptionBrief {
  prescription_id: string;
  appointment_id: string;
  doctor_name: string | null;
  created_at: string;
  medicine_count: number;
}

export interface ContinueCare {
  recent_doctors: RecentDoctorBrief[];
  recent_prescriptions: RecentPrescriptionBrief[];
}

export interface TimelinePreviewCard {
  appointment_id: string;
  appointment_time: string;
  doctor_name: string;
  doctor_specialization: string | null;
  diagnosis: string | null;
  treatment_summary: string | null;
  has_prescription: boolean;
  has_encounter_summary: boolean;
}

export interface HealthTimelinePreview {
  recent_cards: TimelinePreviewCard[];
  total_encounters: number;
}

export interface QuickAction {
  id: string;
  label: string;
  icon: string;
  route: string;
  description: string | null;
  is_future: boolean;
}

export interface QuickActions {
  actions: QuickAction[];
}

export interface DailyCareDashboardAggregate {
  medicines_due_today: MedicinesDueToday;
  upcoming_care: UpcomingCare;
  continue_care: ContinueCare;
  health_timeline_preview: HealthTimelinePreview;
  quick_actions: QuickActions;
}

// ═════════════════════════════════════════════════════════════════════════════
// API calls
// ═════════════════════════════════════════════════════════════════════════════

export const dailyCareApi = {
  /**
   * Get the full Daily Care Dashboard for the authenticated patient.
   *
   * Returns a comprehensive daily care dashboard with 5 sections:
   * 1. MedicinesDueToday — medications grouped by due now / upcoming / overdue / completed
   * 2. UpcomingCare — next appointment, follow-ups, unread communications
   * 3. ContinueCare — recent doctors, recent prescriptions
   * 4. HealthTimelinePreview — last 3 encounter preview cards
   * 5. QuickActions — action shortcuts
   */
  getDashboard: async (): Promise<DailyCareDashboardAggregate> => {
    const response = await api.get('/patient/daily-care');
    return response.data;
  },
};
