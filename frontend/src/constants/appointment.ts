/**
 * Appointment Constants
 * Centralized constants for appointment module
 */

export const APPOINTMENT_DEFAULT_PARAMS = {
  skip: 0,
  limit: 100,
};

export const EMPTY_APPOINTMENT = {
  patient_id: '',
  doctor_id: '',
  scheduled_at: '',
  notes: '',
};

export const APPOINTMENT_STATUSES = [
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
] as const;

export const APPOINTMENT_STATUS_CLASSES: Record<string, string> = {
  scheduled: 'status-badge scheduled',
  completed: 'status-badge completed',
  cancelled: 'status-badge cancelled',
};
