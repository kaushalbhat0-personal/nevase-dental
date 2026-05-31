import { BOOKING_DATA_REFRESH_EVENT } from '../constants/booking';

/**
 * After a successful booking, notify data hooks to refetch (single source of truth — no duplicate API warm-up here).
 */
export async function runAfterBookingSuccess(): Promise<void> {
  console.log('[BOOKING_SUCCESS] dispatching refresh event');
  window.dispatchEvent(new Event(BOOKING_DATA_REFRESH_EVENT));
}
