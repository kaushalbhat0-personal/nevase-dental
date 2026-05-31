/**
 * CommunicationPreferences — patient-facing communication channel preference settings.
 *
 * Phase P2 — Patient Communication Center.
 *
 * Architecture:
 *   - Patients can configure email, SMS, WhatsApp, and reminder preferences
 *   - Preferences should NOT bypass critical healthcare notifications
 *   - opt_out_all is displayed with a clear warning about critical notifications
 *   - Mobile-first, calm design
 *
 * CRITICAL:
 *   - opt_out_all must NOT bypass critical healthcare notifications
 *   - Critical notifications (appointment reminders, urgent results) are ALWAYS sent
 *
 * TODO: Phase 3 — Quiet hours enforcement
 * TODO: Phase 3 — Multilingual communication (locale switching)
 * TODO: Phase 3 — Consent management / GDPR compliance
 * TODO: Phase 3 — Family/dependent notification preferences
 * TODO: Phase 3 — Medication adherence reminder preferences
 */

import { useState } from 'react';
import {
  AlertTriangle,
  Bell,
  BellOff,
  Clock,
  Globe,
  Mail,
  MessageSquare,
  Smartphone,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import type { CommunicationPreferencesRead, CommunicationPreferencesUpdate } from '../../types';

interface CommunicationPreferencesProps {
  preferences: CommunicationPreferencesRead;
  onUpdate: (data: CommunicationPreferencesUpdate) => Promise<void>;
  isUpdating?: boolean;
}

export function CommunicationPreferences({
  preferences,
  onUpdate,
  isUpdating = false,
}: CommunicationPreferencesProps) {
  const [localPrefs, setLocalPrefs] = useState<CommunicationPreferencesRead>(preferences);

  const handleToggle = async (key: keyof CommunicationPreferencesUpdate, value: boolean) => {
    // Optimistic update
    setLocalPrefs((prev) => ({ ...prev, [key]: value }));
    try {
      await onUpdate({ [key]: value });
    } catch {
      // Revert on failure
      setLocalPrefs((prev) => ({ ...prev, [key]: !value }));
    }
  };

  return (
    <div className="space-y-4">
      {/* ── Channel Preferences ─────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Notification Channels</CardTitle>
          <CardDescription className="text-xs">
            Choose how you'd like to receive communications from your healthcare providers.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Email */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
                <Mail className="h-4 w-4 text-primary" />
              </div>
              <div>
                <Label htmlFor="email_enabled" className="text-sm font-medium">
                  Email Notifications
                </Label>
                <p className="text-xs text-muted-foreground">
                  Receive updates via email
                </p>
              </div>
            </div>
            <Switch
              id="email_enabled"
              checked={localPrefs.email_enabled}
              onCheckedChange={(checked) => handleToggle('email_enabled', checked)}
              disabled={isUpdating}
            />
          </div>

          {/* SMS */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
                <Smartphone className="h-4 w-4 text-primary" />
              </div>
              <div>
                <Label htmlFor="sms_enabled" className="text-sm font-medium">
                  SMS Notifications
                </Label>
                <p className="text-xs text-muted-foreground">
                  Receive updates via text message
                </p>
              </div>
            </div>
            <Switch
              id="sms_enabled"
              checked={localPrefs.sms_enabled}
              onCheckedChange={(checked) => handleToggle('sms_enabled', checked)}
              disabled={isUpdating}
            />
          </div>

          {/* WhatsApp */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
                <MessageSquare className="h-4 w-4 text-primary" />
              </div>
              <div>
                <Label htmlFor="whatsapp_enabled" className="text-sm font-medium">
                  WhatsApp Notifications
                </Label>
                <p className="text-xs text-muted-foreground">
                  Receive updates via WhatsApp
                </p>
              </div>
            </div>
            <Switch
              id="whatsapp_enabled"
              checked={localPrefs.whatsapp_enabled}
              onCheckedChange={(checked) => handleToggle('whatsapp_enabled', checked)}
              disabled={isUpdating}
            />
          </div>

          {/* Reminders */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
                <Bell className="h-4 w-4 text-primary" />
              </div>
              <div>
                <Label htmlFor="reminder_enabled" className="text-sm font-medium">
                  Reminder Notifications
                </Label>
                <p className="text-xs text-muted-foreground">
                  Appointment and follow-up reminders
                </p>
              </div>
            </div>
            <Switch
              id="reminder_enabled"
              checked={localPrefs.reminder_enabled}
              onCheckedChange={(checked) => handleToggle('reminder_enabled', checked)}
              disabled={isUpdating}
            />
          </div>
        </CardContent>
      </Card>

      {/* ── Future-ready: Quiet Hours ────────────────────────────────────── */}
      <Card className="opacity-60">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">Quiet Hours</CardTitle>
          </div>
          <CardDescription className="text-xs">
            Set times when you prefer not to receive non-critical notifications.
            <span className="block mt-1 text-[10px] text-muted-foreground italic">
              Coming soon — Phase 3
            </span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <Label className="text-xs text-muted-foreground">Start</Label>
              <div className="mt-1 h-9 rounded-lg bg-muted px-3 flex items-center text-sm text-muted-foreground">
                {localPrefs.quiet_hours_start || '--:--'}
              </div>
            </div>
            <div className="flex-1">
              <Label className="text-xs text-muted-foreground">End</Label>
              <div className="mt-1 h-9 rounded-lg bg-muted px-3 flex items-center text-sm text-muted-foreground">
                {localPrefs.quiet_hours_end || '--:--'}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Future-ready: Language ───────────────────────────────────────── */}
      <Card className="opacity-60">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">Language</CardTitle>
          </div>
          <CardDescription className="text-xs">
            Choose your preferred language for communications.
            <span className="block mt-1 text-[10px] text-muted-foreground italic">
              Coming soon — Phase 3
            </span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-9 rounded-lg bg-muted px-3 flex items-center text-sm text-muted-foreground">
            {localPrefs.locale === 'en' ? 'English' : localPrefs.locale}
          </div>
        </CardContent>
      </Card>

      {/* ── Opt-out (with warning) ───────────────────────────────────────── */}
      <Card
        className={cn(
          'border-2',
          localPrefs.opt_out_all
            ? 'border-red-200 bg-red-50 dark:border-red-800/30 dark:bg-red-950/20'
            : 'border-border'
        )}
      >
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {localPrefs.opt_out_all ? (
                <BellOff className="h-4 w-4 text-red-500" />
              ) : (
                <Bell className="h-4 w-4 text-muted-foreground" />
              )}
              <CardTitle className="text-base">Opt Out of All Communications</CardTitle>
            </div>
            <Switch
              id="opt_out_all"
              checked={localPrefs.opt_out_all}
              onCheckedChange={(checked) => handleToggle('opt_out_all', checked)}
              disabled={isUpdating}
            />
          </div>
          <CardDescription className="text-xs">
            Disable all non-critical communications.
          </CardDescription>
        </CardHeader>
        {localPrefs.opt_out_all && (
          <CardContent>
            <div className="flex items-start gap-2 rounded-lg bg-red-100 p-3 dark:bg-red-900/20">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
              <div>
                <p className="text-xs font-medium text-red-800 dark:text-red-300">
                  Critical healthcare notifications will still be sent
                </p>
                <p className="mt-1 text-[11px] text-red-600 dark:text-red-400">
                  Appointment reminders, urgent medical results, prescription readiness,
                  and follow-up reminders are always delivered for your safety.
                </p>
              </div>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
