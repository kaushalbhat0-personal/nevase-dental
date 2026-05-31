/**
 * AlertSeverityChip — small badge/chip showing alert severity.
 *
 * Tablet-friendly: ≥32px height, clear color coding.
 */
import { cn } from '@/lib/utils';
import type { AlertSeverity } from '../../services/clinicOperations';

interface AlertSeverityChipProps {
  severity: AlertSeverity;
  className?: string;
}

const severityStyles: Record<AlertSeverity, string> = {
  critical:
    'bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800',
  warning:
    'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800',
  info: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800',
};

const severityLabels: Record<AlertSeverity, string> = {
  critical: 'Critical',
  warning: 'Warning',
  info: 'Info',
};

export function AlertSeverityChip({ severity, className }: AlertSeverityChipProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold leading-none min-h-[22px]',
        severityStyles[severity],
        className
      )}
    >
      {severityLabels[severity]}
    </span>
  );
}
