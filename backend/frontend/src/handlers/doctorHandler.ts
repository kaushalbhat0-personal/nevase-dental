/**
 * Doctor Handler
 * Business logic for doctor operations
 */

import { doctorsApi } from '../services';
import { DOCTOR_DEFAULT_PARAMS } from '../constants';
import { safeArray } from '../utils';
import type { Doctor } from '../types';

/**
 * Fetch all doctors
 */
export const fetchDoctorsHandler = async (): Promise<Doctor[]> => {
  const response = await doctorsApi.getAll(DOCTOR_DEFAULT_PARAMS);
  return safeArray<Doctor>(response);
};
