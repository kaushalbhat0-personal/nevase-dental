/**
 * PatientHealthSummaryCard.tsx — Download consolidated health summary.
 *
 * Shows preview of what's included and triggers download.
 * Leverages existing document generation infrastructure.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  FileText,
  Download,
  Loader2,
  Calendar,
  Pill,
  HeartPulse,
  Shield,
  FileCheck,
} from 'lucide-react';
import type { HealthSummaryMetadata } from '@/types';
import { downloadHealthSummary } from '@/services/trustAndFamily';
import { calmLastUpdated, encounterCountSummary, medicationCountSummary } from '@/utils/trustSignals';
import dayjs from 'dayjs';

interface PatientHealthSummaryCardProps {
  metadata: HealthSummaryMetadata | null;
  loading?: boolean;
}

export function PatientHealthSummaryCard({
  metadata,
  loading = false,
}: PatientHealthSummaryCardProps) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    setDownloading(true);
    setError(null);
    try {
      const blob = await downloadHealthSummary();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `health-summary-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Could not download health summary. Please try again.');
      console.error('Health summary download error:', err);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Card className="border border-gray-200">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-blue-500" />
          <CardTitle className="text-lg">Health Summary</CardTitle>
        </div>
        <p className="text-sm text-gray-500">
          A consolidated overview of your health information. Download it to share
          with your doctors or keep for your records.
        </p>
      </CardHeader>

      <CardContent className="space-y-4">
        {loading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
          </div>
        ) : metadata ? (
          <>
            {/* Summary preview */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700">
                This summary includes:
              </h4>
              <div className="flex flex-wrap gap-2">
                <Badge
                  variant="outline"
                  className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 border-blue-200"
                >
                  <Calendar className="h-3 w-3" />
                  {encounterCountSummary(metadata.encounter_count)}
                </Badge>
                <Badge
                  variant="outline"
                  className="inline-flex items-center gap-1 bg-purple-50 text-purple-700 border-purple-200"
                >
                  <Pill className="h-3 w-3" />
                  {medicationCountSummary(metadata.active_medication_count)}
                </Badge>
                <Badge
                  variant="outline"
                  className="inline-flex items-center gap-1 bg-green-50 text-green-700 border-green-200"
                >
                  <FileCheck className="h-3 w-3" />
                  {metadata.document_count} document{metadata.document_count !== 1 ? 's' : ''}
                </Badge>
                {metadata.has_emergency_profile && (
                  <Badge
                    variant="outline"
                    className="inline-flex items-center gap-1 bg-amber-50 text-amber-700 border-amber-200"
                  >
                    <HeartPulse className="h-3 w-3" />
                    Emergency info
                  </Badge>
                )}
              </div>
            </div>

            {/* Last encounter */}
            {metadata.last_encounter_date && (
              <p className="text-xs text-gray-400">
                Last visit: {dayjs(metadata.last_encounter_date).format('MMMM D, YYYY')}
              </p>
            )}

            {/* Generated timestamp */}
            {metadata.generated_at && (
              <p className="text-xs text-gray-400">
                {calmLastUpdated(metadata.generated_at)}
              </p>
            )}

            {/* Download button */}
            <Button
              onClick={handleDownload}
              disabled={downloading}
              className="w-full"
            >
              {downloading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  Download Health Summary
                </>
              )}
            </Button>

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
          </>
        ) : (
          <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center">
            <Shield className="mx-auto h-8 w-8 text-gray-300" />
            <p className="mt-2 text-sm text-gray-500">
              Your health summary will be available here once you have visits and
              documents on record.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

