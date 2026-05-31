import { api } from './api';
import { dedupeDoctorSlots } from '../utils/doctorSchedule';
import { safeArray } from '../utils';
import type { Doctor, DoctorAvailabilityWindow, DoctorTimeOff } from '../types';

export interface DoctorSlot {
  start: string;
  available: boolean;
  /** From backend availability window; never infer from neighbor slots. */
  duration_minutes?: number;
}

export interface DoctorDayMeta {
  full_day_time_off: boolean;
}

export interface DoctorScheduleDay {
  slots: DoctorSlot[];
  full_day_time_off: boolean;
  next_available: DoctorSlot | null;
}

const SLOT_CLIENT_CACHE_TTL_MS = 25_000;
const slotClientCache = new Map<string, { expires: number; data: DoctorSlot[] }>();

export const SLOTS_INVALIDATE_STORAGE_KEY = 'slots_invalidate';

/** Dispatched in other tabs after `storage` (same as localStorage set from booking tab). */
export const SLOTS_CROSS_TAB_BROADCAST = 'medical:slots-broadcast-invalidate';

let lastSlotsCrossTabSyncMs = 0;

/** Debounces rapid same-tab `SLOTS_CROSS_TAB_BROADCAST` handlers to limit refetch storms. */
export function shouldSyncSlotsCrossTab(): boolean {
  const now = Date.now();
  if (now - lastSlotsCrossTabSyncMs < 500) return false;
  lastSlotsCrossTabSyncMs = now;
  return true;
}

function slotsCacheKey(doctorId: string, date: string): string {
  return `${doctorId}:${date}`;
}

/**
 * When another tab invalidates, clear our in-process cache and nudge mounted UIs to refetch
 * (storage events do not update React state by themselves).
 */
function notifySlotsBroadcastListeners(): void {
  if (typeof window === 'undefined') return;
  try {
    window.dispatchEvent(new CustomEvent(SLOTS_CROSS_TAB_BROADCAST));
  } catch {
    /* ignore */
  }
}

/**
 * Subscribes to `storage` for cross-tab client cache; call once at app root.
 * Other tabs clear their Map and receive `SLOTS_CROSS_TAB_BROADCAST` to refetch.
 */
export function initDoctorSlotsCacheCrossTabSync(): () => void {
  if (typeof window === 'undefined') {
    return () => {};
  }
  const onStorage = (e: StorageEvent) => {
    if (e.key !== SLOTS_INVALIDATE_STORAGE_KEY || e.newValue == null) return;
    invalidateDoctorSlotsClientCache();
    notifySlotsBroadcastListeners();
  };
  window.addEventListener('storage', onStorage);
  return () => window.removeEventListener('storage', onStorage);
}

/** Drop client-side slot cache for a doctor/day or entire doctor. */
export function invalidateDoctorSlotsClientCache(doctorId?: string, dateYmd?: string): void {
  if (doctorId != null && dateYmd != null) {
    slotClientCache.delete(slotsCacheKey(doctorId, dateYmd));
  } else if (doctorId != null) {
    const prefix = `${doctorId}:`;
    for (const k of [...slotClientCache.keys()]) {
      if (k.startsWith(prefix)) slotClientCache.delete(k);
    }
  } else {
    slotClientCache.clear();
  }
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(SLOTS_INVALIDATE_STORAGE_KEY, String(Date.now()));
    }
  } catch {
    /* private mode / disabled */
  }
  try {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(SLOTS_CROSS_TAB_BROADCAST));
    }
  } catch {
    /* ignore */
  }
}

export interface CreateDoctorData {
  name: string;
  specialty?: string;
  specialization?: string;
  license_number?: string;
  experience_years?: number;
  account_email: string;
  account_password: string;
}

export const doctorsApi = {
  getSlots: async (
    doctorId: string,
    date: string,
    options?: { signal?: AbortSignal; skipCache?: boolean }
  ): Promise<DoctorSlot[]> => {
    try {
      const key = slotsCacheKey(doctorId, date);
      const now = Date.now();
      if (!options?.skipCache) {
        const hit = slotClientCache.get(key);
        if (hit && hit.expires > now) {
          return dedupeDoctorSlots([...hit.data]);
        }
      }
      const response = await api.get(`/doctors/${doctorId}/slots`, {
        params: { date },
        signal: options?.signal,
      });
      const raw = Array.isArray(response.data) ? response.data : [];
      const list = dedupeDoctorSlots(raw as DoctorSlot[]);
      slotClientCache.set(key, { expires: now + SLOT_CLIENT_CACHE_TTL_MS, data: list });
      return [...list];
    } catch (error) {
      console.error('[doctorsApi.getSlots] Error:', error);
      throw error;
    }
  },

  getDayMeta: async (
    doctorId: string,
    date: string,
    options?: { signal?: AbortSignal }
  ): Promise<DoctorDayMeta> => {
    const response = await api.get(`/doctors/${doctorId}/day-meta`, {
      params: { date },
      signal: options?.signal,
    });
    return response.data as DoctorDayMeta;
  },

  getNextAvailable: async (
    doctorId: string,
    fromYmd: string,
    options?: { signal?: AbortSignal; horizonDays?: number }
  ): Promise<DoctorSlot | null> => {
    const response = await api.get(`/doctors/${doctorId}/next-available`, {
      params: { from: fromYmd, horizon_days: options?.horizonDays ?? 14 },
      signal: options?.signal,
    });
    const data = response.data;
    if (data == null) return null;
    return data as DoctorSlot;
  },

  getScheduleDay: async (
    doctorId: string,
    date: string,
    options?: {
      fromYmd?: string;
      signal?: AbortSignal;
      horizonDays?: number;
      skipSlotsCache?: boolean;
    }
  ): Promise<DoctorScheduleDay> => {
    const fromYmd = options?.fromYmd;
    const response = await api.get<DoctorScheduleDay>(`/doctors/${doctorId}/schedule/day`, {
      params: {
        date,
        horizon_days: options?.horizonDays ?? 14,
        ...(fromYmd != null ? { from: fromYmd } : {}),
      },
      signal: options?.signal,
    });
    const raw = response.data;
    const slots = dedupeDoctorSlots(Array.isArray(raw.slots) ? raw.slots : []);
    if (!options?.skipSlotsCache) {
      const now = Date.now();
      const key = slotsCacheKey(doctorId, date);
      slotClientCache.set(key, { expires: now + SLOT_CLIENT_CACHE_TTL_MS, data: [...slots] });
    }
    return {
      full_day_time_off: Boolean(raw?.full_day_time_off),
      next_available: (raw?.next_available ?? null) as DoctorSlot | null,
      slots: [...slots],
    };
  },

  getOne: async (id: string, options?: { signal?: AbortSignal }): Promise<Doctor> => {
    const response = await api.get(`/doctors/${id}`, { signal: options?.signal });
    return response.data as Doctor;
  },

  /**
   * Set the doctor's linked user to org admin in-place (PATCH /doctors/{id}/promote).
   * Requires X-Tenant-ID; does not create a new user.
   */
  promoteDoctor: async (
    doctorId: string,
    options: { tenantScopeId: string }
  ): Promise<{ id: string; email: string; role: string; is_owner?: boolean }> => {
    const { data } = await api.patch(`/doctors/${doctorId}/promote`, {}, {
      headers: { 'X-Tenant-ID': options.tenantScopeId },
    });
    return data as { id: string; email: string; role: string; is_owner?: boolean };
  },

  getAll: async (
    params?: {
      search?: string;
      skip?: number;
      limit?: number;
      available_today?: boolean;
      lat?: number;
      lng?: number;
      radius?: string;
      specialization?: string;
      include_availability_hint?: boolean;
      /** Only marketplace-approved doctors (also enforced server-side for patients). */
      only_verified?: boolean;
    },
    options?: { tenantScopeId?: string }
  ): Promise<Doctor[]> => {
    try {
      const headers =
        options?.tenantScopeId != null && options.tenantScopeId !== ''
          ? { 'X-Tenant-ID': options.tenantScopeId }
          : undefined;
      const response = await api.get('/doctors', {
        params: { skip: 0, limit: 100, ...params },
        headers,
      });
      // Debug log in development
      if (import.meta.env.DEV) {
        console.log('[doctorsApi.getAll] Response:', response.data);
      }
      // Safe array extraction - handles { data: [...] } or direct array
      return safeArray<Doctor>(response.data);
    } catch (error) {
      console.error('[doctorsApi.getAll] Error:', error);
      throw error;
    }
  },
  create: async (doctor: CreateDoctorData): Promise<Doctor> => {
    try {
      const response = await api.post('/doctors', doctor);
      return response.data;
    } catch (error) {
      console.error('[doctorsApi.create] Error:', error);
      throw error;
    }
  },
  delete: async (id: string): Promise<void> => {
    try {
      await api.delete(`/doctors/${id}`);
    } catch (error) {
      console.error('[doctorsApi.delete] Error:', error);
      throw error;
    }
  },

  getAvailabilityWindows: async (
    doctorId: string,
    options?: { signal?: AbortSignal }
  ): Promise<DoctorAvailabilityWindow[]> => {
    const response = await api.get<DoctorAvailabilityWindow[]>(
      `/doctors/${doctorId}/availability-windows`,
      { signal: options?.signal }
    );
    return Array.isArray(response.data) ? response.data : [];
  },

  createAvailabilityWindow: async (
    doctorId: string,
    body: {
      day_of_week: number;
      start_time: string;
      end_time: string;
      slot_duration: number;
    }
  ): Promise<DoctorAvailabilityWindow> => {
    const response = await api.post<DoctorAvailabilityWindow>(
      `/doctors/${doctorId}/availability-windows`,
      body
    );
    return response.data;
  },

  copyAvailabilityWindows: async (
    doctorId: string,
    body: { source_day: number; target_days: number[] }
  ): Promise<DoctorAvailabilityWindow[]> => {
    const response = await api.post<DoctorAvailabilityWindow[]>(
      `/doctors/${doctorId}/availability-windows/copy`,
      body
    );
    return Array.isArray(response.data) ? response.data : [];
  },

  updateAvailabilityWindow: async (
    doctorId: string,
    windowId: string,
    body: {
      day_of_week?: number;
      start_time?: string;
      end_time?: string;
      slot_duration?: number;
    }
  ): Promise<DoctorAvailabilityWindow> => {
    const response = await api.put<DoctorAvailabilityWindow>(
      `/doctors/${doctorId}/availability-windows/${windowId}`,
      body
    );
    return response.data;
  },

  deleteAvailabilityWindow: async (doctorId: string, windowId: string): Promise<void> => {
    await api.delete(`/doctors/${doctorId}/availability-windows/${windowId}`);
  },

  getTimeOff: async (
    doctorId: string,
    params?: { from_date?: string; to_date?: string; signal?: AbortSignal }
  ): Promise<DoctorTimeOff[]> => {
    const response = await api.get<DoctorTimeOff[]>(`/doctors/${doctorId}/time-off`, {
      params: { from_date: params?.from_date, to_date: params?.to_date },
      signal: params?.signal,
    });
    return Array.isArray(response.data) ? response.data : [];
  },

  createTimeOff: async (
    doctorId: string,
    body: { off_date: string; start_time?: string | null; end_time?: string | null }
  ): Promise<DoctorTimeOff> => {
    const response = await api.post<DoctorTimeOff>(`/doctors/${doctorId}/time-off`, body);
    return response.data;
  },

  updateTimeOff: async (
    doctorId: string,
    timeOffId: string,
    body: { off_date?: string; start_time?: string | null; end_time?: string | null }
  ): Promise<DoctorTimeOff> => {
    const response = await api.put<DoctorTimeOff>(`/doctors/${doctorId}/time-off/${timeOffId}`, body);
    return response.data;
  },

  deleteTimeOff: async (doctorId: string, timeOffId: string): Promise<void> => {
    await api.delete(`/doctors/${doctorId}/time-off/${timeOffId}`);
  },
};
