import { CalendarDays, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { FollowUpPlan } from '../../types';

interface EncounterFollowUpSectionProps {
  followUp?: FollowUpPlan | null;
  compact?: boolean;
}

export function EncounterFollowUpSection({
  followUp,
  compact = false,
}: EncounterFollowUpSectionProps) {
  const hasFollowUp = Boolean(followUp?.follow_up_date || followUp?.follow_up_notes);

  return (
    <Card className={cn('overflow-hidden', compact && 'text-sm')}>
      <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
        <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
          <CalendarDays className="h-4 w-4 text-primary shrink-0" aria-hidden />
          Follow-up Plan
        </CardTitle>
      </CardHeader>

      <CardContent className={cn('space-y-4', compact && 'p-3 pt-0')}>
        {!hasFollowUp ? (
          <p className="text-sm text-muted-foreground italic">
            No follow-up plan has been recorded for this encounter.
          </p>
        ) : (
          <div className="space-y-3">
            {followUp?.follow_up_date ? (
              <div className="flex items-center gap-2 text-sm text-foreground">
                <ArrowRight className="h-4 w-4 text-primary shrink-0" aria-hidden />
                <span>Next review scheduled for </span>
                <strong>{new Date(followUp.follow_up_date).toLocaleString()}</strong>
              </div>
            ) : null}

            {followUp?.follow_up_notes ? (
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                  Notes
                </p>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {followUp.follow_up_notes}
                </p>
              </div>
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
