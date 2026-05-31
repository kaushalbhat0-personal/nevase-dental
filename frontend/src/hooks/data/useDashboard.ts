import { useFetch } from './useFetch';
import { fetchDashboardStatsHandler } from '../../handlers';
import type { DashboardStats } from '../../types';

/**
 * Default empty dashboard stats
 * Used only when data is loading or not yet fetched
 */
const DEFAULT_STATS: DashboardStats = {
  total_patients: 0,
  total_doctors: 0,
  today_appointments: 0,
  total_revenue: 0,
};

/**
 * Hook for fetching dashboard statistics
 * - Shows loader only when data is null (initial load)
 * - Shows error state if API fails (no silent fallbacks)
 * - Stats are only valid when error is null
 */
export function useDashboard() {
  const { data, loading, error, refetch } = useFetch(
    fetchDashboardStatsHandler,
    undefined,
    'dashboard'
  );

  // Only use defaults during loading - don't mask errors with fallback data
  const stats: DashboardStats = error ? DEFAULT_STATS : (data ?? DEFAULT_STATS);

  return {
    stats,
    loading,
    error,
    refetch,
  };
}
