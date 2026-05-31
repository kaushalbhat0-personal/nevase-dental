import { Navigate, useLocation } from 'react-router-dom';
import type { User } from '../../types';
import {
  getEffectiveRoles,
  isDoctorRole,
  isPatientRole,
  needsStructuredDoctorProfile,
  patientHomePath,
  staffHomePath,
} from '../../utils/roles';
import { useAppMode } from '../../contexts/AppModeContext';
import { getDoctorVerificationRestrictedRedirect } from '../../utils/doctorVerification';

interface DoctorRouteProps {
  user: User | null;
  children: React.ReactNode;
}

/** Clinician shell; patients and staff are redirected to their own areas. */
export function DoctorRoute({ user, children }: DoctorRouteProps) {
  const { isDualModeUser, resolvedMode } = useAppMode();
  const location = useLocation();
  const token = localStorage.getItem('token');
  const eff = getEffectiveRoles(user, token);
  if (isDualModeUser && resolvedMode === 'admin') {
    return <Navigate to="/admin/dashboard" replace />;
  }
  const verificationRedirect = getDoctorVerificationRestrictedRedirect(location.pathname, user, token);
  if (verificationRedirect) {
    return <Navigate to={verificationRedirect} replace />;
  }
  if (needsStructuredDoctorProfile(user) && location.pathname !== '/complete-profile') {
    return <Navigate to="/complete-profile" replace state={{ from: location }} />;
  }
  if (isDoctorRole(eff)) {
    return <>{children}</>;
  }
  if (isPatientRole(eff)) {
    return <Navigate to={patientHomePath()} replace />;
  }
  return <Navigate to={staffHomePath()} replace />;
}
