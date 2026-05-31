import { useAuth } from './useAuth';

/**
 * Linked patient profile for the signed-in user (prefetched in AuthProvider after login / session restore).
 */
export function useLinkedPatient() {
  const { patientId, patientProfileLoading, patientProfileError, refreshPatientProfile } = useAuth();
  return {
    patientId,
    loading: patientProfileLoading,
    error: patientProfileError,
    refresh: refreshPatientProfile,
  };
}
