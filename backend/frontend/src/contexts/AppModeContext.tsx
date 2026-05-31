import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { User } from '../types';
import { getEffectiveRoles, normalizeRoles } from '../utils/roles';
import {
  APP_MODE_STORAGE_KEY,
  type AppMode,
  readStoredAppMode,
  writeStoredAppMode,
  dispatchAppModeChangeEvent,
} from '../constants/appMode';
import { useAuth } from '../hooks/useAuth';

export interface AppModeContextValue {
  isDualModeUser: boolean;
  isDoctor: boolean;
  isAdmin: boolean;
  mode: AppMode;
  setMode: (m: AppMode) => void;
  resolvedMode: AppMode;
}

const AppModeContext = createContext<AppModeContextValue | null>(null);

function detect(
  user: User | null,
  token: string | null
): { isDoctor: boolean; isAdmin: boolean; isDual: boolean } {
  const r = normalizeRoles(getEffectiveRoles(user, token));
  const isDoctor = r.includes('doctor');
  const isAdmin = r.includes('admin');
  return {
    isDoctor,
    isAdmin,
    isDual: isDoctor && isAdmin,
  };
}

function defaultDualMode(stored: AppMode | null): AppMode {
  if (stored === 'admin' || stored === 'practice') return stored;
  return 'practice';
}

export function AppModeProvider({ children }: { children: ReactNode }) {
  const { user, isAuthenticated } = useAuth();
  const [mode, setModeState] = useState<AppMode>('practice');

  const { isDoctor, isAdmin, isDual: isDualModeUser } = useMemo(
    () => detect(user, localStorage.getItem('token')),
    [user]
  );

  useEffect(() => {
    if (!isAuthenticated || !user) return;
    const t = localStorage.getItem('token');
    const { isDoctor: d, isAdmin: a, isDual: dual } = detect(user, t);
    const raw = Array.isArray(user.roles) && user.roles.length > 0 ? user.roles : [];
    const rawNorm = normalizeRoles(raw);
    // Tenant type from GET /me is the source of truth for practice vs org shell (not role alone).
    if (user.tenant?.type === 'individual') {
      setModeState('practice');
      writeStoredAppMode('practice');
    } else if (rawNorm.length === 1 && rawNorm[0] === 'doctor') {
      setModeState('practice');
      writeStoredAppMode('practice');
    } else if (dual) {
      setModeState(defaultDualMode(readStoredAppMode()));
    } else if (d && !a) {
      setModeState('practice');
      writeStoredAppMode('practice');
    } else {
      setModeState('admin');
    }
  }, [isAuthenticated, user]);

  const setMode = useCallback((m: AppMode) => {
    setModeState(m);
    writeStoredAppMode(m);
    dispatchAppModeChangeEvent();
  }, []);

  const resolvedMode: AppMode = useMemo(() => {
    if (!isAuthenticated) return 'practice';
    if (user?.tenant?.type === 'individual') return 'practice';
    if (isDoctor && !isAdmin) return 'practice';
    if (isAdmin && !isDoctor) return 'admin';
    if (isDualModeUser) return mode;
    return 'admin';
  }, [isAuthenticated, user?.tenant?.type, isAdmin, isDoctor, isDualModeUser, mode]);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.setAttribute('data-app-mode', resolvedMode);
    return () => {
      document.documentElement.removeAttribute('data-app-mode');
    };
  }, [resolvedMode]);

  // Persist canonical mode for API headers (X-Data-Scope). No global event: avoids refetch storm on init.
  useEffect(() => {
    if (!isAuthenticated) return;
    try {
      const current = readStoredAppMode();
      if (current !== resolvedMode) {
        localStorage.setItem(APP_MODE_STORAGE_KEY, resolvedMode);
      }
    } catch {
      // ignore
    }
  }, [isAuthenticated, resolvedMode]);

  const value = useMemo<AppModeContextValue>(
    () => ({
      isDualModeUser,
      isDoctor,
      isAdmin,
      mode,
      setMode,
      resolvedMode,
    }),
    [isDualModeUser, isDoctor, isAdmin, mode, setMode, resolvedMode]
  );

  return <AppModeContext.Provider value={value}>{children}</AppModeContext.Provider>;
}

export function useAppMode(): AppModeContextValue {
  const ctx = useContext(AppModeContext);
  if (!ctx) {
    throw new Error('useAppMode must be used within AppModeProvider');
  }
  return ctx;
}

export { APP_MODE_CHANGE_EVENT } from '../constants/appMode';
