import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, Clock, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Appointment, Bill, VisitAggregate } from '../../types';

interface TimelineEvent {
  id: string;
  type: 'visit' | 'bill' | 'note';
  timestamp: string;
  title: string;
  description?: string;
  status?: string;
  linkTo?: string;
}

interface EncounterTimelineSectionProps {
  /** Current encounter for context */
  currentEncounter: Appointment;
  /** Previous visit aggregates for this patient */
  previousVisits?: VisitAggregate[];
  /** Previous bills for this patient */
  previousBills?: Bill[];
  /** Mobile-optimized compact mode */
  compact?: boolean;
  /** Maximum items to show */
  limit?: number;
}

function formatRelativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '—';
  
  const diff = Date.now() - t;
  const minutes = Math.floor(diff / 60_000);
  const hours = Math.floor(diff / 3_600_000);
  const days = Math.floor(diff / 86_400_000);
  
  if (days > 30) {
    const months = Math.floor(days / 30);
    return months === 1 ? '1 month ago' : `${months} months ago`;
  }
  if (days > 0) return days === 1 ? 'Yesterday' : `${days} days ago`;
  if (hours > 0) return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
  if (minutes > 0) return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`;
  return 'Just now';
}

function appointmentStatusVariant(
  s: Appointment['status']
): 'default' | 'secondary' | 'outline' | 'destructive' {
  if (s === 'completed') return 'secondary';
  if (s === 'cancelled') return 'destructive';
  if (s === 'scheduled' || s === 'pending') return 'default';
  return 'outline';
}

/**
 * EncounterTimelineSection - Timeline of patient encounters
 * 
 * Clinical-first context: Shows the patient's visit history
 * to provide context for the current encounter.
 * 
 * Future extension hooks (Phase 2):
 * - TODO: Add prescription events to timeline
 * - TODO: Add lab result events
 * - TODO: Add follow-up tracking
 * - TODO: Add attachment uploads
 * 
 * Mobile considerations:
 * - Chronological order (newest first)
 * - Clear visual separation
 * - Condensed view for limited space
 */
export function EncounterTimelineSection({
  currentEncounter,
  previousVisits = [],
  previousBills = [],
  compact = false,
  limit = 5,
}: EncounterTimelineSectionProps) {
  const timelineEvents = useMemo((): TimelineEvent[] => {
    const events: TimelineEvent[] = [];

    // Add previous visits
    for (const visit of previousVisits) {
      const a = visit.appointment;
      const time = a.appointment_time || a.scheduled_at;
      if (!time) continue;

      events.push({
        id: `visit-${a.id}`,
        type: 'visit',
        timestamp: time,
        title: 'Visit',
        description: a.diagnosis || a.treatment_summary || undefined,
        status: a.status,
        linkTo: `/doctor/appointments/${a.id}`,
      });
    }

    // Add previous bills (that aren't linked to appointments we've already shown)
    const linkedBillIds = new Set(
      previousVisits
        .filter(v => v.bill)
        .map(v => String(v.bill!.id))
    );

    for (const bill of previousBills) {
      if (linkedBillIds.has(String(bill.id))) continue;
      
      events.push({
        id: `bill-${bill.id}`,
        type: 'bill',
        timestamp: bill.created_at,
        title: `Bill ${bill.currency} ${Number(bill.amount).toFixed(0)}`,
        description: bill.description || undefined,
        status: bill.status,
        linkTo: `/doctor/bills/${bill.id}`,
      });
    }

    // Sort by timestamp (newest first)
    return events
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, limit);
  }, [previousVisits, previousBills, limit]);

  if (timelineEvents.length === 0) {
    return (
      <Card className={cn('bg-muted/30', compact && 'opacity-75')}>
        <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
          <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
            <Clock className="h-4 w-4 text-primary shrink-0" aria-hidden />
            Patient History
          </CardTitle>
        </CardHeader>
        <CardContent className={cn(compact && 'p-3 pt-0')}>
          <p className="text-sm text-muted-foreground italic">
            No previous encounters recorded for this patient.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('overflow-hidden', compact && 'text-sm')}>
      <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
        <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
          <Clock className="h-4 w-4 text-primary shrink-0" aria-hidden />
          Patient History
          <span className="text-xs font-normal text-muted-foreground ml-auto">
            Recent {timelineEvents.length}
          </span>
        </CardTitle>
      </CardHeader>
      
      <CardContent className={cn('space-y-1', compact && 'p-3 pt-0')}>
        <ul className="space-y-2">
          {timelineEvents.map((event, idx) => (
            <li 
              key={event.id}
              className={cn(
                'flex items-start gap-3 p-2 rounded-md',
                idx % 2 === 0 ? 'bg-muted/20' : 'bg-transparent'
              )}
            >
              {/* Icon based on type */}
              <div className="shrink-0 mt-0.5">
                {event.type === 'visit' && (
                  <div className="h-7 w-7 rounded-full bg-emerald-500/10 flex items-center justify-center">
                    <Calendar className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                )}
                {event.type === 'bill' && (
                  <div className="h-7 w-7 rounded-full bg-amber-500/10 flex items-center justify-center">
                    <Clock className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm">{event.title}</span>
                  {event.status && event.type === 'visit' && (
                    <Badge 
                      variant={appointmentStatusVariant(event.status as Appointment['status'])}
                      className="text-xs capitalize"
                    >
                      {event.status}
                    </Badge>
                  )}
                  {event.status && event.type === 'bill' && (
                    <Badge 
                      variant={event.status === 'paid' ? 'secondary' : 'outline'}
                      className="text-xs capitalize"
                    >
                      {event.status}
                    </Badge>
                  )}
                </div>
                
                {event.description && (
                  <p className="text-xs text-muted-foreground truncate">
                    {event.description}
                  </p>
                )}
                
                <p className="text-xs text-muted-foreground tabular-nums">
                  {formatRelativeTime(event.timestamp)}
                </p>
              </div>

              {/* Link arrow */}
              {event.linkTo && (
                <Link
                  to={event.linkTo}
                  className="shrink-0 p-1 text-muted-foreground hover:text-primary transition-colors"
                  aria-label={`View ${event.type}`}
                >
                  <ArrowRight className="h-4 w-4" />
                </Link>
              )}
            </li>
          ))}
        </ul>

        {/* View all link */}
        {previousVisits.length > limit && (
          <div className="border-t border-border/50 pt-2 mt-2">
            <Link
              to={`/doctor/patients/${currentEncounter.patient_id}`}
              className="text-sm text-primary font-medium hover:underline inline-flex items-center gap-1.5"
            >
              View full patient history
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
