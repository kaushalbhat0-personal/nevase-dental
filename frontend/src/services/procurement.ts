/**
 * Procurement API service — suppliers, purchase orders, reports.
 */

import { api } from './index';

export interface Supplier {
  id: string;
  tenant_id: string;
  supplier_name: string;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  gst_number: string | null;
  tax_id: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SupplierCreate {
  supplier_name: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  gst_number?: string;
  tax_id?: string;
  notes?: string;
  is_active?: boolean;
}

export interface SupplierUpdate {
  supplier_name?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  gst_number?: string;
  tax_id?: string;
  notes?: string;
  is_active?: boolean;
}

export interface PurchaseOrderItemCreate {
  inventory_item_id: string;
  quantity: number;
  unit_cost: number;
  tax_percent: number;
  batch_number?: string;
  expiry_date?: string;
  line_total: number;
}

export interface PurchaseOrderCreate {
  supplier_id: string;
  invoice_number?: string;
  invoice_date?: string;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total_amount: number;
  payment_status?: string;
  payment_method?: string;
  notes?: string;
  items: PurchaseOrderItemCreate[];
}

export interface PurchaseOrderItem {
  id: string;
  purchase_order_id: string;
  inventory_item_id: string;
  quantity: number;
  unit_cost: number;
  tax_percent: number;
  batch_number: string | null;
  expiry_date: string | null;
  line_total: number;
  inventory_item_name: string | null;
}

export interface PurchaseOrder {
  id: string;
  tenant_id: string;
  supplier_id: string;
  invoice_number: string | null;
  invoice_date: string | null;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total_amount: number;
  payment_status: string;
  payment_method: string | null;
  status: string;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  supplier_name: string | null;
  items: PurchaseOrderItem[];
}

export interface ProcurementReportRow {
  purchase_order_id: string;
  invoice_number: string | null;
  invoice_date: string | null;
  supplier_name: string;
  supplier_gst: string | null;
  item_count: number;
  total_qty: number;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  status: string;
  created_at: string;
}

export interface ProcurementReport {
  rows: ProcurementReportRow[];
  total_subtotal: number;
  total_tax: number;
  total_amount: number;
  grand_total: number;
}

export interface TaxSummaryRow {
  supplier_name: string;
  gst_number: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  taxable_value: number;
  total_tax: number;
  invoice_count: number;
}

export interface TaxSummary {
  rows: TaxSummaryRow[];
  total_taxable_value: number;
  total_tax: number;
}

export interface StockValuation {
  total_items: number;
  total_quantity: number;
  total_value_at_cost: number;
  total_value_at_selling: number;
}

export interface InwardOutwardRow {
  period: string;
  inward_qty: number;
  inward_value: number;
  outward_qty: number;
  outward_value: number;
}

export interface InwardOutwardValuation {
  rows: InwardOutwardRow[];
  total_inward_qty: number;
  total_inward_value: number;
  total_outward_qty: number;
  total_outward_value: number;
}

// ── Suppliers ──────────────────────────────────────────────────────────────

export async function createSupplier(data: SupplierCreate): Promise<Supplier> {
  const res = await api.post('/api/v1/procurement/suppliers', data);
  return res.data;
}

export async function listSuppliers(params?: {
  skip?: number;
  limit?: number;
  search?: string;
  active_only?: boolean;
}): Promise<{ suppliers: Supplier[]; total: number }> {
  const res = await api.get('/api/v1/procurement/suppliers', { params });
  return res.data;
}

export async function getSupplier(id: string): Promise<Supplier> {
  const res = await api.get(`/api/v1/procurement/suppliers/${id}`);
  return res.data;
}

export async function updateSupplier(id: string, data: SupplierUpdate): Promise<Supplier> {
  const res = await api.put(`/api/v1/procurement/suppliers/${id}`, data);
  return res.data;
}

// ── Purchase Orders ────────────────────────────────────────────────────────

export async function createPurchaseOrder(data: PurchaseOrderCreate): Promise<PurchaseOrder> {
  const res = await api.post('/api/v1/procurement/purchase-orders', data);
  return res.data;
}

export async function listPurchaseOrders(params?: {
  skip?: number;
  limit?: number;
  status?: string;
  supplier_id?: string;
}): Promise<{ purchase_orders: PurchaseOrder[]; total: number }> {
  const res = await api.get('/api/v1/procurement/purchase-orders', { params });
  return res.data;
}

export async function getPurchaseOrder(id: string): Promise<PurchaseOrder> {
  const res = await api.get(`/api/v1/procurement/purchase-orders/${id}`);
  return res.data;
}

export async function completePurchaseOrder(id: string): Promise<PurchaseOrder> {
  const res = await api.post(`/api/v1/procurement/purchase-orders/${id}/complete`);
  return res.data;
}

export async function cancelPurchaseOrder(id: string): Promise<PurchaseOrder> {
  const res = await api.post(`/api/v1/procurement/purchase-orders/${id}/cancel`);
  return res.data;
}

// ── Reports ────────────────────────────────────────────────────────────────

export async function getProcurementReport(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<ProcurementReport> {
  const res = await api.get('/api/v1/procurement/reports/procurement', { params });
  return res.data;
}

export async function getTaxSummary(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<TaxSummary> {
  const res = await api.get('/api/v1/procurement/reports/tax-summary', { params });
  return res.data;
}

export async function getStockValuation(): Promise<StockValuation> {
  const res = await api.get('/api/v1/procurement/reports/stock-valuation');
  return res.data;
}

export async function getInwardOutwardValuation(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<InwardOutwardValuation> {
  const res = await api.get('/api/v1/procurement/reports/inward-outward-valuation', { params });
  return res.data;
}

// ── CSV Exports ────────────────────────────────────────────────────────────

export function getProcurementCsvUrl(params?: { date_from?: string; date_to?: string }): string {
  const base = '/api/v1/procurement/exports/procurement-csv';
  const searchParams = new URLSearchParams();
  if (params?.date_from) searchParams.set('date_from', params.date_from);
  if (params?.date_to) searchParams.set('date_to', params.date_to);
  const qs = searchParams.toString();
  return qs ? `${base}?${qs}` : base;
}

export function getTaxCsvUrl(params?: { date_from?: string; date_to?: string }): string {
  const base = '/api/v1/procurement/exports/tax-csv';
  const searchParams = new URLSearchParams();
  if (params?.date_from) searchParams.set('date_from', params.date_from);
  if (params?.date_to) searchParams.set('date_to', params.date_to);
  const qs = searchParams.toString();
  return qs ? `${base}?${qs}` : base;
}
