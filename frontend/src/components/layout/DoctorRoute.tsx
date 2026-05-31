import { Navigate } from 'react-router-dom';
import type { User } from '../../types';
import {
  getEffectiveRoles,
  isDoctorRole,
  isPatientRole,
  patientHomePath,
  staffHomePath,
} from '../../utils/roles';
import { useAppMode } from '../../contexts/AppModeContext';

interface DoctorRouteProps {
  user: User | null;
  children: React.ReactNode;
}

/** Clinician shell; patients and staff are redirected to their own areas. */
export function DoctorRoute({ user, children }: DoctorRouteProps) {
  const { isDualModeUser, resolvedMode } = useAppMode();
  const token = localStorage.getItem('token');
  const eff = getEffectiveRoles(user, token);
  if (isDualModeUser && resolvedMode === 'admin') {
    return <Navigate to="/admin/dashboard" replace />;
  }

  if (isDoctorRole(eff)) {
    return <>{children}</>;
  }
  if (isPatientRole(eff)) {
    return <Navigate to={patientHomePath()} replace />;
  }
  return <Navigate to={staffHomePath()} replace />;
}
