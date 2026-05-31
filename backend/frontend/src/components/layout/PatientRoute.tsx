import { Navigate } from 'react-router-dom';
import type { User } from '../../types';
import { doctorHomePath, getEffectiveRoles, isDoctorRole, isPatientRole, staffHomePath } from '../../utils/roles';

interface PatientRouteProps {
  user: User | null;
  children: React.ReactNode;
}

/** Patient-only shell; doctors and staff are sent to their dashboards. */
export function PatientRoute({ user, children }: PatientRouteProps) {
  const eff = getEffectiveRoles(user, localStorage.getItem('token'));
  if (isPatientRole(eff)) {
    return <>{children}</>;
  }
  if (isDoctorRole(eff)) {
    return <Navigate to={doctorHomePath()} replace />;
  }
  return <Navigate to={staffHomePath()} replace />;
}
