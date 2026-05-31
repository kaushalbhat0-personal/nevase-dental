import { dashboardApi } from '../services';
import type { DashboardStats } from '../types';

/**
 * Handler for fetching dashboard statistics
 * Simply delegates to the API service and lets errors bubble up
 * for the useFetch hook to handle
 */
export const fetchDashboardStatsHandler = async (): Promise<DashboardStats> => {
  const stats = await dashboardApi.getStats();
  if (!stats) {
    throw new Error('Failed to load dashboard statistics');
  }
  return stats;
};
