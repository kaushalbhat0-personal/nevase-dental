/** Nested tenant on GET /me — source of truth for individual vs organization UI mode. */
export interface MeTenantBrief {
  id: string;
  type: 'individual' | 'organization' | string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  /** Effective roles: account role plus `doctor` when a doctor profile is linked (from API / JWT). */
  roles: string[];
  /** Practice owner: solo doctor who created the tenant; admin-equivalent in UI/API */
  is_owner?: boolean;
  /** Primary tenant from login / JWT when applicable */
  tenant_id?: string | null;
  /** Linked doctor row (GET /me); use for doctor-scoped UI and params. */
  doctor_id?: string | null;
  /** False until mandatory `doctor_profiles` fields are saved; null if not a doctor login. */
  doctor_profile_complete?: boolean | null;
  /** From backend verification workflow (display-only badge). */
  doctor_verification_status?: string | null;
  /** When verification is rejected, admin may include a reason (GET /me). */
  doctor_verification_rejection_reason?: string | null;
  /** From GET /me after sync — use ``type`` for practice vs org mode (not roles/localStorage). */
  tenant?: MeTenantBrief | null;
  /** When true, client must complete password reset before using the app */
  force_password_reset?: boolean;
}

/** GET /me — `UserRead` from the API */
export interface MeUserResponse {
  id: string;
  email: string;
  role: string;
  roles: string[];
  is_active: boolean;
  is_owner: boolean;
  tenant_id: string | null;
  doctor_id: string | null;
  doctor_profile_complete?: boolean | null;
  doctor_verification_status?: string | null;
  doctor_verification_rejection_reason?: string | null;
  tenant: MeTenantBrief | null;
  created_at: string;
  updated_at: string;
}

/** GET/PUT /doctor/profile */
export interface DoctorStructuredProfile {
  id: string;
  doctor_id: string;
  full_name: string;
  specialization: string | null;
  experience_years: number | null;
  qualification: string | null;
  registration_number: string | null;
  registration_council: string | null;
  clinic_name: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  phone: string | null;
  profile_image: string | null;
  is_profile_complete: boolean;
  verification_status: string;
  verification_rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
}

/** GET /public/tenants — marketplace tenant with doctor count */
export interface PublicTenantDiscovery {
  id: string;
  name: string;
  doctor_count: number;
  type: string;
  /** Derived: "Clinic/Hospital" vs "Individual Doctor" from active doctor count */
  organization_label: string;
  sole_doctor: PublicTenantDoctorBrief | null;
}

/** GET /public/tenants/{id}/doctors */
export interface PublicTenantDoctorBrief {
  id: string;
  name: string;
  specialization: string;
  availability_status: string;
  next_available_slot: string | null;
  available_today: boolean;
  rating_average: number;
  review_count: number;
  distance_km: number;
  slots_today_count?: number;
  slots_tomorrow_count?: number;
  metrics_are_synthetic?: boolean;
}

/** GET /public/doctors/{id} — approved marketplace profile only (404 otherwise) */
export interface PublicDoctorProfile {
  id: string;
  full_name: string;
  specialization: string;
  experience: number;
  qualification: string | null;
  clinic_name: string | null;
  address: string | null;
  city: string | null;
  profile_image: string | null;
  verified: boolean;
  verification_status: string;
  timezone: string;
  has_availability_windows: boolean;
  /** Earliest bookable slot (UTC) from public profile — avoids an extra schedule call for the headline */
  next_available_slot?: string | null;
  available_today: boolean;
  rating_average: number;
  review_count: number;
  /** Illustrative distance until real geolocation */
  distance_km: number;
  slots_today_count?: number;
  slots_tomorrow_count?: number;
  /** When true, show ratings/distance/patient volume as illustrative — not verified facts */
  metrics_are_synthetic?: boolean;
}

/** GET /patients/me/doctors */
export interface PatientMyDoctor {
  id: string;
  name: string;
  specialization: string;
  tenant_id: string;
}

export interface Tenant {
  id: string;
  name: string;
  /** URL-safe tenant key when set (e.g. apollo-hospital-pune) */
  slug?: string | null;
  type: string;
  is_active: boolean;
  /** Super-admin soft-delete; deactivated orgs are hidden from lists and API scope by default */
  is_deleted?: boolean;
  /** Shown for tenants that have contact info (may be null for legacy rows) */
  address?: string | null;
  phone?: string | null;
  created_at: string;
  /** Present on POST /tenants create response (initial admin login email, normalized) */
  admin_email?: string | null;
}

export interface Patient {
  id: number | string;
  /** When present on GET /patients, matches the authenticated user. */
  user_id?: string | number;
  // Backend returns 'name', not first_name/last_name
  name?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  date_of_birth?: string;
  // Backend returns 'age' instead of date_of_birth
  age?: number;
  gender?: string;
  medical_history?: string;
  /** Doctor-facing notes (from API); persisted per patient. */
  clinical_notes?: string | null;
  created_by?: number | string;
  created_at?: string;
  updated_at?: string;
  /** Set on GET /patients for tenant (admin) and doctor list when the backend can resolve a label. */
  doctor_name?: string | null;
}

/** Weekly availability pattern from GET /doctors/{id}/availability-windows */
export interface DoctorAvailabilityWindow {
  id: string;
  doctor_id: string;
  /** Monday = 0 … Sunday = 6 (server convention) */
  day_of_week: number;
  /** "HH:MM:SS" */
  start_time: string;
  end_time: string;
  slot_duration: number;
  tenant_id: string;
  created_at: string;
}

/** Calendar time off (full day or partial) from GET /doctors/{id}/time-off */
export interface DoctorTimeOff {
  id: string;
  doctor_id: string;
  /** YYYY-MM-DD */
  off_date: string;
  start_time: string | null;
  end_time: string | null;
  tenant_id: string;
  created_at: string;
}

export interface Doctor {
  id: number | string;
  // Backend returns flat structure, not nested user
  name?: string;
  /** Linked login user (promote to admin) */
  user_id?: string | number;
  user?: User;
  specialty?: string;
  specialization?: string;
  license_number?: string;
  experience_years?: number;
  created_at?: string;
  /** IANA timezone for the doctor's schedule (e.g. Asia/Kolkata) */
  timezone?: string;
  /** True when the doctor has at least one weekly availability window */
  has_availability_windows?: boolean;
  /** Login email for the linked user account (admin-created doctors) */
  linked_user_email?: string | null;
  /** Linked user's role (admin vs doctor) for badges and promote UI */
  linked_user_role?: string | null;
  /** From GET /doctors (DoctorRead); tenant type label for the UI. */
  tenant_type?: string | null;
  /** Derived from active doctor count in tenant; complements tenant_type. */
  tenant_organization_label?: string | null;
  tenant_name?: string | null;
  tenant_id?: string | null;
  /** From GET /doctors when include_availability_hint=true */
  availability_status?: 'available_today' | 'next_available_tomorrow' | 'none' | string | null;
  /** Set on public tenant doctor list (and profile) for filters and row sublabels */
  available_today?: boolean;
  next_available_slot?: string | null;
  rating_average?: number;
  review_count?: number;
  distance_km?: number;
  slots_today_count?: number;
  slots_tomorrow_count?: number;
  metrics_are_synthetic?: boolean;
  /** Marketplace verification on structured profile (patient trust / discovery). */
  verification_status?: string | null;
  /** From GET /doctors when structured profile is approved. */
  verified?: boolean;
}

/**
 * Appointment acts as the Visit/Encounter anchor in the clinical domain model.
 * Billing, inventory usage, prescriptions, and clinical notes are attached to the appointment encounter.
 * The timeline is visit-centric: one clinical encounter renders as one VisitAggregate card.
 */
export interface Appointment {
  id: number | string;
  patient_id: number | string;
  doctor_id: number | string;
  // Backend returns 'appointment_time', frontend form uses 'scheduled_at'
  appointment_time?: string;
  scheduled_at?: string;
  /** `pending` is client-only until refetch replaces with server status. */
  status: 'scheduled' | 'confirmed' | 'arrived' | 'checked_in' | 'vitals_completed' | 'waiting_for_doctor' | 'in_consultation' | 'completed' | 'cancelled' | 'no_show' | 'pending';
  /**
   * DEPRECATED: completion_notes is deprecated and should not be written for new visits.
   * Use clinical_notes for visit documentation. Preserved for backward compatibility.
   * Operational completion metadata only - not clinical documentation.
   */
  completion_notes?: string | null;
  /**
   * Clinical notes = medical observations/treatment documentation for THIS visit/encounter.
   * This is the primary field for clinical encounter documentation.
   */
  clinical_notes?: string | null;
  /**
   * Diagnosis = primary and differential diagnoses recorded during this visit.
   */
  diagnosis?: string | null;
  /**
   * Treatment summary = treatment provided, medications prescribed, follow-up plan.
   */
  treatment_summary?: string | null;
  /**
   * SOAP notes: structured clinical documentation
   */
  subjective_notes?: string | null;
  objective_notes?: string | null;
  assessment_notes?: string | null;
  plan_notes?: string | null;
  follow_up_date?: string | null;
  follow_up_notes?: string | null;
  vitals?: VitalSigns;
  prescriptions?: Prescription[];
  /** Patient context notes (persistent across visits) - stored on Patient, not Appointment. */
  notes?: string;
  // Backend returns flat structure, no nested objects
  patient?: Patient;
  doctor?: Doctor;
  /** From GET /appointments/:id — materials tied to completion */
  inventory_usages?: AppointmentInventoryUsageLine[];
  /** Σ quantity × selling_price — billing parity */
  inventory_materials_selling_total?: string | number | null;
  created_by?: number | string;
  created_at?: string;
}

export interface AppointmentInventoryUsageLine {
  item_id: string;
  quantity: number;
  item_name?: string;
}

export interface VitalSigns {
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
  created_at: string;
}

export interface PrescriptionItem {
  medicine_name: string;
  dosage?: string | null;
  frequency?: string | null;
  duration?: string | null;
  instructions?: string | null;
}

export interface Prescription {
  id: string;
  appointment_id: string;
  doctor_id: string;
  patient_id: string;
  tenant_id: string;
  notes?: string | null;
  created_at: string;
  items: PrescriptionItem[];
}

export interface FollowUpPlan {
  follow_up_date?: string | null;
  follow_up_notes?: string | null;
}

/**
 * VisitAggregate represents a clinical encounter (visit) and all attached metadata.
 * This is an INTERNAL abstraction for timeline rendering - there is NO database table.
 * One appointment = one VisitAggregate = one card in the timeline.
 *
 * Attached metadata (billing, inventory, prescriptions, etc.) are grouped under
 * the appointment encounter for clinical-centered display.
 *
 * TODO: Future extensions:
 * - prescriptions?: Prescription[]
 * - vitals?: VitalSigns
 * - attachments?: Attachment[]
 * - followUp?: FollowUpPlan
 * - soapNotes?: SoapNotes
 * - aiSummary?: AiVisitSummary
 */
export interface VisitAggregate {
  appointment: Appointment;
  /** Linked bill for this visit, if any */
  bill?: Bill | null;
  /** Inventory/medicines used during this visit */
  inventoryUsage?: AppointmentInventoryUsageLine[];
  prescriptions?: Prescription[];
  vitals?: VitalSigns;
  followUp?: FollowUpPlan;
}

/**
 * TimelineContext — lightweight patient history for encounter context.
 * Returned by the Encounter Aggregate API.
 */
export interface TimelineContext {
  previous_visit_count: number;
  previous_appointment_ids: string[];
}

/**
 * EncounterDetailAggregate represents the complete clinical encounter workspace data.
 * This is a READ-ONLY aggregate returned by GET /encounters/{appointment_id}.
 * There is NO database table — it composes existing domain entities.
 * 
 * The appointment acts as the clinical encounter anchor.
 * Bills, inventory usage, prescriptions, etc. are attached metadata.
 * 
 * This is the SINGLE canonical source for:
 * - Encounter Workspace rendering
 * - AI clinical summaries (future)
 * - PDF/export generation (future)
 * - mobile sync (future)
 * - analytics (future)
 * - clinical integrations (future)
 * 
 * TODO: Future Phase 2 clinical extensions:
 * - attachments?: Attachment[] - lab reports, images, documents
 * - followUp?: FollowUpPlan - scheduled follow-up appointments
 * - aiSummary?: AiVisitSummary - AI-generated visit summary
 * - icdCodes?: IcdCodeAssignment[]
 * - referrals?: ReferralRead[]
 * - ePrescriptionSigned?: boolean
 */
export interface EncounterDetailAggregate {
  /** The appointment acts as the clinical encounter anchor */
  appointment: Appointment;
  /** Patient associated with this encounter */
  patient: Patient;
  /** Doctor who conducted this encounter */
  doctor: Doctor;
  /** Clinical data */
  vitals?: VitalSigns | null;
  prescriptions?: Prescription[];
  /** Operational data */
  inventory_usage?: AppointmentInventoryUsageLine[];
  bill?: Bill | null;
  /** Context */
  timeline_context?: TimelineContext | null;
  // TODO: Future extension - attachments?: Attachment[];
  // TODO: Future extension - aiSummary?: AiVisitSummary;
  // TODO: Future extension - icdCodes?: IcdCodeAssignment[];
  // TODO: Future extension - referrals?: ReferralRead[];
  // TODO: Future extension - ePrescriptionSigned?: boolean;
}

export interface Bill {
  id: string;
  patient_id: string;
  appointment_id?: string;
  amount: number;
  currency: string;
  status: 'unpaid' | 'paid';
  description?: string;
  due_date?: string;
  paid_at?: string;
  payment_id?: string;
  payment_method?: string;
  patient?: Patient;
  created_at: string;
  updated_at?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  /** Primary account role (legacy; prefer `roles`). */
  role?: string;
  roles?: string[];
  tenant_id?: string | null;
  /** Linked doctor profile id (same as JWT claim when present). */
  doctor_id?: string | null;
  doctor_profile_complete?: boolean | null;
  is_owner?: boolean;
  user?: User;
  force_password_reset?: boolean;
}

export interface LoginResult {
  success: boolean;
  error?: string;
  roles?: string[];
  is_owner?: boolean;
  forcePasswordReset?: boolean;
  doctor_id?: string | null;
  doctor_profile_complete?: boolean | null;
}

export interface RegisterResponseUser {
  id: string;
  email: string;
  role: string;
  roles?: string[];
  is_active: boolean;
  is_owner?: boolean;
  full_name?: string;
  tenant_id?: string | null;
  doctor_id?: string | null;
  doctor_profile_complete?: boolean | null;
  doctor_verification_status?: string | null;
  doctor_verification_rejection_reason?: string | null;
}

export interface RegisterResponse {
  access_token: string;
  token_type: string;
  user: RegisterResponseUser;
}

export interface PatientProfileSignup {
  name: string;
  age: number;
  gender: string;
  phone: string;
}

export interface DoctorProfileSignup {
  name: string;
  specialization: string;
  experience_years: number;
}

export type RegisterPayload =
  | {
      email: string;
      password: string;
      role: 'patient';
      signup_type: 'patient';
      patient_profile: PatientProfileSignup;
    }
  | {
      email: string;
      password: string;
      role: 'doctor';
      signup_type: 'doctor';
      doctor_profile: DoctorProfileSignup;
    }
  | {
      email: string;
      password: string;
      role: 'admin';
      signup_type: 'hospital';
      organization_name: string;
      doctor_profile: DoctorProfileSignup;
    };

export interface DashboardStats {
  total_patients: number;
  total_doctors: number;
  today_appointments: number;
  total_revenue: number;
}

/** GET /api/v1/admin/dashboard/metrics */
export interface AdminDashboardMetrics {
  total_revenue: number;
  revenue_today: number;
  appointments_today: number;
  completed_appointments: number;
  pending_bills: number;
}

/** GET /api/v1/admin/dashboard/revenue-trend — one point per day (7 days) */
export interface AdminRevenueTrendItem {
  date: string;
  revenue: number;
}

/** GET /api/v1/admin/dashboard/doctor-performance */
export interface AdminDoctorPerformanceRow {
  doctor_id: string;
  doctor_name: string;
  appointments_count: number;
  completed_appointments: number;
  total_revenue: number;
}

export interface HealthNewsItem {
  id: number;
  title: string;
  description: string;
  category: string;
  published_at: string;
}

// ═════════════════════════════════════════════════════════════════════════════
// Phase P1 — Patient Health Workspace Types
// ═════════════════════════════════════════════════════════════════════════════

/**
 * EncounterCard — patient-safe encounter summary for timeline rendering.
 * Maps to backend EncounterCard schema (patient_workspace.py).
 * SOAP internal sections are NEVER exposed.
 */
export interface EncounterCard {
  appointment_id: string;
  appointment_time: string;
  status: string;
  doctor_id: string;
  doctor_name: string;
  doctor_specialization: string | null;
  clinic_name: string | null;
  diagnosis: string | null;
  treatment_summary: string | null;
  prescriptions_count: number;
  follow_up_date: string | null;
  follow_up_notes: string | null;
  has_prescription: boolean;
  has_encounter_summary: boolean;
  encounter_started_at: string | null;
  encounter_completed_at: string | null;
}

/**
 * VitalsSnapshot — vitals captured during an appointment, for chronological history.
 * Maps to backend VitalsSnapshot schema (patient_workspace.py).
 */
export interface VitalsSnapshot {
  appointment_id: string;
  appointment_time: string;
  doctor_name: string | null;
  temperature: number | null;
  bp_systolic: number | null;
  bp_diastolic: number | null;
  pulse: number | null;
  respiratory_rate: number | null;
  spo2: number | null;
  weight: number | null;
  height: number | null;
  bmi: number | null;
  notes: string | null;
}

/**
 * FollowUpItem — single follow-up recommendation.
 * Maps to backend FollowUpItem schema (patient_workspace.py).
 */
export interface FollowUpItem {
  appointment_id: string;
  appointment_time: string;
  doctor_id: string;
  doctor_name: string;
  doctor_specialization: string | null;
  follow_up_date: string;
  follow_up_notes: string | null;
  is_overdue: boolean;
}

/**
 * FollowUpSummary — aggregated follow-up information.
 * Maps to backend FollowUpSummary schema (patient_workspace.py).
 */
export interface FollowUpSummary {
  upcoming: FollowUpItem[];
  overdue: FollowUpItem[];
  total_upcoming: number;
  total_overdue: number;
}

/**
 * DocumentRef — reference to a downloadable document.
 * Maps to backend DocumentRef schema (patient_workspace.py).
 */
export interface DocumentRef {
  appointment_id: string;
  appointment_time: string | null;
  doctor_name: string | null;
  document_type: string; // "prescription" | "encounter_summary" | "invoice"
  download_url: string | null;
}

/**
 * PatientHealthWorkspaceAggregate — canonical READ-ONLY aggregate for the Patient Health Workspace.
 * Maps to backend PatientHealthWorkspaceAggregate schema (patient_workspace.py).
 * Appointment is the encounter anchor. No separate Encounter table exists.
 */
export interface PatientHealthWorkspaceAggregate {
  patient_profile: {
    id: string;
    name: string;
    age: number | null;
    gender: string | null;
    phone: string | null;
  };
  upcoming_appointments: Array<{
    id: string;
    appointment_time: string;
    status: string;
    doctor_id: string;
    doctor_name: string;
    doctor_specialization: string | null;
    clinic_name: string | null;
  }>;
  recent_encounters: EncounterCard[];
  vitals_history: VitalsSnapshot[];
  prescriptions_history: Array<{
    id: string;
    appointment_id: string;
    appointment_time: string | null;
    doctor_name: string | null;
    notes: string | null;
    created_at: string;
    items: Array<{
      medicine_name: string;
      dosage: string | null;
      frequency: string | null;
      duration: string | null;
      instructions: string | null;
    }>;
  }>;
  follow_ups: FollowUpSummary;
  billing_summary: {
    total_billed: number;
    total_paid: number;
    total_unpaid: number;
    recent_bills: Array<{
      id: string;
      amount: number;
      currency: string;
      status: string;
      description: string | null;
      created_at: string;
      paid_at: string | null;
    }>;
  };
  recent_documents: DocumentRef[];
  communication_summary: {
    unread_messages: number;
    last_message_at: string | null;
  };
}

// ═════════════════════════════════════════════════════════════════════════════
// Phase P2 — Patient Communication Center Types
// ═════════════════════════════════════════════════════════════════════════════

export interface DocumentLink {
  document_type: string; // "prescription" | "encounter_summary" | "invoice"
  download_url: string | null;
  appointment_id: string | null;
}

export interface CommunicationCard {
  id: string;
  event_type: string;
  title: string;
  summary: string;
  created_at: string;
  is_read: boolean;
  is_urgent: boolean;
  doctor_name: string | null;
  clinic_name: string | null;
  linked_appointment_id: string | null;
  linked_bill_id: string | null;
  linked_documents: DocumentLink[];
  cta_actions: string[];
}

export interface ReminderCard {
  id: string;
  event_type: string;
  title: string;
  reminder_date: string;
  urgency: "urgent" | "upcoming" | "completed";
  doctor_name: string | null;
  clinic_name: string | null;
  linked_appointment_id: string | null;
  linked_bill_id: string | null;
  cta_actions: string[];
}

export interface CommunicationPreferencesRead {
  email_enabled: boolean;
  sms_enabled: boolean;
  whatsapp_enabled: boolean;
  reminder_enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  locale: string;
  opt_out_all: boolean;
}

export interface CommunicationPreferencesUpdate {
  email_enabled?: boolean;
  sms_enabled?: boolean;
  whatsapp_enabled?: boolean;
  reminder_enabled?: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  locale?: string;
  opt_out_all?: boolean;
}

// ═════════════════════════════════════════════════════════════════════════════
// Phase Trust — Patient Trust & Family Foundation Types
// ═════════════════════════════════════════════════════════════════════════════

/**
 * EmergencyProfile — patient-visible emergency information.
 * Stored as nullable metadata on the patient record.
 */
export interface EmergencyProfile {
  blood_group: string | null;
  allergies: string[];
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  emergency_contact_relation: string | null;
  /** Comma-separated or newline-separated list of chronic conditions */
  chronic_conditions: string;
  /** Derived from encounter data — read-only */
  active_medications_summary: string | null;
  /** Derived from encounter data — read-only */
  primary_doctor_name: string | null;
  /** Derived from encounter data — read-only */
  primary_doctor_specialization: string | null;
  insurance_provider: string | null;
  insurance_id: string | null;
  /** Last updated timestamp */
  updated_at: string | null;
}

/**
 * EmergencyProfileUpdate — mutable fields for emergency profile.
 */
export interface EmergencyProfileUpdate {
  blood_group?: string | null;
  allergies?: string[];
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  emergency_contact_relation?: string | null;
  chronic_conditions?: string | null;
  insurance_provider?: string | null;
  insurance_id?: string | null;
}

/**
 * TrustedContact — a person the patient trusts with their care information.
 */
export interface TrustedContact {
  id: string;
  name: string;
  relationship: string;
  phone: string | null;
  email: string | null;
  communication_preference: 'sms' | 'email' | 'whatsapp' | 'none';
  is_emergency_contact: boolean;
  /** What information is shared with this contact */
  shared_items: Array<'appointments' | 'medications' | 'documents' | 'all'>;
  created_at: string | null;
}

/**
 * DependentProfile — a family member whose care is managed by this patient.
 */
export interface DependentProfile {
  id: string;
  name: string;
  relationship: string;
  age: number | null;
  gender: string | null;
  /** Upcoming appointments for this dependent */
  upcoming_appointments: Array<{
    id: string;
    appointment_time: string;
    doctor_name: string;
    doctor_specialization: string | null;
    clinic_name: string | null;
  }>;
  /** Shared medication reminders count */
  shared_medication_count: number;
}

/**
 * CaregiverAccess — a person who has access to this patient's care information.
 */
export interface CaregiverAccess {
  id: string;
  name: string;
  relationship: string;
  phone: string | null;
  email: string | null;
  /** When access was granted */
  access_granted_at: string | null;
  /** Trust level */
  trust_level: 'view_only' | 'limited' | 'full';
}

/**
 * HealthSummaryMetadata — metadata for the downloadable health summary.
 */
export interface HealthSummaryMetadata {
  encounter_count: number;
  active_medication_count: number;
  document_count: number;
  has_emergency_profile: boolean;
  last_encounter_date: string | null;
  generated_at: string | null;
}

/**
 * VisitPreparationItem — a single preparation checklist item with local state.
 */
export interface VisitPreparationItem {
  id: string;
  label: string;
  description: string | null;
  category: 'documents' | 'medication' | 'preparation' | 'logistics';
  checked: boolean;
}

/**
 * PatientTrustAggregate — aggregate of all trust & family data.
 */
export interface PatientTrustAggregate {
  emergency_profile: EmergencyProfile | null;
  trusted_contacts: TrustedContact[];
  dependents: DependentProfile[];
  caregivers: CaregiverAccess[];
  health_summary: HealthSummaryMetadata | null;
}

export interface PatientCommunicationAggregate {
  recent_notifications: CommunicationCard[];
  unread_count: number;
  reminders_by_urgency: {
    urgent: ReminderCard[];
    upcoming: ReminderCard[];
    completed: ReminderCard[];
  };
  preferences: CommunicationPreferencesRead;
  linked_documents: DocumentLink[];
}

export interface CommunicationTimelineResponse {
  items: CommunicationCard[];
  total: number;
  skip: number;
  limit: number;
}

export interface ReminderListResponse {
  reminders_by_urgency: {
    urgent: ReminderCard[];
    upcoming: ReminderCard[];
    completed: ReminderCard[];
  };
  total_urgent: number;
  total_upcoming: number;
  total_completed: number;
}
