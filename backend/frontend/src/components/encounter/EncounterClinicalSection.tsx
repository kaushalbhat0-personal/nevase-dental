import { Stethoscope, FileText, ClipboardList } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { Appointment } from '../../types';

interface EncounterClinicalSectionProps {
  appointment: Appointment;
  /** Mobile-optimized compact mode */
  compact?: boolean;
  /** Edit mode for inline editing (future enhancement) */
  editable?: boolean;
}

/**
 * EncounterClinicalSection - Clinical encounter documentation display
 * 
 * Clinical-first hierarchy elements #2-4:
 * 2. Diagnosis (most important clinical output)
 * 3. Treatment summary (what was done)
 * 4. Clinical notes (detailed observations)
 * 
 * Future extension hooks (Phase 2):
 * - TODO: Add prescriptions subsection
 * - TODO: Add vitals subsection
 * - TODO: Add SOAP notes structured view
 * - TODO: Add AI summary integration
 * 
 * Mobile considerations:
 * - Clear visual hierarchy with distinct sections
 * - Collapsible sections for long content
 * - Scrollable within the card if needed
 */
export function EncounterClinicalSection({
  appointment,
  compact = false,
  editable = false,
}: EncounterClinicalSectionProps) {
  const hasClinicalData = appointment.diagnosis || 
    appointment.treatment_summary || 
    appointment.clinical_notes ||
    appointment.completion_notes;

  if (!hasClinicalData && !editable) {
    return (
      <Card className={cn('bg-muted/30', compact && 'opacity-75')}>
        <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
          <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
            <Stethoscope className="h-4 w-4 text-primary shrink-0" aria-hidden />
            Clinical Documentation
          </CardTitle>
        </CardHeader>
        <CardContent className={cn(compact && 'p-3 pt-0')}>
          <p className="text-sm text-muted-foreground italic">
            No clinical documentation recorded for this encounter.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('overflow-hidden', compact && 'text-sm')}>
      <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
        <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
          <Stethoscope className="h-4 w-4 text-primary shrink-0" aria-hidden />
          Clinical Documentation
        </CardTitle>
      </CardHeader>
      
      <CardContent className={cn('space-y-4', compact && 'p-3 pt-0 space-y-3')}>
        {/* 
          Clinical-first hierarchy:
          1. Diagnosis (primary clinical output)
          2. Treatment summary
          3. Clinical notes (detailed observations)
        */}
        
        {/* Diagnosis - Priority 1 */}
        {appointment.diagnosis && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <ClipboardList className="h-3.5 w-3.5 text-primary/70 shrink-0" aria-hidden />
              <h3 className="font-medium text-sm text-foreground">Diagnosis</h3>
            </div>
            <p className={cn(
              'text-muted-foreground leading-relaxed',
              compact ? 'text-sm' : 'text-sm'
            )}>
              {appointment.diagnosis}
            </p>
          </div>
        )}

        {/* Treatment Summary - Priority 2 */}
        {appointment.treatment_summary && (
          <div className={cn('space-y-1.5', appointment.diagnosis && 'border-t border-border/50 pt-3')}>
            <div className="flex items-center gap-2">
              <FileText className="h-3.5 w-3.5 text-primary/70 shrink-0" aria-hidden />
              <h3 className="font-medium text-sm text-foreground">Treatment Summary</h3>
            </div>
            <p className={cn(
              'text-muted-foreground leading-relaxed',
              compact ? 'text-sm' : 'text-sm'
            )}>
              {appointment.treatment_summary}
            </p>
          </div>
        )}

        {/* Clinical Notes - Priority 3 */}
        {appointment.clinical_notes && (
          <div className={cn(
            'space-y-1.5',
            (appointment.diagnosis || appointment.treatment_summary) && 'border-t border-border/50 pt-3'
          )}>
            <div className="flex items-center gap-2">
              <FileText className="h-3.5 w-3.5 text-primary/70 shrink-0" aria-hidden />
              <h3 className="font-medium text-sm text-foreground">Clinical Notes</h3>
            </div>
            <p className={cn(
              'text-muted-foreground leading-relaxed whitespace-pre-wrap',
              compact ? 'text-sm' : 'text-sm'
            )}>
              {appointment.clinical_notes}
            </p>
          </div>
        )}

        {/* Legacy completion_notes - preserved for backward compatibility */}
        {appointment.completion_notes && (
          <div className={cn(
            'space-y-1.5',
            (appointment.diagnosis || appointment.treatment_summary || appointment.clinical_notes) && 'border-t border-border/50 pt-3'
          )}>
            <h3 className="font-medium text-sm text-muted-foreground flex items-center gap-2">
              <span className="text-xs bg-muted px-1.5 py-0.5 rounded">Legacy</span>
              Notes
            </h3>
            <p className="text-muted-foreground text-sm leading-relaxed">
              {appointment.completion_notes}
            </p>
          </div>
        )}

        {/* 
          TODO: Future Phase 2 clinical extensions
          
          {/* Prescriptions subsection }
          {prescriptions && prescriptions.length > 0 && (
            <div className="border-t border-border/50 pt-3">
              <EncounterPrescriptionsSubsection prescriptions={prescriptions} />
            </div>
          )}
          
          {/* Vitals subsection }
          {vitals && (
            <div className="border-t border-border/50 pt-3">
              <EncounterVitalsSubsection vitals={vitals} />
            </div>
          )}
          
          {/* SOAP Notes subsection }
          {soapNotes && (
            <div className="border-t border-border/50 pt-3">
              <EncounterSoapNotesSubsection notes={soapNotes} />
            </div>
          )}
          
          {/* AI Summary subsection }
          {aiSummary && (
            <div className="border-t border-border/50 pt-3">
              <EncounterAiSummarySubsection summary={aiSummary} />
            </div>
          )}
        */}
      </CardContent>
    </Card>
  );
}
