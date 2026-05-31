import { api, type TenantScopedRequestConfig } from './api';

/** GET /admin/doctor-profiles — one row per doctor with a structured profile. */
export interface DoctorVerificationQueueItem {
  doctor_id: string;
  doctor_name: string;
  tenant_id: string;
  tenant_name: string;
  tenant_type: string;
  verification_status: string;
  verification_rejection_reason?: string | null;
}

export interface DoctorVerificationQueueCounts {
  pending: number;
  approved: number;
  rejected: number;
  draft: number;
}

export interface DoctorVerificationQueuePage {
  items: DoctorVerificationQueueItem[];
  total: number;
  skip: number;
  limit: number;
  counts: DoctorVerificationQueueCounts;
}

/** GET /admin/doctor-profiles/{id} — structured profile for the review panel. */
export interface DoctorProfileRead {
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

export type DoctorVerificationListScope =
  | { mode: 'org' }
  | { mode: 'super_all_tenants' }
  | { mode: 'super_tenant'; tenantId: string };

function withScopeConfig(
  scope: DoctorVerificationListScope,
  base: { params?: Record<string, unknown> }
): TenantScopedRequestConfig {
  if (scope.mode === 'super_all_tenants') {
    return { ...base, __allTenantsDoctorVerification: true } as TenantScopedRequestConfig;
  }
  if (scope.mode === 'super_tenant') {
    return {
      ...base,
      headers: { 'X-Tenant-ID': scope.tenantId },
    } as unknown as TenantScopedRequestConfig;
  }
  return base as TenantScopedRequestConfig;
}

export const doctorVerificationAdminApi = {
  list: async (
    params: {
      verification_status?: string;
      skip?: number;
      limit?: number;
    },
    scope: DoctorVerificationListScope
  ): Promise<DoctorVerificationQueuePage> => {
    const { data } = await api.get<DoctorVerificationQueuePage>(
      '/admin/doctor-profiles',
      withScopeConfig(scope, {
        params: {
          skip: params.skip ?? 0,
          limit: params.limit ?? 200,
          ...(params.verification_status
            ? { verification_status: params.verification_status }
            : {}),
        },
      })
    );
    return data;
  },

  getProfile: async (
    doctorId: string,
    scope: DoctorVerificationListScope
  ): Promise<DoctorProfileRead> => {
    const { data } = await api.get<DoctorProfileRead>(
      `/admin/doctor-profiles/${doctorId}`,
      withScopeConfig(scope, {})
    );
    return data;
  },

  setVerification: async (
    doctorId: string,
    body: { status: string; reason?: string | null }
  ): Promise<unknown> => {
    const { data } = await api.patch(`/admin/doctor-profiles/${doctorId}/verification`, body);
    return data;
  },
};
