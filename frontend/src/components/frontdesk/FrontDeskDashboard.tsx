/**
 * FrontDeskDashboard — enhanced receptionist console.
 *
 * Tablet-first UX improvements:
 * - Sticky action areas
 * - Larger operational chips
 * - Queue delay indicators
 * - Touch-friendly controls
 * - Better queue visualization
 */
import { useState, useEffect, useCallback } from 'react';
import { Calendar, Plus, Search, Clock, Users, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { QueueManagementPanel } from './QueueManagementPanel';
import { AppointmentStatusActions } from './AppointmentStatusActions';
import { appointmentsApi } from '../../services/appointments';
import { frontDeskApi } from '../../services/clinicQueue';
import type { Appointment } from '../../types';

interface FrontDeskDashboardProps {
  /** Auto-refresh interval in ms (default: 30000 = 30s) */
  refreshInterval?: number;
}

/**
 * Front desk dashboard — the main receptionist view.
 *
 * Layout:
 * - Sticky header with search + walk-in
 * - Left: Today's appointments list with status actions
 * - Right: Queue management panel
 *
 * Designed for tablet-friendly use with large touch targets.
 */
export function FrontDeskDashboard({
  refreshInterval = 30000,
}: FrontDeskDashboardProps) {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [selectedAppointment, setSelectedAppointment] =
    useState<Appointment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showWalkInModal, setShowWalkInModal] = useState(false);

  const fetchAppointments = useCallback(async () => {
    try {
      setError(null);
      const data = await appointmentsApi.getAll({
        limit: 50,
        type: 'upcoming',
      });
      setAppointments(data);
    } catch (err) {
      console.error('[FrontDeskDashboard] Fetch error:', err);
      setError('Failed to load appointments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAppointments();
    const interval = setInterval(fetchAppointments, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchAppointments, refreshInterval]);

  const handleStatusChange = (updated: Appointment) => {
    setAppointments((prev) =>
      prev.map((a) => (a.id === updated.id ? updated : a))
    );
    setSelectedAppointment(updated);
  };

  const filteredAppointments = appointments.filter((a) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.patient?.name?.toLowerCase().includes(q) ||
      a.doctor?.name?.toLowerCase().includes(q) ||
      String(a.id).toLowerCase().includes(q)
    );
  });

  // Group by status for display
  const waitingAppointments = filteredAppointments.filter((a) =>
    ['arrived', 'checked_in', 'vitals_completed', 'waiting_for_doctor'].includes(
      a.status
    )
  );
  const upcomingAppointments = filteredAppointments.filter((a) =>
    ['scheduled', 'confirmed'].includes(a.status)
  );
  const completedAppointments = filteredAppointments.filter((a) =>
    ['completed', 'cancelled', 'no_show'].includes(a.status)
  );

  return (
    <div className="flex flex-col lg:flex-row gap-4 p-3 md:p-4 lg:p-6 max-w-7xl mx-auto">
      {/* Left: Appointments list */}
      <div className="flex-1 min-w-0">
        {/* ── Sticky Header ── */}
        <div className="sticky top-0 z-20 -mx-3 md:-mx-4 lg:-mx-6 px-3 md:px-4 lg:px-6 pb-2 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Calendar className="w-5 h-5 text-primary" />
              Front Desk
            </h2>
            <button
              type="button"
              onClick={() => setShowWalkInModal(true)}
              className="inline-flex items-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 font-medium text-sm min-h-[48px] shadow-sm"
            >
              <Plus className="w-5 h-5" />
              Walk-In
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search patients or doctors..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-border rounded-lg text-sm bg-background focus:ring-2 focus:ring-primary focus:border-primary min-h-[48px]"
            />
          </div>

          {/* Quick stats chips */}
          <div className="flex gap-2 mb-2 overflow-x-auto pb-1">
            <div className="flex items-center gap-1.5 rounded-full bg-amber-100 dark:bg-amber-950 px-3 py-1.5 text-xs font-medium text-amber-700 dark:text-amber-300 whitespace-nowrap">
              <Users className="h-3.5 w-3.5" aria-hidden />
              {waitingAppointments.length} waiting
            </div>
            <div className="flex items-center gap-1.5 rounded-full bg-blue-100 dark:bg-blue-950 px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-300 whitespace-nowrap">
              <Calendar className="h-3.5 w-3.5" aria-hidden />
              {upcomingAppointments.length} upcoming
            </div>
            <div className="flex items-center gap-1.5 rounded-full bg-gray-100 dark:bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">
              <Clock className="h-3.5 w-3.5" aria-hidden />
              {completedAppointments.length} done
            </div>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="p-4 mb-4 bg-destructive/10 rounded-lg border border-destructive/20">
            <p className="text-destructive text-sm">{error}</p>
            <button
              type="button"
              onClick={fetchAppointments}
              className="mt-2 text-sm text-destructive underline hover:text-destructive/80"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-24 bg-muted rounded-lg animate-pulse"
              />
            ))}
          </div>
        )}

        {/* Appointment sections */}
        {!loading && !error && (
          <div className="space-y-4">
            {/* Waiting patients */}
            {waitingAppointments.length > 0 && (
              <Section title="In Clinic" count={waitingAppointments.length}>
                {waitingAppointments.map((appt) => (
                  <AppointmentCard
                    key={appt.id}
                    appointment={appt}
                    isSelected={selectedAppointment?.id === appt.id}
                    onSelect={setSelectedAppointment}
                  />
                ))}
              </Section>
            )}

            {/* Upcoming */}
            {upcomingAppointments.length > 0 && (
              <Section title="Upcoming" count={upcomingAppointments.length}>
                {upcomingAppointments.map((appt) => (
                  <AppointmentCard
                    key={appt.id}
                    appointment={appt}
                    isSelected={selectedAppointment?.id === appt.id}
                    onSelect={setSelectedAppointment}
                  />
                ))}
              </Section>
            )}

            {/* Completed / Terminal */}
            {completedAppointments.length > 0 && (
              <Section
                title="Completed / Cancelled"
                count={completedAppointments.length}
              >
                {completedAppointments.map((appt) => (
                  <AppointmentCard
                    key={appt.id}
                    appointment={appt}
                    isSelected={selectedAppointment?.id === appt.id}
                    onSelect={setSelectedAppointment}
                  />
                ))}
              </Section>
            )}

            {/* Empty state */}
            {filteredAppointments.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <Calendar className="w-16 h-16 mx-auto mb-3 opacity-50" />
                <p className="text-lg font-medium">No appointments found</p>
                <p className="text-sm mt-1">
                  {searchQuery
                    ? 'Try a different search term'
                    : 'Schedule an appointment or register a walk-in'}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right: Queue panel + selected appointment actions */}
      <div className="w-full lg:w-96 flex-shrink-0 space-y-4">
        <QueueManagementPanel refreshInterval={refreshInterval} />

        {/* Selected appointment actions */}
        {selectedAppointment && (
          <div className="bg-card rounded-lg shadow-sm border border-border p-4">
            <h4 className="text-sm font-semibold text-foreground mb-2">
              Selected: {selectedAppointment.patient?.name || 'Patient'}
            </h4>
            <p className="text-xs text-muted-foreground mb-3">
              Status: <span className="font-medium">{selectedAppointment.status}</span>
              {selectedAppointment.doctor?.name &&
                ` • Dr. ${selectedAppointment.doctor.name}`}
            </p>
            <AppointmentStatusActions
              appointment={selectedAppointment}
              onStatusChange={handleStatusChange}
            />
          </div>
        )}
      </div>

      {/* Walk-in modal */}
      {showWalkInModal && (
        <WalkInModal
          onClose={() => setShowWalkInModal(false)}
          onCreated={(appt) => {
            setShowWalkInModal(false);
            setAppointments((prev) => [appt, ...prev]);
            setSelectedAppointment(appt);
          }}
        />
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section component
// ──────────────────────────────────────────────────────────────────────────────

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
        {title} ({count})
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Appointment card — enhanced with delay indicators
// ──────────────────────────────────────────────────────────────────────────────

function AppointmentCard({
  appointment,
  isSelected,
  onSelect,
}: {
  appointment: Appointment;
  isSelected: boolean;
  onSelect: (appt: Appointment) => void;
}) {
  const statusColors: Record<string, string> = {
    scheduled: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    confirmed: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
    arrived: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
    checked_in: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
    vitals_completed: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
    waiting_for_doctor: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300',
    in_consultation: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    completed: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
    cancelled: 'bg-red-100 text-red-500 dark:bg-red-900 dark:text-red-400',
    no_show: 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500',
  };

  // Calculate delay indicator for waiting patients
  const isWaiting = ['arrived', 'checked_in', 'vitals_completed', 'waiting_for_doctor'].includes(appointment.status);
  const delayMinutes = isWaiting && appointment.appointment_time
    ? Math.floor(
        (Date.now() - new Date(appointment.appointment_time).getTime()) / 60000
      )
    : 0;
  const isDelayed = delayMinutes > 15;

  return (
    <button
      type="button"
      onClick={() => onSelect(appointment)}
      className={cn(
        'w-full text-left p-4 rounded-lg border-2 transition-all min-h-[72px]',
        isSelected
          ? 'border-primary bg-primary/5'
          : 'border-border bg-card hover:border-primary/30 hover:shadow-sm',
        isDelayed && 'border-l-4 border-l-red-500'
      )}
    >
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <p className="font-medium text-foreground truncate">
            {appointment.patient?.name || 'Unknown Patient'}
          </p>
          <p className="text-sm text-muted-foreground truncate">
            {appointment.doctor?.name
              ? `Dr. ${appointment.doctor.name}`
              : 'No doctor assigned'}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {isDelayed && (
            <span className="flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400">
              <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
              {delayMinutes}m
            </span>
          )}
          <span
            className={cn(
              'px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap',
              statusColors[appointment.status] || 'bg-muted text-muted-foreground'
            )}
          >
            {appointment.status.replace(/_/g, ' ')}
          </span>
        </div>
      </div>
      {appointment.appointment_time && (
        <p className="text-xs text-muted-foreground mt-1">
          {new Date(appointment.appointment_time).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      )}
    </button>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Walk-in modal
// ──────────────────────────────────────────────────────────────────────────────

function WalkInModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (appt: Appointment) => void;
}) {
  const [patientId, setPatientId] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId || !doctorId) {
      setError('Patient ID and Doctor ID are required');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const appt = await frontDeskApi.createWalkIn({
        patient_id: patientId,
        doctor_id: doctorId,
      });
      onCreated(appt);
    } catch (err) {
      console.error('[WalkInModal] Create error:', err);
      setError('Failed to create walk-in appointment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-card rounded-xl shadow-xl p-6 w-full max-w-md mx-4 border border-border">
        <h3 className="text-lg font-bold text-foreground mb-4">
          New Walk-In Appointment
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Patient ID
            </label>
            <input
              type="text"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="w-full px-3 py-3 border border-border rounded-lg text-sm bg-background focus:ring-2 focus:ring-primary min-h-[48px]"
              placeholder="Enter patient UUID"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Doctor ID
            </label>
            <input
              type="text"
              value={doctorId}
              onChange={(e) => setDoctorId(e.target.value)}
              className="w-full px-3 py-3 border border-border rounded-lg text-sm bg-background focus:ring-2 focus:ring-primary min-h-[48px]"
              placeholder="Enter doctor UUID"
              required
            />
          </div>
          {error && (
            <p className="text-sm text-destructive bg-destructive/10 p-2 rounded">
              {error}
            </p>
          )}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-accent min-h-[48px]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-3 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 min-h-[48px]"
            >
              {loading ? 'Creating...' : 'Create Walk-In'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
