import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import type { User } from '../../types';
import { getEffectiveRoles, isSuperAdminRole } from '../../utils/roles';
import { getActiveTenantId } from '../../utils/tenantIdForRequest';

interface SuperAdminTenantGateProps {
  user: User | null;
  children: ReactNode;
}

/**
 * Super admins have no home tenant; they must pick an organization before calling scoped APIs.
 * Allows `/admin/tenants` (and password reset, handled on a separate route) without selection.
 */
export function SuperAdminTenantGate({ user, children }: SuperAdminTenantGateProps) {
  const { pathname } = useLocation();
  const eff = getEffectiveRoles(user, localStorage.getItem('token'));

  if (!isSuperAdminRole(eff)) {
    return <>{children}</>;
  }

  if (pathname === '/admin/tenants' || pathname === '/admin/doctor-verifications') {
    return <>{children}</>;
  }

  if (!getActiveTenantId()) {
    return <Navigate to="/admin/tenants" replace />;
  }

  return <>{children}</>;
}
