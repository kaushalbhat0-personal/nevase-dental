import type { User } from '../types';

/** Practice-style tenant (solo); use for upgrade CTA and copy — from GET /me only. */
export function isIndividualTenantUser(user: User | null | undefined): boolean {
  return user?.tenant?.type === 'individual';
}

/** Multi-staff org tenant; “clinic/hospital” mode — from GET /me only. */
export function isOrganizationTenantUser(user: User | null | undefined): boolean {
  return user?.tenant?.type === 'organization';
}
