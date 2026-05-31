/** Persisted UI mode for users with both clinician and org-admin access. */
export const APP_MODE_STORAGE_KEY = 'app_mode';

/** Window event: fired when practice ↔ admin mode changes (refetch scoped data). */
export const APP_MODE_CHANGE_EVENT = 'app_mode_changed';

export function dispatchAppModeChangeEvent(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(APP_MODE_CHANGE_EVENT));
}

export type AppMode = 'practice' | 'admin';

export function isAppMode(s: string | null | undefined): s is AppMode {
  return s === 'practice' || s === 'admin';
}

export function readStoredAppMode(): AppMode | null {
  try {
    const raw = localStorage.getItem(APP_MODE_STORAGE_KEY);
    if (!raw) return null;
    return isAppMode(raw) ? raw : null;
  } catch {
    return null;
  }
}

export function writeStoredAppMode(mode: AppMode): void {
  try {
    localStorage.setItem(APP_MODE_STORAGE_KEY, mode);
  } catch {
    // ignore
  }
}

export function clearStoredAppMode(): void {
  try {
    localStorage.removeItem(APP_MODE_STORAGE_KEY);
  } catch {
    // ignore
  }
}
