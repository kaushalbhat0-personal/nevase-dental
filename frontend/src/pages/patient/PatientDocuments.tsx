/**
 * PatientDocuments — enhanced document center for the patient workspace.
 *
 * PHASE UX2: Encounter Experience + Health Memory
 *
 * Improved with:
 * - Better PDF action cards
 * - Download status feedback
 * - Mobile-friendly actions
 * - Document grouping
 * - Calm medical-record presentation
 *
 * Does NOT redesign document generation backend.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import {
  Download,
  FileText,
  FileWarning,
  Loader2,
  Pill,
  Receipt,
  Search,
  X,
} from 'lucide-react';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { patientWorkspaceApi } from '../../services/patientWorkspace';
import { documentsApi } from '../../services/documents';
import type { DocumentRef } from '../../types';
import { ErrorState } from '../../components/common';
import toast from 'react-hot-toast';

export function PatientDocuments() {
  const [documents, setDocuments] = useState<DocumentRef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState('');

  const loadDocuments = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const workspace = await patientWorkspaceApi.getWorkspace();
      setDocuments(workspace.recent_documents);
    } catch {
      setError('Unable to load your documents.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  // ── Filter by search ────────────────────────────────────────────────────
  const filteredDocuments = useMemo(() => {
    if (!searchQuery.trim()) return documents;
    const q = searchQuery.toLowerCase().trim();
    return documents.filter(
      (doc) =>
        doc.document_type?.toLowerCase().includes(q) ||
        doc.doctor_name?.toLowerCase().includes(q),
    );
  }, [documents, searchQuery]);

  // ── Group by type ────────────────────────────────────────────────────────
  const groupedDocuments = useMemo(() => {
    const groups: Record<string, DocumentRef[]> = {
      prescription: [],
      encounter_summary: [],
      invoice: [],
      other: [],
    };

    for (const doc of filteredDocuments) {
      if (groups[doc.document_type]) {
        groups[doc.document_type]!.push(doc);
      } else {
        groups.other!.push(doc);
      }
    }

    return Object.entries(groups).filter(([, items]) => items.length > 0);
  }, [filteredDocuments]);

  const handleDownload = async (doc: DocumentRef) => {
    const key = `${doc.appointment_id}-${doc.document_type}`;
    setDownloading((prev) => ({ ...prev, [key]: true }));
    try {
      if (doc.document_type === 'prescription') {
        await documentsApi.triggerPrescriptionDownload(doc.appointment_id);
      } else if (doc.document_type === 'encounter_summary') {
        await documentsApi.triggerEncounterSummaryDownload(doc.appointment_id);
      } else if (doc.document_type === 'invoice') {
        await documentsApi.triggerInvoiceDownload(doc.appointment_id);
      }
      toast.success(`${getTypeLabel(doc.document_type)} downloaded`);
    } catch {
      toast.error(`Failed to download ${getTypeLabel(doc.document_type)}`);
    } finally {
      setDownloading((prev) => ({ ...prev, [key]: false }));
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'prescription':
        return <Pill className="h-5 w-5 text-blue-500" />;
      case 'encounter_summary':
        return <FileWarning className="h-5 w-5 text-emerald-500" />;
      case 'invoice':
        return <Receipt className="h-5 w-5 text-amber-500" />;
      default:
        return <FileText className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'prescription':
        return 'Prescription';
      case 'encounter_summary':
        return 'Encounter Summary';
      case 'invoice':
        return 'Invoice / Statement';
      default:
        return type.replace('_', ' ');
    }
  };

  const getGroupLabel = (type: string) => {
    switch (type) {
      case 'prescription':
        return 'Prescriptions';
      case 'encounter_summary':
        return 'Encounter Summaries';
      case 'invoice':
        return 'Invoices & Statements';
      default:
        return 'Other Documents';
    }
  };

  const getGroupIcon = (type: string) => {
    switch (type) {
      case 'prescription':
        return <Pill className="h-4 w-4 text-blue-500" />;
      case 'encounter_summary':
        return <FileWarning className="h-4 w-4 text-emerald-500" />;
      case 'invoice':
        return <Receipt className="h-4 w-4 text-amber-500" />;
      default:
        return <FileText className="h-4 w-4 text-muted-foreground" />;
    }
  };

  if (error) {
    return <ErrorState title="Documents" description={error} />;
  }

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Documents</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Download your medical records and documents.
        </p>
      </div>

      {/* ── Search ────────────────────────────────────────────────────────── */}
      {!loading && documents.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" aria-hidden />
          <Input
            type="text"
            placeholder="Search documents…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="rounded-2xl border-border/60 pl-10 text-sm h-12 bg-card"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-muted-foreground transition-colors touch-manipulation min-h-[36px] min-w-[36px] flex items-center justify-center"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 rounded-2xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : filteredDocuments.length === 0 && searchQuery ? (
        <Card className="border-dashed">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-muted/50">
              <Search className="h-7 w-7 text-muted-foreground" />
            </div>
            <CardTitle className="text-lg pt-3">No documents found</CardTitle>
            <CardDescription className="max-w-sm mx-auto">
              No documents match "{searchQuery}". Try a different search term.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : documents.length === 0 ? (
        <Card className="border-dashed">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
              <FileText className="h-7 w-7 text-primary" />
            </div>
            <CardTitle className="text-lg pt-3">No documents yet</CardTitle>
            <CardDescription className="max-w-sm mx-auto">
              After your first visit, you'll be able to download prescriptions,
              encounter summaries, and invoices here.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        /* ── Grouped document list ──────────────────────────────────────── */
        <div className="space-y-6">
          {groupedDocuments.map(([groupType, items]) => (
            <div key={groupType}>
              <div className="flex items-center gap-2 mb-3">
                {getGroupIcon(groupType)}
                <h2 className="text-sm font-semibold text-foreground">
                  {getGroupLabel(groupType)}
                </h2>
                <span className="text-xs text-muted-foreground/50">
                  {items.length}
                </span>
              </div>
              <div className="space-y-2">
                {items.map((doc, idx) => {
                  const key = `${doc.appointment_id}-${doc.document_type}`;
                  const isDownloading = downloading[key];
                  return (
                    <button
                      key={`${key}-${idx}`}
                      type="button"
                      onClick={() => handleDownload(doc)}
                      disabled={isDownloading}
                      className="flex w-full items-center gap-4 rounded-2xl border border-border/60 bg-card px-4 py-3.5 text-left shadow-sm transition-all hover:border-primary/20 hover:shadow-md active:scale-[0.98] disabled:opacity-50 touch-manipulation min-h-[60px]"
                    >
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/50">
                        {getIcon(doc.document_type)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-foreground capitalize">
                          {getTypeLabel(doc.document_type)}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          {doc.doctor_name && (
                            <span className="text-xs text-muted-foreground truncate">
                              {doc.doctor_name}
                            </span>
                          )}
                          {doc.appointment_time && (
                            <span className="text-xs text-muted-foreground/50 shrink-0">
                              {dayjs(doc.appointment_time).format('MMM D, YYYY')}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="shrink-0">
                        {isDownloading ? (
                          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        ) : (
                          <Download className="h-5 w-5 text-muted-foreground/60" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
