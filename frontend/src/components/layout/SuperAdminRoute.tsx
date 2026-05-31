import { Navigate } from 'react-router-dom';
import type { User } from '../../types';
import { getEffectiveRoles, isSuperAdminRole, staffHomePath } from '../../utils/roles';

interface SuperAdminRouteProps {
  user: User | null;
  children: React.ReactNode;
}

/** Only `super_admin` may access wrapped routes. */
export function SuperAdminRoute({ user, children }: SuperAdminRouteProps) {
  const eff = getEffectiveRoles(user, localStorage.getItem('token'));
  if (!isSuperAdminRole(eff)) {
    return <Navigate to={staffHomePath()} replace />;
  }
  return <>{children}</>;
}
