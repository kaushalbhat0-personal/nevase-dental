/**
 * Admin Communications Dashboard — Phase 3D Communication Infrastructure.
 *
 * Features:
 * - Notification history with delivery status
 * - Failed messages with resend action
 * - Communication template management
 * - Template preview
 * - Reminder settings
 * - Dashboard stats overview
 *
 * Mobile-first responsive.
 */

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Bell,
  Mail,
  MessageSquare,
  MessageCircle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Eye,
  Plus,
  Pencil,
  Trash2,
  Send,
  Settings,
  AlertTriangle,
  Loader2,
  ChevronLeft,
  ChevronRight,
  FileText,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  fetchNotifications,
  fetchFailedDeliveries,
  fetchDeliveryStatus,
  resendNotification,
  fetchTemplates,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  previewTemplate,
  fetchPlaceholders,
  fetchCommunicationDashboardStats,
  fetchReminderSettings,
  updateReminderSettings,
  triggerReminders,
  type NotificationEvent,
  type NotificationDelivery,
  type CommunicationTemplate,
  type CommunicationDashboardStats,
  type ReminderSettings,
} from '../services/notifications';

// ── Helpers ─────────────────────────────────────────────────────────────────

const EVENT_TYPE_LABELS: Record<string, string> = {
  appointment_booked: 'Appointment Booked',
  appointment_reminder: 'Appointment Reminder',
  appointment_completed: 'Appointment Completed',
  prescription_ready: 'Prescription Ready',
  bill_generated: 'Bill Generated',
  payment_received: 'Payment Received',
  follow_up_reminder: 'Follow-up Reminder',
};

const CHANNEL_ICONS: Record<string, typeof Mail> = {
  email: Mail,
  sms: MessageSquare,
  whatsapp: MessageCircle,
  in_app: Bell,
};

const CHANNEL_LABELS: Record<string, string> = {
  email: 'Email',
  sms: 'SMS',
  whatsapp: 'WhatsApp',
  in_app: 'In-App',
};

const STATUS_BADGE_VARIANTS: Record<
  string,
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  pending: 'secondary',
  sent: 'default',
  delivered: 'default',
  read: 'default',
  failed: 'destructive',
};

function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString();
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'sent':
    case 'delivered':
    case 'read':
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-yellow-500" />;
  }
}

// ── Sub-components ──────────────────────────────────────────────────────────

function StatsCards({ stats }: { stats: CommunicationDashboardStats | null }) {
  if (!stats) return null;

  const cards = [
    {
      label: 'Total Notifications',
      value: stats.total_notifications,
      icon: Bell,
      color: 'text-blue-600',
    },
    {
      label: 'Sent',
      value: stats.total_sent,
      icon: CheckCircle2,
      color: 'text-green-600',
    },
    {
      label: 'Failed',
      value: stats.total_failed,
      icon: XCircle,
      color: 'text-red-600',
    },
    {
      label: 'Success Rate',
      value: `${(stats.success_rate * 100).toFixed(1)}%`,
      icon: RefreshCw,
      color: 'text-purple-600',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className="p-4 flex items-center gap-3">
            <card.icon className={`h-8 w-8 ${card.color}`} />
            <div>
              <p className="text-xs text-muted-foreground">{card.label}</p>
              <p className="text-xl font-bold">{card.value}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function NotificationHistory() {
  const [events, setEvents] = useState<NotificationEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [deliveries, setDeliveries] = useState<NotificationDelivery[]>([]);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);
  const limit = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchNotifications({ skip, limit });
      setEvents(result.items);
      setTotal(result.total);
    } catch {
      toast.error('Failed to load notifications');
    } finally {
      setLoading(false);
    }
  }, [skip]);

  useEffect(() => {
    load();
  }, [load]);

  const viewDeliveries = async (eventId: string) => {
    setSelectedEvent(eventId);
    setDeliveriesLoading(true);
    try {
      const result = await fetchDeliveryStatus(eventId);
      setDeliveries(result.items);
    } catch {
      toast.error('Failed to load delivery details');
    } finally {
      setDeliveriesLoading(false);
    }
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(skip / limit) + 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Notification History</h3>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={skip === 0}
            onClick={() => setSkip(Math.max(0, skip - limit))}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {currentPage} of {totalPages || 1}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={skip + limit >= total}
            onClick={() => setSkip(skip + limit)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : events.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <Bell className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No notifications yet</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {events.map((event) => (
            <Card
              key={event.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => viewDeliveries(event.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline">
                        {EVENT_TYPE_LABELS[event.event_type] || event.event_type}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDateTime(event.created_at)}
                      </span>
                    </div>
                    {event.payload && (
                      <p className="text-sm text-muted-foreground truncate max-w-md">
                        {JSON.stringify(event.payload).substring(0, 100)}
                      </p>
                    )}
                  </div>
                  <Eye className="h-4 w-4 text-muted-foreground shrink-0 ml-2" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delivery Details Dialog */}
      <Dialog
        open={selectedEvent !== null}
        onOpenChange={(open: boolean) => {
          if (!open) setSelectedEvent(null);
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Delivery Details</DialogTitle>
            <DialogDescription>
              Channel delivery status for this notification event.
            </DialogDescription>
          </DialogHeader>
          {deliveriesLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : deliveries.length === 0 ? (
            <p className="text-center text-muted-foreground py-4">
              No delivery records found.
            </p>
          ) : (
            <div className="space-y-3">
              {deliveries.map((d) => {
                const ChannelIcon = CHANNEL_ICONS[d.channel] || Mail;
                return (
                  <div
                    key={d.id}
                    className="flex items-start gap-3 p-3 border rounded-lg"
                  >
                    <ChannelIcon className="h-5 w-5 mt-0.5 text-muted-foreground" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">
                          {CHANNEL_LABELS[d.channel] || d.channel}
                        </span>
                        <Badge
                          variant={STATUS_BADGE_VARIANTS[d.status] || 'outline'}
                          className="text-xs"
                        >
                          {d.status}
                        </Badge>
                        {getStatusIcon(d.status)}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        To: {d.recipient}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Sent: {formatDateTime(d.sent_at)}
                        {d.failed_at && ` | Failed: ${formatDateTime(d.failed_at)}`}
                      </p>
                      {d.retry_count > 0 && (
                        <p className="text-xs text-muted-foreground">
                          Retries: {d.retry_count}
                        </p>
                      )}
                      {d.error_message && (
                        <p className="text-xs text-red-500 mt-1">
                          Error: {d.error_message}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function FailedMessages() {
  const [deliveries, setDeliveries] = useState<NotificationDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [resending, setResending] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchFailedDeliveries({ limit: 50 });
      setDeliveries(result.items);
    } catch {
      toast.error('Failed to load failed messages');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleResend = async (deliveryId: string) => {
    setResending(deliveryId);
    try {
      await resendNotification(deliveryId);
      toast.success('Resend initiated');
      load();
    } catch {
      toast.error('Failed to resend');
    } finally {
      setResending(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (deliveries.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-muted-foreground">
          <CheckCircle2 className="h-12 w-12 mx-auto mb-2 text-green-500" />
          <p>No failed messages</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {deliveries.map((d) => {
        const ChannelIcon = CHANNEL_ICONS[d.channel] || Mail;
        return (
          <Card key={d.id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <ChannelIcon className="h-4 w-4" />
                    <Badge variant="destructive">Failed</Badge>
                    <span className="text-xs text-muted-foreground">
                      {CHANNEL_LABELS[d.channel] || d.channel}
                    </span>
                  </div>
                  <p className="text-sm">To: {d.recipient}</p>
                  {d.error_message && (
                    <p className="text-xs text-red-500 mt-1">
                      <AlertTriangle className="h-3 w-3 inline mr-1" />
                      {d.error_message}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    Retries: {d.retry_count} | {formatDateTime(d.failed_at)}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleResend(d.id)}
                  disabled={resending === d.id}
                >
                  {resending === d.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                  <span className="ml-1 hidden sm:inline">Resend</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function TemplateManager() {
  const [templates, setTemplates] = useState<CommunicationTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingTemplate, setEditingTemplate] = useState<CommunicationTemplate | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [previewResult, setPreviewResult] = useState<{
    subject: string | null;
    body: string;
  } | null>(null);
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [placeholders, setPlaceholders] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchTemplates({ limit: 100 });
      setTemplates(result.items);
      const ph = await fetchPlaceholders();
      setPlaceholders(ph);
    } catch {
      toast.error('Failed to load templates');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (data: {
    template_type: string;
    channel: string;
    subject?: string;
    body: string;
  }) => {
    try {
      await createTemplate(data);
      toast.success('Template created');
      setShowCreateDialog(false);
      load();
    } catch {
      toast.error('Failed to create template');
    }
  };

  const handleUpdate = async (
    id: string,
    data: { subject?: string; body?: string }
  ) => {
    try {
      await updateTemplate(id, data);
      toast.success('Template updated');
      setEditingTemplate(null);
      load();
    } catch {
      toast.error('Failed to update template');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this template?')) return;
    try {
      await deleteTemplate(id);
      toast.success('Template deleted');
      load();
    } catch {
      toast.error('Failed to delete template');
    }
  };

  const handlePreview = async (template: CommunicationTemplate) => {
    try {
      const result = await previewTemplate({
        template_id: template.id,
        test_context: {
          patient_name: 'John Doe',
          doctor_name: 'Dr. Smith',
          appointment_time: '2026-05-15 10:00 AM',
          clinic_name: 'City Medical Center',
        },
      });
      setPreviewResult(result);
      setShowPreviewDialog(true);
    } catch {
      toast.error('Failed to preview template');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Communication Templates</h3>
        <Button size="sm" onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-1" />
          New Template
        </Button>
      </div>

      {/* Placeholder reference */}
      {Object.keys(placeholders).length > 0 && (
        <Card className="bg-muted/50">
          <CardContent className="p-3">
            <p className="text-xs font-medium mb-1">Available Placeholders:</p>
            <div className="flex flex-wrap gap-1">
              {Object.entries(placeholders).map(([key, desc]) => (
                <Badge key={key} variant="outline" className="text-xs">
                  {'{{'}{key}{'}}'} — {desc}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {templates.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No templates yet. Create your first template.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Channel</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Locale</TableHead>
                <TableHead>Active</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {templates.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>
                    <Badge variant="outline">
                      {EVENT_TYPE_LABELS[t.template_type] || t.template_type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {(() => {
                        const Icon = CHANNEL_ICONS[t.channel] || Mail;
                        return <Icon className="h-3.5 w-3.5" />;
                      })()}
                      <span className="text-sm">
                        {CHANNEL_LABELS[t.channel] || t.channel}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm max-w-[200px] truncate">
                    {t.subject || '—'}
                  </TableCell>
                  <TableCell className="text-sm">{t.locale}</TableCell>
                  <TableCell>
                    {t.is_active ? (
                      <Badge className="bg-green-100 text-green-700">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handlePreview(t)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setEditingTemplate(t)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(t.id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Template</DialogTitle>
            <DialogDescription>
              Create a new communication template for your tenant.
            </DialogDescription>
          </DialogHeader>
          <TemplateForm
            onSubmit={handleCreate}
            onCancel={() => setShowCreateDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={editingTemplate !== null}
        onOpenChange={(open: boolean) => {
          if (!open) setEditingTemplate(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Template</DialogTitle>
            <DialogDescription>Update the template content.</DialogDescription>
          </DialogHeader>
          {editingTemplate && (
            <TemplateForm
              initial={editingTemplate}
              onSubmit={(data) => handleUpdate(editingTemplate.id, data)}
              onCancel={() => setEditingTemplate(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={showPreviewDialog} onOpenChange={setShowPreviewDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Template Preview</DialogTitle>
          </DialogHeader>
          {previewResult && (
            <div className="space-y-3">
              {previewResult.subject && (
                <div>
                  <Label>Subject</Label>
                  <p className="text-sm font-medium p-2 border rounded mt-1">
                    {previewResult.subject}
                  </p>
                </div>
              )}
              <div>
                <Label>Body</Label>
                <div className="mt-1 p-3 border rounded bg-muted/30 whitespace-pre-wrap text-sm">
                  {previewResult.body}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function TemplateForm({
  initial,
  onSubmit,
  onCancel,
}: {
  initial?: CommunicationTemplate;
  onSubmit: (data: {
    template_type: string;
    channel: string;
    subject?: string;
    body: string;
  }) => void;
  onCancel: () => void;
}) {
  const [templateType, setTemplateType] = useState(
    initial?.template_type || 'appointment_booked'
  );
  const [channel, setChannel] = useState(initial?.channel || 'email');
  const [subject, setSubject] = useState(initial?.subject || '');
  const [body, setBody] = useState(initial?.body || '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!body.trim()) {
      toast.error('Body is required');
      return;
    }
    onSubmit({
      template_type: templateType,
      channel,
      subject: subject.trim() || undefined,
      body: body.trim(),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Template Type</Label>
          <Select value={templateType} onValueChange={setTemplateType}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(EVENT_TYPE_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Channel</Label>
          <Select value={channel} onValueChange={setChannel}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(CHANNEL_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div>
        <Label>Subject (optional)</Label>
        <Input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Your appointment is confirmed"
        />
      </div>
      <div>
        <Label>Body *</Label>
        <Textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={6}
          placeholder="Dear {{ patient_name }}, your appointment with {{ doctor_name }} is confirmed for {{ appointment_time }}."
        />
        <p className="text-xs text-muted-foreground mt-1">
          Use {'{{'} placeholder_name {'}}'} for dynamic content.
        </p>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">
          {initial ? 'Update' : 'Create'}
        </Button>
      </DialogFooter>
    </form>
  );
}

function ReminderSettingsPanel() {
  const [settings, setSettings] = useState<ReminderSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchReminderSettings();
      setSettings(result);
    } catch {
      toast.error('Failed to load reminder settings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleToggle = async (key: keyof ReminderSettings) => {
    if (!settings) return;
    const updated = {
      ...settings,
      [key]: !settings[key],
    };
    setSettings(updated);
    setSaving(true);
    try {
      await updateReminderSettings(updated);
      toast.success('Reminder settings updated');
    } catch {
      toast.error('Failed to update settings');
      load();
    } finally {
      setSaving(false);
    }
  };

  const handleChannelToggle = async (channel: string) => {
    if (!settings) return;
    const channels = settings.reminder_channels.includes(channel)
      ? settings.reminder_channels.filter((c) => c !== channel)
      : [...settings.reminder_channels, channel];
    const updated = { ...settings, reminder_channels: channels };
    setSettings(updated);
    setSaving(true);
    try {
      await updateReminderSettings(updated);
      toast.success('Reminder channels updated');
    } catch {
      toast.error('Failed to update channels');
      load();
    } finally {
      setSaving(false);
    }
  };

  const handleTriggerReminders = async () => {
    try {
      const result = await triggerReminders();
      toast.success(
        `Reminders triggered: ${JSON.stringify(result.results)}`
      );
    } catch {
      toast.error('Failed to trigger reminders');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!settings) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Reminder Settings</h3>
        <Button
          variant="outline"
          size="sm"
          onClick={handleTriggerReminders}
          disabled={saving}
        >
          <RefreshCw className="h-4 w-4 mr-1" />
          Trigger Now
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reminder Timing</CardTitle>
          <CardDescription>
            Enable or disable automatic reminders for appointments.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">24-hour Reminder</p>
              <p className="text-sm text-muted-foreground">
                Send reminder 24 hours before appointment
              </p>
            </div>
            <Switch
              checked={settings.twenty_four_hour_enabled}
              onCheckedChange={() => handleToggle('twenty_four_hour_enabled')}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">2-hour Reminder</p>
              <p className="text-sm text-muted-foreground">
                Send reminder 2 hours before appointment
              </p>
            </div>
            <Switch
              checked={settings.two_hour_enabled}
              onCheckedChange={() => handleToggle('two_hour_enabled')}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Follow-up Reminder</p>
              <p className="text-sm text-muted-foreground">
                Send follow-up reminder after appointment
              </p>
            </div>
            <Switch
              checked={settings.follow_up_enabled}
              onCheckedChange={() => handleToggle('follow_up_enabled')}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reminder Channels</CardTitle>
          <CardDescription>
            Select which channels to use for sending reminders.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {Object.entries(CHANNEL_LABELS).map(([key, label]) => {
              const Icon = CHANNEL_ICONS[key] || Mail;
              const isActive = settings.reminder_channels.includes(key);
              return (
                <Button
                  key={key}
                  variant={isActive ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleChannelToggle(key)}
                  className="gap-2"
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Button>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

export default function AdminCommunicationsPage() {
  const [stats, setStats] = useState<CommunicationDashboardStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const result = await fetchCommunicationDashboardStats();
        setStats(result);
      } catch {
        // Stats are non-critical
      } finally {
        setStatsLoading(false);
      }
    })();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="p-4 md:p-6 max-w-7xl mx-auto"
    >
      <div className="flex items-center gap-3 mb-6">
        <Bell className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Communications</h1>
          <p className="text-sm text-muted-foreground">
            Notification history, templates, and reminder settings
          </p>
        </div>
      </div>

      {statsLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <StatsCards stats={stats} />
      )}

      <Tabs defaultValue="history" className="mt-6">
        <TabsList className="w-full justify-start overflow-x-auto">
          <TabsTrigger value="history" className="gap-2">
            <Bell className="h-4 w-4" />
            <span className="hidden sm:inline">History</span>
          </TabsTrigger>
          <TabsTrigger value="failed" className="gap-2">
            <AlertTriangle className="h-4 w-4" />
            <span className="hidden sm:inline">Failed</span>
          </TabsTrigger>
          <TabsTrigger value="templates" className="gap-2">
            <FileText className="h-4 w-4" />
            <span className="hidden sm:inline">Templates</span>
          </TabsTrigger>
          <TabsTrigger value="reminders" className="gap-2">
            <Settings className="h-4 w-4" />
            <span className="hidden sm:inline">Reminders</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="history" className="mt-4">
          <NotificationHistory />
        </TabsContent>

        <TabsContent value="failed" className="mt-4">
          <FailedMessages />
        </TabsContent>

        <TabsContent value="templates" className="mt-4">
          <TemplateManager />
        </TabsContent>

        <TabsContent value="reminders" className="mt-4">
          <ReminderSettingsPanel />
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
