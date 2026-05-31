/**
 * PatientCommunicationCenter — patient-facing communication inbox and notification center.
 *
 * Phase P2 — Patient Communication Center.
 *
 * Architecture:
 *   - Composes existing NotificationEvent data into a patient-friendly communication center
 *   - NotificationEvent remains the source-of-truth
 *   - NEVER exposes provider delivery internals or audit metadata
 *   - Mobile-first, calm, conversational design (WhatsApp/app-like)
 *
 * Sections:
 *   1. Communication Inbox — grouped timeline of notification cards
 *   2. Reminder Experience — reminders grouped by urgency
 *   3. Communication Preferences — channel preference settings
 *
 * TODO: Phase 3 — AI health assistant integration
 * TODO: Phase 3 — Conversational chat interface
 * TODO: Phase 3 — Care-plan nudges
 * TODO: Phase 3 — Medication adherence tracking
 * TODO: Phase 3 — Voice reminders
 * TODO: Phase 3 — Push notifications
 * TODO: Phase 3 — Family/dependent notifications
 * TODO: Phase 3 — Multilingual templates
 * TODO: Phase 3 — Patient-provider messaging
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Bell,
  BellRing,
  ChevronDown,
  ChevronUp,
  Inbox,
  MessageSquare,
  RefreshCw,
  Settings,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CommunicationCard } from '../../components/patient/CommunicationCard';
import { ReminderSection } from '../../components/patient/ReminderSection';
import { CommunicationPreferences } from '../../components/patient/CommunicationPreferences';
import { patientCommunicationsApi } from '../../services/patientCommunications';
import type {
  CommunicationPreferencesUpdate,
  PatientCommunicationAggregate,
} from '../../types';

type ActiveTab = 'inbox' | 'reminders' | 'preferences';

export function PatientCommunicationCenter() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('inbox');
  const [aggregate, setAggregate] = useState<PatientCommunicationAggregate | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdatingPrefs, setIsUpdatingPrefs] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAllNotifications, setShowAllNotifications] = useState(false);

  const fetchAggregate = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await patientCommunicationsApi.getAggregate();
      setAggregate(data);
    } catch (err) {
      setError('Unable to load communications. Please try again.');
      console.error('[PatientCommunicationCenter] Failed to load aggregate:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAggregate();
  }, [fetchAggregate]);

  const handleMarkAsRead = (id: string) => {
    if (!aggregate) return;
    setAggregate({
      ...aggregate,
      recent_notifications: aggregate.recent_notifications.map((n) =>
        n.id === id ? { ...n, is_read: true } : n
      ),
      unread_count: Math.max(0, aggregate.unread_count - 1),
    });
  };

  const handleUpdatePreferences = async (data: CommunicationPreferencesUpdate) => {
    if (!aggregate) return;
    setIsUpdatingPrefs(true);
    try {
      const updated = await patientCommunicationsApi.updatePreferences(data);
      setAggregate({
        ...aggregate,
        preferences: updated,
      });
    } catch (err) {
      console.error('[PatientCommunicationCenter] Failed to update preferences:', err);
      throw err;
    } finally {
      setIsUpdatingPrefs(false);
    }
  };

  // ── Loading state ─────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Skeleton header */}
        <div className="flex items-center justify-between">
          <div className="h-7 w-48 animate-pulse rounded-lg bg-muted" />
          <div className="h-9 w-24 animate-pulse rounded-full bg-muted" />
        </div>

        {/* Skeleton tabs */}
        <div className="flex gap-2">
          <div className="h-9 w-24 animate-pulse rounded-full bg-muted" />
          <div className="h-9 w-28 animate-pulse rounded-full bg-muted" />
          <div className="h-9 w-32 animate-pulse rounded-full bg-muted" />
        </div>

        {/* Skeleton cards */}
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <MessageSquare className="mb-3 h-10 w-10 text-muted-foreground" />
        <p className="text-sm font-medium text-foreground">Something went wrong</p>
        <p className="mt-1 text-xs text-muted-foreground">{error}</p>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchAggregate}
          className="mt-4 gap-2 rounded-full"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </Button>
      </div>
    );
  }

  if (!aggregate) return null;

  const displayedNotifications = showAllNotifications
    ? aggregate.recent_notifications
    : aggregate.recent_notifications.slice(0, 10);

  const hasMore = aggregate.recent_notifications.length > 10;

  return (
    <div className="space-y-4">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Communications</h1>
          <p className="text-xs text-muted-foreground">
            Stay updated with your health journey
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchAggregate}
          className="gap-2 rounded-full"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* ── Unread badge ─────────────────────────────────────────────────── */}
      {aggregate.unread_count > 0 && (
        <div className="flex items-center gap-2 rounded-xl bg-primary/5 px-4 py-2.5">
          <BellRing className="h-4 w-4 text-primary" />
          <p className="text-sm font-medium text-primary">
            {aggregate.unread_count} unread{' '}
            {aggregate.unread_count === 1 ? 'notification' : 'notifications'}
          </p>
        </div>
      )}

      {/* ── Tabs ─────────────────────────────────────────────────────────── */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as ActiveTab)}
        className="w-full"
      >
        <TabsList className="w-full gap-1 rounded-full bg-muted/50 p-1">
          <TabsTrigger
            value="inbox"
            className="flex-1 gap-2 rounded-full data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <Inbox className="h-4 w-4" />
            <span className="hidden sm:inline">Inbox</span>
            {aggregate.unread_count > 0 && (
              <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
                {aggregate.unread_count}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="reminders"
            className="flex-1 gap-2 rounded-full data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <Bell className="h-4 w-4" />
            <span className="hidden sm:inline">Reminders</span>
            {aggregate.reminders_by_urgency.urgent.length > 0 && (
              <Badge variant="destructive" className="h-5 px-1.5 text-[10px]">
                {aggregate.reminders_by_urgency.urgent.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="preferences"
            className="flex-1 gap-2 rounded-full data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <Settings className="h-4 w-4" />
            <span className="hidden sm:inline">Preferences</span>
          </TabsTrigger>
        </TabsList>

        {/* ── Inbox Tab ──────────────────────────────────────────────────── */}
        <TabsContent value="inbox" className="mt-4 space-y-3">
          {aggregate.recent_notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Inbox className="mb-3 h-10 w-10 text-muted-foreground" />
              <p className="text-sm font-medium text-foreground">No communications yet</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Your health updates will appear here.
              </p>
            </div>
          ) : (
            <>
              {displayedNotifications.map((notification) => (
                <CommunicationCard
                  key={notification.id}
                  communication={notification}
                  onRead={handleMarkAsRead}
                />
              ))}

              {/* Show more / Show less */}
              {hasMore && (
                <div className="text-center">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAllNotifications(!showAllNotifications)}
                    className="gap-2 rounded-full text-xs text-muted-foreground"
                  >
                    {showAllNotifications ? (
                      <>
                        Show less <ChevronUp className="h-3 w-3" />
                      </>
                    ) : (
                      <>
                        Show all ({aggregate.recent_notifications.length}){' '}
                        <ChevronDown className="h-3 w-3" />
                      </>
                    )}
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>

        {/* ── Reminders Tab ──────────────────────────────────────────────── */}
        <TabsContent value="reminders" className="mt-4">
          <ReminderSection remindersByUrgency={aggregate.reminders_by_urgency} />
        </TabsContent>

        {/* ── Preferences Tab ────────────────────────────────────────────── */}
        <TabsContent value="preferences" className="mt-4">
          <CommunicationPreferences
            preferences={aggregate.preferences}
            onUpdate={handleUpdatePreferences}
            isUpdating={isUpdatingPrefs}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
