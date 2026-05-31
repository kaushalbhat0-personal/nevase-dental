import { useState, useMemo, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useLocation } from 'react-router-dom';
import debounce from 'lodash.debounce';
import toast from 'react-hot-toast';
import { usePatients } from '../hooks';
import { createPatientHandler } from '../handlers';
import { patientsApi, type PatientAutoCredentials } from '../services';
import { EMPTY_PATIENT } from '../constants';
import { formatPatientName, formatPatientDobOrAge, formatDateSafe } from '../utils';
import { useAuth } from '../hooks/useAuth';
import { useAppMode } from '../contexts/AppModeContext';
import { getActiveTenantId } from '../utils/tenantIdForRequest';
import { ErrorState, EmptyState, SkeletonTable, FormWrapper, FormInput, FormSelect, Button, Card as CommonCard, Input } from '../components/common';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
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

  // Auto-credentials modal
  const [credentials, setCredentials] = useState<PatientAutoCredentials | null>(null);
  const [credentialsOpen, setCredentialsOpen] = useState(false);

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
      const result = await createPatientHandler(data);

      toast.success('Patient created successfully', {
        duration: 3000,
        icon: '👤',
      });

      if (result.auto_credentials) {
        setCredentials(result.auto_credentials);
        setCredentialsOpen(true);
      }

      reset();
      setShowForm(false);

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
      {/* Auto-credentials Dialog */}
      <Dialog open={credentialsOpen} onOpenChange={setCredentialsOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl text-center">Patient Account Created</DialogTitle>
            <DialogDescription className="text-center">
              Share these credentials with the patient
            </DialogDescription>
          </DialogHeader>
          {credentials && (
            <div className="space-y-5">
              <div className="bg-blue-50 rounded-xl p-4 space-y-3">
                <div>
                  <p className="text-xs font-medium text-blue-600 uppercase tracking-wider">Username</p>
                  <p className="text-sm font-semibold text-[#0F172A] mt-0.5">{credentials.username}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-blue-600 uppercase tracking-wider">Temporary Password</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <code className="text-sm font-mono font-bold text-[#0F172A] bg-white px-2 py-1 rounded border border-blue-200 flex-1">
                      {credentials.password}
                    </code>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(credentials.password);
                        toast.success('Password copied!');
                      }}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium text-blue-600 bg-white border border-blue-200 hover:bg-blue-50 transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                </div>
              </div>
              <a
                href={credentials.whatsapp_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full py-3 rounded-xl text-sm font-semibold text-white bg-[#25D366] hover:bg-[#1DA851] transition-colors"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                Send Credentials via WhatsApp
              </a>
              <button
                onClick={() => setCredentialsOpen(false)}
                className="w-full py-2.5 rounded-xl text-sm font-medium text-[#1E293B] bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                Done
              </button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
