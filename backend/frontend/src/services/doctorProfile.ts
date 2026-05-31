import { api } from './api';
import type { DoctorStructuredProfile } from '../types';

export const doctorProfileApi = {
  get: async (): Promise<DoctorStructuredProfile> => {
    const { data } = await api.get<DoctorStructuredProfile>('/doctor/profile');
    return data;
  },
  put: async (body: DoctorStructuredProfileInput): Promise<DoctorStructuredProfile> => {
    const { data } = await api.put<DoctorStructuredProfile>('/doctor/profile', body);
    return data;
  },
  submitForVerification: async (): Promise<DoctorStructuredProfile> => {
    const { data } = await api.post<DoctorStructuredProfile>('/doctor/profile/submit-for-verification');
    return data;
  },
};

/** Payload for create/replace (matches backend `DoctorProfileWrite`). */
export type DoctorStructuredProfileInput = {
  full_name: string;
  phone?: string | null;
  profile_image?: string | null;
  specialization?: string | null;
  experience_years?: number | null;
  qualification?: string | null;
  registration_number?: string | null;
  registration_council?: string | null;
  clinic_name?: string | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
};
