/**
 * EncounterJourneySection — visual journey of an encounter lifecycle.
 *
 * Displays a timeline of encounter milestones:
 * - Appointment booked
 * - Visit completed
 * - Prescription generated
 * - Follow-up scheduled
 * - Documents available
 *
 * All derived from the existing encounter aggregate.
 * NO new backend tables.
 *
 * CRITICAL:
 * - SOAP internal sections are NEVER exposed
 * - Doctor-only notes are NEVER exposed
 * - Audit metadata is NEVER exposed
 */

import { Link } from 'react-router-dom';
import {
  CalendarCheck,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  FileText,
  Pill,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { EncounterDetailAggregate } from '../../types';
import { formatShortDate } from '../../utils/patientTimeline';

interface EncounterJourneySectionProps {
  encounter: EncounterDetailAggregate;
  documentCount?: number;
  className?: string;
}

interface JourneyStep {
  icon: React.ReactNode;
  label: string;
  date: string | null;
  completed: boolean;
  action?: {
    label: string;
    to: string;
  };
}

export function EncounterJourneySection({
  encounter,
  documentCount = 0,
  className,
}: EncounterJourneySectionProps) {
  const { appointment, prescriptions } = encounter;

  const steps: JourneyStep[] = [
    {
      icon: <CalendarCheck className="h-4 w-4" />,
      label: 'Appointment booked',
      date: (appointment.created_at ?? appointment.appointment_time) ?? null,
      completed: true,
    },
    {
      icon: <CheckCircle2 className="h-4 w-4" />,
      label: 'Visit completed',
      date: appointment.status === 'completed' ? (appointment.appointment_time ?? null) : null,
      completed: appointment.status === 'completed',
    },
    {
      icon: <Pill className="h-4 w-4" />,
      label: 'Prescription generated',
      date: prescriptions && prescriptions.length > 0
        ? (appointment.appointment_time ?? null)
        : null,
      completed: (prescriptions?.length ?? 0) > 0,
      action: (prescriptions?.length ?? 0) > 0
        ? { label: 'View medicines', to: '/patient/medications' }
        : undefined,
    },
    {
      icon: <ClipboardList className="h-4 w-4" />,
      label: 'Follow-up scheduled',
      date: appointment.follow_up_date ?? null,
      completed: !!appointment.follow_up_date,
      action: appointment.follow_up_date
        ? { label: 'View details', to: '/patient/care/follow-ups' }
        : undefined,
    },
    {
      icon: <FileText className="h-4 w-4" />,
      label: 'Documents available',
      date: documentCount > 0 ? (appointment.appointment_time ?? null) : null,
      completed: documentCount > 0,
      action: documentCount > 0
        ? { label: `${documentCount} document${documentCount > 1 ? 's' : ''}`, to: '/patient/care/documents' }
        : undefined,
    },
  ];

  return (
    <div className={cn('rounded-2xl border border-border/60 bg-card shadow-sm', className)}>
      <div className="px-5 pt-4 pb-3">
        <h2 className="text-sm font-semibold text-foreground">Visit Journey</h2>
      </div>

      <div className="px-5 pb-5">
        <div className="relative">
          {/* Vertical connector line */}
          <div className="absolute left-[17px] top-2 bottom-2 w-px bg-border/60" aria-hidden />

          <div className="space-y-0">
            {steps.map((step, idx) => (
              <div key={idx} className="relative flex items-start gap-4 pb-5 last:pb-0">
                {/* Step indicator */}
                <div
                  className={cn(
                    'relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 transition-colors',
                    step.completed
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-muted-foreground/20 bg-muted/30 text-muted-foreground/40',
                  )}
                >
                  {step.icon}
                </div>

                {/* Step content */}
                <div className="min-w-0 flex-1 pt-1">
                  <p
                    className={cn(
                      'text-sm font-medium',
                      step.completed ? 'text-foreground' : 'text-muted-foreground/50',
                    )}
                  >
                    {step.label}
                  </p>
                  {step.date && (
                    <p className="text-xs text-muted-foreground/60 mt-0.5">
                      {formatShortDate(step.date)}
                    </p>
                  )}
                  {step.action && step.completed && (
                    <Link
                      to={step.action.to}
                      className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                      {step.action.label}
                      <ChevronRight className="h-3 w-3" />
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
