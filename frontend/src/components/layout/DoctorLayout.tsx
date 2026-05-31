import { useCallback, useState } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { DoctorWorkspaceProvider, useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import { useAppMode } from '../../contexts/AppModeContext';
import { Header } from './Header';
import { DoctorSidebar } from './DoctorSidebar';
import { Badge } from '@/components/ui/badge';
import { Button, buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { doctorProfileApi } from '../../services/doctorProfile';
import toast from 'react-hot-toast';
import { isDoctorVerificationApproved } from '../../utils/doctorVerification';
import { getEffectiveRoles } from '../../utils/roles';

function DoctorLayoutInner() {
  const { user, logout, refreshUser } = useAuth();
  const { resolvedMode } = useAppMode();
  const { isIndependent, selfDoctor, profilePartial, loading, error } = useDoctorWorkspace();
  const [mobileOpen, setMobileOpen] = useState(false);
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const eff = getEffectiveRoles(user, token);
  const isClinician = Boolean(user?.doctor_id) && eff.includes('doctor');
  const approved = isDoctorVerificationApproved(user, token);
  const [submittingVerification, setSubmittingVerification] = useState(false);
  const vstat = user?.doctor_verification_status ?? null;
  const showVerificationStrip =
    isClinician && !approved && vstat != null && vstat !== '';

  const submitForVerification = useCallback(async () => {
    setSubmittingVerification(true);
    try {
      await doctorProfileApi.submitForVerification();
      await refreshUser();
      toast.success('Submitted for review');
    } catch (e) {
      console.error(e);
      toast.error('Could not submit for verification');
    } finally {
      setSubmittingVerification(false);
    }
  }, [refreshUser]);

  return (
    <div
      className={cn(
        'flex h-dvh min-h-0 w-full overflow-hidden text-foreground',
        resolvedMode === 'practice' &&
          'bg-gradient-to-b from-sky-50/50 via-background to-emerald-50/30 dark:from-sky-950/20 dark:via-background dark:to-emerald-950/20',
        resolvedMode === 'admin' && 'bg-background'
      )}
    >
      <div className="hidden h-full min-h-0 w-64 flex-shrink-0 lg:block">
        <DoctorSidebar user={user} />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
            aria-hidden
          />
          <div className="absolute left-0 top-0 h-full w-64 max-w-[85vw] border-r border-border bg-card shadow-2xl">
            <DoctorSidebar user={user} onClose={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <Header
          user={user}
          onLogout={logout}
          onMenuToggle={() => setMobileOpen(true)}
          centerSlot={
            <div className={cn('min-w-0 lg:hidden')}>
              <p className="truncate text-sm font-semibold text-foreground">Clinician portal</p>
              <p className="truncate text-xs text-muted-foreground">Schedule &amp; care</p>
            </div>
          }
        />

        {selfDoctor?.tenant_name && (
          <div className="hidden border-b border-border/60 bg-muted/30 px-4 py-1.5 lg:block">
            <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">{selfDoctor.tenant_name}</span>
              {(selfDoctor.tenant_organization_label || selfDoctor.tenant_type) && (
                <Badge variant="outline" className="normal-case">
                  {selfDoctor.tenant_organization_label ?? selfDoctor.tenant_type?.replace(/_/g, ' ')}
                </Badge>
              )}
            </div>
          </div>
        )}

        {loading && (
          <p
            className="border-b border-border/60 bg-muted/20 px-4 py-1.5 text-center text-xs text-muted-foreground"
            aria-live="polite"
          >
            Loading your workspace…
          </p>
        )}
        {error && !loading && (
          <p className="border-b border-border/60 bg-destructive/5 px-4 py-2 text-center text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        {profilePartial && !loading && !error && (
          <p
            className="border-b border-amber-200/80 bg-amber-50 px-4 py-2 text-sm text-amber-900"
            role="status"
          >
            Your user account is not clearly linked to a single doctor record in this organization. The portal
            stays in view-only mode; ask an administrator to confirm your email on your doctor profile.
          </p>
        )}

        {isIndependent && !loading && (
          <p className="border-b border-border/40 bg-primary/[0.04] px-4 py-1.5 text-center text-xs text-muted-foreground">
            Independent practice — patients, schedule, and billing in one place.
          </p>
        )}

        {showVerificationStrip && !loading && (
          <div
            className={cn(
              'border-b px-4 py-3 text-sm',
              vstat === 'rejected'
                ? 'border-destructive/30 bg-destructive/5 text-destructive'
                : 'border-amber-200/80 bg-amber-50 text-amber-950'
            )}
            role="status"
          >
            <div className="mx-auto flex max-w-5xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                {vstat === 'pending' && (
                  <div>
                    <p className="font-semibold tracking-tight">Under review</p>
                    <p className="mt-1 text-sm font-normal opacity-90">
                      Your profile is being verified. You’ll unlock patients, scheduling, and billing once
                      approved.
                    </p>
                  </div>
                )}
                {vstat === 'draft' && (
                  <p>
                    Submit your profile for verification to unlock patients, appointments, availability, and
                    billing.
                  </p>
                )}
                {vstat === 'rejected' && (
                  <div>
                    <p className="font-medium">Verification needs attention</p>
                    {user?.doctor_verification_rejection_reason ? (
                      <p className="mt-1 text-sm opacity-90">{user.doctor_verification_rejection_reason}</p>
                    ) : (
                      <p className="mt-1 text-sm">Update your profile and resubmit for review.</p>
                    )}
                  </div>
                )}
              </div>
              {(vstat === 'draft' || vstat === 'rejected') &&
                user?.doctor_profile_complete === true && (
                  <div className="flex flex-wrap items-center gap-2 shrink-0 self-start sm:self-center">
                    {vstat === 'rejected' && (
                      <Link
                        to="/complete-profile"
                        className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
                      >
                        Edit profile
                      </Link>
                    )}
                    <Button
                      type="button"
                      size="sm"
                      variant={vstat === 'rejected' ? 'default' : 'secondary'}
                      disabled={submittingVerification}
                      onClick={() => void submitForVerification()}
                    >
                      {submittingVerification
                        ? 'Submitting…'
                        : vstat === 'rejected'
                          ? 'Resubmit for verification'
                          : 'Submit for verification'}
                    </Button>
                  </div>
                )}
            </div>
          </div>
        )}

        <main className="mx-auto w-full max-w-5xl flex-1 min-h-0 scroll-smooth overflow-y-auto px-4 py-6 md:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function DoctorLayout() {
  return (
    <DoctorWorkspaceProvider>
      <DoctorLayoutInner />
    </DoctorWorkspaceProvider>
  );
}
