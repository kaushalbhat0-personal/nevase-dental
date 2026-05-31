import { ClipboardList, FileText } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { Prescription as PrescriptionType } from '../../types';

interface EncounterPrescriptionsSectionProps {
  prescriptions?: PrescriptionType[] | null;
  compact?: boolean;
}

export function EncounterPrescriptionsSection({
  prescriptions,
  compact = false,
}: EncounterPrescriptionsSectionProps) {
  const hasPrescriptions = prescriptions && prescriptions.length > 0;

  return (
    <Card className={cn('overflow-hidden', compact && 'text-sm')}>
      <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
        <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
          <FileText className="h-4 w-4 text-primary shrink-0" aria-hidden />
          Prescriptions
        </CardTitle>
      </CardHeader>

      <CardContent className={cn('space-y-4', compact && 'p-3 pt-0')}>
        {!hasPrescriptions ? (
          <p className="text-sm text-muted-foreground italic">
            No formal prescriptions recorded for this encounter.
          </p>
        ) : (
          <div className="space-y-4">
            {prescriptions!.map((prescription) => (
              <div key={prescription.id} className="rounded-xl border border-border/50 p-4 bg-muted/10">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <ClipboardList className="h-4 w-4 text-primary shrink-0" aria-hidden />
                    Prescription #{String(prescription.id).slice(0, 8)}
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(prescription.created_at).toLocaleString()}
                  </span>
                </div>

                {prescription.notes ? (
                  <div className="mb-3 text-sm text-muted-foreground">
                    {prescription.notes}
                  </div>
                ) : null}

                <ul className="space-y-3">
                  {prescription.items.map((item, itemIndex) => (
                    <li key={`${prescription.id}-${itemIndex}`} className="rounded-lg border border-border p-3 bg-background">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-foreground">
                          {item.medicine_name}
                        </span>
                        {item.dosage ? (
                          <span className="text-xs text-muted-foreground">
                            {item.dosage}
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-2 text-sm text-muted-foreground space-y-1">
                        {item.frequency ? <p>Frequency: {item.frequency}</p> : null}
                        {item.duration ? <p>Duration: {item.duration}</p> : null}
                        {item.instructions ? <p>Instructions: {item.instructions}</p> : null}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
