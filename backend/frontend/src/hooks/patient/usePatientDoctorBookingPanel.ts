import { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import axios from 'axios';
import {
  appointmentsApi,
  doctorsApi,
  invalidateDoctorSlotsClientCache,
  shouldSyncSlotsCrossTab,
  SLOTS_CROSS_TAB_BROADCAST,
  type DoctorSlot,
} from '../../services';
import { runAfterBookingSuccess } from '../../utils/bookingDataRefresh';
import { DISPLAY_TIMEZONE } from '../../constants/time';
import {
  dedupeDoctorSlots,
  isSlotInstantInTheFuture,
  slotKey,
  ymdNowInIana,
} from '../../utils/doctorSchedule';
import { useModalFocusTrap } from '../useModalFocusTrap';
import type { Appointment, Doctor } from '../../types';
import { findNextAvailableSlotKey } from '../../utils/slotTimeGroups';

export function usePatientDoctorBookingPanel(
  patientId: string | null,
  bookingDoctor: Doctor | null,
  onExit: () => void,
  onBooked: (a: Appointment) => void,
  /** Doctor IANA zone for "today" / default date (defaults to India display zone). */
  scheduleTimeZone?: string | null
) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [bookDate, setBookDateState] = useState('');
  const [slots, setSlots] = useState<DoctorSlot[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(true);
  const [slotsError, setSlotsError] = useState<string | null>(null);
  const [selectedSlotStart, setSelectedSlotStartState] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [bookingIdempotencyKey, setBookingIdempotencyKey] = useState('');

  const dialogRef = useRef<HTMLDivElement>(null);
  const abortCreateRef = useRef<AbortController | null>(null);
  const slotsRequestIdRef = useRef(0);
  const slotsFetchAbortRef = useRef<AbortController | null>(null);
  /** Once the user changes date or taps a slot, stop auto-selecting the first opening. */
  const scheduleInteractedRef = useRef(false);

  const scheduleTz = (scheduleTimeZone && scheduleTimeZone.trim()) || DISPLAY_TIMEZONE;
  const doctorTodayYmd = ymdNowInIana(scheduleTz);
  const nextAvailableKey = findNextAvailableSlotKey(slots, bookDate, doctorTodayYmd);

  useModalFocusTrap(dialogRef, confirmOpen && Boolean(bookingDoctor));

  const slotOk = selectedSlotStart != null && isSlotInstantInTheFuture(selectedSlotStart);
  const bookingReady = Boolean(patientId) && Boolean(bookDate) && Boolean(bookingIdempotencyKey) && slotOk;
  const stickyBookEnabled =
    Boolean(patientId) && slotOk && !slotsLoading && !submitting && !slotsError && slots.length > 0;
  const inTimeStep = Boolean(bookingDoctor) && !confirmOpen;

  const exitBookingFlow = useCallback(() => {
    abortCreateRef.current?.abort();
    abortCreateRef.current = null;
    slotsFetchAbortRef.current?.abort();
    slotsFetchAbortRef.current = null;
    setConfirmOpen(false);
    scheduleInteractedRef.current = false;
    setBookDateState('');
    setSlots([]);
    setSlotsLoading(false);
    setSlotsError(null);
    setSelectedSlotStartState(null);
    setSubmitting(false);
    setBookingIdempotencyKey('');
    onExit();
  }, [onExit]);

  const closeConfirmOnly = useCallback(() => {
    if (submitting) return;
    setConfirmOpen(false);
  }, [submitting]);

  useEffect(() => {
    return () => {
      abortCreateRef.current?.abort();
      abortCreateRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!bookingDoctor) {
      setConfirmOpen(false);
      scheduleInteractedRef.current = false;
      setBookDateState('');
      setSlots([]);
      setSlotsLoading(false);
      setSlotsError(null);
      setSelectedSlotStartState(null);
      setSubmitting(false);
      setBookingIdempotencyKey('');
      return;
    }
    scheduleInteractedRef.current = false;
    setBookingIdempotencyKey(crypto.randomUUID());
    setBookDateState(ymdNowInIana(scheduleTz));
    setSlots([]);
    setSlotsLoading(true);
    setSlotsError(null);
    setSelectedSlotStartState(null);
    setConfirmOpen(false);
  }, [bookingDoctor?.id, scheduleTz]);

  useEffect(() => {
    if (!confirmOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) {
        e.preventDefault();
        closeConfirmOnly();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [confirmOpen, submitting, closeConfirmOnly]);

  const fetchSlots = useCallback(
    async (mode: 'initial' | 'poll') => {
      if (!bookingDoctor || !bookDate || !patientId) return;
      const reqId = ++slotsRequestIdRef.current;
      let signal: AbortSignal | undefined;
      if (mode === 'initial') {
        slotsFetchAbortRef.current?.abort();
        const ac = new AbortController();
        slotsFetchAbortRef.current = ac;
        signal = ac.signal;
        setSlots([]);
        setSlotsLoading(true);
        setSlotsError(null);
      }
      try {
        const list = await doctorsApi.getSlots(String(bookingDoctor.id), bookDate, {
          signal,
          skipCache: true,
        });
        if (reqId !== slotsRequestIdRef.current) return;
        const deduped = dedupeDoctorSlots(list).filter((s) => isSlotInstantInTheFuture(s.start));
        setSlots(deduped);
        setSelectedSlotStartState((cur) => {
          const stillValid =
            cur != null &&
            deduped.some(
              (s) =>
                s.available &&
                isSlotInstantInTheFuture(s.start) &&
                slotKey(s.start) === slotKey(cur)
            );
          if (stillValid) return cur;
          if (scheduleInteractedRef.current) return null;
          const first = deduped.find((s) => s.available && isSlotInstantInTheFuture(s.start));
          return first ? first.start : null;
        });
        if (mode === 'poll') setSlotsError(null);
      } catch (e) {
        if (axios.isCancel(e)) return;
        if (signal?.aborted) return;
        if (reqId !== slotsRequestIdRef.current) return;
        if (mode === 'initial') {
          setSlotsError('Unable to load available slots.');
          setSlots([]);
        }
      } finally {
        if (mode === 'initial' && (!signal || !signal.aborted) && reqId === slotsRequestIdRef.current) {
          setSlotsLoading(false);
        }
      }
    },
    [bookingDoctor?.id, bookDate, patientId]
  );

  const refetchSlots = useCallback(() => {
    void fetchSlots('poll');
  }, [fetchSlots]);

  useEffect(() => {
    if (!bookingDoctor?.id || !bookDate || !patientId) {
      setSlots([]);
      setSlotsLoading(false);
      setSlotsError(null);
      setSelectedSlotStartState(null);
      return;
    }
    void fetchSlots('initial');
    return () => slotsFetchAbortRef.current?.abort();
  }, [bookingDoctor?.id, bookDate, patientId, fetchSlots]);

  useEffect(() => {
    if (!confirmOpen || !bookingDoctor?.id || !bookDate || !patientId) return;
    refetchSlots();
  }, [confirmOpen, bookingDoctor?.id, bookDate, patientId, refetchSlots]);

  useEffect(() => {
    if (!bookingDoctor || !bookDate || !patientId) return;

    let intervalId: ReturnType<typeof window.setInterval> | undefined;
    const clearPoll = () => {
      if (intervalId !== undefined) {
        window.clearInterval(intervalId);
        intervalId = undefined;
      }
    };
    const startPollIfVisible = () => {
      clearPoll();
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return;
      intervalId = window.setInterval(() => {
        refetchSlots();
      }, 30_000);
    };
    startPollIfVisible();
    const onVisibility = () => {
      if (typeof document === 'undefined') return;
      if (document.visibilityState === 'visible') {
        refetchSlots();
        startPollIfVisible();
      } else {
        clearPoll();
      }
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      clearPoll();
    };
  }, [bookingDoctor, bookDate, patientId, refetchSlots]);

  useEffect(() => {
    if (!bookingDoctor) return;
    const onOtherTab = () => {
      if (!shouldSyncSlotsCrossTab()) return;
      refetchSlots();
    };
    window.addEventListener(SLOTS_CROSS_TAB_BROADCAST, onOtherTab);
    return () => window.removeEventListener(SLOTS_CROSS_TAB_BROADCAST, onOtherTab);
  }, [bookingDoctor, refetchSlots]);

  useEffect(() => {
    if (!bookingDoctor || confirmOpen) return;
    const id = requestAnimationFrame(() => {
      document.getElementById('book-date')?.focus();
    });
    return () => cancelAnimationFrame(id);
  }, [bookingDoctor?.id, confirmOpen]);

  const confirmBooking = async () => {
    if (!bookingDoctor || !patientId) {
      toast.error('Unable to resolve patient profile. Use Retry or contact the clinic.');
      return;
    }
    if (!bookingIdempotencyKey) {
      toast.error('Please reopen the booking dialog.');
      return;
    }
    if (!bookDate || !selectedSlotStart) {
      toast.error('Please select a date and time slot.');
      return;
    }
    if (!isSlotInstantInTheFuture(selectedSlotStart)) {
      toast.error('Choose a valid time in the future.');
      return;
    }
    if (submitting) return;

    abortCreateRef.current?.abort();
    const ac = new AbortController();
    abortCreateRef.current = ac;
    setSubmitting(true);
    try {
      const { appointment: created, idempotentReplay } = await appointmentsApi.create(
        {
          doctor_id: String(bookingDoctor.id),
          patient_id: patientId,
          appointment_time: selectedSlotStart,
        },
        { idempotencyKey: bookingIdempotencyKey, signal: ac.signal }
      );
      await runAfterBookingSuccess();
      invalidateDoctorSlotsClientCache(String(bookingDoctor.id), bookDate);
      onBooked(created);
      toast.success(
        idempotentReplay ? 'Appointment already booked successfully.' : 'Appointment booked.'
      );
    } catch (err) {
      if (axios.isCancel(err)) return;
      const detail =
        axios.isAxiosError(err) && err.response?.data && typeof err.response.data === 'object'
          ? String((err.response.data as { detail?: unknown }).detail ?? '')
          : '';
      if (detail.toLowerCase().includes('already have an appointment at this time')) {
        toast.error('You already have another visit booked at this time. Pick a different time.');
      } else if (detail.includes('Slot already booked')) {
        toast.error('That slot was just taken. Choose another time.');
        setSelectedSlotStartState(null);
        if (bookDate && bookingDoctor) {
          invalidateDoctorSlotsClientCache(String(bookingDoctor.id), bookDate);
          setSlotsLoading(true);
          try {
            const list = await doctorsApi.getSlots(String(bookingDoctor.id), bookDate, { skipCache: true });
            const deduped = dedupeDoctorSlots(list).filter((s) => isSlotInstantInTheFuture(s.start));
            setSlots(deduped);
            if (!scheduleInteractedRef.current) {
              const first = deduped.find((s) => s.available && isSlotInstantInTheFuture(s.start));
              setSelectedSlotStartState(first ? first.start : null);
            }
          } catch {
            setSlotsError('Unable to load available slots.');
          } finally {
            setSlotsLoading(false);
          }
        }
      } else {
        toast.error('Booking failed. Try another time or contact the clinic.', { duration: 5000 });
      }
    } finally {
      if (abortCreateRef.current === ac) {
        abortCreateRef.current = null;
      }
      setSubmitting(false);
    }
  };

  const setBookDate = useCallback((d: string) => {
    scheduleInteractedRef.current = true;
    setBookDateState(d);
    setSelectedSlotStartState(null);
  }, []);

  const pickSlot = useCallback((key: string | null) => {
    if (key !== null) scheduleInteractedRef.current = true;
    setSelectedSlotStartState(key);
  }, []);

  return {
    confirmOpen,
    setConfirmOpen,
    bookDate,
    setBookDate,
    slots,
    slotsLoading,
    slotsError,
    selectedSlotStart,
    setSelectedSlotStart: pickSlot,
    submitting,
    bookingReady,
    slotOk,
    stickyBookEnabled,
    inTimeStep,
    dialogRef,
    doctorTodayYmd,
    nextAvailableKey,
    exitBookingFlow,
    closeConfirmOnly,
    confirmBooking,
  };
}
