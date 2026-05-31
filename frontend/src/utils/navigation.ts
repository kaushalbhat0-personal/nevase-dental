/**
 * Imperative navigation helper.
 *
 * Allows code outside the React tree (e.g. Axios interceptors) to trigger
 * React Router navigation without a full page reload.
 *
 * Usage:
 *   1. Call `setNavigator(navigate)` once inside a component that has access
 *      to React Router's `useNavigate` hook (App.tsx).
 *   2. Call `navigateTo('/login')` from anywhere (interceptors, services, etc.)
 */

import type { NavigateFunction } from 'react-router-dom';

let _navigator: NavigateFunction | null = null;

/** Register the React Router navigate function. Call this once in App.tsx. */
export function setNavigator(navigate: NavigateFunction): void {
  _navigator = navigate;
}

/** Navigate imperatively. Falls back to window.location if navigator not yet set. */
export function navigateTo(path: string): void {
  if (_navigator) {
    _navigator(path, { replace: true });
  } else {
    // Fallback: navigator not initialised yet (e.g. very early boot)
    window.location.href = path;
  }
}
