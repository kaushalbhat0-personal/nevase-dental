/**
 * Reporting API client — Phase 3A Financial Reporting + Inventory Ledger.
 *
 * All endpoints are READ-ONLY derived aggregates.
 * Exports are derived artifacts — they NEVER mutate financial records.
 */

import { api } from './index';

// ── Types ──────────────────────────────────────────────────────────────────

export interface BillingReportRow {
  bill_id: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string | null;
  doctor_name: string | null;
  appointment_id: string | null;
  appointment_time: string | null;
  tenant_id: string;
  bill_amount: string;
  consultation_amount: string;
  inventory_amount: string;
  status: 'paid' | 'unpaid';
  paid_at: string | null;
  paid_via: string | null;
  created_by: string;
  created_at: string;
}

export interface BillingReportResult {
  items: BillingReportRow[];
  total: number;
  skip: number;
  limit: number;
}

export interface InventoryLedgerRow {
  movement_id: string;
  item_id: string;
  item_name: string;
  item_type: string;
  movement_type: 'IN' | 'OUT' | 'ADJUST';
  quantity: number;
  running_stock: number;
  doctor_id: string | null;
  billing_id: string | null;
  encounter_id: string | null;
  actor_id: string | null;
  actor_role: string | null;
  created_at: string;
}

export interface InventoryLedgerResult {
  items: InventoryLedgerRow[];
  total: number;
  skip: number;
  limit: number;
}

export interface PatientBillSummary {
  bill_id: string;
  appointment_id: string | null;
  amount: string;
  status: string;
  paid_at: string | null;
  created_at: string;
}

export interface PatientEncounterRef {
  appointment_id: string;
  appointment_time: string;
  doctor_name: string;
  has_bill: boolean;
}

export interface PatientFinancialLedger {
  patient_id: string;
  patient_name: string;
  total_billed: string;
  total_paid: string;
  total_unpaid: string;
  balance: string;
  last_payment_at: string | null;
  bills: PatientBillSummary[];
  encounters: PatientEncounterRef[];
}

export interface BillingReportFilters {
  date_from?: string;
  date_to?: string;
  status?: 'paid' | 'unpaid';
  doctor_id?: string;
  patient_id?: string;
  skip?: number;
  limit?: number;
}

export interface InventoryLedgerFilters {
  date_from?: string;
  date_to?: string;
  item_id?: string;
  movement_type?: 'IN' | 'OUT' | 'ADJUST';
  skip?: number;
  limit?: number;
}

export interface ExportRequest {
  format: 'csv' | 'xlsx' | 'pdf';
  date_from?: string;
  date_to?: string;
  status?: 'paid' | 'unpaid';
  doctor_id?: string;
  patient_id?: string;
  item_id?: string;
  movement_type?: 'IN' | 'OUT' | 'ADJUST';
}

// ── API Functions ──────────────────────────────────────────────────────────

/**
 * Fetch paginated billing report with filters.
 */
export async function fetchBillingReport(
  filters: BillingReportFilters = {}
): Promise<BillingReportResult> {
  const params = new URLSearchParams();
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  if (filters.status) params.set('status', filters.status);
  if (filters.doctor_id) params.set('doctor_id', filters.doctor_id);
  if (filters.patient_id) params.set('patient_id', filters.patient_id);
  if (filters.skip !== undefined) params.set('skip', String(filters.skip));
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));

  const query = params.toString();
  const res = await api.get(`/reports/billing${query ? `?${query}` : ''}`);
  return res.data;
}

/**
 * Fetch paginated inventory ledger with filters.
 */
export async function fetchInventoryLedger(
  filters: InventoryLedgerFilters = {}
): Promise<InventoryLedgerResult> {
  const params = new URLSearchParams();
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  if (filters.item_id) params.set('item_id', filters.item_id);
  if (filters.movement_type) params.set('movement_type', filters.movement_type);
  if (filters.skip !== undefined) params.set('skip', String(filters.skip));
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));

  const query = params.toString();
  const res = await api.get(`/reports/inventory-ledger${query ? `?${query}` : ''}`);
  return res.data;
}

/**
 * Fetch full financial ledger for a patient.
 */
export async function fetchPatientFinancialLedger(
  patientId: string
): Promise<PatientFinancialLedger> {
  const res = await api.get(`/reports/patient-financial/${patientId}`);
  return res.data;
}

/**
 * Export a report in the requested format.
 * Returns a Blob for download.
 */
export async function exportReport(
  reportType: 'billing' | 'inventory-ledger' | 'patient-financial',
  patientId: string | undefined,
  body: ExportRequest
): Promise<Blob> {
  let url: string;
  if (reportType === 'patient-financial' && patientId) {
    url = `/reports/patient-financial/${patientId}/export`;
  } else {
    url = `/reports/${reportType}/export`;
  }

  const res = await api.post(url, body, {
    responseType: 'blob',
  });
  return res.data;
}

/**
 * Trigger a file download from a Blob.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}
