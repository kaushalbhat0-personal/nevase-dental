import { api } from './api';
import { safeArray } from '../utils';
import type { PublicDoctorProfile, PublicTenantDiscovery, PublicTenantDoctorBrief } from '../types';

export const publicDiscoveryApi = {
  listTenants: async (): Promise<PublicTenantDiscovery[]> => {
    const response = await api.get('/public/tenants');
    return safeArray<PublicTenantDiscovery>(response.data);
  },

  listTenantDoctors: async (tenantId: string): Promise<PublicTenantDoctorBrief[]> => {
    const response = await api.get(`/public/tenants/${tenantId}/doctors`);
    return safeArray<PublicTenantDoctorBrief>(response.data);
  },

  /** Marketplace-approved doctor only; 404 for draft / pending / rejected. */
  getDoctor: async (doctorId: string, options?: { signal?: AbortSignal }): Promise<PublicDoctorProfile> => {
    const response = await api.get<PublicDoctorProfile>(`/public/doctors/${doctorId}`, {
      signal: options?.signal,
    });
    return response.data;
  },
};
