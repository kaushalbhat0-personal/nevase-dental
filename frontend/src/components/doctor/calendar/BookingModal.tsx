import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useModalFocusTrap } from '../../../hooks';
import { appointmentsApi } from '../../../services';
import { runAfterBookingSuccess } from '../../../utils/bookingDataRefresh';
import type { Patient } from '../../../types';
import { cn } from '@/lib/utils';
import { PatientSearchSelect } from '../PatientSearchSelect';
import { DISPLAY_TIMEZONE } from '../../../constants/time';
import { formatAppointmentDateTimeWithZoneLabel } from '../../../utils/doctorSchedule';

export interface BookingModalProps {
  open: boolean;
  onClose: () => void;
  /** ISO start from selected slot */
  slotStart: string | null;
  doctorId: string;
  patients: Patient[];
  /** When set, the patient field defaults to this id if present in the list. */
  defaultPatientId?: string | null;
  onSuccess: (bookedSlotStart?: string) => void | Promise<void>;
  /** @deprecated Unused; subtitles always use Asia/Kolkata (IST). */
  timeZone: string;
  onSubmittingChange?: (submitting: boolean) => void;
}

export function BookingModal({
  open,
  onClose,
  slotStart,
  doctorId,
  patients,
  defaultPatientId = null,
  onSuccess,
  timeZone: _timeZone,
  onSubmittingChange,
}: BookingModalProps) {
  const [patientId, setPatientId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const dialogRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const setSubmittingBoth = (v: boolean) => {
    setSubmitting(v);
    onSubmittingChange?.(v);
  };

  useModalFocusTrap(dialogRef, open && Boolean(slotStart));

  useEffect(() => {
    if (open) {
      setIdempotencyKey(crypto.randomUUID());
      const def = defaultPatientId?.trim() ?? '';
      const match = def && patients.some((p) => String(p.id) === def);
      setPatientId(match ? def : '');
    }
  }, [open, slotStart, defaultPatientId, patients]);

  const close = useCallback(() => {
    if (submitting) return;
    abortRef.current?.abort();
    onClose();
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

  const confirm = async () => {
    if (!slotStart || !patientId || !idempotencyKey) {
      toast.error('Select a patient to confirm.');
      return;
    }
    if (submitting) return;
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setSubmittingBoth(true);
    try {
      const { idempotentReplay } = await appointmentsApi.create(
        {
          doctor_id: doctorId,
          patient_id: patientId,
          appointment_time: slotStart,
        },
        { idempotencyKey, signal: ac.signal }
      );
      await runAfterBookingSuccess();
      await new Promise((r) => setTimeout(r, 100));
      await Promise.resolve(onSuccess(idempotentReplay ? undefined : slotStart));
      toast.success(
        idempotentReplay
          ? 'Appointment already booked successfully.'
          : 'Appointment booked successfully'
      );
      close();
    } catch (err) {
      if (axios.isCancel(err)) return;
      const detail =
        axios.isAxiosError(err) && err.response?.data && typeof err.response.data === 'object'
          ? String((err.response.data as { detail?: unknown }).detail ?? '')
          : '';
      if (detail.includes('Slot already booked')) {
        toast.error('That slot was just taken. Pick another time.');
        onSuccess(slotStart);
        close();
        return;
      }
      toast.error(detail || 'Could not create appointment', { duration: 5000 });
    } finally {
      if (abortRef.current === ac) abortRef.current = null;
      setSubmittingBoth(false);
    }
  };

  if (!open || !slotStart) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onClick={() => close()}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="day-cal-book-title"
        aria-describedby="day-cal-book-desc"
        aria-busy={submitting}
        className={cn(
          'w-full max-w-md max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-card text-foreground shadow-lg outline-none'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-border px-4 py-3">
          <h2 id="day-cal-book-title" className="text-lg font-semibold">
            Book appointment
          </h2>
          <p id="day-cal-book-desc" className="text-sm text-muted-foreground mt-0.5">
            {formatAppointmentDateTimeWithZoneLabel(slotStart, DISPLAY_TIMEZONE)}. Choose a patient, then confirm.
          </p>
        </div>
        <div className="space-y-4 px-4 py-4">
          <div>
            <label htmlFor="day-cal-patient" className="text-xs font-medium text-muted-foreground">
              Patient
            </label>
            <PatientSearchSelect
              id="day-cal-patient"
              patients={patients}
              value={patientId}
              onChange={setPatientId}
              disabled={submitting}
            />
          </div>
        </div>
        <div className="flex flex-wrap justify-end gap-2 border-t border-border px-4 py-3">
          <Button type="button" variant="outline" onClick={close} disabled={submitting}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => void confirm()}
            disabled={submitting || !patientId}
          >
            {submitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                Saving…
              </>
            ) : (
              'Confirm'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
