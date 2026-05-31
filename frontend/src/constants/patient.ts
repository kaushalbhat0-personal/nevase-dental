/**
 * Patient Constants
 * Centralized constants for patient module
 */

/** Session key: last booked appointment JSON for optimistic UI after navigation (StrictMode-safe). */
export const PATIENT_BOOKING_PENDING_STORAGE_KEY = 'medical_webapp:pending_patient_booking';

/** Session key: clinic tenant when booking from /patient/clinic/:id (survives refresh; cleared on explicit global browse). */
export const PATIENT_CLINIC_BOOKING_SCOPE_KEY = 'medical_webapp:patient_booking_tenant_id';

export const PATIENT_DEFAULT_PARAMS = {
  skip: 0,
  limit: 100,
};

export const EMPTY_PATIENT = {
  name: '',
  age: '',
  gender: '',
  phone: '',
};

/** Pills and search shortcuts — matches common booking intents. */
export const POPULAR_SPECIALIZATIONS = [
  'General Physician',
  'Dermatology',
  'Pediatrics',
  'Cardiology',
  'Gynecology',
  'Orthopedics',
  'ENT',
  'Dentist',
] as const;

export const PATIENT_TABLE_COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Phone' },
  { key: 'dob', label: 'DOB / Age' },
  { key: 'registered', label: 'Registered' },
] as const;
