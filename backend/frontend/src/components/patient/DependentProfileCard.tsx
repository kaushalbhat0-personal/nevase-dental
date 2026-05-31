/**
 * DependentProfileCard.tsx — View a linked dependent.
 *
 * Shows avatar, relationship, age, upcoming appointments badge.
 * Foundation only — no auth delegation.
 */

import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, ChevronRight, Baby, Users, Heart, UserPlus, Shield, User } from 'lucide-react';
import type { DependentProfile } from '@/types';
import { getRelationshipLabel, dependentAgeLabel } from '@/utils/familyHelpers';
import { calmEmptyMessages } from '@/utils/trustSignals';

interface DependentProfileCardProps {
  dependent: DependentProfile;
  onSwitchProfile?: (dependentId: string) => void;
}

const relationshipIconMap: Record<string, React.ReactNode> = {
  child: <Baby className="h-5 w-5 text-blue-500" />,
  spouse: <Heart className="h-5 w-5 text-rose-500" />,
  parent: <Users className="h-5 w-5 text-amber-500" />,
  sibling: <Users className="h-5 w-5 text-green-500" />,
  grandparent: <Users className="h-5 w-5 text-purple-500" />,
  grandchild: <Baby className="h-5 w-5 text-teal-500" />,
  legal_guardian: <Shield className="h-5 w-5 text-indigo-500" />,
  caregiver: <UserPlus className="h-5 w-5 text-orange-500" />,
};

export function DependentProfileCard({
  dependent,
  onSwitchProfile,
}: DependentProfileCardProps) {
  const appointmentCount = dependent.upcoming_appointments?.length ?? 0;
  const icon = relationshipIconMap[dependent.relationship] ?? <User className="h-5 w-5 text-gray-500" />;

  return (
    <Card className="overflow-hidden border border-gray-200 transition-shadow hover:shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Avatar with relationship icon */}
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gray-100">
            {icon}
          </div>

          {/* Details */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900 truncate">
                {dependent.name}
              </h3>
              <Badge variant="secondary" className="shrink-0 text-xs">
                {getRelationshipLabel(dependent.relationship)}
              </Badge>
            </div>

            <p className="mt-0.5 text-sm text-gray-500">
              {dependentAgeLabel(dependent.age)}
              {dependent.gender ? ` · ${dependent.gender}` : ''}
            </p>

            {/* Upcoming appointments badge */}
            {appointmentCount > 0 ? (
              <div className="mt-2 flex items-center gap-1.5 text-sm text-blue-600">
                <Calendar className="h-3.5 w-3.5" />
                <span>
                  {appointmentCount} upcoming appointment{appointmentCount > 1 ? 's' : ''}
                </span>
              </div>
            ) : (
              <p className="mt-2 text-xs text-gray-400">
                {calmEmptyMessages.noAppointments}
              </p>
            )}

            {/* Shared medication count */}
            {dependent.shared_medication_count > 0 && (
              <p className="mt-1 text-xs text-gray-500">
                {dependent.shared_medication_count} shared medication reminder{dependent.shared_medication_count > 1 ? 's' : ''}
              </p>
            )}
          </div>

          {/* Action */}
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 text-gray-400 hover:text-gray-600"
            onClick={() => onSwitchProfile?.(dependent.id)}
            title="View dependent profile"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* TODO: Phase 2 — Switch to dependent profile */}
        {/* <div className="mt-3 pt-3 border-t border-gray-100">
          <Button
            variant="outline"
            size="sm"
            className="w-full text-sm"
            onClick={() => onSwitchProfile?.(dependent.id)}
          >
            Switch to {dependent.name}'s profile
          </Button>
          <p className="mt-1 text-xs text-gray-400 text-center">
            Coming soon — manage care on their behalf
          </p>
        </div> */}
      </CardContent>
    </Card>
  );
}
