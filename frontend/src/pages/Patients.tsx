import { useState, useMemo, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useLocation } from 'react-router-dom';
import debounce from 'lodash.debounce';
import toast from 'react-hot-toast';
import { usePatients } from '../hooks';
import { createPatientHandler } from '../handlers';
import { patientsApi } from '../services';
import { EMPTY_PATIENT } from '../constants';
import { formatPatientName, formatPatientDobOrAge, formatDateSafe } from '../utils';
import { useAuth } from '../hooks/useAuth';
import { useAppMode } from '../contexts/AppModeContext';
import { getActiveTenantId } from '../utils/tenantIdForRequest';
import { ErrorState, EmptyState, SkeletonTable, FormWrapper, FormInput, FormSelect, Button, Card as CommonCard, Input } from '../components/common';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { patientSchema, type PatientFormData, type PatientFormInput } from '../validation';

export function Patients() {
  const { user } = useAuth();
  const { resolvedMode } = useAppMode();
  const location = useLocation();

  // Search state with debounce
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');

  const debouncedSearch = useMemo(
    () => debounce((value: string) => setSearch(value), 400),
    []
  );

  // Data fetching via hook
  const { patients, loading, error, refetch } = usePatients(search);

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
        const formElement = document.getElementById('patient-form');
        formElement?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [showForm, location.state]);

  const form = useForm<PatientFormInput, any, PatientFormData>({
    resolver: zodResolver(patientSchema),
    defaultValues: EMPTY_PATIENT,
    mode: 'onBlur',
    reValidateMode: 'onChange',
  });

  const { reset } = form;

  // Debug: Log form errors whenever they change
  if (import.meta.env.DEV) {
    const errors = form.formState.errors;
    if (Object.keys(errors).length > 0) {
      console.log('[Patients] Form errors:', errors);
    }
  }

  // Delete handler
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this patient?')) return;

    try {
      await patientsApi.delete(id);
      toast.success('Patient deleted successfully');
      await refetch();
    } catch (err: any) {
      console.error('[Patients.handleDelete] Error:', err);
      const errorMessage = err?.detail || err?.message || 'Failed to delete patient';
      toast.error(errorMessage, { duration: 5000 });
    }
  };

  // Create handler with robust error handling and toast notifications
  const onSubmit = async (data: PatientFormData) => {
    console.log('SUBMIT TRIGGERED - Patients form');
    setApiError('');

    console.log('[Patients.onSubmit] Submitting:', data);

    try {
      await createPatientHandler(data);

      toast.success('Patient created successfully', {
        duration: 3000,
        icon: '👤',
      });

      reset();
      setShowForm(false);

      // Refetch to update UI
      if (import.meta.env.DEV) {
        console.log('[Patients.onSubmit] Refetching data...');
      }
      await refetch();

      console.log('[Patients.onSubmit] Success - form reset and data refreshed');
    } catch (err: any) {
      console.error('[Patients.onSubmit] Error:', err);

      let errorMessage = 'Failed to create patient';

      if (err?.detail) {
        errorMessage = err.detail;
      } else if (err?.message) {
        errorMessage = err.message;
      } else if (typeof err === 'string') {
        errorMessage = err;
      }

      setApiError(errorMessage);
      toast.error(errorMessage, { duration: 5000 });
    }
  };

  // Safe rendering guards - only show empty after loading completes
  const safePatients = Array.isArray(patients) ? patients : [];
  const isEmpty = !loading && safePatients.length === 0;

  return (
    <div className="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

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
          title="No patients found"
          description={`scope: ${resolvedMode} · tenant: ${getActiveTenantId() ?? 'none'} · doctor: ${user?.doctor_id ?? 'none'}`}
        />
      )}
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Patients</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage patient records</p>
        </div>
        <Button
          variant={showForm ? 'ghost' : 'primary'}
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : '+ Add Patient'}
        </Button>
      </div>

      {loading && (
        <div className="mb-6">
          <SkeletonTable rows={5} columns={5} />
        </div>
      )}

      {!loading && (
        <div className="space-y-6">
          {/* Search */}
          <div className="max-w-md">
            <Input
              type="text"
              placeholder="Search patients..."
              value={searchInput}
              onChange={(e) => {
                const value = e.target.value;
                setSearchInput(value);
                debouncedSearch(value);
              }}
            />
          </div>

          {/* Create Form */}
          {showForm && (
            <CommonCard id="patient-form">
              <h3 className="text-lg font-semibold mb-6">New Patient</h3>
              <FormWrapper<PatientFormInput, PatientFormData>
                form={form}
                onSubmit={onSubmit}
                submitLabel="Create Patient"
                loadingLabel="Creating..."
                apiError={apiError}
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormInput<PatientFormInput>
                    name="name"
                    label="Full Name"
                    disabled={form.formState.isSubmitting}
                    required
                  />
                  <FormInput<PatientFormInput>
                    name="age"
                    label="Age"
                    type="number"
                    disabled={form.formState.isSubmitting}
                    required
                  />
                  <FormSelect<PatientFormInput>
                    name="gender"
                    label="Gender"
                    placeholder="Select gender"
                    options={[
                      { value: 'male', label: 'Male' },
                      { value: 'female', label: 'Female' },
                      { value: 'other', label: 'Other' },
                    ]}
                    disabled={form.formState.isSubmitting}
                    required
                  />
                  <FormInput<PatientFormInput>
                    name="phone"
                    label="Phone"
                    type="tel"
                    disabled={form.formState.isSubmitting}
                    required
                  />
                </div>
              </FormWrapper>
            </CommonCard>
          )}

          {/* Table */}
          <Card className="p-0">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead>DOB / Age</TableHead>
                    <TableHead>Registered</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {safePatients.map((patient, index) => (
                    <TableRow key={patient?.id != null ? String(patient.id) : `patient-row-${index}`}>
                      <TableCell>
                        <div className="flex flex-col gap-1.5">
                          <span className="font-medium">{formatPatientName(patient)}</span>
                          {patient?.doctor_name ? (
                            <Badge
                              variant="secondary"
                              className="w-fit max-w-full font-normal line-clamp-2 whitespace-normal"
                            >
                              {patient.doctor_name}
                            </Badge>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{patient?.email || '-'}</TableCell>
                      <TableCell className="text-muted-foreground">{patient?.phone || '-'}</TableCell>
                      <TableCell className="text-muted-foreground">{formatPatientDobOrAge(patient)}</TableCell>
                      <TableCell className="text-muted-foreground">{formatDateSafe(patient?.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handleDelete(String(patient.id))}
                          disabled={loading}
                        >
                          Delete
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
