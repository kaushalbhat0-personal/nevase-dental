/**
 * OperationalTaskList — task list grouped by severity and category.
 *
 * Groups tasks into High/Medium/Low priority sections.
 * Tablet-friendly: fast scanning, clear visual hierarchy.
 */
import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, AlertCircle, Info, RefreshCw, ClipboardList } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StaffTaskCard } from './StaffTaskCard';
import { operationsApi } from '../../services/clinicOperations';
import type { OperationalTaskItem, OperationalTaskList as TaskListData } from '../../services/clinicOperations';

interface OperationalTaskListProps {
  /** Auto-refresh interval in ms. Default 30000 (30s). Set 0 to disable. */
  refreshInterval?: number;
}

export function OperationalTaskList({ refreshInterval = 30000 }: OperationalTaskListProps) {
  const [tasks, setTasks] = useState<TaskListData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await operationsApi.getTasks();
      setTasks(data);
      setError(null);
    } catch (e) {
      if (!tasks) setError('Could not load tasks');
    } finally {
      setLoading(false);
    }
  }, [tasks]);

  useEffect(() => {
    void fetchTasks();
    if (refreshInterval > 0) {
      const interval = setInterval(fetchTasks, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchTasks, refreshInterval]);

  const handleTaskAction = (task: OperationalTaskItem) => {
    // Default action: navigate to action_url if available
    if (task.action_url) {
      window.location.href = task.action_url;
    }
  };

  const sections: Array<{
    key: 'high_priority' | 'medium_priority' | 'low_priority';
    label: string;
    icon: typeof AlertTriangle;
    iconClass: string;
    items: OperationalTaskItem[];
  }> = [
    {
      key: 'high_priority',
      label: 'High Priority',
      icon: AlertTriangle,
      iconClass: 'text-red-500',
      items: tasks?.high_priority ?? [],
    },
    {
      key: 'medium_priority',
      label: 'Medium Priority',
      icon: AlertCircle,
      iconClass: 'text-amber-500',
      items: tasks?.medium_priority ?? [],
    },
    {
      key: 'low_priority',
      label: 'Low Priority',
      icon: Info,
      iconClass: 'text-gray-400',
      items: tasks?.low_priority ?? [],
    },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3 sticky top-0 bg-card z-10">
        <CardTitle className="text-base flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-primary" aria-hidden />
          Tasks
          {tasks && (
            <span className="text-xs font-normal text-muted-foreground ml-1">
              ({tasks.total_count})
            </span>
          )}
        </CardTitle>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => { setLoading(true); void fetchTasks(); }}
          disabled={loading}
          className="h-9 min-h-[36px]"
        >
          <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} aria-hidden />
          <span className="sr-only">Refresh</span>
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading && !tasks && (
          <p className="text-sm text-muted-foreground py-4 text-center">Loading tasks…</p>
        )}
        {error && (
          <p className="text-sm text-destructive py-4 text-center">{error}</p>
        )}
        {!loading && tasks && tasks.total_count === 0 && (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No pending tasks — everything is up to date
          </p>
        )}

        {sections.map((section) => {
          if (section.items.length === 0) return null;
          const Icon = section.icon;
          return (
            <div key={section.key}>
              <div className="flex items-center gap-2 mb-2">
                <Icon className={cn('h-4 w-4', section.iconClass)} aria-hidden />
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {section.label}
                  <span className="ml-1.5 font-normal">({section.items.length})</span>
                </h4>
              </div>
              <div className="space-y-2">
                {section.items.map((task) => (
                  <StaffTaskCard key={task.id} task={task} onAction={handleTaskAction} />
                ))}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}


