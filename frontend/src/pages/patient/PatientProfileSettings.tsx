/**
 * PatientProfileSettings — preferences and communication settings.
 *
 * Consolidates:
 * - Communication preferences
 * - Notification settings
 * - Account info
 * - Future: insurance, dependents
 */

import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { CommunicationPreferences } from '../../components/patient/CommunicationPreferences';
import { patientCommunicationsApi } from '../../services/patientCommunications';
import type { CommunicationPreferencesUpdate, CommunicationPreferencesRead } from '../../types';

import { Skeleton } from '@/components/ui/skeleton';

export function PatientProfileSettings() {
  const navigate = useNavigate();
  const [preferences, setPreferences] = useState<CommunicationPreferencesRead | null>(null);

  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);

  const loadPreferences = useCallback(async () => {
    setLoading(true);
    try {
      const data = await patientCommunicationsApi.getAggregate();
      setPreferences(data.preferences);
    } catch {
      // Silently handle
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  const handleUpdatePreferences = async (data: CommunicationPreferencesUpdate) => {
    setIsUpdating(true);
    try {
      const updated = await patientCommunicationsApi.updatePreferences(data);
      setPreferences(updated);
    } catch (err) {
      throw err;
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate('/patient/profile')}
          className="flex h-10 w-10 items-center justify-center rounded-xl hover:bg-muted transition-colors"
          aria-label="Back to profile"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-foreground">Settings</h1>
          <p className="text-sm text-muted-foreground">Manage your preferences</p>
        </div>
      </div>

      {/* Communication Preferences */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">Communication Preferences</h2>
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-20 rounded-2xl" />
            <Skeleton className="h-20 rounded-2xl" />
          </div>
        ) : preferences ? (
          <CommunicationPreferences
            preferences={preferences}
            onUpdate={handleUpdatePreferences}
            isUpdating={isUpdating}
          />
        ) : (
          <p className="text-sm text-muted-foreground">Unable to load preferences.</p>
        )}
      </section>

      {/* Account Info */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">Account</h2>
        <div className="rounded-2xl border border-border/60 bg-card p-4 shadow-sm">
          <p className="text-sm text-muted-foreground">
            Account management features coming soon.
          </p>
        </div>
      </section>

      {/* Future sections */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">Coming Soon</h2>
        <div className="space-y-2">
          <div className="rounded-2xl border border-dashed border-border/60 bg-muted/20 p-4 opacity-60">
            <p className="text-sm font-medium text-foreground">Insurance Information</p>
            <p className="text-xs text-muted-foreground">Manage your insurance details</p>
          </div>
          <div className="rounded-2xl border border-dashed border-border/60 bg-muted/20 p-4 opacity-60">
            <p className="text-sm font-medium text-foreground">Family & Dependents</p>
            <p className="text-xs text-muted-foreground">Manage family members and dependents</p>
          </div>
        </div>
      </section>
    </div>
  );
}
