import { api } from './api';
import { safeArray } from '../utils';
import type { Patient, PatientMyDoctor } from '../types';

export interface CreatePatientData {
  name: string;
  age: number;
  gender: string;
  phone: string;
}

export type PatientUpdatePayload = {
  name?: string;
  age?: number;
  gender?: string;
  phone?: string;
  clinical_notes?: string | null;
};

export const patientsApi = {
  getAll: async (params?: { search?: string; skip?: number; limit?: number }): Promise<Patient[]> => {
    try {
      const response = await api.get('/patients', { params: { skip: 0, limit: 100, ...params } });
      // Debug log in development
      if (import.meta.env.DEV) {
        console.log('[patientsApi.getAll] Response:', response.data);
      }
      // Safe array extraction - handles { data: [...] } or direct array
      return safeArray<Patient>(response.data);
    } catch (error) {
      console.error('[patientsApi.getAll] Error:', error);
      throw error;
    }
  },
  getById: async (id: string): Promise<Patient> => {
    try {
      const response = await api.get(`/patients/${id}`);
      return response.data;
    } catch (error) {
      console.error('[patientsApi.getById] Error:', error);
      throw error;
    }
  },
  create: async (patient: CreatePatientData): Promise<Patient> => {
    try {
      const response = await api.post('/patients', patient);
      return response.data;
    } catch (error) {
      console.error('[patientsApi.create] Error:', error);
      throw error;
    }
  },
  update: async (id: string, payload: PatientUpdatePayload): Promise<Patient> => {
    const response = await api.put(`/patients/${id}`, payload);
    return response.data;
  },
  delete: async (id: string): Promise<void> => {
    try {
      await api.delete(`/patients/${id}`);
    } catch (error) {
      console.error('[patientsApi.delete] Error:', error);
      throw error;
    }
  },

  getMyDoctors: async (): Promise<PatientMyDoctor[]> => {
    const response = await api.get('/patients/me/doctors');
    return safeArray<PatientMyDoctor>(response.data);
  },
};
