import { api } from './api';

export type OrganizationUserCreatePayload = {
  /** Optional label; backend may ignore until User stores display name */
  name?: string;
  email: string;
  password: string;
  role: 'admin' | 'staff';
  tenant_id: string;
};

export const usersApi = {
  createOrganizationUser: async (payload: OrganizationUserCreatePayload) => {
    const { data } = await api.post('/users', payload);
    return data as { id: string; email: string; role: string; tenant_id?: string | null };
  },
};
