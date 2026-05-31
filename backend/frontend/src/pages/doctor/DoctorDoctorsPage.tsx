import { Card, CardContent } from '@/components/ui/card';
import { useDoctors } from '../../hooks';
import { ErrorState, EmptyState } from '../../components/common';
import { useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import type { Doctor } from '../../types';
import { formatDoctorInitials, formatDoctorName } from '../../utils';

function doctorLoginEmailLabel(d: Doctor): string {
  return d.linked_user_email || d.user?.email || 'No login email linked';
}

export function DoctorDoctorsPage() {
  const { isReadOnly } = useDoctorWorkspace();
  const { doctors, loading, error, refetch } = useDoctors();

  if (error) {
    return (
      <ErrorState
        title="Could not load doctors"
        description="We could not load your organization directory."
        error={error}
        onRetry={refetch}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Doctors</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {isReadOnly
            ? 'Providers in your organization (directory — read only).'
            : 'Providers in your tenant.'}
        </p>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {!loading && doctors.length === 0 && (
        <EmptyState title="No doctors" description="No providers are listed for your organization yet." />
      )}

      {!loading && doctors.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {doctors.map((d) => (
            <Card key={String(d.id)}>
              <CardContent className="flex items-start gap-4">
                <div className="w-11 h-11 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-sm font-semibold shrink-0">
                  {formatDoctorInitials(d)}
                </div>
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="font-semibold truncate">{formatDoctorName(d)}</p>
                  <p className="text-sm text-primary">{d.specialization || d.specialty || '—'}</p>
                  {d.experience_years != null && (
                    <p className="text-xs text-muted-foreground">{d.experience_years} years experience</p>
                  )}
                  <p className="text-xs text-muted-foreground truncate" title="Login email">
                    {doctorLoginEmailLabel(d)}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
