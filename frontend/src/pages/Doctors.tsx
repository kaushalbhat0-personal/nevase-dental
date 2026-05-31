import { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useLocation } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useDoctors } from '../hooks';
import { useAuth } from '../hooks/useAuth';
import { useModalFocusTrap } from '../hooks/useModalFocusTrap';
import { doctorsApi, doctorVerificationAdminApi } from '../services';
import { getEffectiveRoles, canVerifyDoctorsInTenant, isSuperAdminRole } from '../utils/roles';
import { formatDoctorName, formatDoctorInitials } from '../utils';
import { ErrorState, EmptyState, Button, Card as CommonCard } from '../components/common';
import { Card, CardContent } from '@/components/ui/card';
import { SkeletonCard } from '../components/common/skeletons';
import { FormWrapper, FormInput } from '../components/common';
import { doctorSchema, type DoctorFormData, type DoctorFormInput } from '../validation';
import { EMPTY_DOCTOR } from '../constants';
import { cn } from '@/lib/utils';
import type { Doctor } from '../types';

function formatDoctorCreateError(err: unknown): string {
  const e = err as { detail?: string | { msg?: string }[]; message?: string };
  let raw = '';
  if (typeof e?.detail === 'string') {
    raw = e.detail;
  } else if (Array.isArray(e?.detail) && e.detail.length > 0) {
    const first = e.detail[0];
    raw = typeof first === 'object' && first && 'msg' in first ? String(first.msg) : JSON.stringify(e.detail);
  } else if (typeof e?.message === 'string') {
    raw = e.message;
  }
  const lower = raw.toLowerCase();
  if (lower.includes('email already')) {
    return 'Email already exists';
  }
  if (lower.includes('internal error')) {
    return 'Failed to create doctor account';
  }
  if (raw) {
    return raw;
  }
  return 'Failed to create doctor account';
}

export function Doctors() {
  const location = useLocation();
  const { user } = useAuth();
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const canVerify = canVerifyDoctorsInTenant(user, token);
  const superAdmin = isSuperAdminRole(getEffectiveRoles(user, token));

  // Data fetching via hook
  const { doctors, loading, error, refetch } = useDoctors();

  const [rejectDoctor, setRejectDoctor] = useState<Doctor | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [verificationSubmitting, setVerificationSubmitting] = useState(false);
  const rejectModalRef = useRef<HTMLDivElement>(null);
  useModalFocusTrap(rejectModalRef, Boolean(rejectDoctor));

  const showVerifyActions = (d: Doctor) => {
    if (!canVerify || (d.verification_status ?? '') !== 'pending') return false;
    if (d.tenant_type === 'individual' && !superAdmin) return false;
    return true;
  };

  const approveDoctor = async (d: Doctor) => {
    const id = String(d.id);
    setVerificationSubmitting(true);
    try {
      await doctorVerificationAdminApi.setVerification(id, { status: 'approved' });
      toast.success('Doctor approved');
      await refetch();
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'detail' in err
          ? String((err as { detail?: unknown }).detail)
          : 'Approve failed';
      toast.error(msg);
    } finally {
      setVerificationSubmitting(false);
    }
  };

  const submitReject = async () => {
    if (!rejectDoctor) return;
    const reason = rejectReason.trim();
    if (!reason) {
      toast.error('Enter a reason for rejection');
      return;
    }
    setVerificationSubmitting(true);
    try {
      await doctorVerificationAdminApi.setVerification(String(rejectDoctor.id), {
        status: 'rejected',
        reason,
      });
      toast.success('Doctor rejected');
      setRejectDoctor(null);
      setRejectReason('');
      await refetch();
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'detail' in err
          ? String((err as { detail?: unknown }).detail)
          : 'Reject failed';
      toast.error(msg);
    } finally {
      setVerificationSubmitting(false);
    }
  };

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
        const formElement = document.getElementById('doctor-form');
        formElement?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [showForm, location.state]);

  const form = useForm<DoctorFormInput, any, DoctorFormData>({
    resolver: zodResolver(doctorSchema),
    defaultValues: EMPTY_DOCTOR,
    mode: 'onBlur',
    reValidateMode: 'onChange',
  });

  const { reset } = form;

  // Delete handler
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this doctor?')) return;

    try {
      await doctorsApi.delete(id);
      toast.success('Doctor deleted successfully');
      await refetch();
    } catch (err: any) {
      console.error('[Doctors.handleDelete] Error:', err);
      const errorMessage = err?.detail || err?.message || 'Failed to delete doctor';
      toast.error(errorMessage, { duration: 5000 });
    }
  };

  // Create handler
  const onSubmit = async (data: DoctorFormData) => {
    setApiError('');

    try {
      await doctorsApi.create({
        name: data.name,
        specialization: data.specialization || 'General',
        experience_years: data.experience_years ?? 0,
        account_email: data.account_email,
        account_password: data.account_password,
        license_number: data.license_number,
      });

      toast.success('Doctor created successfully', {
        duration: 3000,
        icon: '👨‍⚕️',
      });

      reset();
      setShowForm(false);

      // Refetch to update UI
      await refetch();
    } catch (err: unknown) {
      const errorMessage = formatDoctorCreateError(err);
      setApiError(errorMessage);
      toast.error(errorMessage, { duration: 5000 });
    }
  };

  // Safe rendering guards - only show empty after loading completes
  const isEmpty = !loading && doctors.length === 0;

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
          title="No data available"
          description="There are no doctors to display at the moment."
        />
      )}
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Doctors</h1>
          <p className="text-sm text-muted-foreground mt-1">Medical staff directory</p>
        </div>
        <Button
          variant={showForm ? 'ghost' : 'primary'}
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : '+ Add Doctor'}
        </Button>
      </div>

      {showForm && (
        <CommonCard id="doctor-form" className="mb-6">
          <h3 className="text-lg font-semibold mb-6">New Doctor</h3>
          <FormWrapper<DoctorFormInput, DoctorFormData>
            form={form}
            onSubmit={onSubmit}
            submitLabel="Create Doctor"
            loadingLabel="Creating..."
            apiError={apiError}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormInput<DoctorFormInput>
                name="name"
                label="Full Name"
                disabled={form.formState.isSubmitting}
                required
              />
              <FormInput<DoctorFormInput>
                name="specialization"
                label="Specialization"
                disabled={form.formState.isSubmitting}
                placeholder="e.g., Cardiology, Pediatrics"
                required
              />
              <FormInput<DoctorFormInput>
                name="account_email"
                label="Login email"
                type="email"
                disabled={form.formState.isSubmitting}
                placeholder="doctor@clinic.com"
                required
              />
              <FormInput<DoctorFormInput>
                name="account_password"
                label="Initial password"
                type="password"
                disabled={form.formState.isSubmitting}
                placeholder="At least 8 characters"
                required
              />
              <FormInput<DoctorFormInput>
                name="license_number"
                label="License Number"
                disabled={form.formState.isSubmitting}
                placeholder="e.g., MED123456"
              />
              <FormInput<DoctorFormInput>
                name="experience_years"
                label="Years of Experience"
                type="number"
                disabled={form.formState.isSubmitting}
                placeholder="e.g., 5"
              />
            </div>
          </FormWrapper>
        </CommonCard>
      )}

      {/* Grid */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {doctors.map((doctor) => (
            <Card key={doctor.id}>
              <CardContent className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-semibold flex-shrink-0">
                  {formatDoctorInitials(doctor)}
                </div>
                <div className="flex-1 min-w-0 space-y-1">
                  <h3 className="font-semibold truncate">{formatDoctorName(doctor)}</h3>
                  <p className="text-sm font-medium text-primary">
                    {doctor.specialization || doctor.specialty || 'General'}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {doctor.experience_years ? `${doctor.experience_years} years exp.` : ''}
                  </p>
                  <p className="text-sm text-muted-foreground truncate">
                    {doctor.linked_user_email || doctor.user?.email || ''}
                  </p>
                  {canVerify && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Marketplace:{' '}
                      <span
                        className={cn(
                          'font-medium',
                          doctor.verification_status === 'approved' && 'text-emerald-700',
                          doctor.verification_status === 'pending' && 'text-amber-800',
                          doctor.verification_status === 'rejected' && 'text-red-700'
                        )}
                      >
                        {doctor.verification_status ?? '—'}
                        {doctor.verified === true && (
                          <span className="ml-1.5 text-emerald-700" title="Verified">
                            ✓
                          </span>
                        )}
                      </span>
                    </p>
                  )}
                  {showVerifyActions(doctor) && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      <Button
                        type="button"
                        size="sm"
                        variant="primary"
                        disabled={verificationSubmitting}
                        onClick={() => void approveDoctor(doctor)}
                      >
                        Approve
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="danger"
                        disabled={verificationSubmitting}
                        onClick={() => {
                          setRejectReason('');
                          setRejectDoctor(doctor);
                        }}
                      >
                        Reject
                      </Button>
                    </div>
                  )}
                </div>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => handleDelete(String(doctor.id))}
                  disabled={loading}
                >
                  Delete
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {rejectDoctor && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setRejectDoctor(null);
          }}
        >
          <div
            ref={rejectModalRef}
            className={cn(
              'w-full max-w-md rounded-xl border border-border bg-background shadow-lg',
              'p-6 space-y-4'
            )}
            role="dialog"
            aria-modal="true"
            aria-labelledby="reject-doc-title"
          >
            <h2 id="reject-doc-title" className="text-lg font-semibold">
              Reject verification
            </h2>
            <p className="text-sm text-muted-foreground">A reason is required before rejecting.</p>
            <div className="space-y-2">
              <label htmlFor="doc-reject-reason" className="text-sm font-medium">
                Reason for rejection
              </label>
              <textarea
                id="doc-reject-reason"
                className={cn(
                  'flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm',
                  'ring-offset-background placeholder:text-muted-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                )}
                placeholder="Reason for rejection"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" onClick={() => setRejectDoctor(null)}>
                Cancel
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={() => void submitReject()}
                disabled={verificationSubmitting || !rejectReason.trim()}
              >
                {verificationSubmitting ? 'Submitting…' : 'Reject'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
