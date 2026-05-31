import { FileText, Stethoscope, Brain, ClipboardList, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { hasMedicineLikeNotes, hasStructuredMedicines } from '@/lib/medicinePatternDetector';
import type { Appointment } from '../../types';

interface EncounterSOAPSectionProps {
  appointment: Appointment;
  compact?: boolean;
}

export function EncounterSOAPSection({ appointment, compact = false }: EncounterSOAPSectionProps) {
  const hasSOAP = appointment.subjective_notes || appointment.objective_notes ||
                  appointment.assessment_notes || appointment.plan_notes;
  const hasMedicineInstructions = hasMedicineLikeNotes(appointment);
  const hasStructuredMedicinesPresent = hasStructuredMedicines(appointment);
  const showWarning = hasMedicineInstructions && !hasStructuredMedicinesPresent;

  return (
    <Card className={cn('overflow-hidden', compact && 'text-sm')}>
      <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
        <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
          <FileText className="h-4 w-4 text-primary shrink-0" aria-hidden />
          SOAP Notes
        </CardTitle>
      </CardHeader>
      <CardContent className={cn('space-y-4', compact && 'p-3 pt-0')}>
        {!hasSOAP ? (
          <p className="text-sm text-muted-foreground italic">
            No structured SOAP notes recorded for this encounter.
          </p>
        ) : (
          <>
            {showWarning && (
              <div className="flex items-start gap-3 mb-4">
                <AlertTriangle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-medium text-destructive">
                    Medicine-like instructions detected in notes
                  </p>
                  <p className="text-xs text-destructive/80">
                    Consider using the Medicines Given or Prescriptions sections for structured medication tracking.
                  </p>
                </div>
              </div>
            )}
            <div className="space-y-4">
              {appointment.subjective_notes && (
                <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
                    <FileText className="h-4 w-4 text-primary shrink-0" aria-hidden />
                    Subjective
                  </div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{appointment.subjective_notes}</p>
                </div>
              )}
              {appointment.objective_notes && (
                <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
                    <Stethoscope className="h-4 w-4 text-primary shrink-0" aria-hidden />
                    Objective
                  </div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{appointment.objective_notes}</p>
                </div>
              )}
              {appointment.assessment_notes && (
                <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
                    <Brain className="h-4 w-4 text-primary shrink-0" aria-hidden />
                    Assessment
                  </div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{appointment.assessment_notes}</p>
                </div>
              )}
              {appointment.plan_notes && (
                <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
                    <ClipboardList className="h-4 w-4 text-primary shrink-0" aria-hidden />
                    Plan
                  </div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{appointment.plan_notes}</p>
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}