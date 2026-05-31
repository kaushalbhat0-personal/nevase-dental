/**
 * CommunicationCard — patient-safe communication card for the inbox/timeline.
 *
 * Phase P2 — Patient Communication Center.
 *
 * Architecture:
 *   - Renders NotificationEvent data as a patient-friendly card
 *   - NEVER exposes provider delivery internals or audit metadata
 *   - Supports CTA actions and document download links
 *   - Mobile-first, calm, conversational design (WhatsApp/app-like)
 *
 * Design:
 *   - Calm, readable, mobile-first, app-like (NOT enterprise inbox)
 *   - Unread indicator with subtle dot
 *   - Urgent items get a subtle accent treatment
 *   - Grouped by date with sticky date headers
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import {
  Bell,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  CreditCard,
  Download,
  FileText,
  FlaskConical,
  MessageSquare,
  Pill,
  Stethoscope,
  Syringe,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { patientCommunicationsApi } from '../../services/patientCommunications';
import type { CommunicationCard as CommunicationCardType } from '../../types';

dayjs.extend(relativeTime);

interface CommunicationCardProps {
  communication: CommunicationCardType;
  onRead?: (id: string) => void;
}

const EVENT_ICONS: Record<string, React.ElementType> = {
  appointment_reminder: Calendar,
  appointment_confirmed: Calendar,
  appointment_cancelled: Calendar,
  follow_up_reminder: Clock,
  prescription_ready: Pill,
  prescription_refill: Pill,
  invoice_generated: CreditCard,
  payment_received: CheckCircle2,
  payment_reminder: CreditCard,
  lab_result_ready: FlaskConical,
  immunization_due: Syringe,
  general_notification: Bell,
  message_from_provider: MessageSquare,
};

const EVENT_COLORS: Record<string, string> = {
  appointment_reminder: 'border-l-blue-400',
  appointment_confirmed: 'border-l-emerald-400',
  appointment_cancelled: 'border-l-amber-400',
  follow_up_reminder: 'border-l-violet-400',
  prescription_ready: 'border-l-sky-400',
  prescription_refill: 'border-l-sky-400',
  invoice_generated: 'border-l-orange-400',
  payment_received: 'border-l-emerald-400',
  payment_reminder: 'border-l-red-400',
  lab_result_ready: 'border-l-cyan-400',
  immunization_due: 'border-l-teal-400',
  general_notification: 'border-l-gray-400',
  message_from_provider: 'border-l-indigo-400',
};

function getEventIcon(eventType: string): React.ElementType {
  return EVENT_ICONS[eventType] || Bell;
}

function getEventColor(eventType: string): string {
  return EVENT_COLORS[eventType] || 'border-l-gray-400';
}

function getEventTypeLabel(eventType: string): string {
  const labels: Record<string, string> = {
    appointment_reminder: 'Appointment Reminder',
    appointment_confirmed: 'Appointment Confirmed',
    appointment_cancelled: 'Appointment Cancelled',
    follow_up_reminder: 'Follow-up Reminder',
    prescription_ready: 'Prescription Ready',
    prescription_refill: 'Prescription Refill',
    invoice_generated: 'Invoice Generated',
    payment_received: 'Payment Received',
    payment_reminder: 'Payment Reminder',
    lab_result_ready: 'Lab Result Ready',
    immunization_due: 'Immunization Due',
    general_notification: 'Notification',
    message_from_provider: 'Message from Provider',
  };
  return labels[eventType] || eventType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function CommunicationCard({ communication, onRead }: CommunicationCardProps) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [isMarkingRead, setIsMarkingRead] = useState(false);

  const Icon = getEventIcon(communication.event_type);
  const colorClass = getEventColor(communication.event_type);
  const timeAgo = dayjs(communication.created_at).fromNow();

  const handleMarkRead = async () => {
    if (communication.is_read || isMarkingRead) return;
    setIsMarkingRead(true);
    try {
      await patientCommunicationsApi.markAsRead(communication.id);
      onRead?.(communication.id);
    } catch {
      // Silently fail — read status is non-critical
    } finally {
      setIsMarkingRead(false);
    }
  };

  const handleCtaAction = (action: string) => {
    switch (action) {
      case 'view_appointment':
        if (communication.linked_appointment_id) {
          navigate(`/patient/appointments`);
        }
        break;
      case 'view_bill':
        if (communication.linked_bill_id) {
          navigate(`/patient/bills`);
        }
        break;
      case 'view_timeline':
        navigate('/patient/timeline');
        break;
      case 'book_appointment':
        navigate('/patient/doctors');
        break;
      default:
        break;
    }
  };

  const handleDocumentDownload = async (doc: { document_type: string; download_url: string | null }) => {
    if (doc.download_url) {
      window.open(doc.download_url, '_blank');
    }
  };

  return (
    <Card
      className={cn(
        'relative overflow-hidden border-l-4 transition-all duration-200',
        colorClass,
        !communication.is_read && 'bg-primary/[0.02]',
        communication.is_urgent && 'ring-1 ring-red-200',
        'hover:shadow-md'
      )}
      onClick={() => {
        if (!communication.is_read) {
          handleMarkRead();
        }
      }}
    >
      <CardContent className="p-4">
        {/* ── Header row ─────────────────────────────────────────────── */}
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div
            className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
              communication.is_read ? 'bg-muted text-muted-foreground' : 'bg-primary/10 text-primary'
            )}
          >
            <Icon className="h-5 w-5" />
          </div>

          {/* Content */}
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p
                    className={cn(
                      'truncate text-sm font-medium',
                      !communication.is_read && 'font-semibold'
                    )}
                  >
                    {communication.title}
                  </p>
                  {!communication.is_read && (
                    <span className="h-2 w-2 shrink-0 rounded-full bg-primary" />
                  )}
                  {communication.is_urgent && (
                    <Badge variant="destructive" className="h-5 px-1.5 text-[10px]">
                      Urgent
                    </Badge>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {getEventTypeLabel(communication.event_type)}
                </p>
              </div>
            </div>

            {/* Summary */}
            <p
              className={cn(
                'mt-1.5 text-sm leading-relaxed text-muted-foreground',
                !expanded && 'line-clamp-2'
              )}
            >
              {communication.summary}
            </p>

            {/* Expand/Collapse */}
            {communication.summary.length > 120 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(!expanded);
                }}
                className="mt-1 flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                {expanded ? (
                  <>
                    Show less <ChevronUp className="h-3 w-3" />
                  </>
                ) : (
                  <>
                    Read more <ChevronDown className="h-3 w-3" />
                  </>
                )}
              </button>
            )}

            {/* ── Metadata row ──────────────────────────────────────────── */}
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {timeAgo}
              </span>
              {communication.doctor_name && (
                <span className="flex items-center gap-1">
                  <Stethoscope className="h-3 w-3" />
                  {communication.doctor_name}
                </span>
              )}
              {communication.clinic_name && (
                <span className="flex items-center gap-1">
                  <MessageSquare className="h-3 w-3" />
                  {communication.clinic_name}
                </span>
              )}
            </div>

            {/* ── Document download links ────────────────────────────────── */}
            {communication.linked_documents.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {communication.linked_documents.map((doc, idx) => (
                  <Button
                    key={idx}
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDocumentDownload(doc);
                    }}
                    disabled={!doc.download_url}
                    className="h-7 gap-1 rounded-full px-2.5 text-xs"
                  >
                    <Download className="h-3 w-3" />
                    {doc.document_type === 'prescription'
                      ? 'Prescription'
                      : doc.document_type === 'encounter_summary'
                        ? 'Visit Summary'
                        : doc.document_type === 'invoice'
                          ? 'Invoice'
                          : doc.document_type}
                  </Button>
                ))}
              </div>
            )}

            {/* ── CTA actions ────────────────────────────────────────────── */}
            {communication.cta_actions.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2 border-t border-border/50 pt-3">
                {communication.cta_actions.map((action, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCtaAction(action);
                    }}
                    className="h-8 gap-1.5 rounded-full px-3 text-xs font-medium"
                  >
                    {action === 'view_appointment' && <Calendar className="h-3.5 w-3.5" />}
                    {action === 'view_bill' && <CreditCard className="h-3.5 w-3.5" />}
                    {action === 'view_timeline' && <FileText className="h-3.5 w-3.5" />}
                    {action === 'book_appointment' && <Calendar className="h-3.5 w-3.5" />}
                    {action === 'download_prescription' && <Download className="h-3.5 w-3.5" />}
                    {action === 'download_invoice' && <Download className="h-3.5 w-3.5" />}
                    {action
                      .replace(/_/g, ' ')
                      .replace(/\b\w/g, (c) => c.toUpperCase())}
                  </Button>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
