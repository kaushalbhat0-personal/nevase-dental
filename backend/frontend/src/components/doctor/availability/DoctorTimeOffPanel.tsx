import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { CalendarOff, Loader2, Pencil, Plus, Trash2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useModalFocusTrap } from '../../../hooks';
import { doctorsApi, invalidateDoctorSlotsClientCache } from '../../../services';
import { formatTimeShort, toApiTime } from '../../../utils/availabilityWindows';
import type { DoctorTimeOff } from '../../../types';

function apiErr(e: unknown): string {
  if (axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object') {
    const d = (e.response.data as { detail?: unknown }).detail;
    if (typeof d === 'string') return d;
  }
  return 'Request failed. Try again.';
}

function offLabel(t: DoctorTimeOff): string {
  if (t.start_time == null && t.end_time == null) return 'Full day — doctor unavailable';
  if (t.start_time && t.end_time) {
    return `Unavailable ${formatTimeShort(t.start_time)} – ${formatTimeShort(t.end_time)}`;
  }
  return 'Time off';
}

export function DoctorTimeOffPanel({
  doctorId,
  onAfterChange,
  readOnly,
}: {
  doctorId: string;
  onAfterChange: () => void;
  readOnly: boolean;
}) {
  const [rows, setRows] = useState<DoctorTimeOff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<DoctorTimeOff | null>(null);
  const [offDate, setOffDate] = useState('');
  const [fullDay, setFullDay] = useState(true);
  const [start, setStart] = useState('12:00');
  const [end, setEnd] = useState('15:00');
  const [saving, setSaving] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  useModalFocusTrap(dialogRef, modalOpen);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const list = await doctorsApi.getTimeOff(doctorId);
      setRows(
        list.slice().sort((a, b) => a.off_date.localeCompare(b.off_date) || String(a.id).localeCompare(String(b.id)))
      );
    } catch (e) {
      setError(apiErr(e));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [doctorId]);

  useEffect(() => {
    void load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setOffDate('');
    setFullDay(true);
    setStart('12:00');
    setEnd('15:00');
    setModalOpen(true);
  };

  const openEdit = (t: DoctorTimeOff) => {
    setEditing(t);
    setOffDate(t.off_date);
    const fd = t.start_time == null && t.end_time == null;
    setFullDay(fd);
    if (t.start_time) setStart(formatTimeShort(t.start_time));
    if (t.end_time) setEnd(formatTimeShort(t.end_time));
    setModalOpen(true);
  };

  const afterMut = () => {
    invalidateDoctorSlotsClientCache(doctorId);
    onAfterChange();
    void load();
  };

  const save = async () => {
    if (!offDate) {
      toast.error('Choose a date');
      return;
    }
    if (!fullDay) {
      const a = toApiTime(start);
      const b = toApiTime(end);
      if (a >= b) {
        toast.error('End time must be after start');
        return;
      }
    }
    setSaving(true);
    try {
      if (editing) {
        await doctorsApi.updateTimeOff(doctorId, String(editing.id), {
          off_date: offDate,
          start_time: fullDay ? null : toApiTime(start),
          end_time: fullDay ? null : toApiTime(end),
        });
      } else {
        await doctorsApi.createTimeOff(doctorId, {
          off_date: offDate,
          start_time: fullDay ? null : toApiTime(start),
          end_time: fullDay ? null : toApiTime(end),
        });
      }
      toast.success(editing ? 'Time off updated' : 'Time off added');
      setModalOpen(false);
      afterMut();
    } catch (e) {
      toast.error(apiErr(e), { duration: 5000 });
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (t: DoctorTimeOff) => {
    if (readOnly) return;
    if (!window.confirm(`Remove time off on ${t.off_date}?`)) return;
    try {
      await doctorsApi.deleteTimeOff(doctorId, String(t.id));
      toast.success('Time off removed');
      afterMut();
    } catch (e) {
      toast.error(apiErr(e), { duration: 5000 });
    }
  };

  return (
    <Card data-testid="doctor-time-off-section">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2 space-y-0">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <CalendarOff className="h-4 w-4" aria-hidden />
            Time off
          </CardTitle>
          <CardDescription>
            Block whole days or hours when you are not seeing patients. All times in IST.
          </CardDescription>
        </div>
        {!readOnly && (
          <Button type="button" size="sm" className="gap-1" onClick={openCreate} data-testid="time-off-add">
            <Plus className="h-4 w-4" aria-hidden />
            Add
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {readOnly && (
          <p className="text-sm text-muted-foreground">Organization-managed: time off is not editable here.</p>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {loading && (
          <p className="text-sm text-muted-foreground flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Loading time off…
          </p>
        )}
        {!loading && !error && rows.length === 0 && (
          <p className="text-sm text-muted-foreground">No blocked dates. Add full or partial time off as needed.</p>
        )}
        {!loading && rows.length > 0 && (
          <ul className="space-y-2" aria-label="Time off list">
            {rows.map((t) => (
              <li
                key={String(t.id)}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2"
                data-testid={`time-off-row-${t.id}`}
              >
                <div>
                  <p className="text-sm font-medium tabular-nums">{t.off_date}</p>
                  <p className="text-xs text-muted-foreground">{offLabel(t)}</p>
                </div>
                {!readOnly && (
                  <div className="flex items-center gap-1">
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() => openEdit(t)}
                      data-testid={`time-off-edit-${t.id}`}
                      title="Edit"
                    >
                      <Pencil className="h-4 w-4" aria-hidden />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                      onClick={() => void onDelete(t)}
                      data-testid={`time-off-delete-${t.id}`}
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

      {modalOpen && !readOnly && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="presentation"
          onClick={() => !saving && setModalOpen(false)}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            data-testid="time-off-modal"
            className="w-full max-w-md rounded-xl border border-border bg-card text-foreground shadow-lg outline-none p-0"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-border px-4 py-3">
              <h2 className="text-lg font-semibold">{editing ? 'Edit time off' : 'Add time off'}</h2>
            </div>
            <div className="space-y-3 px-4 py-4">
              <div>
                <label htmlFor="t-off-date" className="text-xs font-medium text-muted-foreground">
                  Date
                </label>
                <Input
                  id="t-off-date"
                  type="date"
                  className="mt-1"
                  value={offDate}
                  onChange={(e) => setOffDate(e.target.value)}
                  disabled={saving}
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={fullDay}
                  onChange={(e) => setFullDay(e.target.checked)}
                  disabled={saving}
                  data-testid="time-off-full-day"
                />
                Full day (unavailable)
              </label>
              {!fullDay && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="t-off-st" className="text-xs font-medium text-muted-foreground">
                      Unavailable from
                    </label>
                    <Input
                      id="t-off-st"
                      type="time"
                      className="mt-1"
                      value={start}
                      onChange={(e) => setStart(e.target.value)}
                      disabled={saving}
                    />
                  </div>
                  <div>
                    <label htmlFor="t-off-en" className="text-xs font-medium text-muted-foreground">
                      to
                    </label>
                    <Input
                      id="t-off-en"
                      type="time"
                      className="mt-1"
                      value={end}
                      onChange={(e) => setEnd(e.target.value)}
                      disabled={saving}
                    />
                  </div>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 border-t border-border px-4 py-3">
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)} disabled={saving}>
                Cancel
              </Button>
              <Button type="button" onClick={() => void save()} disabled={saving} className="gap-2" data-testid="time-off-save">
                {saving && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
                Save
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
