/**
 * Backend `TenantType` values (app.models.tenant.TenantType).
 */
export const TENANT_TYPE_INDIVIDUAL = 'individual';
export const TENANT_TYPE_ORGANIZATION = 'organization';

export function isManagedOrgTenant(tenantType: string | null | undefined): boolean {
  return tenantType === TENANT_TYPE_ORGANIZATION;
}
