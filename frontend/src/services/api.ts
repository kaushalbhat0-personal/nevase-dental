/**
 * Core API configuration + request/response policy.
 *
 * Key goals:
 * - Centralize auth header attachment and common error handling.
 * - Be resilient to PaaS "cold starts" (e.g. Render) without incorrectly logging users out.
 *
 * SECURITY NOTE:
 * We currently store tokens in localStorage for simplicity. For production hardening,
 * prefer httpOnly cookies (mitigates XSS token theft). See `SECURITY.md`.
 */

import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

/** Strip auto `X-Tenant-ID` so super-admins can load the global doctor verification queue. */
export type TenantScopedRequestConfig = InternalAxiosRequestConfig & {
  __allTenantsDoctorVerification?: boolean;
};
import toast from 'react-hot-toast';
import { handleApiError, type ApiErrorResponse } from '../utils/errors';
import { cleanParams } from '../utils/api';
import { navigateTo } from '../utils/navigation';
import {
  getActiveTenantId,
  getTenantIdForRequest,
  NIL_TENANT_UUID,
} from '../utils/tenantIdForRequest';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Debug: Log API configuration
if (import.meta.env.DEV) {
  console.log('[API] Base URL:', API_BASE_URL);
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60s — PaaS cold starts often exceed 15s
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor:
// - attach auth token (if present)
// - normalize query params so FastAPI doesn't receive empty strings (422s)
// - add extra logs in dev for debugging
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Log request details in dev mode
    if (import.meta.env.DEV) {
      console.log('API REQUEST:', {
        url: config.url,
        method: config.method,
        params: config.params,
        data: config.data,
      });
    }

    const token = localStorage.getItem('token');
    if (import.meta.env.DEV) {
      console.log('TOKEN:', token ? `${token.substring(0, 15)}...` : 'none');
    }
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    if (config.headers) {
      // Multi-tenant: X-Tenant-ID = active org; X-Data-Scope = doctor (practice) vs tenant (admin).
      const ext = config as TenantScopedRequestConfig;
      const rawHeader = config.headers['X-Tenant-ID'];
      const rawStr =
        rawHeader != null && rawHeader !== '' ? String(rawHeader).trim() : '';
      if (rawStr === NIL_TENANT_UUID) {
        delete (config.headers as Record<string, unknown>)['X-Tenant-ID'];
      }
      const hasExplicit = rawStr !== '' && rawStr !== NIL_TENANT_UUID;

      if (ext.__allTenantsDoctorVerification) {
        delete (config.headers as Record<string, unknown>)['X-Tenant-ID'];
      } else if (!hasExplicit) {
        const activeTenantId = getActiveTenantId();
        const tenantId = activeTenantId ?? getTenantIdForRequest();
        if (tenantId && tenantId !== NIL_TENANT_UUID) {
          config.headers['X-Tenant-ID'] = tenantId;
        }
      }
      const mode = localStorage.getItem('app_mode');
      config.headers['X-Data-Scope'] = mode === 'practice' ? 'doctor' : 'tenant';

      // Active workspace context: propagate the current workspace slug so the
      // backend can apply request-scoped operational context (see workspace_context.py).
      // Falls back safely if no workspace is stored (backward-compatible).
      const lastWorkspace = localStorage.getItem('medical_webapp_last_workspace');
      if (lastWorkspace) {
        config.headers['X-Workspace'] = lastWorkspace;
      }
    }

    // Some forms submit empty strings for optional filters (e.g. ?doctor_id=).
    // FastAPI may treat that as invalid input, so we strip empty values consistently here.
    if (config.params) {
      config.params = cleanParams(config.params);
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor:
// - special-case network errors (cold start / offline) so we *don't* treat them as auth failures
// - redirect to login only on real 401s
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Debug: Log error details
    console.error('API ERROR:', error.response?.data || error.message);

    // Network error (no response):
    // Treat as "server unavailable" (cold start, offline, DNS, etc.). Do NOT clear session here,
    // because a cold start should not force a re-login.
    if (error.request && !error.response) {
      // This is likely a Render cold start or network issue, NOT an auth failure
      const isColdStart = error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK' || !navigator.onLine;
      if (isColdStart) {
        console.log('[API] Cold start or network issue detected, not logging out');
      }
      // Return a structured object so UI can show a friendly "waking up" state and optionally retry.
      return Promise.reject({
        __networkError: true,
        __coldStart: isColdStart,
        message: 'Server is waking up, please wait...',
        originalError: error,
      });
    }

    // Extract error message from response (FastAPI 422 `detail` is often an array of objects)
    const data = error.response?.data as
      | { detail?: unknown; message?: string; errors?: string[] }
      | undefined;
    const rawDetail = data?.detail;
    const detailString =
      typeof rawDetail === 'string'
        ? rawDetail
        : Array.isArray(rawDetail) && rawDetail.length > 0
          ? typeof (rawDetail[0] as { msg?: string })?.msg === 'string'
            ? (rawDetail[0] as { msg: string }).msg
            : 'Validation failed. Please check your input.'
          : undefined;
    const message =
      detailString ||
      data?.message ||
      data?.errors?.[0] ||
      handleApiError(error as AxiosError<ApiErrorResponse>);

    const messageForToast = typeof message === 'string' ? message : 'Something went wrong.';

    // 401 means "your token is not valid for this request" (expired, revoked, missing, etc.).
    // This is the one case where we clear local state and force the login flow.
    if (error.response?.status === 401) {
      // Prevent redirect loops if already on login page
      if (window.location.pathname !== '/login') {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('activeTenantId');
        try {
          localStorage.removeItem('active_tenant_id');
        } catch {
          /* ignore */
        }
        localStorage.removeItem('tenant_id');
        localStorage.removeItem('adminSelectedTenantId');
        toast.error('Session expired. Please log in again.');
        navigateTo('/login');
      }
      return Promise.reject(error.response?.data || error);
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      const m =
        typeof messageForToast === 'string' && messageForToast
          ? messageForToast
          : typeof message === 'string'
            ? message
            : '';
      if (m.toLowerCase().includes('complete your profile')) {
        if (window.location.pathname !== '/complete-profile') {
          toast.error('Please complete your profile to continue.');
          navigateTo('/complete-profile');
        } else {
          toast.error(m);
        }
      } else if (m.toLowerCase().includes('doctor verification pending')) {
        toast.error('Your profile is not verified yet. Submit for review or wait for approval.');
      } else {
        toast.error('Access denied. You do not have permission.');
      }
    }

    // Handle 404 Not Found
    else if (error.response?.status === 404) {
      toast.error('Resource not found.');
    }

    // Handle 400 (service ValidationError, etc.); do not leave silent
    else if (error.response?.status === 400) {
      toast.error(messageForToast);
    }

    // Handle validation errors (422)
    else if (error.response?.status === 422) {
      toast.error(messageForToast);
    }

    // Handle 500+ Server errors
    else if (error.response?.status && error.response.status >= 500) {
      toast.error('Server error. Please try again later.');
    }

    // Generic fallback for other errors
    else if (![400, 409].includes(error.response?.status || 0)) {
      toast.error(messageForToast);
    }

    // Return clean error data for consistent error handling
    return Promise.reject(error.response?.data || error);
  }
);

// Retry helper for transient network errors (typically cold starts).
// Keep retry rules conservative: we should not retry validation/auth errors.
export const retryRequest = async <T>(
  fn: () => Promise<T>,
  retries = 2,
  delay = 2000
): Promise<T> => {
  try {
    return await fn();
  } catch (err: any) {
    // Only retry on network errors (cold start), not on 4xx/5xx responses
    const isNetworkError = err?.__networkError || (!err?.response && err?.request);

    if (retries > 0 && isNetworkError) {
      console.log(`[API] Retrying request, ${retries} attempts left...`);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return retryRequest(fn, retries - 1, delay);
    }

    throw err;
  }
};

// Helper to check if error is a network/cold start error
export const isNetworkError = (error: any): boolean => {
  return error?.__networkError === true || (!error?.response && error?.request);
};

// Helper to check if error is a cold start error
export const isColdStartError = (error: any): boolean => {
  return error?.__coldStart === true || error?.code === 'ECONNABORTED';
};
