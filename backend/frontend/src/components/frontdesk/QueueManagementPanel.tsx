/**
 * QueueManagementPanel — enhanced queue visualization.
 *
 * Tablet-first improvements:
 * - Larger operational chips
 * - Queue delay indicators
 * - Sticky action areas
 * - Touch-friendly controls
 * - Better visual hierarchy
 */
import { useState, useEffect, useCallback } from 'react';
import { Users, CheckCircle, SkipForward, DoorOpen, AlertTriangle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { queueApi } from '../../services/clinicQueue';
import type { QueueEntry, QueueDashboard } from '../../services/clinicQueue';

interface QueueManagementPanelProps {
  /** Auto-refresh interval in ms (default: 30000 = 30s) */
  refreshInterval?: number;
  /** Optional doctor ID filter */
  doctorId?: string;
  /** Title for the panel */
  title?: string;
}

/**
 * Queue management panel for front desk and nurse workflow.
 * Displays today's queue with call/complete/skip actions.
 * Polling-compatible — no websocket dependency.
 */
export function QueueManagementPanel({
  refreshInterval = 30000,
  title = "Today's Queue",
}: QueueManagementPanelProps) {
  const [dashboard, setDashboard] = useState<QueueDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    try {
      setError(null);
      const data = await queueApi.getFrontDesk();
      setDashboard(data);
    } catch (err) {
      console.error('[QueueManagementPanel] Fetch error:', err);
      setError('Failed to load queue');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchQueue, refreshInterval]);

  const handleAction = async (
    entryId: string,
    action: 'call' | 'complete' | 'skip',
    fn: () => Promise<QueueEntry>
  ) => {
    if (actionLoading) return;
    setActionLoading(`${action}-${entryId}`);
    try {
      await fn();
      await fetchQueue(); // Refresh after action
    } catch (err) {
      console.error(`[QueueManagementPanel] ${action} failed:`, err);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="bg-card rounded-lg shadow-sm border border-border">
        <div className="animate-pulse space-y-3 p-4">
          <div className="h-6 bg-muted rounded w-1/3" />
          <div className="h-12 bg-muted rounded" />
          <div className="h-12 bg-muted rounded" />
          <div className="h-12 bg-muted rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-destructive/10 rounded-lg border border-destructive/20">
        <p className="text-destructive text-sm">{error}</p>
        <button
          type="button"
          onClick={fetchQueue}
          className="mt-2 text-sm text-destructive underline hover:text-destructive/80"
        >
          Retry
        </button>
      </div>
    );
  }

  const entries = dashboard?.entries ?? [];
  const waiting = entries.filter((e) => e.queue_status === 'waiting');
  const inRoom = entries.filter((e) => e.queue_status === 'in_room');
  const completed = entries.filter((e) => e.queue_status === 'completed');

  return (
    <div className="bg-card rounded-lg shadow-sm border border-border">
      {/* Header with counts */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-foreground">{title}</h3>
          <button
            type="button"
            onClick={fetchQueue}
            className="p-2 rounded-lg hover:bg-accent transition-colors min-h-[36px] min-w-[36px]"
            title="Refresh queue"
          >
            <RefreshCw className="h-4 w-4 text-muted-foreground" aria-hidden />
          </button>
        </div>
        <div className="flex gap-3 mt-2">
          <span className="flex items-center gap-1.5 text-sm text-amber-600 dark:text-amber-400 font-medium">
            <Users className="w-4 h-4" aria-hidden />
            {waiting.length} waiting
          </span>
          <span className="flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400 font-medium">
            <DoorOpen className="w-4 h-4" aria-hidden />
            {inRoom.length} in room
          </span>
          <span className="flex items-center gap-1.5 text-sm text-muted-foreground font-medium">
            <CheckCircle className="w-4 h-4" aria-hidden />
            {completed.length} done
          </span>
        </div>
      </div>

      {/* Queue list */}
      <div className="divide-y divide-border max-h-[600px] overflow-y-auto">
        {entries.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Users className="w-12 h-12 mx-auto mb-2 opacity-50" aria-hidden />
            <p className="text-sm">No patients in queue today</p>
          </div>
        ) : (
          entries.map((entry) => (
            <QueueRow
              key={entry.id}
              entry={entry}
              actionLoading={actionLoading}
              onCall={() =>
                handleAction(entry.id, 'call', () =>
                  queueApi.callEntry(entry.id)
                )
              }
              onComplete={() =>
                handleAction(entry.id, 'complete', () =>
                  queueApi.completeEntry(entry.id)
                )
              }
              onSkip={() =>
                handleAction(entry.id, 'skip', () =>
                  queueApi.skipEntry(entry.id)
                )
              }
            />
          ))
        )}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Queue Row — enhanced with delay indicators
// ──────────────────────────────────────────────────────────────────────────────

interface QueueRowProps {
  entry: QueueEntry;
  actionLoading: string | null;
  onCall: () => void;
  onComplete: () => void;
  onSkip: () => void;
}

function QueueRow({
  entry,
  actionLoading,
  onCall,
  onComplete,
  onSkip,
}: QueueRowProps) {
  const isWaiting = entry.queue_status === 'waiting';
  const isInRoom = entry.queue_status === 'in_room';
  const isCompleted = entry.queue_status === 'completed';

  const statusBadge = isWaiting
    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300'
    : isInRoom
    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-300'
    : isCompleted
    ? 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
    : 'bg-red-100 text-red-500 dark:bg-red-900 dark:text-red-400';

  const statusLabel = isWaiting
    ? 'Waiting'
    : isInRoom
    ? 'In Room'
    : isCompleted
    ? 'Done'
    : 'Skipped';

  const isLoading =
    actionLoading === `call-${entry.id}` ||
    actionLoading === `complete-${entry.id}` ||
    actionLoading === `skip-${entry.id}`;

  // Calculate wait time from entered_at
  const waitMinutes = entry.entered_at
    ? Math.floor((Date.now() - new Date(entry.entered_at).getTime()) / 60000)
    : 0;
  const isDelayed = isWaiting && waitMinutes > 15;


  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 hover:bg-accent/50 transition-colors min-h-[64px]',
        isDelayed && 'bg-red-50/50 dark:bg-red-950/10'
      )}
    >
      {/* Token number */}
      <div
        className={cn(
          'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
          isWaiting
            ? 'bg-amber-100 dark:bg-amber-900'
            : isInRoom
              ? 'bg-emerald-100 dark:bg-emerald-900'
              : 'bg-muted'
        )}
      >
        <span
          className={cn(
            'text-sm font-bold',
            isWaiting
              ? 'text-amber-700 dark:text-amber-300'
              : isInRoom
                ? 'text-emerald-700 dark:text-emerald-300'
                : 'text-muted-foreground'
          )}
        >
          {entry.token_number}
        </span>
      </div>

      {/* Patient info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">
          {entry.patient_name || 'Unknown Patient'}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <p className="text-xs text-muted-foreground truncate">
            {entry.doctor_name}
            {entry.room_number && ` • Room ${entry.room_number}`}
          </p>
          {/* Delay indicator */}
          {isDelayed && (
            <span className="flex items-center gap-0.5 text-[10px] font-medium text-red-600 dark:text-red-400 shrink-0">
              <AlertTriangle className="h-3 w-3" aria-hidden />
              {waitMinutes}m
            </span>
          )}
        </div>
      </div>

      {/* Status badge */}
      <span
        className={cn(
          'flex-shrink-0 px-2.5 py-1 rounded-full text-xs font-medium',
          statusBadge
        )}
      >
        {statusLabel}
      </span>

      {/* Actions */}
      <div className="flex-shrink-0 flex gap-1">
        {isWaiting && (
          <>
            <button
              type="button"
              onClick={onCall}
              disabled={isLoading}
              className="p-2.5 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 transition-colors min-h-[40px] min-w-[40px]"
              title="Call patient"
            >
              {isLoading ? (
                <span className="block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <DoorOpen className="w-4 h-4" aria-hidden />
              )}
            </button>
            <button
              type="button"
              onClick={onSkip}
              disabled={isLoading}
              className="p-2.5 rounded-lg bg-gray-50 text-gray-500 hover:bg-gray-100 disabled:opacity-50 transition-colors min-h-[40px] min-w-[40px]"
              title="Skip patient"
            >
              <SkipForward className="w-4 h-4" aria-hidden />
            </button>
          </>
        )}
        {isInRoom && (
          <button
            type="button"
            onClick={onComplete}
            disabled={isLoading}
            className="p-2.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-50 transition-colors min-h-[40px] min-w-[40px]"
            title="Mark complete"
          >
            {isLoading ? (
              <span className="block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4" aria-hidden />
            )}
          </button>
        )}
      </div>
    </div>
  );
}
