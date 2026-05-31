import { Navigate } from 'react-router-dom';
import type { User } from '../../types';
import { canAccessAdminUI, getEffectiveRoles, staffHomePath } from '../../utils/roles';

interface AdminRouteProps {
  user: User | null;
  children: React.ReactNode;
}

/** Only `admin` and `super_admin` may access wrapped routes. */
export function AdminRoute({ user, children }: AdminRouteProps) {
  const eff = getEffectiveRoles(user, localStorage.getItem('token'));
  if (!canAccessAdminUI(eff)) {
    return <Navigate to={staffHomePath()} replace />;
  }
  return <>{children}</>;
}
