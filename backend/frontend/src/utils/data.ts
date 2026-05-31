/**
 * Data Transformation Utilities
 * Helper functions for formatting and transforming data
 */

import type { Patient, Doctor, Appointment } from '../types';

/**
 * Format patient name from various possible field combinations
 * Handles: name field, first_name + last_name, or falls back to '-'
 */
export const formatPatientName = (patient?: Patient | null): string => {
  if (!patient) return '-';
  return (
    patient.name ||
    `${patient.first_name || ''} ${patient.last_name || ''}`.trim() ||
    '-'
  );
};

/**
 * Format doctor name from various possible field combinations
 * Handles: name field, user.full_name, or falls back to 'Unknown Doctor'
 */
export const formatDoctorName = (doctor?: Doctor | null): string => {
  if (!doctor) return '-';
  return (
    doctor.name ||
    doctor.user?.full_name ||
    'Unknown Doctor'
  );
};

/**
 * Format doctor display name with specialty
 * Example: "Dr. Smith - Cardiology"
 */
export const formatDoctorDisplay = (doctor?: Doctor | null): string => {
  if (!doctor) return 'Unknown - General';
  const name = formatDoctorName(doctor);
  const specialty = doctor.specialization || doctor.specialty || 'General';
  return `${name} - ${specialty}`;
};

/**
 * Format appointment patient name from nested patient object
 */
export const formatAppointmentPatientName = (appointment?: Appointment | null): string => {
  if (!appointment?.patient) return '-';
  return formatPatientName(appointment.patient);
};

/**
 * Format appointment doctor name from nested doctor object
 */
export const formatAppointmentDoctorName = (appointment?: Appointment | null): string => {
  if (!appointment?.doctor) return '-';
  return formatDoctorName(appointment.doctor);
};

/**
 * Format date to locale string, with fallback for invalid dates
 */
export const formatDateSafe = (
  dateString?: string | null,
  fallback = '-'
): string => {
  if (!dateString) return fallback;
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return fallback;
  return date.toLocaleDateString();
};

/**
 * Format date and time to locale string, with fallback for invalid dates
 */
export const formatDateTimeSafe = (
  dateString?: string | null,
  fallback = '-'
): string => {
  if (!dateString) return fallback;
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return fallback;
  return date.toLocaleString();
};

/**
 * Format patient age or date of birth display
 * Shows DOB if available, otherwise shows age if available
 */
export const formatPatientDobOrAge = (patient?: Patient | null): string => {
  if (!patient) return '-';

  if (patient.date_of_birth) {
    const date = new Date(patient.date_of_birth);
    if (!isNaN(date.getTime())) {
      return date.toLocaleDateString();
    }
  }

  if (patient.age) {
    return `${patient.age} years`;
  }

  return '-';
};

/**
 * Format currency amount with symbol
 */
export const formatCurrency = (
  amount?: number | string | null,
  currency = 'USD'
): string => {
  const numericAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
  const safeAmount = Number(numericAmount ?? 0);
  return `$${safeAmount.toFixed(2)} ${currency}`;
};

/**
 * Get initials from a name (for avatars)
 */
export const getInitials = (name?: string | null, fallback = '?'): string => {
  if (!name) return fallback;
  return name.charAt(0).toUpperCase();
};

/**
 * Format doctor avatar initials
 */
export const formatDoctorInitials = (doctor?: Doctor | null): string => {
  if (!doctor) return 'D';
  const name = doctor.name || doctor.user?.full_name;
  return getInitials(name, 'D');
};
