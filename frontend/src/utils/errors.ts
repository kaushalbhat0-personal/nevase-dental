import type { AxiosError } from 'axios';

export interface ApiErrorResponse {
  message: string;
  errors?: Record<string, string[]>;
}

/**
 * Best-effort message for API rejects (`error.response.data`) or `Error` instances.
 * FastAPI often sends `detail` as a string or a list of validation objects — never pass raw objects to React.
 */
export function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error && typeof error === 'object' && 'detail' in error) {
    const d = (error as { detail?: unknown }).detail;
    if (typeof d === 'string' && d) {
      return d;
    }
    if (Array.isArray(d) && d.length > 0) {
      const first = d[0] as { msg?: string } | undefined;
      if (first && typeof first === 'object' && typeof first.msg === 'string') {
        return first.msg;
      }
    }
  }

  if (error && typeof error === 'object' && 'message' in error) {
    const m = (error as { message?: unknown }).message;
    if (typeof m === 'string' && m) {
      return m;
    }
  }

  return 'An unexpected error occurred. Please try again.';
}

export function handleApiError(error: AxiosError<ApiErrorResponse>): string {
  if (error.response) {
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        return data?.message || 'Invalid request. Please check your input.';
      case 401:
        return 'Session expired. Please log in again.';
      case 403:
        return 'You do not have permission to perform this action.';
      case 404:
        return 'The requested resource was not found.';
      case 409:
        return data?.message || 'This action conflicts with existing data.';
      case 422:
        return data?.message || 'Validation failed. Please check your input.';
      case 500:
        return 'Server error. Please try again later.';
      case 503:
        return 'Service temporarily unavailable. Please try again later.';
      default:
        return data?.message || `Request failed with status ${status}`;
    }
  }
  
  if (error.request) {
    return 'Network error. Please check your connection.';
  }
  
  return extractErrorMessage(error);
}

export function logError(context: string, error: unknown): void {
  if (import.meta.env.DEV) {
    console.error(`[${context}]`, error);
  }
  // In production, send to error tracking service (Sentry, etc.)
}
