import { useState } from 'react';
import { CheckCircle, XCircle, UserCheck, UserX, Clock, ArrowRight } from 'lucide-react';
import { frontDeskApi, nurseWorkflowApi } from '../../services/clinicQueue';
import type { Appointment } from '../../types';

interface AppointmentStatusActionsProps {
  appointment: Appointment;
  onStatusChange: (updated: Appointment) => void;
  /** Disable all actions (e.g., while loading) */
  disabled?: boolean;
}

/**
 * Large-touch-target action buttons for receptionist workflow.
 * Shows available actions based on current appointment status.
 */
export function AppointmentStatusActions({
  appointment,
  onStatusChange,
  disabled = false,
}: AppointmentStatusActionsProps) {
  const [loading, setLoading] = useState<string | null>(null);

  const handleAction = async (
    action: string,
    fn: () => Promise<Appointment>
  ) => {
    if (disabled || loading) return;
    setLoading(action);
    try {
      const updated = await fn();
      onStatusChange(updated);
    } catch (err) {
      console.error(`[AppointmentStatusActions] ${action} failed:`, err);
    } finally {
      setLoading(null);
    }
  };

  const status = appointment.status;

  return (
    <div className="flex flex-wrap gap-2">
      {/* Scheduled / Confirmed → Arrive */}
      {(status === 'scheduled' || status === 'confirmed') && (
        <ActionButton
          icon={<UserCheck className="w-5 h-5" />}
          label="Mark Arrived"
          loading={loading === 'arrive'}
          disabled={disabled}
          onClick={() =>
            handleAction('arrive', () =>
              frontDeskApi.markArrived(String(appointment.id))
            )
          }
          variant="primary"
        />
      )}

      {/* Arrived → Check In */}
      {status === 'arrived' && (
        <>
          <ActionButton
            icon={<CheckCircle className="w-5 h-5" />}
            label="Check In"
            loading={loading === 'checkin'}
            disabled={disabled}
            onClick={() =>
              handleAction('checkin', () =>
                frontDeskApi.checkIn(String(appointment.id))
              )
            }
            variant="primary"
          />
          <ActionButton
            icon={<UserX className="w-5 h-5" />}
            label="No Show"
            loading={loading === 'noshow'}
            disabled={disabled}
            onClick={() =>
              handleAction('noshow', () =>
                frontDeskApi.markNoShow(String(appointment.id))
              )
            }
            variant="danger"
          />
        </>
      )}

      {/* Checked In → Vitals (nurse action) */}
      {status === 'checked_in' && (
        <ActionButton
          icon={<ActivityIcon className="w-5 h-5" />}
          label="Start Vitals"
          loading={loading === 'vitals'}
          disabled={disabled}
          onClick={() =>
            handleAction('vitals', () =>
              nurseWorkflowApi.markVitalsCompleted(String(appointment.id))
            )
          }
          variant="primary"
        />
      )}

      {/* Vitals Completed → Send to Doctor */}
      {status === 'vitals_completed' && (
        <ActionButton
          icon={<ArrowRight className="w-5 h-5" />}
          label="Send to Doctor"
          loading={loading === 'sendtoodoctor'}
          disabled={disabled}
          onClick={() =>
            handleAction('sendtoodoctor', () =>
              nurseWorkflowApi.sendToDoctor(String(appointment.id))
            )
          }
          variant="primary"
        />
      )}

      {/* Cancel (available from multiple states) */}
      {['scheduled', 'confirmed', 'arrived', 'checked_in', 'vitals_completed', 'waiting_for_doctor'].includes(
        status
      ) && (
        <ActionButton
          icon={<XCircle className="w-5 h-5" />}
          label="Cancel"
          loading={loading === 'cancel'}
          disabled={disabled}
          onClick={() =>
            handleAction('cancel', () =>
              frontDeskApi.cancel(String(appointment.id))
            )
          }
          variant="danger"
        />
      )}

      {/* Reschedule (available from non-terminal states) */}
      {!['completed', 'cancelled', 'no_show'].includes(status) && (
        <ActionButton
          icon={<Clock className="w-5 h-5" />}
          label="Reschedule"
          loading={loading === 'reschedule'}
          disabled={disabled}
          onClick={() => {
            // Reschedule requires a date picker — for now, prompt
            const newTime = prompt('Enter new appointment time (ISO 8601):');
            if (newTime) {
              handleAction('reschedule', () =>
                frontDeskApi.reschedule(String(appointment.id), { new_time: newTime })
              );
            }
          }}
          variant="secondary"
        />
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Internal components
// ──────────────────────────────────────────────────────────────────────────────

interface ActionButtonProps {
  icon: React.ReactNode;
  label: string;
  loading?: boolean;
  disabled?: boolean;
  onClick: () => void;
  variant: 'primary' | 'secondary' | 'danger';
}

function ActionButton({
  icon,
  label,
  loading = false,
  disabled = false,
  onClick,
  variant,
}: ActionButtonProps) {
  const baseClasses =
    'inline-flex items-center gap-2 px-4 py-3 rounded-lg font-medium text-sm transition-all min-h-[48px] min-w-[120px] justify-center';
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 active:bg-gray-300',
    danger: 'bg-red-50 text-red-700 hover:bg-red-100 active:bg-red-200 border border-red-200',
  };

  return (
    <button
      type="button"
      className={`${baseClasses} ${variantClasses[variant]} ${
        loading || disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
      }`}
      onClick={onClick}
      disabled={loading || disabled}
    >
      {loading ? (
        <span className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        icon
      )}
      {loading ? 'Processing...' : label}
    </button>
  );
}

/** Simple inline SVG for activity icon (avoids importing from lucide if not available) */
function ActivityIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}
