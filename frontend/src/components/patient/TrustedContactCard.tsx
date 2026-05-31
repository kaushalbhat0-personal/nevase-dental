/**
 * TrustedContactCard.tsx — Single trusted contact display.
 *
 * Shows contact name, relationship badge, phone/email,
 * communication preference, emergency contact badge,
 * and "shared with" indicators.
 */

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Phone,
  Mail,
  MessageSquare,
  AlertTriangle,
  User,
  ChevronRight,
  Shield,
  Calendar,
  Pill,
  FileText,
} from 'lucide-react';
import type { TrustedContact } from '@/types';
import { getRelationshipLabel } from '@/utils/familyHelpers';
import { calmCreated } from '@/utils/trustSignals';

interface TrustedContactCardProps {
  contact: TrustedContact;
  onEdit?: (contactId: string) => void;
}

const communicationIcons: Record<string, React.ReactNode> = {
  sms: <MessageSquare className="h-3.5 w-3.5" />,
  email: <Mail className="h-3.5 w-3.5" />,
  whatsapp: <MessageSquare className="h-3.5 w-3.5" />,
  none: null,
};

const communicationLabels: Record<string, string> = {
  sms: 'SMS',
  email: 'Email',
  whatsapp: 'WhatsApp',
  none: 'No preference',
};

const sharedItemIcons: Record<string, React.ReactNode> = {
  appointments: <Calendar className="h-3 w-3" />,
  medications: <Pill className="h-3 w-3" />,
  documents: <FileText className="h-3 w-3" />,
  all: <Shield className="h-3 w-3" />,
};

const sharedItemLabels: Record<string, string> = {
  appointments: 'Appointments',
  medications: 'Medications',
  documents: 'Documents',
  all: 'Full access',
};

export function TrustedContactCard({
  contact,
  onEdit,
}: TrustedContactCardProps) {
  return (
    <Card className="overflow-hidden border border-gray-200 transition-shadow hover:shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gray-100">
            <User className="h-5 w-5 text-gray-500" />
          </div>

          {/* Details */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900 truncate">
                {contact.name}
              </h3>
              <Badge variant="secondary" className="shrink-0 text-xs">
                {getRelationshipLabel(contact.relationship)}
              </Badge>
              {contact.is_emergency_contact && (
                <Badge
                  variant="outline"
                  className="shrink-0 flex items-center gap-1 text-xs bg-amber-50 text-amber-700 border-amber-200"
                >
                  <AlertTriangle className="h-3 w-3" />
                  Emergency
                </Badge>
              )}
            </div>

            {/* Contact info */}
            <div className="mt-1 space-y-0.5 text-sm text-gray-500">
              {contact.phone && (
                <div className="flex items-center gap-1.5">
                  <Phone className="h-3.5 w-3.5" />
                  <span>{contact.phone}</span>
                </div>
              )}
              {contact.email && (
                <div className="flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5" />
                  <span className="truncate">{contact.email}</span>
                </div>
              )}
            </div>

            {/* Communication preference */}
            <div className="mt-2 flex items-center gap-1.5 text-xs text-gray-500">
              {communicationIcons[contact.communication_preference]}
              <span>
                Prefers {communicationLabels[contact.communication_preference] ?? 'No preference'}
              </span>
            </div>

            {/* Shared items */}
            {contact.shared_items && contact.shared_items.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {contact.shared_items.map((item) => (
                  <Badge
                    key={item}
                    variant="outline"
                    className="inline-flex items-center gap-1 text-xs bg-blue-50 text-blue-700 border-blue-200"
                  >
                    {sharedItemIcons[item]}
                    {sharedItemLabels[item]}
                  </Badge>
                ))}
              </div>
            )}

            {/* Created timestamp */}
            {contact.created_at && (
              <p className="mt-1 text-xs text-gray-400">
                {calmCreated(contact.created_at)}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex shrink-0 items-start gap-1">
            {/* TODO: Phase 2 — Edit contact */}
            {/* <Button
              variant="ghost"
              size="icon"
              className="text-gray-400 hover:text-gray-600"
              onClick={() => onEdit?.(contact.id)}
            >
              <Pencil className="h-4 w-4" />
            </Button> */}
            <Button
              variant="ghost"
              size="icon"
              className="text-gray-400 hover:text-gray-600"
              onClick={() => onEdit?.(contact.id)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
