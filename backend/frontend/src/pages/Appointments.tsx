import { useState, useMemo, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useLocation } from 'react-router-dom';
import { Filter, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAppointments, type AppointmentFilters } from '../hooks';
import { createAppointmentHandler } from '../handlers';
import { appointmentsApi } from '../services';
import { EMPTY_APPOINTMENT } from '../constants';
import { DISPLAY_TIMEZONE } from '../constants/time';
import { formatPatientName, formatDoctorName } from '../utils';
import { formatAppointmentDateTimeWithZoneLabel } from '../utils/doctorSchedule';
import { ErrorState, EmptyState, GlobalLoader, FormWrapper, FormSelect, FormInput, FormTextarea, Button, Card as CommonCard } from '../components/common';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { appointmentSchema, type AppointmentFormData, type AppointmentFormInput } from '../validation';

export function Appointments() {
  const location = useLocation();

  // Filter states
  const [filterDoctor, setFilterDoctor] = useState<number | ''>('');
  const [filterStatus, setFilterStatus] = useState<AppointmentFilters['status'] | ''>('');
  const [showFilters, setShowFilters] = useState(false);

  // Stable filters object - only recreate when filter values actually change
  const filters = useMemo(
    () => ({
      doctor_id: filterDoctor ? String(filterDoctor) : undefined,
      status: filterStatus || undefined,
    }),
    [filterDoctor, filterStatus]
  );

  // Data fetching via hook
  const { appointments, patients, doctors, loading, refetching, error, refetch } = useAppointments(filters);

  // Form state - auto-show if navigated from Quick Actions
  const [showForm, setShowForm] = useState(() => (location.state as { showForm?: boolean })?.showForm ?? false);
  const [apiError, setApiError] = useState('');

  // Scroll to form when shown via Quick Actions
  useEffect(() => {
    if (showForm && (location.state as { showForm?: boolean })?.showForm) {
      // Clear the state to prevent re-triggering on refresh
      window.history.replaceState({}, document.title);
      // Scroll to form with smooth animation
      setTimeout(() => {
        const formElement = document.getElementById('appointment-form');
        formElement?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [showForm, location.state]);

  const form = useForm<AppointmentFormInput, any, AppointmentFormData>({
    resolver: zodResolver(appointmentSchema),
    defaultValues: EMPTY_APPOINTMENT,
    mode: 'onBlur',
    reValidateMode: 'onChange',
  });

  const { reset } = form;

  const hasActiveFilters = filterDoctor || filterStatus;

  const clearFilters = () => {
    setFilterDoctor('');
    setFilterStatus('');
  };

  // Debug: Log form errors whenever they change
  if (import.meta.env.DEV) {
    const errors = form.formState.errors;
    if (Object.keys(errors).length > 0) {
      console.log('[Appointments] Form errors:', errors);
    }
  }

  // Delete handler
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this appointment?')) return;

    try {
      await appointmentsApi.delete(id);
      toast.success('Appointment deleted successfully');
      await refetch();
    } catch (err: any) {
      console.error('[Appointments.handleDelete] Error:', err);
      const errorMessage = err?.detail || err?.message || 'Failed to delete appointment';
      toast.error(errorMessage, { duration: 5000 });
    }
  };

  // Create handler with robust error handling and toast notifications
  const onSubmit = async (data: AppointmentFormData) => {
    console.log('SUBMIT TRIGGERED - Appointments form');
    setApiError('');

    console.log('[Appointments.onSubmit] Submitting:', data);

    try {
      await createAppointmentHandler(data);

      // Success: show toast, reset form, close modal, refresh data
      toast.success('Appointment scheduled successfully', {
        duration: 3000,
        icon: '📅',
      });

      reset();
      setShowForm(false);

      if (import.meta.env.DEV) {
        console.log('[Appointments.onSubmit] Refetching data...');
      }
      await refetch();

      console.log('[Appointments.onSubmit] Success - form reset and data refreshed');
    } catch (err: any) {
      console.error('[Appointments.onSubmit] Error:', err);

      // Handle different error types
      let errorMessage = 'Failed to create appointment';

      if (err?.detail) {
        // Backend validation error (422)
        errorMessage = err.detail;
      } else if (err?.message) {
        // Generic error message
        errorMessage = err.message;
      } else if (typeof err === 'string') {
        errorMessage = err;
      }

      // Show error in form for visibility and toast for notification
      setApiError(errorMessage);
      toast.error(errorMessage, { duration: 5000 });

      // Keep form open so user can correct errors
      // Don't reset form on error to preserve user input
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'completed': return 'default';
      case 'scheduled': return 'secondary';
      case 'cancelled': return 'destructive';
      default: return 'secondary';
    }
  };

  // Safe rendering guards - only show empty after loading completes
  const isLoading = loading && appointments.length === 0; // Only block UI on initial load
  const isEmpty = !loading && !refetching && appointments.length === 0;

  return (
    <div className="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Appointments</h1>
          <p className="text-sm text-muted-foreground mt-1">Schedule and manage appointments</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <Button
            variant={hasActiveFilters ? 'primary' : 'secondary'}
            onClick={() => setShowFilters(!showFilters)}
            disabled={loading || refetching}
            leftIcon={<Filter className="h-4 w-4" />}
          >
            Filters {hasActiveFilters && '(Active)'}
          </Button>
          <Button
            variant={showForm ? 'ghost' : 'primary'}
            onClick={() => setShowForm(!showForm)}
            disabled={loading || refetching}
          >
            {showForm ? 'Cancel' : '+ New Appointment'}
          </Button>
        </div>
      </div>

      {isLoading && <GlobalLoader />}
      {refetching && (
        <div className="text-sm text-text-muted py-2 text-right mb-4">Updating...</div>
      )}

      {error && (
        <ErrorState
          title="Something went wrong"
          description="Failed to load data"
          error={error}
          onRetry={refetch}
        />
      )}

      {!error && isEmpty && (
        <EmptyState
          title="No data available"
          description="There are no appointments to display at the moment."
        />
      )}

      {showFilters && (
        <CommonCard className="space-y-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium">Doctor</label>
              <select
                value={filterDoctor}
                onChange={(e) => setFilterDoctor(Number(e.target.value) || '')}
                disabled={loading || refetching}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground"
              >
                <option value="">All Doctors</option>
                {doctors.map((d) => (
                  <option key={d.id} value={d.id}>
                    {formatDoctorName(d)} - {d.specialization || d.specialty || 'General'}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium">Status</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as AppointmentFilters['status'])}
                disabled={loading || refetching}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground"
              >
                <option value="">All Status</option>
                <option value="scheduled">Scheduled</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 sm:justify-between">
            <Button
              variant="ghost"
              onClick={clearFilters}
              disabled={!hasActiveFilters || loading}
              leftIcon={<X className="h-4 w-4" />}
            >
              Clear Filters
            </Button>
            <Button
              variant="primary"
              onClick={refetch}
              disabled={loading || refetching}
              isLoading={refetching}
            >
              {refetching ? 'Updating...' : 'Apply Filters'}
            </Button>
          </div>
        </CommonCard>
      )}

      {showForm && (
        <CommonCard id="appointment-form" className="mb-6">
          <h3 className="text-lg font-semibold mb-6">New Appointment</h3>
          <FormWrapper<AppointmentFormInput, AppointmentFormData>
            form={form}
            onSubmit={onSubmit}
            submitLabel="Schedule Appointment"
            loadingLabel="Scheduling..."
            apiError={apiError}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormSelect<AppointmentFormInput>
                name="patient_id"
                label="Patient"
                placeholder="Select patient"
                options={patients.map((p) => ({
                  value: p.id,
                  label: formatPatientName(p),
                }))}
                disabled={form.formState.isSubmitting}
                required
              />
              <FormSelect<AppointmentFormInput>
                name="doctor_id"
                label="Doctor"
                placeholder="Select doctor"
                options={doctors.map((d) => ({
                  value: d.id,
                  label: `${formatDoctorName(d)} - ${d.specialization || d.specialty || 'General'}`,
                }))}
                disabled={form.formState.isSubmitting}
                required
              />
              <FormInput<AppointmentFormInput>
                name="scheduled_at"
                label="Date & Time"
                type="datetime-local"
                disabled={form.formState.isSubmitting}
                required
              />
            </div>
            <FormTextarea<AppointmentFormInput>
              name="notes"
              label="Notes"
              rows={2}
              disabled={form.formState.isSubmitting}
            />
          </FormWrapper>
        </CommonCard>
      )}

      <Card className="p-0">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Patient</TableHead>
                <TableHead>Doctor</TableHead>
                <TableHead>Date & Time</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {appointments.map((apt) => {
                const appointmentTime = apt.appointment_time || apt.scheduled_at;
                return (
                  <TableRow key={apt.id}>
                    <TableCell className="font-medium">{formatPatientName(apt.patient)}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDoctorName(apt.doctor)}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatAppointmentDateTimeWithZoneLabel(
                        appointmentTime || '',
                        DISPLAY_TIMEZONE
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusVariant(apt.status)}>{apt.status}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{apt.notes || '-'}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(String(apt.id))}
                        disabled={loading || refetching}
                      >
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
