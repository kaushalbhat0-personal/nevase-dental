/**
 * CaregiverAccessCard.tsx — Display a trusted caregiver who has access.
 *
 * Shows avatar, name, relationship, trust level, access duration.
 * Foundation only — no permission escalation.
 */

import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Shield, ShieldCheck, Eye, HeartHandshake } from 'lucide-react';
import type { CaregiverAccess } from '@/types';
import { getRelationshipLabel } from '@/utils/familyHelpers';
import { calmCreated } from '@/utils/trustSignals';

interface CaregiverAccessCardProps {
  caregiver: CaregiverAccess;
}

const trustLevelConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  view_only: {
    label: 'View only',
    icon: <Eye className="h-3.5 w-3.5" />,
    color: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  limited: {
    label: 'Limited access',
    icon: <Shield className="h-3.5 w-3.5" />,
    color: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  full: {
    label: 'Full access',
    icon: <ShieldCheck className="h-3.5 w-3.5" />,
    color: 'bg-green-50 text-green-700 border-green-200',
  },
};

export function CaregiverAccessCard({
  caregiver,
}: CaregiverAccessCardProps) {
  const trustConfig = trustLevelConfig[caregiver.trust_level] ?? trustLevelConfig.view_only;

  return (
    <Card className="overflow-hidden border border-gray-200 transition-shadow hover:shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-indigo-50">
            <HeartHandshake className="h-5 w-5 text-indigo-500" />
          </div>

          {/* Details */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900 truncate">
                {caregiver.name}
              </h3>
              <Badge variant="secondary" className="shrink-0 text-xs">
                {getRelationshipLabel(caregiver.relationship)}
              </Badge>
            </div>

            {/* Contact info */}
            <div className="mt-1 space-y-0.5 text-sm text-gray-500">
              {caregiver.phone && <p>{caregiver.phone}</p>}
              {caregiver.email && <p className="truncate">{caregiver.email}</p>}
            </div>

            {/* Trust level badge */}
            <div className="mt-2">
              <Badge
                variant="outline"
                className={`inline-flex items-center gap-1 text-xs ${trustConfig.color}`}
              >
                {trustConfig.icon}
                {trustConfig.label}
              </Badge>
            </div>

            {/* Access duration */}
            {caregiver.access_granted_at && (
              <p className="mt-1 text-xs text-gray-400">
                {calmCreated(caregiver.access_granted_at)}
              </p>
            )}
          </div>

          {/* TODO: Phase 2 — Remove access */}
          {/* <Button
            variant="ghost"
            size="sm"
            className="shrink-0 text-gray-400 hover:text-red-500"
            onClick={() => onRemoveAccess?.(caregiver.id)}
          >
            Remove
          </Button> */}
        </div>
      </CardContent>
    </Card>
  );
}
