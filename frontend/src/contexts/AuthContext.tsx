import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import type {
  User,
  LoginCredentials,
  LoginResponse,
  LoginResult,
  RegisterPayload,
  RegisterResponse,
} from '../types';
import { api, authApi, formatLoginError, patientsApi } from '../services';
import {
  doctorIdFromToken,
  doctorProfileCompleteFromToken,
  isOwnerFromToken,
  roleFromToken,
  rolesFromToken,
  tenantIdFromToken,
  userIdFromAccessToken,
} from '../utils/jwtPayload';
import { getEffectiveRoles, isPatientRole, mergeRoleSources } from '../utils/roles';
import { resolveLinkedPatient } from '../utils/patientProfile';
import { ACTIVE_TENANT_ID_ALIAS_KEY, setActiveTenantId } from '../utils/tenantIdForRequest';
import { clearStoredAppMode } from '../constants/appMode';

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<LoginResult>;
  signUp: (payload: RegisterPayload) => Promise<LoginResult>;
  logout: () => void;
  /** Merge partial fields into the signed-in user and persist to localStorage */
  patchUser: (updates: Partial<User>) => void;
  /**
   * Reload the signed-in user from GET /me (e.g. after server-side role changes
   * such as org admin handoff) so the client matches the database and JWT `sub` continues to work.
   */
  refreshUser: () => Promise<void>;
  /** Resolved patient row id for the signed-in patient user; null for staff or unresolved. */
  patientId: string | null;
  patientProfileLoading: boolean;
  patientProfileError: string | null;
  refreshPatientProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function coalesceRoles(...candidates: (string[] | string | undefined)[]): string[] {
  for (const c of candidates) {
    if (Array.isArray(c) && c.length > 0) return c;
    if (typeof c === 'string' && c.length > 0) return [c];
  }
  return [];
}

const safeParseUser = (): User | null => {
  try {
    const storedUser = localStorage.getItem('user');
    if (!storedUser || storedUser === 'undefined') return null;
    const raw = JSON.parse(storedUser) as User & { role?: string };
    if (!raw.roles || !Array.isArray(raw.roles) || raw.roles.length === 0) {
      if (typeof raw.role === 'string' && raw.role) {
        raw.roles = [raw.role];
      } else {
        raw.roles = [];
      }
    }
    const { role: _drop, ...rest } = raw;
    void _drop;
    return rest as User;
  } catch {
    return null;
  }
};

function buildUserFromLogin(credentials: LoginCredentials, response: LoginResponse): User {
  const base = response.user;
  // Roles: API body + JWT; keep fallbacks for minimal login responses.
  const roles = coalesceRoles(
    response.roles,
    base?.roles,
    response.role,
    rolesFromToken(response.access_token),
    roleFromToken(response.access_token) ? [roleFromToken(response.access_token)!] : undefined
  );
  const tenantRaw = response.tenant_id ?? base?.tenant_id ?? tenantIdFromToken(response.access_token);
  const fromBaseDoc =
    base?.doctor_id != null && String(base.doctor_id).length > 0 ? String(base.doctor_id) : undefined;
  const fromRespDoc =
    response.doctor_id != null && String(response.doctor_id).length > 0
      ? String(response.doctor_id)
      : undefined;
  const fromTokDoc = doctorIdFromToken(response.access_token);
  const doctor_id = fromBaseDoc ?? fromRespDoc ?? (fromTokDoc !== undefined ? fromTokDoc : undefined);
  const isOwner =
    base?.is_owner ??
    response.is_owner ??
    isOwnerFromToken(response.access_token) ??
    false;

  const dpcRaw =
    response.doctor_profile_complete ??
    (base as { doctor_profile_complete?: boolean | null } | undefined)?.doctor_profile_complete ??
    doctorProfileCompleteFromToken(response.access_token);

  return {
    id: base?.id ?? 0,
    email: base?.email ?? credentials.email,
    full_name: base?.full_name ?? credentials.email.split('@')[0] ?? 'User',
    is_active: base?.is_active ?? true,
    roles: roles.length > 0 ? roles : ['admin'],
    is_owner: isOwner,
    ...(tenantRaw !== undefined ? { tenant_id: tenantRaw } : {}),
    ...(doctor_id !== undefined ? { doctor_id } : {}),
    ...(dpcRaw !== undefined ? { doctor_profile_complete: dpcRaw } : {}),
    ...(response.force_password_reset !== undefined
      ? { force_password_reset: response.force_password_reset }
      : {}),
  };
}

function buildUserFromRegister(response: RegisterResponse): User {
  const u = response.user;
  const roles = coalesceRoles(
    u.roles,
    u.role,
    rolesFromToken(response.access_token),
    roleFromToken(response.access_token) ? [roleFromToken(response.access_token)!] : undefined
  );
  const tenantRaw =
    u.tenant_id != null && u.tenant_id !== ''
      ? String(u.tenant_id)
      : tenantIdFromToken(response.access_token);
  const fromApiDoc =
    u.doctor_id != null && String(u.doctor_id).length > 0 ? String(u.doctor_id) : undefined;
  const fromTokDoc = doctorIdFromToken(response.access_token);
  const doctor_id = fromApiDoc ?? (fromTokDoc !== undefined ? fromTokDoc : undefined);
  const dpc = u.doctor_profile_complete ?? doctorProfileCompleteFromToken(response.access_token);
  return {
    id: u.id as unknown as number,
    email: u.email,
    full_name: u.full_name ?? u.email.split('@')[0] ?? 'User',
    is_active: u.is_active ?? true,
    roles: roles.length > 0 ? roles : ['patient'],
    is_owner: u.is_owner ?? isOwnerFromToken(response.access_token) ?? false,
    ...(tenantRaw !== undefined && tenantRaw !== null ? { tenant_id: String(tenantRaw) } : {}),
    ...(doctor_id !== undefined ? { doctor_id } : {}),
    ...(dpc !== undefined ? { doctor_profile_complete: dpc } : {}),
    ...(u.doctor_verification_status != null
      ? { doctor_verification_status: u.doctor_verification_status }
      : {}),
    ...(u.doctor_verification_rejection_reason != null
      ? { doctor_verification_rejection_reason: u.doctor_verification_rejection_reason }
      : {}),
  };
}

function mergeUserWithToken(user: User, token: string | null): User {
  if (!token) return user;
  const fromToken = rolesFromToken(token);
  const single = roleFromToken(token);
  const merged = mergeRoleSources(
    user.roles?.length ? user.roles : [],
    fromToken && fromToken.length > 0 ? fromToken : undefined,
    single ? [single] : undefined
  );
  const roles = merged.length > 0 ? merged : user.roles;
  const tenant_id = user.tenant_id ?? tenantIdFromToken(token) ?? undefined;
  const fromUserDoc =
    user.doctor_id != null && String(user.doctor_id).length > 0 ? String(user.doctor_id) : undefined;
  const fromTokDoc = doctorIdFromToken(token);
  const doctor_id = fromUserDoc ?? (fromTokDoc !== undefined ? fromTokDoc : undefined);
  const ownerHint = isOwnerFromToken(token);
  const dpc = doctorProfileCompleteFromToken(token);
  return {
    ...user,
    roles: roles && roles.length > 0 ? roles : user.roles,
    ...(tenant_id !== undefined ? { tenant_id } : {}),
    ...(doctor_id !== undefined ? { doctor_id } : {}),
    ...(dpc !== undefined && user.doctor_profile_complete === undefined
      ? { doctor_profile_complete: dpc }
      : {}),
    ...(ownerHint !== undefined && user.is_owner === undefined ? { is_owner: ownerHint } : {}),
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [patientId, setPatientId] = useState<string | null>(null);
  const [patientProfileLoading, setPatientProfileLoading] = useState(false);
  const [patientProfileError, setPatientProfileError] = useState<string | null>(null);
  /** Skip one post-login profile effect run when login() already prefetched the patient. */
  const skipPatientProfileEffectRef = useRef(false);
  /** One GET /me per authenticated session to load tenant.type, doctor_id, roles (source of truth over localStorage). */
  const initialMeSyncRef = useRef(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    let storedUser = safeParseUser();

    if (import.meta.env.DEV) {
      console.log('[Auth] Token on init:', token ? `${token.substring(0, 10)}...` : 'none');
    }

    if (token) {
      setIsAuthenticated(true);
      if (storedUser) {
        // Keep local user info in sync with the current token (role/tenant may change across sessions).
        storedUser = mergeUserWithToken(storedUser, token);
        localStorage.setItem('user', JSON.stringify(storedUser));
        setUser(storedUser);
      } else {
        // Token exists but user blob is missing/corrupted; synthesize a minimal user so routes can render.
        // We intentionally keep this minimal to avoid "inventing" profile fields.
        const tr = rolesFromToken(token);
        const single = roleFromToken(token);
        const roles = tr?.length ? tr : single ? [single] : [];
        if (roles.length > 0) {
          const did = doctorIdFromToken(token);
          const minimal: User = {
            id: 0,
            email: '',
            full_name: 'User',
            is_active: true,
            roles,
            is_owner: isOwnerFromToken(token) ?? false,
            tenant_id: tenantIdFromToken(token) ?? undefined,
            ...(did !== undefined ? { doctor_id: did } : {}),
          };
          localStorage.setItem('user', JSON.stringify(minimal));
          setUser(minimal);
        }
      }
    }
    setIsLoading(false);
  }, []);

  const loadPatientProfile = useCallback(async (userOverride?: User | null) => {
    const effectiveUser = userOverride ?? user;
    const token = localStorage.getItem('token');
    const effRoles = getEffectiveRoles(effectiveUser, token);
    if (!isPatientRole(effRoles)) {
      setPatientId(null);
      setPatientProfileError(null);
      setPatientProfileLoading(false);
      return;
    }
    setPatientProfileLoading(true);
    setPatientProfileError(null);
    try {
      // The backend links Patient → User via `patient.user_id`. We resolve the current patient's row
      // by matching that field against either the app user id or the JWT `sub`.
      const list = await patientsApi.getAll();
      const tokenUserId = userIdFromAccessToken(token);
      const linked = resolveLinkedPatient(list, effectiveUser?.id, tokenUserId);
      if (linked?.id != null) {
        setPatientId(String(linked.id));
        setPatientProfileError(null);
      } else {
        setPatientId(null);
        setPatientProfileError('Unable to resolve patient profile');
      }
    } catch {
      setPatientId(null);
      setPatientProfileError('Unable to load your patient profile');
    } finally {
      setPatientProfileLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated || !user) {
      setPatientId(null);
      setPatientProfileError(null);
      setPatientProfileLoading(false);
      return;
    }
    if (skipPatientProfileEffectRef.current) {
      // login()/signUp() already fetched patient profile; avoid duplicate network call right after auth.
      skipPatientProfileEffectRef.current = false;
      return;
    }
    void loadPatientProfile();
  }, [isLoading, isAuthenticated, user, loadPatientProfile]);

  const patchUser = useCallback((updates: Partial<User>) => {
    setUser((prev) => {
      if (!prev) return prev;
      const next = { ...prev, ...updates };
      localStorage.setItem('user', JSON.stringify(next));
      return next;
    });
  }, []);

  const signUp = useCallback(async (payload: RegisterPayload): Promise<LoginResult> => {
    setIsLoading(true);
    try {
      const response = await authApi.register(payload);
      if (!response.access_token) {
        return { success: false, error: 'No access token received' };
      }
      localStorage.setItem('token', response.access_token);
      setIsAuthenticated(true);
      const userData = buildUserFromRegister(response);
      localStorage.setItem('user', JSON.stringify(userData));
      if (!userData.roles.includes('super_admin') && userData.tenant_id) {
        setActiveTenantId(String(userData.tenant_id));
      }
      if (isPatientRole(userData.roles)) {
        skipPatientProfileEffectRef.current = true;
      }
      setUser(userData);
      try {
        await api.get('/health');
      } catch {
        /* cold start — session is valid; subsequent calls retry */
      }
      if (isPatientRole(userData.roles)) {
        await loadPatientProfile(userData);
      } else {
        setPatientId(null);
        setPatientProfileError(null);
        setPatientProfileLoading(false);
      }
        return {
          success: true,
          roles: userData.roles,
          is_owner: userData.is_owner,
          forcePasswordReset: false,
          doctor_id: userData.doctor_id != null ? String(userData.doctor_id) : null,
          doctor_profile_complete: userData.doctor_profile_complete,
        };
    } catch (error) {
      const errorMessage = formatLoginError(error);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  }, [loadPatientProfile]);

  const login = useCallback(async (credentials: LoginCredentials): Promise<LoginResult> => {
    setIsLoading(true);
    try {
      if (import.meta.env.DEV) {
        console.log('[Auth] Login attempt:', credentials.email);
      }

      const response: LoginResponse = await authApi.login(credentials.email, credentials.password);

      if (import.meta.env.DEV) {
        console.log('[Auth] Login response:', {
          hasToken: !!response.access_token,
          roles: response.roles ?? response.role,
        });
      }

      if (response.access_token) {
        localStorage.setItem('token', response.access_token);
        setIsAuthenticated(true);

        const userData = buildUserFromLogin(credentials, response);
        localStorage.setItem('user', JSON.stringify(userData));
        if (!userData.roles.includes('super_admin') && userData.tenant_id) {
          setActiveTenantId(String(userData.tenant_id));
        }
        if (isPatientRole(userData.roles)) {
          skipPatientProfileEffectRef.current = true;
        }
        setUser(userData);

        try {
          await api.get('/health');
        } catch {
          /* cold start — wake worker before heavier routes */
        }

        if (isPatientRole(userData.roles)) {
          await loadPatientProfile(userData);
        } else {
          setPatientId(null);
          setPatientProfileError(null);
          setPatientProfileLoading(false);
        }

        return {
          success: true,
          roles: userData.roles,
          is_owner: userData.is_owner,
          forcePasswordReset: response.force_password_reset === true,
          doctor_id: userData.doctor_id != null ? String(userData.doctor_id) : null,
          doctor_profile_complete: userData.doctor_profile_complete,
        };
      }
      return { success: false, error: 'No access token received' };
    } catch (error) {
      const errorMessage = formatLoginError(error);
      if (import.meta.env.DEV) {
        console.error('[Auth] Login error:', error);
      }
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  }, [loadPatientProfile]);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    clearStoredAppMode();
    localStorage.removeItem('activeTenantId');
    try {
      localStorage.removeItem(ACTIVE_TENANT_ID_ALIAS_KEY);
    } catch {
      /* ignore */
    }
    localStorage.removeItem('tenant_id');
    localStorage.removeItem('adminSelectedTenantId');
    setIsAuthenticated(false);
    setUser(null);
    setPatientId(null);
    setPatientProfileError(null);
    setPatientProfileLoading(false);
    skipPatientProfileEffectRef.current = false;
    initialMeSyncRef.current = false;
    // Hard navigation guarantees all state is reset (including any in-memory caches).
    window.location.href = '/login';
  }, []);

  const refreshPatientProfile = useCallback(async () => {
    await loadPatientProfile();
  }, [loadPatientProfile]);

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      const me = await authApi.getMe();
      const roles = me.roles?.length ? me.roles : [me.role];
      if (me.tenant_id && !roles.map((r) => String(r).toLowerCase()).includes('super_admin')) {
        setActiveTenantId(String(me.tenant_id));
      }
      setUser((prev) => {
        const next: User = {
          id: me.id as unknown as number,
          email: me.email,
          full_name: prev?.full_name ?? me.email.split('@')[0] ?? 'User',
          is_active: me.is_active,
          roles: me.roles?.length ? me.roles : [me.role],
          is_owner: me.is_owner,
          tenant_id: me.tenant_id ?? undefined,
          doctor_id: me.doctor_id != null ? String(me.doctor_id) : null,
          doctor_profile_complete: me.doctor_profile_complete,
          doctor_verification_status: me.doctor_verification_status,
          doctor_verification_rejection_reason: me.doctor_verification_rejection_reason,
          ...(me.tenant != null ? { tenant: me.tenant } : { tenant: undefined }),
        };
        if (prev?.force_password_reset !== undefined) {
          next.force_password_reset = prev.force_password_reset;
        }
        localStorage.setItem('user', JSON.stringify(next));
        return next;
      });
    } catch {
      // Silent: not worth interrupting admin flows; failed auth would surface on next request.
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      initialMeSyncRef.current = false;
    }
  }, [isAuthenticated]);

  /**
   * Always sync from GET /me once per authenticated session so ``tenant.type`` and roles
   * override stale localStorage / JWT hints (e.g. after deploy or upgrade flow).
   */
  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated || !localStorage.getItem('token')) return;
    if (initialMeSyncRef.current) return;
    initialMeSyncRef.current = true;
    void refreshUser();
  }, [isLoading, isAuthenticated, refreshUser]);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated,
      isLoading,
      login,
      signUp,
      logout,
      patchUser,
      refreshUser,
      patientId,
      patientProfileLoading,
      patientProfileError,
      refreshPatientProfile,
    }),
    [
      user,
      isAuthenticated,
      isLoading,
      login,
      signUp,
      logout,
      patchUser,
      refreshUser,
      patientId,
      patientProfileLoading,
      patientProfileError,
      refreshPatientProfile,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
