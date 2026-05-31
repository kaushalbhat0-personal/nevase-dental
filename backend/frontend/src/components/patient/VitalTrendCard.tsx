/**
 * VitalTrendCard — single vital sign display card for the vitals history page.
 *
 * Shows metric name, value, unit, and date.
 * Color-coded for normal/abnormal ranges.
 * Large touch target for mobile.
 */

import dayjs from 'dayjs';
import { cn } from '@/lib/utils';

interface VitalTrendCardProps {
  /** Display label (e.g. "Blood Pressure", "Pulse") */
  label: string;
  /** Current/most recent value */
  value: string | number | null;
  /** Unit of measurement (e.g. "mmHg", "bpm", "°F", "%", "kg") */
  unit: string;
  /** Date of the most recent reading */
  date: string | null;
  /** Optional sub-value (e.g. diastolic BP) */
  subValue?: string | number | null;
  /** Optional sub-value label */
  subLabel?: string;
  /** Whether the value is within normal range */
  isNormal?: boolean;
  /** Icon to display */
  icon?: React.ReactNode;
}

export function VitalTrendCard({
  label,
  value,
  unit,
  date,
  subValue,
  subLabel,
  isNormal = true,
  icon,
}: VitalTrendCardProps) {
  if (value === null || value === undefined) return null;

  return (
    <div
      className={cn(
        'flex min-h-[88px] touch-manipulation flex-col rounded-2xl border p-4 transition hover:shadow-sm',
        isNormal
          ? 'border-border/60 bg-white'
          : 'border-red-200 bg-red-50/40 dark:border-red-800/40 dark:bg-red-950/10'
      )}
    >
      <div className="flex items-center gap-2">
        {icon && <span className="shrink-0 text-muted-foreground">{icon}</span>}
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
      </div>

      <div className="mt-1.5 flex items-baseline gap-1.5">
        <span
          className={cn(
            'text-2xl font-bold tracking-tight',
            isNormal ? 'text-foreground' : 'text-red-600 dark:text-red-400'
          )}
        >
          {value}
        </span>
        <span className="text-sm text-muted-foreground">{unit}</span>

        {subValue !== null && subValue !== undefined && (
          <span className="ml-2 text-sm text-muted-foreground">
            <span className="text-xs text-muted-foreground/60">
              {subLabel ? `${subLabel} ` : ''}
            </span>
            <span className="font-medium text-foreground">{subValue}</span>
          </span>
        )}
      </div>

      {date && (
        <p className="mt-1 text-xs text-muted-foreground/60">
          {dayjs(date).format('MMM D, YYYY')}
        </p>
      )}
    </div>
  );
}
