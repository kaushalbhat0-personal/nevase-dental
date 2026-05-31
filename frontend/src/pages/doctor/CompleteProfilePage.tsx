import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Navigate, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../../hooks/useAuth';
import { doctorProfileApi, retryRequest } from '../../services';
import { Button, Card, Input } from '../../components/common';
import {
  completeStructuredDoctorProfileSchema,
  type CompleteStructuredDoctorProfileFormData,
  type CompleteStructuredDoctorProfileFormInput,
} from '../../validation';
import {
  doctorHomePath,
  getEffectiveRoles,
  isAdminRole,
  isSuperAdminRole,
} from '../../utils/roles';
import type { DoctorStructuredProfile } from '../../types';
import { doctorProfileFieldsToReview } from '../../utils/doctorVerification';

const REQUIRED_COMPLETION_KEYS = [
  'full_name',
  'phone',
  'specialization',
  'registration_number',
  'qualification',
] as const;

function completionPercent(watched: Record<string, unknown>): number {
  const checks = [
    String(watched.full_name ?? '').trim().length > 0,
    String(watched.phone ?? '').replace(/\D/g, '').length === 10,
    String(watched.specialization ?? '').trim().length > 0,
    String(watched.registration_number ?? '').trim().length > 0,
    String(watched.qualification ?? '').trim().length > 0,
  ];
  const done = checks.filter(Boolean).length;
  return Math.round((done / REQUIRED_COMPLETION_KEYS.length) * 100);
}

export function CompleteProfilePage() {
  const { user, refreshUser, isLoading, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const eff = getEffectiveRoles(user, token);
  const [doctorProfile, setDoctorProfile] = useState<DoctorStructuredProfile | null>(null);
  const hydratedDoctorIdRef = useRef<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CompleteStructuredDoctorProfileFormInput, unknown, CompleteStructuredDoctorProfileFormData>({
    resolver: zodResolver(completeStructuredDoctorProfileSchema),
    defaultValues: {
      full_name: '',
      phone: '',
      profile_image: '',
      specialization: '',
      experience_years: 0,
      qualification: '',
      registration_number: '',
      registration_council: '',
      clinic_name: '',
      address: '',
      city: '',
      state: '',
    },
  });

  const watched = watch();
  const progressPct = useMemo(() => completionPercent(watched as Record<string, unknown>), [watched]);

  useEffect(() => {
    setDoctorProfile(null);
    hydratedDoctorIdRef.current = null;
  }, [user?.doctor_id]);

  const rejected = user?.doctor_verification_status === 'rejected';

  useEffect(() => {
    if (isLoading || !isAuthenticated) return;
    if (!user?.doctor_id) {
      if (isSuperAdminRole(eff) || isAdminRole(eff)) {
        navigate('/admin/dashboard', { replace: true });
        return;
      }
      navigate('/dashboard', { replace: true });
      return;
    }
    if (user.doctor_profile_complete === true && !rejected) {
      navigate(doctorHomePath(), { replace: true });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const p = await doctorProfileApi.get();
        if (cancelled) return;
        setDoctorProfile(p);
      } catch {
        if (!cancelled) {
          toast.error('Could not load your profile. Try again.');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isLoading, isAuthenticated, user?.doctor_id, user?.doctor_profile_complete, rejected, eff, navigate]);

  useEffect(() => {
    if (!doctorProfile) return;
    if (hydratedDoctorIdRef.current === doctorProfile.id) return;
    reset({
      full_name: doctorProfile.full_name,
      phone: doctorProfile.phone ?? '',
      profile_image: doctorProfile.profile_image ?? '',
      specialization: doctorProfile.specialization ?? '',
      experience_years: doctorProfile.experience_years ?? 0,
      qualification: doctorProfile.qualification ?? '',
      registration_number: doctorProfile.registration_number ?? '',
      registration_council: doctorProfile.registration_council ?? '',
      clinic_name: doctorProfile.clinic_name ?? '',
      address: doctorProfile.address ?? '',
      city: doctorProfile.city ?? '',
      state: doctorProfile.state ?? '',
    });
    hydratedDoctorIdRef.current = doctorProfile.id;
  }, [doctorProfile, reset]);

  function buildProfilePayload(data: CompleteStructuredDoctorProfileFormData) {
    return {
      full_name: data.full_name,
      phone: data.phone,
      profile_image: data.profile_image || null,
      specialization: data.specialization,
      experience_years: data.experience_years,
      qualification: data.qualification || null,
      registration_number: data.registration_number,
      registration_council: data.registration_council,
      clinic_name: data.clinic_name || null,
      address: data.address || null,
      city: data.city || null,
      state: data.state || null,
    };
  }

  const persistProfile = async (
    data: CompleteStructuredDoctorProfileFormData,
    opts: { submitForReview: boolean }
  ) => {
    const payload = buildProfilePayload(data);
    await retryRequest(() => doctorProfileApi.put(payload), 2, 2000);
    if (opts.submitForReview) {
      await doctorProfileApi.submitForVerification();
    }
    await refreshUser();
    toast.success(opts.submitForReview ? 'Submitted for review' : 'Profile saved');
    navigate(doctorHomePath(), { replace: true });
  };

  const onSubmit = async (data: CompleteStructuredDoctorProfileFormData) => {
    try {
      await persistProfile(data, { submitForReview: !rejected });
    } catch (e: unknown) {
      console.error(e);
      const err = e as {
        code?: string;
        __coldStart?: boolean;
        originalError?: { code?: string };
      };
      if (
        err?.__coldStart === true ||
        err?.code === 'ECONNABORTED' ||
        err?.originalError?.code === 'ECONNABORTED'
      ) {
        toast('Server is starting… please wait ⏳');
      } else {
        toast.error(rejected ? 'Failed to save profile' : 'Could not submit for verification');
      }
    }
  };

  const onResubmitForVerification = handleSubmit(async (data: CompleteStructuredDoctorProfileFormData) => {
    try {
      await persistProfile(data, { submitForReview: true });
    } catch (e: unknown) {
      console.error(e);
      const err = e as {
        code?: string;
        __coldStart?: boolean;
        originalError?: { code?: string };
      };
      if (
        err?.__coldStart === true ||
        err?.code === 'ECONNABORTED' ||
        err?.originalError?.code === 'ECONNABORTED'
      ) {
        toast('Server is starting… please wait ⏳');
      } else {
        toast.error('Could not resubmit for verification');
      }
    }
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-background">
        <div className="spinner" />
        <p className="text-sm text-text-secondary">Loading…</p>
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (!user?.doctor_id) {
    return null;
  }
  if (user.doctor_profile_complete === true && !rejected) {
    return null;
  }

  const reviewFields = new Set(
    doctorProfileFieldsToReview(user?.doctor_verification_rejection_reason ?? doctorProfile?.verification_rejection_reason)
  );
  const ringInvalid = (name: string) =>
    rejected && reviewFields.has(name) ? 'ring-2 ring-amber-500/60 border-amber-500/70' : '';

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <div className="flex-1 overflow-y-auto p-4 pb-28 flex justify-center">
        <Card padding="lg" className="w-full max-w-2xl">
          <h1 className="text-xl font-bold text-text-primary mb-1">
            {rejected ? 'Fix your profile and resubmit' : 'Complete your professional profile'}
          </h1>
          <p className="text-sm text-text-secondary mb-4">
            {rejected
              ? 'We could not verify your details yet. Update the highlighted fields and submit again for review.'
              : 'A few required details for licensing and contact. You can update these anytime later.'}
          </p>
          {rejected && (user?.doctor_verification_rejection_reason || doctorProfile?.verification_rejection_reason) && (
            <div
              className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
              role="status"
            >
              <span className="font-medium">Rejected: </span>
              {user?.doctor_verification_rejection_reason ?? doctorProfile?.verification_rejection_reason}
            </div>
          )}
          <div className="mb-6" aria-label="Profile completion">
            <div className="flex items-center justify-between text-sm text-text-secondary mb-1.5">
              <span>Profile completion</span>
              <span className="font-medium text-text-primary tabular-nums">{progressPct}%</span>
            </div>
            <div
              className="h-2 w-full rounded-full bg-border/60 overflow-hidden"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progressPct}
            >
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
          <form id="complete-profile-form" onSubmit={handleSubmit(onSubmit)} className="space-y-8">
            <section>
              <h2 className="text-sm font-semibold text-text-primary mb-3">👤 Personal details</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                <Input
                  label="Full name"
                  error={errors.full_name?.message}
                  disabled={isSubmitting}
                  placeholder="e.g. Dr. Sayali Nevase"
                  autoFocus
                  className={ringInvalid('full_name')}
                  {...register('full_name')}
                />
                <div className="space-y-1.5 sm:min-w-0">
                  <Input
                    label="Phone"
                    error={errors.phone?.message}
                    disabled={isSubmitting}
                    placeholder="e.g. 98765 43210 or +91 9876543210"
                    autoComplete="tel"
                    className={ringInvalid('phone')}
                    {...register('phone')}
                  />
                  <p className="text-sm text-text-secondary">
                    Enter a 10-digit number (with or without +91 or spaces).
                  </p>
                </div>
                <div className="sm:col-span-2">
                  <Input
                    label="Profile photo URL (optional)"
                    error={errors.profile_image?.message}
                    disabled={isSubmitting}
                    placeholder="https://…"
                    {...register('profile_image')}
                  />
                </div>
              </div>
            </section>
            <section>
              <h2 className="text-sm font-semibold text-text-primary mb-3">🩺 Professional details</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                <Input
                  label="Specialization"
                  error={errors.specialization?.message}
                  disabled={isSubmitting}
                  placeholder="e.g. Dentist, Cardiologist"
                  className={ringInvalid('specialization')}
                  {...register('specialization')}
                />
                <Input
                  label="Experience (years)"
                  type="number"
                  error={errors.experience_years?.message}
                  disabled={isSubmitting}
                  className={ringInvalid('experience_years')}
                  {...register('experience_years')}
                />
                <div className="sm:col-span-2">
                  <Input
                    label="Qualification"
                    error={errors.qualification?.message}
                    disabled={isSubmitting}
                    placeholder="e.g. BDS, MBBS, MD"
                    className={ringInvalid('qualification')}
                    {...register('qualification')}
                  />
                </div>
                <Input
                  label="License / registration number"
                  error={errors.registration_number?.message}
                  disabled={isSubmitting}
                  placeholder="e.g. DENT-IND-2024-00123"
                  className={ringInvalid('registration_number')}
                  {...register('registration_number')}
                />
                <Input
                  label="Registration council / medical body (optional)"
                  error={errors.registration_council?.message}
                  disabled={isSubmitting}
                  className={ringInvalid('registration_council')}
                  {...register('registration_council')}
                />
              </div>
            </section>
            <section>
              <h2 className="text-sm font-semibold text-text-primary mb-3">🏥 Clinic info</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                  <Input
                    label="Clinic or practice name (optional)"
                    error={errors.clinic_name?.message}
                    disabled={isSubmitting}
                    placeholder="e.g. Nevase Dental Clinic"
                    className={ringInvalid('clinic_name')}
                    {...register('clinic_name')}
                  />
                </div>
                <div className="sm:col-span-2">
                  <Input
                    label="Address"
                    error={errors.address?.message}
                    disabled={isSubmitting}
                    className={ringInvalid('address')}
                    {...register('address')}
                  />
                </div>
                <Input
                  label="City"
                  error={errors.city?.message}
                  disabled={isSubmitting}
                  className={ringInvalid('city')}
                  {...register('city')}
                />
                <Input
                  label="State"
                  error={errors.state?.message}
                  disabled={isSubmitting}
                  className={ringInvalid('state')}
                  {...register('state')}
                />
              </div>
            </section>
          </form>
        </Card>
      </div>
      <div className="sticky bottom-0 z-10 border-t border-border bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto flex w-full max-w-2xl flex-col gap-2">
          <Button
            form="complete-profile-form"
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            isLoading={isSubmitting}
          >
            {isSubmitting
              ? rejected
                ? 'Saving...'
                : 'Submitting...'
              : rejected
                ? 'Save changes'
                : 'Submit for verification'}
          </Button>
          {rejected && (
            <Button
              type="button"
              variant="secondary"
              size="lg"
              className="w-full"
              disabled={isSubmitting}
              onClick={() => void onResubmitForVerification()}
            >
              Resubmit for verification
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
