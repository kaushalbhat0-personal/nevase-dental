/**
 * PatientVitalsHistory — vitals trend cards and chronological vitals history.
 *
 * Features:
 * - Vitals trend cards (most recent values)
 * - Chronological vitals history
 * - Future-ready for charts/analytics
 *
 * Examples:
 * - BP
 * - pulse
 * - temperature
 * - SpO₂
 * - weight
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import {
  Activity,
  Heart,
  Thermometer,
  Weight,
  Wind,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { VitalTrendCard } from '../../components/patient/VitalTrendCard';
import { patientWorkspaceApi } from '../../services/patientWorkspace';
import type { VitalsSnapshot } from '../../types';
import { ErrorState } from '../../components/common';

export function PatientVitalsHistory() {
  const [vitals, setVitals] = useState<VitalsSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadVitals = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await patientWorkspaceApi.getVitalsHistory();
      setVitals(data);
    } catch {
      setError('Unable to load vitals history.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadVitals();
  }, [loadVitals]);

  // Most recent vitals snapshot
  const latest = useMemo(() => vitals[0] ?? null, [vitals]);

  if (error) {
    return <ErrorState title="Vitals History" description={error} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Vitals History</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Your health metrics recorded during visits.
        </p>
      </div>

      {loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-24 rounded-2xl bg-muted animate-pulse" />
            ))}
          </div>
        </div>
      ) : vitals.length === 0 ? (
        <Card className="border-dashed">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
              <Activity className="h-7 w-7 text-primary" />
            </div>
            <CardTitle className="text-lg pt-3">No vitals recorded yet</CardTitle>
            <CardDescription className="max-w-sm mx-auto">
              After your first checkup, your vitals like blood pressure, pulse, and
              temperature will appear here.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          {/* ── Trend Cards (most recent) ──────────────────────────────────── */}
          <div className="grid grid-cols-2 gap-3">
            {latest?.bp_systolic != null && latest?.bp_diastolic != null && (
              <VitalTrendCard
                label="Blood Pressure"
                value={`${latest.bp_systolic}/${latest.bp_diastolic}`}
                unit="mmHg"
                date={latest.appointment_time}
                icon={<Heart className="h-4 w-4" />}
                isNormal={
                  latest.bp_systolic >= 90 &&
                  latest.bp_systolic <= 140 &&
                  latest.bp_diastolic >= 60 &&
                  latest.bp_diastolic <= 90
                }
              />
            )}
            {latest?.pulse != null && (
              <VitalTrendCard
                label="Pulse"
                value={latest.pulse}
                unit="bpm"
                date={latest.appointment_time}
                icon={<Heart className="h-4 w-4" />}
                isNormal={latest.pulse >= 60 && latest.pulse <= 100}
              />
            )}
            {latest?.temperature != null && (
              <VitalTrendCard
                label="Temperature"
                value={latest.temperature}
                unit="°F"
                date={latest.appointment_time}
                icon={<Thermometer className="h-4 w-4" />}
                isNormal={
                  latest.temperature >= 97 &&
                  latest.temperature <= 100.4
                }
              />
            )}
            {latest?.spo2 != null && (
              <VitalTrendCard
                label="SpO₂"
                value={latest.spo2}
                unit="%"
                date={latest.appointment_time}
                icon={<Wind className="h-4 w-4" />}
                isNormal={latest.spo2 >= 95}
              />
            )}
            {latest?.weight != null && (
              <VitalTrendCard
                label="Weight"
                value={latest.weight}
                unit="kg"
                date={latest.appointment_time}
                icon={<Weight className="h-4 w-4" />}
              />
            )}
            {latest?.bmi != null && (
              <VitalTrendCard
                label="BMI"
                value={latest.bmi}
                unit="kg/m²"
                date={latest.appointment_time}
                icon={<Activity className="h-4 w-4" />}
                isNormal={latest.bmi >= 18.5 && latest.bmi <= 24.9}
              />
            )}
          </div>

          {/* ── Chronological History ──────────────────────────────────────── */}
          <div>
            <h2 className="text-base font-semibold text-foreground mb-3">
              History
            </h2>
            <div className="space-y-3">
              {vitals.map((v) => (
                <Card
                  key={`${v.appointment_id}-${v.appointment_time}`}
                  className="rounded-xl border-border/50 shadow-sm"
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-foreground">
                        {v.doctor_name || 'Doctor'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {dayjs(v.appointment_time).format('MMM D, YYYY · h:mm A')}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                      {v.bp_systolic != null && v.bp_diastolic != null && (
                        <span className="text-muted-foreground">
                          BP: <span className="font-medium text-foreground">{v.bp_systolic}/{v.bp_diastolic}</span>
                        </span>
                      )}
                      {v.pulse != null && (
                        <span className="text-muted-foreground">
                          Pulse: <span className="font-medium text-foreground">{v.pulse}</span>
                        </span>
                      )}
                      {v.temperature != null && (
                        <span className="text-muted-foreground">
                          Temp: <span className="font-medium text-foreground">{v.temperature}°F</span>
                        </span>
                      )}
                      {v.spo2 != null && (
                        <span className="text-muted-foreground">
                          SpO₂: <span className="font-medium text-foreground">{v.spo2}%</span>
                        </span>
                      )}
                      {v.weight != null && (
                        <span className="text-muted-foreground">
                          Weight: <span className="font-medium text-foreground">{v.weight}kg</span>
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* TODO: Phase 2 — Chart visualizations
           * <VitalsChart data={vitals} type="bp" />
           * <VitalsChart data={vitals} type="pulse" />
           * <VitalsChart data={vitals} type="weight" />
           */}

          {/* TODO: Phase 2 — Wearable integrations
           * <WearableDataSummary />
           */}
        </>
      )}
    </div>
  );
}
