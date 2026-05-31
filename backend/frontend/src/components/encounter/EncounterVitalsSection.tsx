import { HeartPulse, Thermometer, Droplet, Scale, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { VitalSigns } from '../../types';

interface EncounterVitalsSectionProps {
  vitals?: VitalSigns | null;
  compact?: boolean;
}

export function EncounterVitalsSection({ vitals, compact = false }: EncounterVitalsSectionProps) {
  const hasVitals = vitals != null && (
    vitals.temperature != null ||
    vitals.bp_systolic != null ||
    vitals.bp_diastolic != null ||
    vitals.pulse != null ||
    vitals.weight != null ||
    vitals.spo2 != null
  );

  return (
    <Card className={cn('overflow-hidden', compact && 'text-sm')}>
      <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
        <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
          <Activity className="h-4 w-4 text-primary shrink-0" aria-hidden />
          Vital Signs
        </CardTitle>
      </CardHeader>
      <CardContent className={cn('space-y-4', compact && 'p-3 pt-0')}>
        {!hasVitals ? (
          <p className="text-sm text-muted-foreground italic">
            No structured vital signs recorded for this encounter.
          </p>
        ) : (
          <div className={cn('grid gap-3', compact ? 'grid-cols-1' : 'grid-cols-2')}>
            {vitals?.temperature != null && (
              <div className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <Thermometer className="h-4 w-4 text-primary shrink-0" aria-hidden />
                  Temperature
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{vitals.temperature.toFixed(1)} °C</p>
              </div>
            )}
            {(vitals?.bp_systolic != null || vitals?.bp_diastolic != null) && (
              <div className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <HeartPulse className="h-4 w-4 text-primary shrink-0" aria-hidden />
                  Blood Pressure
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {vitals?.bp_systolic ?? '–'}/{vitals?.bp_diastolic ?? '–'} mmHg
                </p>
              </div>
            )}
            {vitals?.pulse != null && (
              <div className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <Droplet className="h-4 w-4 text-primary shrink-0" aria-hidden />
                  Pulse
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{vitals.pulse} bpm</p>
              </div>
            )}
            {vitals?.weight != null && (
              <div className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <Scale className="h-4 w-4 text-primary shrink-0" aria-hidden />
                  Weight
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{vitals.weight.toFixed(1)} kg</p>
              </div>
            )}
            {vitals?.respiratory_rate != null && (
              <div className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <Activity className="h-4 w-4 text-primary shrink-0" aria-hidden />
                  Respiratory Rate
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{vitals.respiratory_rate} breaths/min</p>
              </div>
            )}
            {vitals?.height != null && (
              <div className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <Scale className="h-4 w-4 text-primary shrink-0" aria-hidden />
                  Height
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{vitals.height.toFixed(1)} cm</p>
              </div>
            )}
            {vitals?.bmi != null && (
              <div className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <Scale className="h-4 w-4 text-primary shrink-0" aria-hidden />
                  BMI
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{vitals.bmi.toFixed(1)} kg/m²</p>
              </div>
            )}
            {vitals?.notes && (
              <div className="rounded-lg border border-border p-3 col-span-full">
                <p className="text-xs text-muted-foreground">Notes</p>
                <p className="text-sm text-foreground">{vitals.notes}</p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
