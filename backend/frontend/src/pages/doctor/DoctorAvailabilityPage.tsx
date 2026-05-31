import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useAppMode } from '../../contexts/AppModeContext';
import { getEffectiveRoles } from '../../utils/roles';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Loader2, Pencil, Plus, Trash2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { doctorsApi, invalidateDoctorSlotsClientCache } from '../../services';
import { useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import { ErrorState, EmptyState } from '../../components/common';
import { AvailabilityWindowModal } from '../../components/doctor/availability/AvailabilityWindowModal';
import { DoctorTimeOffPanel } from '../../components/doctor/availability/DoctorTimeOffPanel';
import type { DoctorAvailabilityWindow } from '../../types';
import {
  AVAILABILITY_WEEKDAYS,
  countBookableSlotsInWindow,
  formatTimeShort,
  sortAvailabilityWindows,
} from '../../utils/availabilityWindows';
import { cn } from '@/lib/utils';

function apiErr(e: unknown): string {
  if (axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object') {
    const d = (e.response.data as { detail?: unknown }).detail;
    if (typeof d === 'string') return d;
  }
  return 'Request failed. Try again.';
}

function nonTemp(windows: DoctorAvailabilityWindow[]) {
  return windows.filter((w) => !String(w.id).startsWith('temp-'));
}

export function DoctorAvailabilityPage() {
  const { user } = useAuth();
  const { resolvedMode } = useAppMode();
  const { isIndependent, isReadOnly, selfDoctor, loading: workspaceLoading, error: workspaceError, refetch: refetchWorkspace } =
    useDoctorWorkspace();
  /** Editing is allowed when the workspace resolved a single doctor profile (solo or clinic); not "clinic-only" as a product mode. */
  const canManageOwnSchedule = isIndependent;
  const [windows, setWindows] = useState<DoctorAvailabilityWindow[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedDow, setSelectedDow] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [editing, setEditing] = useState<DoctorAvailabilityWindow | null>(null);
  const [copyBusy, setCopyBusy] = useState(false);
  const [presetBusy, setPresetBusy] = useState(false);

  const doctorId = selfDoctor ? String(selfDoctor.id) : null;

  const loadWindows = useCallback(async () => {
    if (!doctorId) return;
    setLoadError(null);
    setLoading(true);
    try {
      const list = await doctorsApi.getAvailabilityWindows(doctorId);
      setWindows(sortAvailabilityWindows(list));
    } catch (e) {
      setLoadError(apiErr(e));
      setWindows([]);
    } finally {
      setLoading(false);
    }
  }, [doctorId]);

  useEffect(() => {
    void loadWindows();
  }, [loadWindows]);

  useEffect(() => {
    if (!import.meta.env.DEV || !user) return;
    console.log('[AVAILABILITY_CHECK]', {
      roles: getEffectiveRoles(user, localStorage.getItem('token')),
      tenant_id: user.tenant_id ?? null,
      mode: resolvedMode,
      selfDoctorId: selfDoctor?.id ?? null,
    });
  }, [user, resolvedMode, selfDoctor?.id]);

  const windowsForDay = useMemo(() => {
    return nonTemp(windows)
      .filter((w) => w.day_of_week === selectedDow)
      .sort((a, b) => a.start_time.localeCompare(b.start_time));
  }, [windows, selectedDow]);

  const countsByDow = useMemo(() => {
    const c: Record<number, number> = {};
    for (const w of nonTemp(windows)) {
      c[w.day_of_week] = (c[w.day_of_week] ?? 0) + 1;
    }
    return c;
  }, [windows]);

  const selectedDaySlotCount = useMemo(() => {
    return nonTemp(windows)
      .filter((w) => w.day_of_week === selectedDow)
      .reduce((s, w) => s + countBookableSlotsInWindow(w.start_time, w.end_time, w.slot_duration), 0);
  }, [windows, selectedDow]);

  const weekSlotCount = useMemo(() => {
    return nonTemp(windows).reduce(
      (s, w) => s + countBookableSlotsInWindow(w.start_time, w.end_time, w.slot_duration),
      0
    );
  }, [windows]);

  const afterMutation = useCallback(
    (docId: string) => {
      invalidateDoctorSlotsClientCache(docId);
      void refetchWorkspace();
    },
    [refetchWorkspace]
  );

  const openCreate = () => {
    setModalMode('create');
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (w: DoctorAvailabilityWindow) => {
    setModalMode('edit');
    setEditing(w);
    setSelectedDow(w.day_of_week);
    setModalOpen(true);
  };

  const onModalSave = async (payload: {
    day_of_week: number;
    start_time: string;
    end_time: string;
    slot_duration: number;
  }) => {
    if (!doctorId || !canManageOwnSchedule) return;

    if (modalMode === 'create') {
      const tempId = `temp-${crypto.randomUUID()}`;
      const tenantId = selfDoctor?.tenant_id != null ? String(selfDoctor.tenant_id) : '';
      const optimistic: DoctorAvailabilityWindow = {
        id: tempId,
        doctor_id: doctorId,
        day_of_week: payload.day_of_week,
        start_time: payload.start_time,
        end_time: payload.end_time,
        slot_duration: payload.slot_duration,
        tenant_id: tenantId,
        created_at: new Date().toISOString(),
      };
      setWindows((prev) => sortAvailabilityWindows([...prev, optimistic]));
      try {
        const created = await doctorsApi.createAvailabilityWindow(doctorId, payload);
        setWindows((prev) => sortAvailabilityWindows([...prev.filter((w) => w.id !== tempId), created]));
        afterMutation(doctorId);
        toast.success('Availability window added');
        setSelectedDow(created.day_of_week);
      } catch (e) {
        setWindows((prev) => prev.filter((w) => w.id !== tempId));
        throw e;
      }
    } else if (editing) {
      const id = String(editing.id);
      const prevRow = windows.find((w) => String(w.id) === id);
      setWindows((prev) =>
        sortAvailabilityWindows(
          prev.map((w) =>
            String(w.id) === id
              ? {
                  ...w,
                  day_of_week: payload.day_of_week,
                  start_time: payload.start_time,
                  end_time: payload.end_time,
                  slot_duration: payload.slot_duration,
                }
              : w
          )
        )
      );
      try {
        const updated = await doctorsApi.updateAvailabilityWindow(doctorId, id, {
          day_of_week: payload.day_of_week,
          start_time: payload.start_time,
          end_time: payload.end_time,
          slot_duration: payload.slot_duration,
        });
        setWindows((prev) => sortAvailabilityWindows(prev.map((w) => (String(w.id) === id ? updated : w))));
        afterMutation(doctorId);
        toast.success('Window updated');
        setSelectedDow(updated.day_of_week);
      } catch (e) {
        if (prevRow) {
          setWindows((prev) => sortAvailabilityWindows(prev.map((w) => (String(w.id) === id ? prevRow : w))));
        } else {
          void loadWindows();
        }
        throw e;
      }
    }
  };

  const onDelete = async (w: DoctorAvailabilityWindow) => {
    if (!doctorId || !canManageOwnSchedule) return;
    if (!window.confirm(`Remove this window (${formatTimeShort(w.start_time)}–${formatTimeShort(w.end_time)})?`)) {
      return;
    }
    const id = String(w.id);
    const snap = windows;
    setWindows((prev) => sortAvailabilityWindows(prev.filter((x) => String(x.id) !== id)));
    try {
      await doctorsApi.deleteAvailabilityWindow(doctorId, id);
      afterMutation(doctorId);
      toast.success('Window removed');
    } catch (e) {
      setWindows(snap);
      toast.error(apiErr(e), { duration: 5000 });
    }
  };

  const copyToTargets = useCallback(
    async (targetDows: number[]) => {
      if (!doctorId || !canManageOwnSchedule) return;
      const source = nonTemp(windows).filter((w) => w.day_of_week === selectedDow);
      if (source.length === 0) {
        toast.error('No windows to copy for this day');
        return;
      }
      const uniqueTargets = [...new Set(targetDows)].filter((d) => d !== selectedDow);
      if (uniqueTargets.length === 0) {
        toast.error('Pick at least one other day to copy to');
        return;
      }
      setCopyBusy(true);
      try {
        const list = await doctorsApi.copyAvailabilityWindows(doctorId, {
          source_day: selectedDow,
          target_days: uniqueTargets,
        });
        setWindows(sortAvailabilityWindows(list));
        afterMutation(doctorId);
        toast.success('Copy finished');
      } catch (e) {
        toast.error(apiErr(e), { duration: 5000 });
        void loadWindows();
      } finally {
        setCopyBusy(false);
      }
    },
    [doctorId, canManageOwnSchedule, windows, selectedDow, afterMutation, loadWindows]
  );

  const copyToAllOtherDays = () => {
    void copyToTargets(AVAILABILITY_WEEKDAYS.map((d) => d.dow).filter((d) => d !== selectedDow));
  };

  const applyMonFriPreset = useCallback(async () => {
    if (!doctorId || !canManageOwnSchedule) return;
    setPresetBusy(true);
    try {
      const next: DoctorAvailabilityWindow[] = [...nonTemp(windows)];
      for (let d = 0; d < 5; d++) {
        if (next.some((w) => w.day_of_week === d)) continue;
        const created = await doctorsApi.createAvailabilityWindow(doctorId, {
          day_of_week: d,
          start_time: '09:00:00',
          end_time: '17:00:00',
          slot_duration: 30,
        });
        next.push(created);
      }
      setWindows(sortAvailabilityWindows(next));
      afterMutation(doctorId);
      toast.success('Added Mon–Fri 9:00–17:00 where there were no hours');
    } catch (e) {
      toast.error(apiErr(e), { duration: 5000 });
    } finally {
      setPresetBusy(false);
    }
  }, [doctorId, canManageOwnSchedule, windows, afterMutation]);

  if (workspaceLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
        <span>Loading…</span>
      </div>
    );
  }

  if (workspaceError) {
    return (
      <ErrorState
        title="Could not load workspace"
        description="We need your organization profile to manage availability."
        error={workspaceError}
        onRetry={() => void refetchWorkspace()}
      />
    );
  }

  if (!selfDoctor) {
    return (
      <ErrorState
        title="No doctor profile"
        description="We could not link your account to a doctor record."
        error="Try again or contact an administrator."
        onRetry={() => void refetchWorkspace()}
      />
    );
  }

  return (
    <div className="space-y-6" data-testid="doctor-availability-page">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Availability</h1>
        <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
          {isReadOnly
            ? 'Your organization manages your schedule in the staff application. The windows below are read only.'
            : 'Set weekly hours for patient booking. Calendar and slots are shown in IST.'}
        </p>
        <p className="text-xs text-muted-foreground mt-2">All times in IST</p>
        {!loadError && (
          <p className="text-sm text-muted-foreground mt-3" data-testid="availability-slot-preview">
            <span className="text-foreground font-medium">Preview:</span> on this weekday, about {selectedDaySlotCount} bookable
            slot {selectedDaySlotCount === 1 ? 'start' : 'starts'}; across the whole week, about {weekSlotCount} slot{' '}
            {weekSlotCount === 1 ? 'start' : 'starts'}
            (approximate; confirm on your calendar).
          </p>
        )}
      </div>

      {isReadOnly && (
        <Card className="border-dashed" data-testid="availability-read-only-notice">
          <CardHeader className="py-3">
            <CardTitle className="text-base">Organization-managed</CardTitle>
            <CardDescription>
              Your account is not linked to a clear doctor record in this organization. You can still review how hours appear
              when listed; ask an admin to confirm your email on your profile.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {loadError && (
        <ErrorState title="Could not load availability" description="Try refreshing." error={loadError} onRetry={() => void loadWindows()} />
      )}

      {!loadError && (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2 space-y-0">
            <div>
              <CardTitle className="text-base">Week</CardTitle>
              <CardDescription>Pick a day, then add or adjust windows for that day.</CardDescription>
            </div>
            {canManageOwnSchedule && (
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => void applyMonFriPreset()}
                  disabled={presetBusy}
                  data-testid="availability-preset-week-mf-9-5"
                >
                  {presetBusy ? 'Applying…' : 'Set Mon–Fri 9–5'}
                </Button>
                <Button type="button" size="sm" className="gap-1" onClick={openCreate} data-testid="availability-add-window">
                  <Plus className="h-4 w-4" aria-hidden />
                  Add window
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-1" role="tablist" aria-label="Day of week">
              {AVAILABILITY_WEEKDAYS.map((d) => {
                const n = countsByDow[d.dow] ?? 0;
                const active = selectedDow === d.dow;
                return (
                  <button
                    key={d.dow}
                    type="button"
                    role="tab"
                    data-testid={`availability-day-tab-${d.dow}`}
                    aria-selected={active}
                    onClick={() => setSelectedDow(d.dow)}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-sm font-medium transition-colors',
                      active
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-border bg-background text-foreground hover:bg-muted'
                    )}
                  >
                    {d.short}
                    {n > 0 && (
                      <span
                        className={cn(
                          'rounded-full px-1.5 text-[10px] tabular-nums',
                          active ? 'bg-primary-foreground/20' : 'bg-muted'
                        )}
                      >
                        {n}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {canManageOwnSchedule && !loading && windowsForDay.length > 0 && (
              <div className="flex flex-col gap-2 rounded-lg border border-dashed border-border p-3">
                <p className="text-xs text-muted-foreground">Copy the windows for {AVAILABILITY_WEEKDAYS.find((x) => x.dow === selectedDow)?.label}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={copyToAllOtherDays}
                    disabled={copyBusy}
                    data-testid="availability-copy-to-all"
                  >
                    {copyBusy ? 'Copying…' : 'Copy to all other days'}
                  </Button>
                  <span className="text-xs text-muted-foreground">or to:</span>
                  {AVAILABILITY_WEEKDAYS.filter((x) => x.dow !== selectedDow).map((d) => (
                    <Button
                      key={d.dow}
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => void copyToTargets([d.dow])}
                      disabled={copyBusy}
                      data-testid={`availability-copy-to-day-${d.dow}`}
                    >
                      {d.short}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {loading && (
              <p className="text-sm text-muted-foreground flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                Loading windows…
              </p>
            )}

            {!loading && windowsForDay.length === 0 && (
              <EmptyState
                title="No windows for this day"
                description="Add a window to offer bookable slots on this weekday."
              />
            )}

            {!loading && windowsForDay.length > 0 && (
              <ul className="space-y-2" aria-label="Availability windows for selected day">
                {windowsForDay.map((w) => (
                  <li
                    key={String(w.id)}
                    data-testid={`availability-window-row-${w.id}`}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2 shadow-sm transition-shadow hover:shadow-md"
                  >
                    <div>
                      <p className="text-sm font-medium">
                        {formatTimeShort(w.start_time)} – {formatTimeShort(w.end_time)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {w.slot_duration} min slots
                        {w.id.toString().startsWith('temp-') ? ' · saving…' : null}
                      </p>
                    </div>
                    {canManageOwnSchedule && !String(w.id).startsWith('temp-') && (
                      <div className="flex items-center gap-1">
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          onClick={() => openEdit(w)}
                          data-testid={`availability-edit-${w.id}`}
                          title="Edit"
                        >
                          <Pencil className="h-4 w-4" aria-hidden />
                        </Button>
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 text-destructive hover:text-destructive"
                          onClick={() => void onDelete(w)}
                          data-testid={`availability-delete-${w.id}`}
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" aria-hidden />
                        </Button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {selfDoctor && doctorId && (
        <DoctorTimeOffPanel
          doctorId={doctorId}
          readOnly={isReadOnly}
          onAfterChange={() => {
            if (doctorId) afterMutation(doctorId);
            void refetchWorkspace();
          }}
        />
      )}

      {canManageOwnSchedule && (
        <AvailabilityWindowModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          mode={modalMode}
          dayOfWeek={selectedDow}
          initial={modalMode === 'edit' ? editing : null}
          allWindows={nonTemp(windows)}
          onSave={onModalSave}
        />
      )}
    </div>
  );
}
