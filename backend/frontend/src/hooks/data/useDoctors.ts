import { useFetch } from './useFetch';
import { fetchDoctorsHandler } from '../../handlers';
import { safeArray } from '../../utils';
import type { Doctor } from '../../types';

export function useDoctors() {
  const { data, loading, error, refetch } = useFetch(fetchDoctorsHandler);

  return {
    doctors: safeArray<Doctor>(data),
    loading,
    error,
    refetch,
  };
}
