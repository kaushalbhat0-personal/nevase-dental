/**
 * OperationalActivityFeed — chronological activity list with grouping.
 *
 * Groups events into "Today" and "Earlier" sections.
 * Tablet-friendly: scrollable, auto-refresh ready.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshCw, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ActivityTimelineCard } from './ActivityTimelineCard';
import { operationsApi } from '../../services/clinicOperations';
import type { ActivityStreamItem } from '../../services/clinicOperations';


interface OperationalActivityFeedProps {
  /** Auto-refresh interval in ms. Default 30000 (30s). Set 0 to disable. */
  refreshInterval?: number;
  maxItems?: number;
}

function isToday(date: Date): boolean {
  const now = new Date();
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  );
}

export function OperationalActivityFeed({
  refreshInterval = 30000,
  maxItems = 50,
}: OperationalActivityFeedProps) {
  const [items, setItems] = useState<ActivityStreamItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchActivity = useCallback(async () => {
    try {
      const data = await operationsApi.getActivityStream(0, maxItems);
      setItems(data.items);
      setError(null);
    } catch (e) {
      if (!error) setError('Could not load activity feed');
    } finally {
      setLoading(false);
    }
  }, [maxItems, error]);

  useEffect(() => {
    void fetchActivity();
    if (refreshInterval > 0) {
      intervalRef.current = setInterval(fetchActivity, refreshInterval);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchActivity, refreshInterval]);

  const todayItems = items.filter((i) => isToday(new Date(i.created_at)));
  const earlierItems = items.filter((i) => !isToday(new Date(i.created_at)));

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3 sticky top-0 bg-card z-10">
        <CardTitle className="text-base flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" aria-hidden />
          Activity
        </CardTitle>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => { setLoading(true); void fetchActivity(); }}
          disabled={loading}
          className="h-9 min-h-[36px]"
        >
          <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} aria-hidden />
          <span className="sr-only">Refresh</span>
        </Button>
      </CardHeader>
      <CardContent className="space-y-0">
        {loading && items.length === 0 && (
          <p className="text-sm text-muted-foreground py-4 text-center">Loading activity…</p>
        )}
        {error && (
          <p className="text-sm text-destructive py-4 text-center">{error}</p>
        )}
        {!loading && items.length === 0 && (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No recent activity
          </p>
        )}

        {todayItems.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Today
            </h4>
            {todayItems.map((item, idx) => (
              <ActivityTimelineCard
                key={item.id}
                item={item}
                isLast={idx === todayItems.length - 1 && earlierItems.length === 0}
              />
            ))}
          </div>
        )}

        {earlierItems.length > 0 && (
          <div className={todayItems.length > 0 ? 'mt-2' : ''}>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Earlier
            </h4>
            {earlierItems.map((item, idx) => (
              <ActivityTimelineCard
                key={item.id}
                item={item}
                isLast={idx === earlierItems.length - 1}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}


