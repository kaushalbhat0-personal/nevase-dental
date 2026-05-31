/**
 * TrustedContactsSection.tsx — Section wrapper for trusted contacts list.
 *
 * Shows header with count, grid of TrustedContactCards,
 * and "Add contact" placeholder.
 */

import { Users } from 'lucide-react';
import { TrustedContactCard } from './TrustedContactCard';
import type { TrustedContact } from '@/types';
import { calmEmptyMessages } from '@/utils/trustSignals';

interface TrustedContactsSectionProps {
  contacts: TrustedContact[];
  onEditContact?: (contactId: string) => void;
}

export function TrustedContactsSection({
  contacts,
  onEditContact,
}: TrustedContactsSectionProps) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900">
            Trusted Contacts
          </h2>
          {contacts.length > 0 && (
            <span className="text-sm text-gray-500">
              ({contacts.length})
            </span>
          )}
        </div>

        {/* TODO: Phase 2 — Add contact */}
        {/* <Button
          variant="outline"
          size="sm"
          onClick={onAddContact}
        >
          <UserPlus className="h-4 w-4 mr-1" />
          Add Contact
        </Button> */}
      </div>

      {/* Description */}
      <p className="text-sm text-gray-500">
        People you trust with your care information. They can help manage
        appointments, medications, and stay informed about your health.
      </p>

      {/* Contact list */}
      {contacts.length > 0 ? (
        <div className="space-y-2">
          {contacts.map((contact) => (
            <TrustedContactCard
              key={contact.id}
              contact={contact}
              onEdit={onEditContact}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center">
          <Users className="mx-auto h-8 w-8 text-gray-300" />
          <p className="mt-2 text-sm text-gray-500">
            {calmEmptyMessages.noTrustedContacts}
          </p>
          {/* TODO: Phase 2 — Add contact button */}
          {/* <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={onAddContact}
          >
            <UserPlus className="h-4 w-4 mr-1" />
            Add a trusted contact
          </Button> */}
        </div>
      )}
    </div>
  );
}
