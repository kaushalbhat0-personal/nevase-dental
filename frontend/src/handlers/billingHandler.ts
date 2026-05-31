/**
 * Billing Handler
 * Business logic for billing operations
 */

import { billingApi, patientsApi, appointmentsApi } from '../services';
import { BILLING_DEFAULT_PARAMS } from '../constants';
import { safeArray } from '../utils';
import type { Bill, Patient, Appointment } from '../types';
import type { BillingFormData } from '../validation';
import type { CreateBillData } from '../services/billing';

export interface BillingDataResult {
  bills: Bill[];
  patients: Patient[];
}

/**
 * Fetch bills and patients for dropdown
 * Appointments are fetched dynamically per-patient
 */
export const fetchBillingDataHandler = async (): Promise<BillingDataResult> => {
  const [billsData, patientsData] = await Promise.all([
    billingApi.getAll(BILLING_DEFAULT_PARAMS),
    patientsApi.getAll(),
  ]);

  return {
    bills: safeArray<Bill>(billsData),
    patients: safeArray<Patient>(patientsData),
  };
};

/**
 * Create a new bill
 */
export const createBillHandler = async (data: BillingFormData): Promise<void> => {
  // Format date as YYYY-MM-DD for backend (handles both date input and datetime)
  const dueDateStr = data.due_date.includes('T') 
    ? data.due_date.split('T')[0]  // Extract date from ISO string
    : data.due_date;               // Already YYYY-MM-DD

  // Build payload - only include appointment_id if provided
  const payload: Record<string, unknown> = {
    patient_id: data.patient_id,
    amount: Number(data.amount),
    currency: data.currency || 'INR',
    description: data.description?.trim(),
    due_date: dueDateStr, // YYYY-MM-DD format - backend will parse
  };

  // Only include appointment_id if it's a non-empty string
  if (data.appointment_id && data.appointment_id.trim()) {
    payload.appointment_id = data.appointment_id;
  }

  if (import.meta.env.DEV) {
    console.log('[createBillHandler] Payload:', payload);
  }

  await billingApi.create(payload as unknown as CreateBillData);
};

/**
 * Pay a bill
 */
export const payBillHandler = async (billId: string): Promise<void> => {
  await billingApi.pay(billId);
};

/**
 * Fetch appointments for a specific patient
 */
export const fetchPatientAppointmentsHandler = async (patientId: string): Promise<Appointment[]> => {
  const appointments = await appointmentsApi.getAll({
    patient_id: patientId,
    status: 'completed',
    skip: 0,
    limit: 100,
  });
  const list = safeArray<Appointment>(appointments);
  const completedOnly = list.filter((a) => a.status === 'completed');
  if (import.meta.env.DEV) {
    const unexpected = list.filter((a) => a.status !== 'completed');
    if (unexpected.length > 0) {
      console.warn(
        '[billing] API returned non-completed appointments despite status=completed filter',
        unexpected
      );
    }
  }
  return completedOnly;
};
