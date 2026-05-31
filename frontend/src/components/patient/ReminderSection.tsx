/**
 * ReminderSection — patient-safe reminder display grouped by urgency.
 *
 * Phase P2 — Patient Communication Center.
 *
 * Architecture:
 *   - Renders reminders grouped by urgency (urgent / upcoming / completed)
 *   - Visual hierarchy: urgent items get prominent treatment
 *   - Mobile-first, calm design
 *   - Future-ready hooks for AI prioritization and smart nudges
 *
 * TODO: Phase 3 — AI reminder prioritization
 * TODO: Phase 3 — Smart nudges based on patient behavior
 * TODO: Phase 3 — Medication adherence tracking
 * TODO: Phase 3 — Voice reminder hooks
 */

import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Clock,
  CreditCard,
  Stethoscope,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ReminderCard } from '../../types';

dayjs.extend(relativeTime);

interface ReminderSectionProps {
  remindersByUrgency: {
    urgent: ReminderCard[];
    upcoming: ReminderCard[];
    completed: ReminderCard[];
  };
}

function ReminderCardItem({ reminder }: { reminder: ReminderCard }) {
  const navigate = useNavigate();
  const isUrgent = reminder.urgency === 'urgent';
  const isCompleted = reminder.urgency === 'completed';
  const reminderDate = dayjs(reminder.reminder_date);
  const isOverdue = isUrgent && reminderDate.isBefore(dayjs());

  const handleCtaAction = (action: string) => {
    switch (action) {
      case 'view_appointment':
        navigate('/patient/appointments');
        break;
      case 'view_bill':
        navigate('/patient/bills');
        break;
      case 'book_appointment':
        navigate('/patient/doctors');
        break;
      case 'view_timeline':
        navigate('/patient/timeline');
        break;
      default:
        break;
    }
  };

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-xl p-3 transition-all',
        isUrgent && 'bg-red-50 ring-1 ring-red-200 dark:bg-red-950/20 dark:ring-red-800/30',
        !isUrgent && !isCompleted && 'bg-muted/50',
        isCompleted && 'opacity-60'
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
          isUrgent && 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
          !isUrgent && !isCompleted && 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
          isCompleted && 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
        )}
      >
        {isCompleted ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : isUrgent ? (
          <AlertTriangle className="h-4 w-4" />
        ) : (
          <Clock className="h-4 w-4" />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p
            className={cn(
              'text-sm font-medium',
              isUrgent && 'text-red-800 dark:text-red-300'
            )}
          >
            {reminder.title}
          </p>
          {isOverdue && (
            <Badge variant="destructive" className="h-5 px-1.5 text-[10px]">
              Overdue
            </Badge>
          )}
        </div>

        <p className="mt-0.5 text-xs text-muted-foreground">
          {reminderDate.format('MMM D, YYYY')}
          {reminderDate.isAfter(dayjs()) && ` (${reminderDate.fromNow()})`}
        </p>

        {(reminder.doctor_name || reminder.clinic_name) && (
          <p className="mt-0.5 text-xs text-muted-foreground">
            {reminder.doctor_name && (
              <span className="flex items-center gap-1">
                <Stethoscope className="h-3 w-3 inline" /> {reminder.doctor_name}
              </span>
            )}
            {reminder.clinic_name && (
              <span className="ml-2">{reminder.clinic_name}</span>
            )}
          </p>
        )}

        {/* CTA actions */}
        {reminder.cta_actions.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {reminder.cta_actions.map((action, idx) => (
              <Button
                key={idx}
                variant={isUrgent ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleCtaAction(action)}
                className={cn(
                  'h-7 gap-1 rounded-full px-2.5 text-xs',
                  isUrgent && 'bg-red-600 hover:bg-red-700 text-white'
                )}
              >
                {action === 'view_appointment' && <Calendar className="h-3 w-3" />}
                {action === 'view_bill' && <CreditCard className="h-3 w-3" />}
                {action === 'book_appointment' && <Calendar className="h-3 w-3" />}
                {action
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, (c) => c.toUpperCase())}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function ReminderSection({ remindersByUrgency }: ReminderSectionProps) {
  const { urgent, upcoming, completed } = remindersByUrgency;
  const hasAny = urgent.length > 0 || upcoming.length > 0 || completed.length > 0;

  if (!hasAny) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <CheckCircle2 className="mb-2 h-8 w-8 text-emerald-400" />
        <p className="text-sm font-medium text-foreground">All caught up!</p>
        <p className="text-xs text-muted-foreground">No pending reminders.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ── Urgent ──────────────────────────────────────────────────────── */}
      {urgent.length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <h3 className="text-sm font-semibold text-red-700 dark:text-red-400">
              Urgent ({urgent.length})
            </h3>
          </div>
          <div className="space-y-2">
            {urgent.map((reminder) => (
              <ReminderCardItem key={reminder.id} reminder={reminder} />
            ))}
          </div>
        </div>
      )}

      {/* ── Upcoming ────────────────────────────────────────────────────── */}
      {upcoming.length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Clock className="h-4 w-4 text-amber-500" />
            <h3 className="text-sm font-semibold text-amber-700 dark:text-amber-400">
              Upcoming ({upcoming.length})
            </h3>
          </div>
          <div className="space-y-2">
            {upcoming.map((reminder) => (
              <ReminderCardItem key={reminder.id} reminder={reminder} />
            ))}
          </div>
        </div>
      )}

      {/* ── Completed ───────────────────────────────────────────────────── */}
      {completed.length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            <h3 className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
              Completed ({completed.length})
            </h3>
          </div>
          <div className="space-y-2">
            {completed.map((reminder) => (
              <ReminderCardItem key={reminder.id} reminder={reminder} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
