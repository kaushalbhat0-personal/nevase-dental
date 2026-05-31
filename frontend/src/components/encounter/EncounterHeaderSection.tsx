import { Link } from 'react-router-dom';
import { ArrowLeft, Calendar, User } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button, buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { Appointment, Patient, Doctor } from '../../types';

function statusVariant(
  s: Appointment['status']
): 'default' | 'secondary' | 'outline' | 'destructive' {
  if (s === 'completed') return 'secondary';
  if (s === 'cancelled') return 'destructive';
  if (s === 'scheduled' || s === 'pending') return 'default';
  return 'outline';
}

interface EncounterHeaderSectionProps {
  appointment: Appointment;
  patient: Patient;
  doctor?: Doctor;
  formattedDateTime: string;
  onBack?: () => void;
  backLabel?: string;
  backTo?: string;
  /** Optional action buttons slot */
  actions?: React.ReactNode;
  /** Mobile-optimized compact mode */
  compact?: boolean;
}

/**
 * EncounterHeaderSection - Primary encounter identification and navigation
 * 
 * Clinical-first hierarchy element #1: Visit status/time
 * Displays the core encounter metadata in a clear, scannable format.
 * 
 * Mobile considerations:
 * - Responsive flex layout with wrap
 * - Compact mode for smaller screens
 * - Touch-friendly tap targets (min 44px)
 */
export function EncounterHeaderSection({
  appointment,
  patient,
  doctor,
  formattedDateTime,
  onBack,
  backLabel = 'Back',
  backTo,
  actions,
  compact = false,
}: EncounterHeaderSectionProps) {
  const pid = patient?.id != null ? String(patient.id) : '';
  const did = doctor?.id != null ? String(doctor.id) : '';

  return (
    <div className="space-y-4">
      {/* Back Navigation */}
      <div>
        {onBack ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="-ml-2 gap-1.5 h-8 text-muted-foreground"
            onClick={onBack}
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
            {backLabel}
          </Button>
        ) : backTo ? (
          <Link
            to={backTo}
            className={cn(
              buttonVariants({ variant: 'ghost', size: 'sm' }),
              '-ml-2 gap-1.5 h-8 text-muted-foreground'
            )}
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
            {backLabel}
          </Link>
        ) : null}
      </div>

      {/* Page Title */}
      <div className={compact ? 'space-y-1' : 'space-y-2'}>
        <h1 className={cn(
          'font-semibold tracking-tight',
          compact ? 'text-xl' : 'text-2xl'
        )}>
          Clinical Encounter
        </h1>
        <p className="text-sm text-muted-foreground">
          Visit details and clinical documentation
        </p>
      </div>

      {/* Main Encounter Card */}
      <Card className="overflow-hidden">
        <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
          <div className="flex flex-wrap items-center gap-2 justify-between">
            <CardTitle className={cn(
              'flex items-center gap-2',
              compact ? 'text-sm' : 'text-base'
            )}>
              <Calendar className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden />
              <span className="tabular-nums">{formattedDateTime}</span>
            </CardTitle>
            <Badge 
              variant={statusVariant(appointment.status)} 
              className="capitalize shrink-0"
            >
              {appointment.status}
            </Badge>
          </div>
        </CardHeader>
        
        <CardContent className={cn('text-sm space-y-3', compact && 'p-3 pt-0 space-y-2')}>
          {/* Patient Link */}
          {pid && (
            <div className="flex items-center gap-2">
              <User className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden />
              <span className="text-muted-foreground">Patient:</span>
              <Link
                to={`/doctor/patients/${pid}`}
                className="text-primary font-medium hover:underline truncate"
              >
                {patient.name || 'Unknown Patient'}
              </Link>
            </div>
          )}

          {/* Doctor Info (if available and different from current user) */}
          {did && doctor?.name && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Doctor:</span>
              <span className="font-medium truncate">{doctor.name}</span>
              {doctor.specialization && (
                <span className="text-muted-foreground text-xs truncate">
                  ({doctor.specialization})
                </span>
              )}
            </div>
          )}

          {/* Custom Actions Slot */}
          {actions && <div className="pt-1">{actions}</div>}
        </CardContent>
      </Card>
    </div>
  );
}
