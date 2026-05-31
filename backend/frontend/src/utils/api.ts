/**
 * API Utilities
 * Global helpers for API parameter sanitization and safe response handling
 */

/**
 * Clean parameters by removing:
 * - undefined values
 * - null values
 * - empty strings
 * - whitespace-only strings
 *
 * This prevents FastAPI 422 errors from empty query params
 */
export const cleanParams = (params?: Record<string, unknown>): Record<string, unknown> => {
  if (!params) return {};

  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => {
      // Remove undefined and null
      if (value === undefined || value === null) return false;
      // Remove empty strings
      if (value === '') return false;
      // Remove whitespace-only strings
      if (typeof value === 'string' && value.trim() === '') return false;
      // Keep everything else
      return true;
    })
  );
};

/**
 * Safely extract array from API response
 * Handles multiple response shapes:
 * - Direct array: `[...]`
 * - Wrapped in data: `{ data: [...] }`
 * - Error response: `{ detail: [...] }` → returns `[]`
 *
 * Never crashes - always returns an array
 */
export const safeArray = <T>(res: unknown): T[] => {
  // Direct array
  if (Array.isArray(res)) return res;

  // Wrapped in data property
  if (res && typeof res === 'object' && 'data' in res) {
    const data = (res as { data: unknown }).data;
    if (Array.isArray(data)) return data;
  }

  // Error response with detail - log and return empty
  if (res && typeof res === 'object' && 'detail' in res) {
    if (import.meta.env.DEV) {
      console.warn('[safeArray] Received error response:', res);
    }
    return [];
  }

  // Unexpected format - log warning in development
  if (import.meta.env.DEV) {
    console.warn('[safeArray] Expected array but received:', res);
  }

  return [];
};

/**
 * Safely extract object from API response
 * Handles:
 * - Direct object: `{ ... }`
 * - Wrapped in data: `{ data: { ... } }`
 */
export const safeObject = <T = Record<string, unknown>>(res: unknown): T | null => {
  if (!res) return null;

  // Direct object (not array)
  if (typeof res === 'object' && !Array.isArray(res)) {
    // Check if it's an error response
    if ('detail' in res) {
      if (import.meta.env.DEV) {
        console.warn('[safeObject] Received error response:', res);
      }
      return null;
    }
    return res as T;
  }

  // Wrapped in data property
  if (res && typeof res === 'object' && 'data' in res) {
    const data = (res as { data: unknown }).data;
    if (typeof data === 'object' && !Array.isArray(data)) {
      return data as T;
    }
  }

  return null;
};
