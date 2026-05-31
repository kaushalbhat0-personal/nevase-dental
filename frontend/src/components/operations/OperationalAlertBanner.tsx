/**
 * OperationalAlertBanner — animated alert banner with dismiss.
 *
 * - Critical alerts persist until dismissed
 * - Warning auto-dismisses after 15s
 * - Info auto-dismisses after 10s
 * - Tablet-friendly: large touch targets, high contrast
 */
import { useCallback, useEffect, useState } from 'react';
import { X, AlertTriangle, AlertCircle, Package, Clock, DollarSign, UserX, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AlertSeverityChip } from './AlertSeverityChip';
import type { OperationalAlertItem, AlertCategory } from '../../services/clinicOperations';

interface OperationalAlertBannerProps {
  alert: OperationalAlertItem;
  onDismiss: (id: string) => void;
  autoDismiss?: boolean;
}

const categoryIcons: Record<AlertCategory, typeof AlertTriangle> = {
  low_stock: Package,
  overdue_appointment: Clock,
  pending_billing: DollarSign,
  delayed_queue: Clock,
  missed_follow_up: UserX,
  incomplete_encounter: FileText,
};

const severityBorder: Record<string, string> = {
  critical: 'border-l-red-500',
  warning: 'border-l-amber-500',
  info: 'border-l-blue-500',
};

const severityBg: Record<string, string> = {
  critical: 'bg-red-50 dark:bg-red-950/40',
  warning: 'bg-amber-50 dark:bg-amber-950/40',
  info: 'bg-blue-50 dark:bg-blue-950/40',
};

export function OperationalAlertBanner({
  alert,
  onDismiss,
  autoDismiss = true,
}: OperationalAlertBannerProps) {
  const [visible, setVisible] = useState(true);
  const [exiting, setExiting] = useState(false);

  const handleDismiss = useCallback(() => {
    setExiting(true);
    setTimeout(() => {
      setVisible(false);
      onDismiss(alert.id);
    }, 300);
  }, [alert.id, onDismiss]);

  useEffect(() => {
    if (!autoDismiss) return;
    const timeout =
      alert.severity === 'critical'
        ? null
        : alert.severity === 'warning'
          ? 15000
          : 10000;
    if (timeout === null) return;
    const timer = setTimeout(handleDismiss, timeout);
    return () => clearTimeout(timer);
  }, [alert.severity, autoDismiss, handleDismiss]);

  if (!visible) return null;

  const IconComponent = categoryIcons[alert.category] || AlertCircle;

  return (
    <div
      className={cn(
        'relative flex items-start gap-3 rounded-lg border border-l-4 p-4 shadow-sm transition-all duration-300 min-h-[56px]',
        severityBorder[alert.severity],
        severityBg[alert.severity],
        exiting ? 'opacity-0 -translate-y-2' : 'opacity-100 translate-y-0'
      )}
      role="alert"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/80 dark:bg-gray-800/80">
        <IconComponent className="h-4 w-4 text-foreground" aria-hidden />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-medium text-foreground">{alert.title}</p>
          <AlertSeverityChip severity={alert.severity} />
        </div>
        {alert.description && (
          <p className="mt-0.5 text-sm text-muted-foreground">{alert.description}</p>
        )}
      </div>

      <button
        type="button"
        onClick={handleDismiss}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full hover:bg-black/5 dark:hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="Dismiss alert"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
