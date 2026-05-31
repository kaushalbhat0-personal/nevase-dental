import { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useModalFocusTrap } from '../../../hooks';
import type { DoctorAvailabilityWindow } from '../../../types';
import {
  AVAILABILITY_WEEKDAYS,
  formatTimeShort,
  timeToMinutes,
  toApiTime,
  windowOverlapsExisting,
} from '../../../utils/availabilityWindows';

export interface AvailabilityWindowModalProps {
  open: boolean;
  onClose: () => void;
  mode: 'create' | 'edit';
  /** Server day index (Mon=0) when creating */
  dayOfWeek: number;
  initial?: DoctorAvailabilityWindow | null;
  allWindows: DoctorAvailabilityWindow[];
  onSave: (payload: {
    day_of_week: number;
    start_time: string;
    end_time: string;
    slot_duration: number;
  }) => Promise<void>;
}

function parseDetail(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: unknown } } }).response;
    const d = r?.data?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) {
      return d
        .map((x) => {
          if (typeof x === 'object' && x && 'msg' in x) return String((x as { msg: string }).msg);
          return '';
        })
        .filter(Boolean)
        .join(' ') || 'Validation failed. Check your input.';
    }
  }
  if (err instanceof Error) return err.message;
  return 'Something went wrong. Try again.';
}

export function AvailabilityWindowModal({
  open,
  onClose,
  mode,
  dayOfWeek,
  initial,
  allWindows,
  onSave,
}: AvailabilityWindowModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [dow, setDow] = useState(dayOfWeek);
  const [start, setStart] = useState('09:00');
  const [end, setEnd] = useState('13:00');
  const [slotMins, setSlotMins] = useState(30);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useModalFocusTrap(dialogRef, open);

  useEffect(() => {
    if (!open) return;
    setFormError(null);
    if (mode === 'edit' && initial) {
      setDow(initial.day_of_week);
      setStart(formatTimeShort(initial.start_time));
      setEnd(formatTimeShort(initial.end_time));
      setSlotMins(initial.slot_duration);
    } else {
      setDow(dayOfWeek);
      setStart('09:00');
      setEnd('13:00');
      setSlotMins(30);
    }
  }, [open, mode, dayOfWeek, initial]);

  const close = useCallback(() => {
    if (!submitting) onClose();
  }, [onClose, submitting]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) {
        e.preventDefault();
        close();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, submitting, close]);

  const submit = async () => {
    setFormError(null);
    const st = toApiTime(start);
    const en = toApiTime(end);
    if (timeToMinutes(st) >= timeToMinutes(en)) {
      setFormError('End time must be after start time.');
      return;
    }
    if (!Number.isFinite(slotMins) || slotMins < 1) {
      setFormError('Slot duration must be at least 1 minute.');
      return;
    }
    const spanMin = timeToMinutes(en) - timeToMinutes(st);
    if (spanMin < slotMins) {
      setFormError('Window is too small for the slot length (at least one full slot is required).');
      return;
    }
    if (
      windowOverlapsExisting(dow, st, en, allWindows, mode === 'edit' && initial ? String(initial.id) : undefined)
    ) {
      setFormError('This range overlaps another window on the same day.');
      return;
    }
    setSubmitting(true);
    try {
      await onSave({
        day_of_week: dow,
        start_time: st,
        end_time: en,
        slot_duration: Math.floor(slotMins),
      });
      onClose();
    } catch (e) {
      setFormError(parseDetail(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onClick={() => !submitting && close()}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="avail-modal-title"
        data-testid="availability-modal"
        className="w-full max-w-md rounded-xl border border-border bg-card text-foreground shadow-lg outline-none p-0"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-border px-4 py-3">
          <h2 id="avail-modal-title" className="text-lg font-semibold">
            {mode === 'create' ? 'Add availability window' : 'Edit availability window'}
          </h2>
          <p className="text-sm text-muted-foreground mt-0.5">Define start, end, and slot length for online booking.</p>
        </div>
        <div className="space-y-3 px-4 py-4">
          {formError && (
            <p className="text-sm text-destructive rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2" role="alert">
              {formError}
            </p>
          )}
          <div>
            <label htmlFor="avail-dow" className="text-xs font-medium text-muted-foreground">
              Day
            </label>
            <select
              id="avail-dow"
              className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground"
              value={dow}
              onChange={(e) => setDow(parseInt(e.target.value, 10))}
              disabled={submitting}
            >
              {AVAILABILITY_WEEKDAYS.map((d) => (
                <option key={d.dow} value={d.dow}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="avail-start" className="text-xs font-medium text-muted-foreground">
                Start
              </label>
              <Input
                id="avail-start"
                type="time"
                className="mt-1"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div>
              <label htmlFor="avail-end" className="text-xs font-medium text-muted-foreground">
                End
              </label>
              <Input
                id="avail-end"
                type="time"
                className="mt-1"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                disabled={submitting}
              />
            </div>
          </div>
          <div>
            <label htmlFor="avail-slot" className="text-xs font-medium text-muted-foreground">
              Slot length (minutes)
            </label>
            <Input
              id="avail-slot"
              type="number"
              min={1}
              className="mt-1"
              value={slotMins}
              onChange={(e) => setSlotMins(parseInt(e.target.value, 10))}
              disabled={submitting}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-border px-4 py-3">
          <Button type="button" variant="outline" onClick={close} disabled={submitting}>
            Cancel
          </Button>
          <Button type="button" onClick={() => void submit()} disabled={submitting} className="gap-2">
            {submitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            {submitting ? 'Saving…' : mode === 'create' ? 'Add window' : 'Save changes'}
          </Button>
        </div>
      </div>
    </div>
  );
}
