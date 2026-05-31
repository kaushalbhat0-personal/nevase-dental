/**
 * EmergencyInfoCard.tsx — Compact emergency profile card.
 *
 * Shows blood group, allergies count, emergency contact.
 * Designed for embedding in Profile page.
 * Calm, non-alarmist design.
 */

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Droplets,
  AlertTriangle,
  Phone,
  Stethoscope,
  Pill,
  ChevronRight,
  Shield,
  HeartPulse,
} from 'lucide-react';
import type { EmergencyProfile } from '@/types';
import { calmLastUpdated } from '@/utils/trustSignals';
import { useNavigate } from 'react-router-dom';

interface EmergencyInfoCardProps {
  profile: EmergencyProfile | null;
  compact?: boolean;
}

export function EmergencyInfoCard({ profile, compact = false }: EmergencyInfoCardProps) {
  const navigate = useNavigate();

  if (!profile) {
    return (
      <Card className="border border-gray-200">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
              <Shield className="h-5 w-5 text-gray-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-gray-900">Emergency Profile</h3>
              <p className="text-sm text-gray-500">
                No emergency information saved yet
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/patient/profile/emergency')}
            >
              Add Info
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const allergyCount = profile.allergies?.length ?? 0;
  const conditionCount = profile.chronic_conditions?.length ?? 0;

  return (
    <Card className="border border-gray-200 transition-shadow hover:shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-50">
              <HeartPulse className="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Emergency Profile</h3>
              {profile.updated_at && (
                <p className="text-xs text-gray-400">
                  {calmLastUpdated(profile.updated_at)}
                </p>
              )}
            </div>
          </div>
          {!compact && (
            <Button
              variant="ghost"
              size="icon"
              className="text-gray-400"
              onClick={() => navigate('/patient/profile/emergency')}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Key info badges */}
        <div className="mt-3 flex flex-wrap gap-2">
          {profile.blood_group && (
            <Badge variant="outline" className="flex items-center gap-1 bg-red-50 text-red-700 border-red-200">
              <Droplets className="h-3 w-3" />
              {profile.blood_group}
            </Badge>
          )}

          {allergyCount > 0 && (
            <Badge variant="outline" className="flex items-center gap-1 bg-amber-50 text-amber-700 border-amber-200">
              <AlertTriangle className="h-3 w-3" />
              {allergyCount} allerg{allergyCount === 1 ? 'y' : 'ies'}
            </Badge>
          )}

          {conditionCount > 0 && (
            <Badge variant="outline" className="flex items-center gap-1 bg-blue-50 text-blue-700 border-blue-200">
              <Stethoscope className="h-3 w-3" />
              {conditionCount} condition{conditionCount > 1 ? 's' : ''}
            </Badge>
          )}

          {profile.emergency_contact_name && (
            <Badge variant="outline" className="flex items-center gap-1 bg-green-50 text-green-700 border-green-200">
              <Phone className="h-3 w-3" />
              Emergency contact set
            </Badge>
          )}

          {profile.active_medications_summary && (
            <Badge variant="outline" className="flex items-center gap-1 bg-purple-50 text-purple-700 border-purple-200">
              <Pill className="h-3 w-3" />
              Active medications
            </Badge>
          )}
        </div>

        {/* Quick summary for compact mode */}
        {compact && (
          <Button
            variant="link"
            size="sm"
            className="mt-2 h-auto p-0 text-sm text-blue-600"
            onClick={() => navigate('/patient/profile/emergency')}
          >
            View full profile
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
