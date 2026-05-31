/**
 * ActivityTimelineCard — single timeline event with icon, actor, timestamp.
 *
 * Tablet-friendly: clear visual hierarchy, touch-friendly spacing.
 */
import { cn } from '@/lib/utils';
import {
  UserCheck,
  ClipboardCheck,
  Stethoscope,
  FileCheck,
  Receipt,
  DollarSign,
  Package,
  AlertTriangle,
  Truck,
  type LucideIcon,
} from 'lucide-react';
import type { ActivityStreamItem, ActivityType } from '../../services/clinicOperations';

interface ActivityTimelineCardProps {
  item: ActivityStreamItem;
  isLast?: boolean;
}

const activityIcons: Record<ActivityType, LucideIcon> = {
  patient_arrived: UserCheck,
  patient_checked_in: ClipboardCheck,
  vitals_completed: ClipboardCheck,
  consultation_started: Stethoscope,
  consultation_completed: FileCheck,
  bill_generated: Receipt,
  bill_paid: DollarSign,
  inventory_received: Package,
  low_stock_alert: AlertTriangle,
  procurement_received: Truck,
};

const activityColors: Record<ActivityType, string> = {
  patient_arrived: 'text-emerald-600 bg-emerald-100 dark:text-emerald-400 dark:bg-emerald-950',
  patient_checked_in: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-950',
  vitals_completed: 'text-cyan-600 bg-cyan-100 dark:text-cyan-400 dark:bg-cyan-950',
  consultation_started: 'text-violet-600 bg-violet-100 dark:text-violet-400 dark:bg-violet-950',
  consultation_completed: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-950',
  bill_generated: 'text-amber-600 bg-amber-100 dark:text-amber-400 dark:bg-amber-950',
  bill_paid: 'text-emerald-600 bg-emerald-100 dark:text-emerald-400 dark:bg-emerald-950',
  inventory_received: 'text-indigo-600 bg-indigo-100 dark:text-indigo-400 dark:bg-indigo-950',
  low_stock_alert: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-950',
  procurement_received: 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-950',
};

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;

  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

export function ActivityTimelineCard({ item, isLast }: ActivityTimelineCardProps) {
  const IconComponent = activityIcons[item.activity_type] || ClipboardCheck;

  return (
    <div className="relative flex gap-3 pb-4">
      {/* Timeline connector */}
      {!isLast && (
        <div className="absolute left-[18px] top-10 bottom-0 w-px bg-border" aria-hidden />
      )}

      {/* Icon */}
      <div
        className={cn(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
          activityColors[item.activity_type]
        )}
      >
        <IconComponent className="h-4 w-4" aria-hidden />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pt-1">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-foreground">{item.title}</p>
            {(item.patient_name || item.doctor_name) && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {item.patient_name && <span>{item.patient_name}</span>}
                {item.patient_name && item.doctor_name && <span> — </span>}
                {item.doctor_name && <span>{item.doctor_name}</span>}
              </p>
            )}
            {item.description && (
              <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
            )}
          </div>
          <span className="shrink-0 text-xs text-muted-foreground whitespace-nowrap">
            {formatTimestamp(item.created_at)}
          </span>
        </div>
      </div>
    </div>
  );
}
