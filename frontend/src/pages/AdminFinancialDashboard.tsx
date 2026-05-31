/**
 * Admin Financial Dashboard — Phase 3A Financial Reporting + Inventory Ledger.
 *
 * Tab-based dashboard with:
 * - Billing Report
 * - Inventory Ledger
 * - Patient Financials
 * - Exports
 *
 * Mobile-first tables with filters, date ranges, and export buttons.
 */

import { useState, useEffect, useCallback } from 'react';
import dayjs from 'dayjs';
import {
  BarChart3,
  Download,
  FileSpreadsheet,
  FileText,
  Filter,
  Package,
  Receipt,
  Search,
  User,
  Wallet,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState, EmptyState } from '../components/common';
import {
  fetchBillingReport,
  fetchInventoryLedger,
  fetchPatientFinancialLedger,
  exportReport,
  downloadBlob,
  type BillingReportResult,
  type InventoryLedgerResult,
  type PatientFinancialLedger,
} from '../services/reporting';
import { documentsApi } from '../services/documents';


// ── Helpers ────────────────────────────────────────────────────────────────

function formatCurrency(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(num);
}

function formatDateShort(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  return dayjs(dateStr).format('MMM D, YYYY');
}

function statusBadge(status: string) {
  const variant = status === 'paid' ? 'default' : status === 'unpaid' ? 'secondary' : 'default';
  return (
    <Badge variant={variant}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

function movementBadge(type: string) {
  const variant = type === 'IN' ? 'default' : type === 'OUT' ? 'destructive' : 'secondary';
  return (
    <Badge variant={variant}>
      {type}
    </Badge>
  );
}

// ── Billing Report Tab ─────────────────────────────────────────────────────

function BillingReportTab() {
  const [data, setData] = useState<BillingReportResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const filters: any = { skip: page * pageSize, limit: pageSize };
      if (dateFrom) filters.date_from = new Date(dateFrom).toISOString();
      if (dateTo) filters.date_to = new Date(dateTo).toISOString();
      if (statusFilter) filters.status = statusFilter;
      const result = await fetchBillingReport(filters);
      setData(result);
    } catch (err: any) {
      setError(err?.message || 'Failed to load billing report');
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, statusFilter, page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExport = async (format: 'csv' | 'xlsx' | 'pdf') => {
    try {
      const blob = await exportReport('billing', undefined, {
        format,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
        status: statusFilter as any || undefined,
      });
      downloadBlob(blob, `billing_report.${format}`);
    } catch (err: any) {
      console.error('Export failed:', err);
    }
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <Label htmlFor="bill-date-from" className="text-xs">Date From</Label>
              <Input
                id="bill-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
                className="h-9 w-40"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="bill-date-to" className="text-xs">Date To</Label>
              <Input
                id="bill-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
                className="h-9 w-40"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="bill-status" className="text-xs">Status</Label>
              <Select
                value={statusFilter}
                onValueChange={(v: string) => { setStatusFilter(v); setPage(0); }}
              >
                <SelectTrigger id="bill-status" className="h-9 w-36">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All</SelectItem>
                  <SelectItem value="paid">Paid</SelectItem>
                  <SelectItem value="unpaid">Unpaid</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
                <Filter className="mr-1 h-4 w-4" />
                Apply
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport('csv')}>
                <Download className="mr-1 h-4 w-4" />
                CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport('xlsx')}>
                <FileSpreadsheet className="mr-1 h-4 w-4" />
                XLSX
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport('pdf')}>
                <FileText className="mr-1 h-4 w-4" />
                PDF
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {error && (
        <ErrorState
          title="Failed to load billing report"
          description={error}
          onRetry={loadData}
        />
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState title="No bills found" description="Try adjusting your filters." />
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Patient</th>
                  <th className="px-3 py-2 text-left font-medium">Doctor</th>
                  <th className="px-3 py-2 text-right font-medium">Amount</th>
                  <th className="px-3 py-2 text-right font-medium">Consultation</th>
                  <th className="px-3 py-2 text-right font-medium">Inventory</th>
                  <th className="px-3 py-2 text-center font-medium">Status</th>
                  <th className="px-3 py-2 text-left font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.bill_id} className="border-t hover:bg-muted/30">
                    <td className="px-3 py-2 font-medium">{row.patient_name}</td>
                    <td className="px-3 py-2 text-muted-foreground">{row.doctor_name || '—'}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{formatCurrency(row.bill_amount)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                      {formatCurrency(row.consultation_amount)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                      {formatCurrency(row.inventory_amount)}
                    </td>
                    <td className="px-3 py-2 text-center">{statusBadge(row.status)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{formatDateShort(row.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Inventory Ledger Tab ───────────────────────────────────────────────────

function InventoryLedgerTab() {
  const [data, setData] = useState<InventoryLedgerResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [movementFilter, setMovementFilter] = useState<string>('');
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const filters: any = { skip: page * pageSize, limit: pageSize };
      if (dateFrom) filters.date_from = new Date(dateFrom).toISOString();
      if (dateTo) filters.date_to = new Date(dateTo).toISOString();
      if (movementFilter) filters.movement_type = movementFilter;
      const result = await fetchInventoryLedger(filters);
      setData(result);
    } catch (err: any) {
      setError(err?.message || 'Failed to load inventory ledger');
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, movementFilter, page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExport = async (format: 'csv' | 'xlsx' | 'pdf') => {
    try {
      const blob = await exportReport('inventory-ledger', undefined, {
        format,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
        movement_type: movementFilter as any || undefined,
      });
      downloadBlob(blob, `inventory_ledger.${format}`);
    } catch (err: any) {
      console.error('Export failed:', err);
    }
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <Label htmlFor="inv-date-from" className="text-xs">Date From</Label>
              <Input
                id="inv-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
                className="h-9 w-40"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="inv-date-to" className="text-xs">Date To</Label>
              <Input
                id="inv-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
                className="h-9 w-40"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="inv-movement" className="text-xs">Movement</Label>
              <Select
                value={movementFilter}
                onValueChange={(v: string) => { setMovementFilter(v); setPage(0); }}
              >
                <SelectTrigger id="inv-movement" className="h-9 w-36">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All</SelectItem>
                  <SelectItem value="IN">IN</SelectItem>
                  <SelectItem value="OUT">OUT</SelectItem>
                  <SelectItem value="ADJUST">ADJUST</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
                <Filter className="mr-1 h-4 w-4" />
                Apply
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport('csv')}>
                <Download className="mr-1 h-4 w-4" />
                CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport('xlsx')}>
                <FileSpreadsheet className="mr-1 h-4 w-4" />
                XLSX
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport('pdf')}>
                <FileText className="mr-1 h-4 w-4" />
                PDF
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {error && (
        <ErrorState
          title="Failed to load inventory ledger"
          description={error}
          onRetry={loadData}
        />
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState title="No movements found" description="Try adjusting your filters." />
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Item</th>
                  <th className="px-3 py-2 text-center font-medium">Type</th>
                  <th className="px-3 py-2 text-right font-medium">Qty</th>
                  <th className="px-3 py-2 text-right font-medium">Running Stock</th>
                  <th className="px-3 py-2 text-left font-medium">Actor</th>
                  <th className="px-3 py-2 text-left font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.movement_id} className="border-t hover:bg-muted/30">
                    <td className="px-3 py-2 font-medium">{row.item_name}</td>
                    <td className="px-3 py-2 text-center">{movementBadge(row.movement_type)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{row.quantity}</td>
                    <td className="px-3 py-2 text-right tabular-nums font-medium">{row.running_stock}</td>
                    <td className="px-3 py-2 text-muted-foreground">{row.actor_role || '—'}</td>
                    <td className="px-3 py-2 text-muted-foreground">{formatDateShort(row.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Patient Financials Tab ─────────────────────────────────────────────────

function PatientFinancialsTab() {
  const [patientId, setPatientId] = useState('');
  const [ledger, setLedger] = useState<PatientFinancialLedger | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!patientId.trim()) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const result = await fetchPatientFinancialLedger(patientId.trim());
      setLedger(result);
    } catch (err: any) {
      setError(err?.message || 'Patient not found');
      setLedger(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'csv' | 'xlsx' | 'pdf') => {
    if (!ledger) return;
    try {
      const blob = await exportReport('patient-financial', ledger.patient_id, { format });
      downloadBlob(blob, `patient_ledger_${ledger.patient_id}.${format}`);
    } catch (err: any) {
      console.error('Export failed:', err);
    }
  };

  return (
    <div className="space-y-4">
      {/* Search */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-end gap-3">
            <div className="flex-1 space-y-1">
              <Label htmlFor="patient-search" className="text-xs">Patient ID</Label>
              <Input
                id="patient-search"
                placeholder="Enter patient UUID..."
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
                className="h-9"
              />
            </div>
            <Button size="sm" onClick={handleSearch} disabled={loading || !patientId.trim()}>
              <Search className="mr-1 h-4 w-4" />
              Search
            </Button>
          </div>
        </CardContent>
      </Card>

      {loading && (
        <div className="space-y-2">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {error && (
        <ErrorState
          title="Failed to load patient financials"
          description={error}
          onRetry={handleSearch}
        />
      )}

      {!loading && !error && searched && !ledger && (
        <EmptyState title="Patient not found" description="Check the patient ID and try again." />
      )}

      {!loading && !error && ledger && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Total Billed</p>
                <p className="text-xl font-semibold tabular-nums">{formatCurrency(ledger.total_billed)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Total Paid</p>
                <p className="text-xl font-semibold tabular-nums text-green-600">{formatCurrency(ledger.total_paid)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Unpaid</p>
                <p className="text-xl font-semibold tabular-nums text-amber-600">{formatCurrency(ledger.total_unpaid)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Balance</p>
                <p className={`text-xl font-semibold tabular-nums ${parseFloat(ledger.balance) > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {formatCurrency(ledger.balance)}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Bills Table */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-base">Bills ({ledger.bills.length})</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleExport('csv')}>
                  <Download className="mr-1 h-4 w-4" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleExport('pdf')}>
                  <FileText className="mr-1 h-4 w-4" /> PDF
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    void documentsApi.triggerStatementDownload(ledger.patient_id);
                  }}
                >
                  <Wallet className="mr-1 h-4 w-4" /> Statement
                </Button>
              </div>

            </CardHeader>
            <CardContent>
              {ledger.bills.length === 0 ? (
                <p className="text-sm text-muted-foreground">No bills found.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium">Bill ID</th>
                        <th className="px-3 py-2 text-right font-medium">Amount</th>
                        <th className="px-3 py-2 text-center font-medium">Status</th>
                        <th className="px-3 py-2 text-left font-medium">Paid At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ledger.bills.map((bill) => (
                        <tr key={bill.bill_id} className="border-t hover:bg-muted/30">
                          <td className="px-3 py-2 font-mono text-xs">{bill.bill_id.slice(0, 8)}…</td>
                          <td className="px-3 py-2 text-right tabular-nums">{formatCurrency(bill.amount)}</td>
                          <td className="px-3 py-2 text-center">{statusBadge(bill.status)}</td>
                          <td className="px-3 py-2 text-muted-foreground">{formatDateShort(bill.paid_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Encounters */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Encounters ({ledger.encounters.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {ledger.encounters.length === 0 ? (
                <p className="text-sm text-muted-foreground">No encounters found.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium">Doctor</th>
                        <th className="px-3 py-2 text-left font-medium">Date</th>
                        <th className="px-3 py-2 text-center font-medium">Billed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ledger.encounters.map((enc) => (
                        <tr key={enc.appointment_id} className="border-t hover:bg-muted/30">
                          <td className="px-3 py-2">{enc.doctor_name}</td>
                          <td className="px-3 py-2 text-muted-foreground">{formatDateShort(enc.appointment_time)}</td>
                          <td className="px-3 py-2 text-center">
                            {enc.has_bill ? (
                              <Badge variant="default">Yes</Badge>
                            ) : (
                              <Badge variant="secondary">No</Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

// ── Exports Tab ────────────────────────────────────────────────────────────

function ExportsTab() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = async (reportType: 'billing' | 'inventory-ledger', format: 'csv' | 'xlsx' | 'pdf') => {
    const key = `${reportType}-${format}`;
    setExporting(key);
    try {
      const blob = await exportReport(reportType, undefined, {
        format,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
      });
      downloadBlob(blob, `${reportType}.${format}`);
    } catch (err: any) {
      console.error('Export failed:', err);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-end gap-3 mb-4">
            <div className="space-y-1">
              <Label htmlFor="export-date-from" className="text-xs">Date From</Label>
              <Input
                id="export-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="h-9 w-40"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="export-date-to" className="text-xs">Date To</Label>
              <Input
                id="export-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="h-9 w-40"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="border-dashed">
              <CardContent className="pt-4">
                <div className="flex flex-col items-center gap-2 text-center">
                  <Receipt className="h-8 w-8 text-muted-foreground" />
                  <h3 className="font-medium">Billing Report</h3>
                  <p className="text-xs text-muted-foreground">Export all bills with current filters</p>
                  <div className="flex gap-2 mt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport('billing', 'csv')}
                      disabled={exporting === 'billing-csv'}
                    >
                      <Download className="mr-1 h-4 w-4" />
                      CSV
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport('billing', 'xlsx')}
                      disabled={exporting === 'billing-xlsx'}
                    >
                      <FileSpreadsheet className="mr-1 h-4 w-4" />
                      XLSX
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport('billing', 'pdf')}
                      disabled={exporting === 'billing-pdf'}
                    >
                      <FileText className="mr-1 h-4 w-4" />
                      PDF
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-dashed">
              <CardContent className="pt-4">
                <div className="flex flex-col items-center gap-2 text-center">
                  <Package className="h-8 w-8 text-muted-foreground" />
                  <h3 className="font-medium">Inventory Ledger</h3>
                  <p className="text-xs text-muted-foreground">Export all inventory movements</p>
                  <div className="flex gap-2 mt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport('inventory-ledger', 'csv')}
                      disabled={exporting === 'inventory-ledger-csv'}
                    >
                      <Download className="mr-1 h-4 w-4" />
                      CSV
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport('inventory-ledger', 'xlsx')}
                      disabled={exporting === 'inventory-ledger-xlsx'}
                    >
                      <FileSpreadsheet className="mr-1 h-4 w-4" />
                      XLSX
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport('inventory-ledger', 'pdf')}
                      disabled={exporting === 'inventory-ledger-pdf'}
                    >
                      <FileText className="mr-1 h-4 w-4" />
                      PDF
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────

export default function AdminFinancialDashboard() {
  return (
    <div className="container mx-auto p-4 sm:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Financial Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Billing reports, inventory ledger, patient financials, and exports
          </p>
        </div>
        <BarChart3 className="h-8 w-8 text-muted-foreground" />
      </div>

      <Tabs defaultValue="billing" className="space-y-4">
        <TabsList className="w-full sm:w-auto flex-wrap">
          <TabsTrigger value="billing" className="flex items-center gap-1">
            <Receipt className="h-4 w-4" />
            <span className="hidden sm:inline">Billing</span>
          </TabsTrigger>
          <TabsTrigger value="inventory" className="flex items-center gap-1">
            <Package className="h-4 w-4" />
            <span className="hidden sm:inline">Inventory Ledger</span>
          </TabsTrigger>
          <TabsTrigger value="patients" className="flex items-center gap-1">
            <User className="h-4 w-4" />
            <span className="hidden sm:inline">Patient Financials</span>
          </TabsTrigger>
          <TabsTrigger value="exports" className="flex items-center gap-1">
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">Exports</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="billing">
          <BillingReportTab />
        </TabsContent>

        <TabsContent value="inventory">
          <InventoryLedgerTab />
        </TabsContent>

        <TabsContent value="patients">
          <PatientFinancialsTab />
        </TabsContent>

        <TabsContent value="exports">
          <ExportsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
