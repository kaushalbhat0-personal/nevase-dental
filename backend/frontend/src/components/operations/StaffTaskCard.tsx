/**
 * StaffTaskCard — single task card with severity/category, action button.
 *
 * Tablet-friendly: large touch targets, clear urgency visualization.
 */
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  FileText,
  DollarSign,
  Package,
  ClipboardList,
  UserPlus,
  Pill,
  Users,
  ArrowRight,
  type LucideIcon,
} from 'lucide-react';
import type { OperationalTaskItem, TaskCategory, TaskPriority } from '../../services/clinicOperations';

interface StaffTaskCardProps {
  task: OperationalTaskItem;
  onAction?: (task: OperationalTaskItem) => void;
}

const categoryIcons: Record<TaskCategory, LucideIcon> = {
  encounter: FileText,
  billing: DollarSign,
  procurement: Package,
  inventory: ClipboardList,
  follow_up: UserPlus,
  prescription: Pill,
  queue: Users,
};

const priorityBorder: Record<TaskPriority, string> = {
  high: 'border-l-red-500',
  medium: 'border-l-amber-500',
  low: 'border-l-gray-400',
};

const priorityBg: Record<TaskPriority, string> = {
  high: 'bg-red-50/50 dark:bg-red-950/20',
  medium: 'bg-amber-50/50 dark:bg-amber-950/20',
  low: 'bg-gray-50/50 dark:bg-gray-900/20',
};

const priorityBadge: Record<TaskPriority, string> = {
  high: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  low: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
};

export function StaffTaskCard({ task, onAction }: StaffTaskCardProps) {
  const navigate = useNavigate();
  const IconComponent = categoryIcons[task.category] || ClipboardList;

  const handleAction = () => {
    if (onAction) {
      onAction(task);
    } else if (task.action_url) {
      navigate(task.action_url);
    }
  };

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border border-l-4 p-3 transition-colors hover:bg-accent/50 min-h-[64px]',
        priorityBorder[task.priority],
        priorityBg[task.priority]
      )}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white dark:bg-gray-800 shadow-sm">
        <IconComponent className="h-4 w-4 text-foreground" aria-hidden />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-medium text-foreground truncate">{task.title}</p>
          <span
            className={cn(
              'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
              priorityBadge[task.priority]
            )}
          >
            {task.priority}
          </span>
        </div>
        {task.description && (
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{task.description}</p>
        )}
        {(task.patient_name || task.doctor_name) && (
          <p className="text-xs text-muted-foreground mt-0.5">
            {task.patient_name && <span>{task.patient_name}</span>}
            {task.patient_name && task.doctor_name && <span> · </span>}
            {task.doctor_name && <span>{task.doctor_name}</span>}
          </p>
        )}
      </div>

      {task.is_actionable && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleAction}
          className="shrink-0 h-9 min-h-[36px] min-w-[36px]"
          aria-label={task.action_label || 'Take action'}
        >
          <ArrowRight className="h-4 w-4" aria-hidden />
          {task.action_label && (
            <span className="hidden sm:inline ml-1">{task.action_label}</span>
          )}
        </Button>
      )}
    </div>
  );
}
