import { useFetch } from './useFetch';
import { fetchPatientsHandler } from '../../handlers';
import { safeArray } from '../../utils';
import type { Patient } from '../../types';

export function usePatients(search?: string, enabled: boolean = true) {
  const { data, loading, error, refetch } = useFetch(
    fetchPatientsHandler,
    search?.trim() || undefined,
    'patients',
    enabled,
    { subscribeScopeEvents: enabled }
  );

  return {
    patients: safeArray<Patient>(data),
    loading,
    error,
    refetch,
  };
}
