import { api } from './api';
import { safeArray, safeObject } from '../utils';
import type {
  AdminDashboardMetrics,
  AdminDoctorPerformanceRow,
  AdminRevenueTrendItem,
  DashboardStats,
} from '../types';

/**
 * Dashboard API service
 * Provides methods to fetch dashboard statistics from /api/v1/dashboard
 */
export const dashboardApi = {
  /**
   * Fetch dashboard statistics from the backend
   * Endpoint: GET /api/v1/dashboard
   * Returns null on error - let the hook handle error states
   */
  getStats: async (): Promise<DashboardStats | null> => {
    const response = await api.get('/dashboard');

    // Debug log in development only
    if (import.meta.env.DEV) {
      console.log('[dashboardApi.getStats] Response:', response.data);
    }

    // Safe object extraction - handles both direct object and { data: {...} } wrapper
    const stats = safeObject<DashboardStats>(response.data);

    if (!stats) {
      throw new Error('Invalid dashboard data received from server');
    }

    // Validate required fields are present
    const requiredFields: (keyof DashboardStats)[] = [
      'total_patients',
      'total_doctors',
      'today_appointments',
      'total_revenue',
    ];

    const missingFields = requiredFields.filter((field) => !(field in stats));
    if (missingFields.length > 0) {
      throw new Error(`Missing dashboard fields: ${missingFields.join(', ')}`);
    }

    return stats;
  },

  /**
   * Admin KPIs — GET /api/v1/admin/dashboard/metrics
   * Requires role admin or super_admin.
   */
  getAdminMetrics: async (): Promise<AdminDashboardMetrics> => {
    const response = await api.get('/admin/dashboard/metrics');
    const data = safeObject<AdminDashboardMetrics>(response.data);
    if (!data) {
      throw new Error('Invalid admin dashboard metrics');
    }
    return data;
  },

  /**
   * Last 7 days paid revenue by day — GET /api/v1/admin/dashboard/revenue-trend
   */
  getAdminRevenueTrend: async (): Promise<AdminRevenueTrendItem[]> => {
    const response = await api.get('/admin/dashboard/revenue-trend');
    return safeArray<AdminRevenueTrendItem>(response.data);
  },

  /**
   * Doctor stats in 7-day window — GET /api/v1/admin/dashboard/doctor-performance
   */
  getAdminDoctorPerformance: async (): Promise<AdminDoctorPerformanceRow[]> => {
    const response = await api.get('/admin/dashboard/doctor-performance');
    return safeArray<AdminDoctorPerformanceRow>(response.data);
  },
};
