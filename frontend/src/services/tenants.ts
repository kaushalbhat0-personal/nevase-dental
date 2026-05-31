import { api } from './api';
import { safeArray } from '../utils';
import type { Tenant } from '../types';

export const tenantsApi = {
  getAll: async (
    params?: { skip?: number; limit?: number; include_deactivated?: boolean }
  ): Promise<Tenant[]> => {
    const response = await api.get('/tenants', { params: { skip: 0, limit: 100, ...params } });
    if (import.meta.env.DEV) {
      console.log('[tenantsApi.getAll] Response:', response.data);
    }
    return safeArray<Tenant>(response.data);
  },

  getById: async (tenantId: string): Promise<Tenant> => {
    const response = await api.get(`/tenants/${tenantId}`);
    return response.data as Tenant;
  },

  create: async (payload: { name: string; type: 'organization' }): Promise<Tenant> => {
    const response = await api.post('/tenants', payload);
    return response.data as Tenant;
  },

  /**
   * Solo individual practice → organization; same tenant id; user becomes org admin.
   * Response includes updated tenant and effective application roles.
   */
  upgradeToOrganization: async (payload: { clinic_name: string }): Promise<{
    tenant: Tenant;
    roles: string[];
  }> => {
    const { data } = await api.post<{
      tenant: Tenant;
      roles: string[];
    }>('/tenants/upgrade-to-organization', { clinic_name: payload.clinic_name });
    return data;
  },

  /** Soft-deactivate (``is_deleted``); super admin only. */
  deactivate: async (tenantId: string): Promise<void> => {
    await api.delete(`/tenants/${tenantId}`);
  },

  reactivate: async (tenantId: string): Promise<Tenant> => {
    const { data } = await api.post<Tenant>(`/tenants/${tenantId}/reactivate`);
    return data;
  },
};
