import { useFetch } from './useFetch';
import { fetchBillingDataHandler } from '../../handlers';
import { safeArray } from '../../utils';
import type { Bill, Patient } from '../../types';

interface BillingData {
  bills: Bill[];
  patients: Patient[];
}

export function useBilling() {
  const { data, loading, error, refetch } = useFetch<BillingData>(fetchBillingDataHandler);

  return {
    bills: safeArray<Bill>(data?.bills),
    patients: safeArray<Patient>(data?.patients),
    loading,
    error,
    refetch,
  };
}
