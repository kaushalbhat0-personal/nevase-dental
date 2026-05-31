/**
 * Patient Handler
 * Business logic for patient operations
 */

import { patientsApi } from '../services';
import { PATIENT_DEFAULT_PARAMS } from '../constants';
import { safeArray } from '../utils';
import type { Patient } from '../types';
import type { PatientFormData } from '../validation';

/**
 * Fetch patients with optional search
 */
export const fetchPatientsHandler = async (search?: string): Promise<Patient[]> => {
  const response = await patientsApi.getAll({
    ...PATIENT_DEFAULT_PARAMS,
    ...(search ? { search } : {}),
  });

  return safeArray<Patient>(response);
};

/**
 * Create a new patient
 */
export const createPatientHandler = async (data: PatientFormData): Promise<void> => {
  // Ensure proper data types and format for API
  const payload = {
    name: data.name,
    age: Number(data.age),
    gender: data.gender,
    phone: data.phone,
  };

  if (import.meta.env.DEV) {
    console.log('[createPatientHandler] Payload:', payload);
  }

  await patientsApi.create(payload);
}
