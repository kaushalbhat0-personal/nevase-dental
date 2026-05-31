import { useCallback, useEffect, useState } from 'react';
import { BOOKING_DATA_REFRESH_EVENT } from '../constants/booking';
import { APP_MODE_CHANGE_EVENT } from '../constants/appMode';
import { dashboardApi } from '../services';
import { TENANT_ID_STORAGE_EVENT } from '../utils/tenantIdForRequest';
import type {
  AdminDashboardMetrics,
  AdminDoctorPerformanceRow,
  AdminRevenueTrendItem,
} from '../types';

export interface UseAdminDashboardResult {
  metrics: AdminDashboardMetrics | null;
  revenueTrend: AdminRevenueTrendItem[];
  /** Sorted by total_revenue descending */
  doctorPerformance: AdminDoctorPerformanceRow[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

function normalizeError(err: unknown): string {
  if (err && typeof err === 'object' && 'detail' in err) {
    const d = (err as { detail?: unknown }).detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d) && d[0] && typeof d[0] === 'object' && 'msg' in d[0]) {
      return String((d[0] as { msg: string }).msg);
    }
  }
  if (err instanceof Error) return err.message;
  return 'Failed to load admin dashboard';
}

/**
 * Fetches admin metrics, 7-day revenue trend, and doctor performance in parallel.
 */
export function useAdminDashboard(): UseAdminDashboardResult {
  const [metrics, setMetrics] = useState<AdminDashboardMetrics | null>(null);
  const [revenueTrend, setRevenueTrend] = useState<AdminRevenueTrendItem[]>([]);
  const [doctorPerformance, setDoctorPerformance] = useState<AdminDoctorPerformanceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [m, trend, doctors] = await Promise.all([
        dashboardApi.getAdminMetrics(),
        dashboardApi.getAdminRevenueTrend(),
        dashboardApi.getAdminDoctorPerformance(),
      ]);
      setMetrics(m);
      setRevenueTrend(trend);
      const sorted = [...doctors].sort((a, b) => b.total_revenue - a.total_revenue);
      setDoctorPerformance(sorted);
    } catch (err) {
      setMetrics(null);
      setRevenueTrend([]);
      setDoctorPerformance([]);
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const onScopeChange = () => {
      void load();
    };
    window.addEventListener(TENANT_ID_STORAGE_EVENT, onScopeChange);
    window.addEventListener(APP_MODE_CHANGE_EVENT, onScopeChange);
    return () => {
      window.removeEventListener(TENANT_ID_STORAGE_EVENT, onScopeChange);
      window.removeEventListener(APP_MODE_CHANGE_EVENT, onScopeChange);
    };
  }, [load]);

  useEffect(() => {
    const onBookingRefresh = () => {
      console.log('[REFETCH_TRIGGERED] adminDashboard');
      void load();
    };
    window.addEventListener(BOOKING_DATA_REFRESH_EVENT, onBookingRefresh);
    return () => {
      window.removeEventListener(BOOKING_DATA_REFRESH_EVENT, onBookingRefresh);
    };
  }, [load]);

  return {
    metrics,
    revenueTrend,
    doctorPerformance,
    loading,
    error,
    refetch: load,
  };
}
