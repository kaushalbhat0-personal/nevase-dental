/**
 * Branding API service — tenant organization profile + branding profile management.
 *
 * Phase 3C — Tenant Branding + Organization Profile Foundation.
 *
 * TODO: Phase 4 — Logo upload endpoint (multipart/form-data)
 * TODO: Phase 4 — Bulk branding import/export for hospital chains
 */

import { api } from './api';

// ── Types ───────────────────────────────────────────────────────────────────

export interface TenantOrganizationProfile {
  id: string;
  tenant_id: string;
  organization_name: string | null;
  legal_name: string | null;
  logo_url: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  gst_number: string | null;
  registration_number: string | null;
  timezone: string | null;
  currency: string | null;
  prescription_footer: string | null;
  invoice_footer: string | null;
  created_at: string;
  updated_at: string;
}

export interface TenantOrganizationProfileUpdate {
  organization_name?: string | null;
  legal_name?: string | null;
  logo_url?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  address_line_1?: string | null;
  address_line_2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  gst_number?: string | null;
  registration_number?: string | null;
  timezone?: string | null;
  currency?: string | null;
  prescription_footer?: string | null;
  invoice_footer?: string | null;
}

export interface TenantBrandingProfile {
  id: string;
  tenant_id: string;
  primary_color: string | null;
  secondary_color: string | null;
  accent_color: string | null;
  document_header_style: string | null;
  watermark_text: string | null;
  prescription_template: string | null;
  invoice_template: string | null;
  created_at: string;
  updated_at: string;
}

export interface TenantBrandingProfileUpdate {
  primary_color?: string | null;
  secondary_color?: string | null;
  accent_color?: string | null;
  document_header_style?: string | null;
  watermark_text?: string | null;
  prescription_template?: string | null;
  invoice_template?: string | null;
}

// ── API Calls ───────────────────────────────────────────────────────────────

const BASE = '/branding';

/**
 * Fetch the organization profile for the current tenant.
 */
export async function getOrganizationProfile(): Promise<TenantOrganizationProfile | null> {
  const response = await api.get(`${BASE}/organization-profile`);
  if (response.status === 204 || response.data === null) {
    return null;
  }
  return response.data;
}

/**
 * Update (or create) the organization profile for the current tenant.
 */
export async function updateOrganizationProfile(
  data: TenantOrganizationProfileUpdate
): Promise<TenantOrganizationProfile> {
  const response = await api.put(`${BASE}/organization-profile`, data);
  return response.data;
}

/**
 * Fetch the branding profile for the current tenant.
 */
export async function getBrandingProfile(): Promise<TenantBrandingProfile | null> {
  const response = await api.get(`${BASE}/profile`);
  if (response.status === 204 || response.data === null) {
    return null;
  }
  return response.data;
}

/**
 * Update (or create) the branding profile for the current tenant.
 */
export async function updateBrandingProfile(
  data: TenantBrandingProfileUpdate
): Promise<TenantBrandingProfile> {
  const response = await api.put(`${BASE}/profile`, data);
  return response.data;
}

/**
 * Preview a document with current branding applied.
 *
 * @param documentType - 'invoice', 'prescription', or 'encounter_summary'
 * @param params - Optional sample IDs for preview data
 * @returns HTML string
 */
export async function previewDocument(
  documentType: 'invoice' | 'prescription' | 'encounter_summary',
  params?: { sample_bill_id?: string; sample_appointment_id?: string }
): Promise<string> {
  const queryParams = new URLSearchParams();
  if (params?.sample_bill_id) {
    queryParams.set('sample_bill_id', params.sample_bill_id);
  }
  if (params?.sample_appointment_id) {
    queryParams.set('sample_appointment_id', params.sample_appointment_id);
  }
  const qs = queryParams.toString();
  const url = `${BASE}/preview/${documentType}${qs ? `?${qs}` : ''}`;
  const response = await api.get(url, { responseType: 'text' });
  return response.data as string;
}
