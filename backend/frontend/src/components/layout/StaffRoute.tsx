import { Navigate } from 'react-router-dom';
import type { User } from '../../types';
import {
  canAccessAdminUI,
  doctorHomePath,
  getEffectiveRoles,
  isDoctorRole,
  isPatientRole,
  patientHomePath,
} from '../../utils/roles';
import { useAppMode } from '../../contexts/AppModeContext';
import { SuperAdminTenantGate } from './SuperAdminTenantGate';

interface StaffRouteProps {
  user: User | null;
  children: React.ReactNode;
}

/** Blocks patients and doctors from admin/staff dashboard routes. */
export function StaffRoute({ user, children }: StaffRouteProps) {
  const { isDualModeUser, resolvedMode } = useAppMode();
  const eff = getEffectiveRoles(user, localStorage.getItem('token'));
  if (isPatientRole(eff)) {
    return <Navigate to={patientHomePath()} replace />;
  }
  if (isDualModeUser && resolvedMode === 'practice') {
    return <Navigate to="/doctor/dashboard" replace />;
  }
  if (isDoctorRole(eff) && !canAccessAdminUI(eff)) {
    return <Navigate to={doctorHomePath()} replace />;
  }
  return <SuperAdminTenantGate user={user}>{children}</SuperAdminTenantGate>;
}
