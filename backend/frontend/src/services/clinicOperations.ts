/**
 * Clinic Operations API service.
 *
 * Wraps the existing clinic_operations_service aggregation layer.
 * All data is computed/aggregated from existing models — no new backend logic.
 */
import { api } from './api';

// ──────────────────────────────────────────────────────────────────────────────
// Types (mirroring backend schemas/clinic_operations.py)
// ──────────────────────────────────────────────────────────────────────────────

export interface TodaySummaryCard {
  waiting_patients: number;
  active_consultations: number;
  overdue_appointments: number;
  pending_bills_count: number;
  pending_bills_amount: number;
  incomplete_encounters: number;
  low_stock_alerts: number;
  procurement_pending: number;
  total_appointments_today: number;
}

export interface DoctorQueueSummary {
  doctor_id: string;
  doctor_name: string;
  waiting_count: number;
  in_consultation_count: number;
  completed_today: number;
  avg_wait_minutes: number | null;
  next_patient_name: string | null;
  status: 'active' | 'idle' | 'away';
}

export interface WaitingPatientItem {
  appointment_id: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string;
  doctor_name: string;
  status: string;
  token_number: number | null;
  wait_time_minutes: number;
  arrived_at: string | null;
  priority: number;
}

export interface ActiveConsultationItem {
  appointment_id: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string;
  doctor_name: string;
  started_at: string | null;
  duration_minutes: number;
}

export interface OverdueAppointmentItem {
  appointment_id: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string;
  doctor_name: string;
  appointment_time: string;
  status: string;
  minutes_overdue: number;
}

export interface PendingBillItem {
  bill_id: string;
  appointment_id: string | null;
  patient_id: string;
  patient_name: string;
  amount: number;
  created_at: string;
  days_pending: number;
}

export interface IncompleteEncounterItem {
  appointment_id: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string;
  doctor_name: string;
  completed_at: string | null;
  missing_clinical_notes: boolean;
  missing_prescriptions: boolean;
  missing_billing: boolean;
}

export interface LowStockAlertItem {
  item_id: string;
  item_name: string;
  current_quantity: number;
  low_stock_threshold: number;
  unit: string;
  days_until_out: number | null;
}

export interface ProcurementPendingItem {
  po_id: string;
  supplier_name: string;
  status: string;
  total_amount: number;
  item_count: number;
  created_at: string;
  days_pending: number;
}

export interface ClinicOperationsDashboard {
  summary: TodaySummaryCard;
  doctor_queues: DoctorQueueSummary[];
  waiting_patients: WaitingPatientItem[];
  active_consultations: ActiveConsultationItem[];
  overdue_appointments: OverdueAppointmentItem[];
  pending_bills: PendingBillItem[];
  incomplete_encounters: IncompleteEncounterItem[];
  low_stock_alerts: LowStockAlertItem[];
  procurement_pending: ProcurementPendingItem[];
}

// ──────────────────────────────────────────────────────────────────────────────
// Task Types
// ──────────────────────────────────────────────────────────────────────────────

export type TaskPriority = 'high' | 'medium' | 'low';
export type TaskCategory =
  | 'encounter'
  | 'billing'
  | 'procurement'
  | 'inventory'
  | 'follow_up'
  | 'prescription'
  | 'queue';

export interface OperationalTaskItem {
  id: string;
  category: TaskCategory;
  priority: TaskPriority;
  title: string;
  description: string | null;
  entity_id: string;
  patient_name: string | null;
  doctor_name: string | null;
  action_label: string | null;
  action_url: string | null;
  created_at: string;
  is_actionable: boolean;
}

export interface OperationalTaskList {
  high_priority: OperationalTaskItem[];
  medium_priority: OperationalTaskItem[];
  low_priority: OperationalTaskItem[];
  total_count: number;
}

// ──────────────────────────────────────────────────────────────────────────────
// Activity Stream Types
// ──────────────────────────────────────────────────────────────────────────────

export type ActivityType =
  | 'patient_arrived'
  | 'patient_checked_in'
  | 'vitals_completed'
  | 'consultation_started'
  | 'consultation_completed'
  | 'bill_generated'
  | 'bill_paid'
  | 'inventory_received'
  | 'low_stock_alert'
  | 'procurement_received';

export interface ActivityStreamItem {
  id: string;
  activity_type: ActivityType;
  title: string;
  description: string | null;
  patient_name: string | null;
  doctor_name: string | null;
  entity_id: string | null;
  created_at: string;
  icon: string | null;
}

export interface ActivityStreamResponse {
  items: ActivityStreamItem[];
  total: number;
  skip: number;
  limit: number;
}

// ──────────────────────────────────────────────────────────────────────────────
// Alert Types
// ──────────────────────────────────────────────────────────────────────────────

export type AlertSeverity = 'critical' | 'warning' | 'info';
export type AlertCategory =
  | 'low_stock'
  | 'overdue_appointment'
  | 'pending_billing'
  | 'delayed_queue'
  | 'missed_follow_up'
  | 'incomplete_encounter';

export interface OperationalAlertItem {
  id: string;
  category: AlertCategory;
  severity: AlertSeverity;
  title: string;
  description: string | null;
  entity_id: string | null;
  action_url: string | null;
  created_at: string;
}

export interface OperationalAlertList {
  items: OperationalAlertItem[];
  critical_count: number;
  warning_count: number;
  info_count: number;
  total: number;
}

// ──────────────────────────────────────────────────────────────────────────────
// Doctor Operations View Types
// ──────────────────────────────────────────────────────────────────────────────

export interface DoctorQueueSlot {
  queue_entry_id: string;
  appointment_id: string;
  patient_id: string;
  patient_name: string;
  token_number: number;
  status: string;
  wait_time_minutes: number;
  priority: number;
  has_vitals: boolean;
  is_ready: boolean;
}

export interface DoctorOperationAction {
  action: 'start_consultation' | 'mark_ready' | 'call_next';
  appointment_id: string | null;
  queue_entry_id: string | null;
  label: string;
}

export interface DoctorOperationsView {
  doctor_id: string;
  doctor_name: string;
  waiting_patients_count: number;
  current_patient: ActiveConsultationItem | null;
  queue: DoctorQueueSlot[];
  completed_today: number;
  quick_actions: DoctorOperationAction[];
}

// ──────────────────────────────────────────────────────────────────────────────
// API Client
// ──────────────────────────────────────────────────────────────────────────────

export const operationsApi = {
  /** Get the complete clinic operations dashboard aggregate */
  getDashboard: async (): Promise<ClinicOperationsDashboard> => {
    const response = await api.get<ClinicOperationsDashboard>('/operations/dashboard');
    return response.data;
  },

  /** Get operational tasks grouped by priority */
  getTasks: async (): Promise<OperationalTaskList> => {
    const response = await api.get<OperationalTaskList>('/operations/tasks');
    return response.data;
  },

  /** Get the clinic activity stream (paginated) */
  getActivityStream: async (
    skip = 0,
    limit = 50
  ): Promise<ActivityStreamResponse> => {
    const response = await api.get<ActivityStreamResponse>(
      '/operations/activity-stream',
      { params: { skip, limit } }
    );
    return response.data;
  },

  /** Get operational alerts grouped by severity */
  getAlerts: async (): Promise<OperationalAlertList> => {
    const response = await api.get<OperationalAlertList>('/operations/alerts');
    return response.data;
  },

  /** Get a doctor-specific operations view */
  getDoctorView: async (
    doctorId: string
  ): Promise<DoctorOperationsView> => {
    const response = await api.get<DoctorOperationsView>(
      '/operations/doctor-view',
      { params: { doctor_id: doctorId } }
    );
    return response.data;
  },
};
