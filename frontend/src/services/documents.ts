/**
 * Document Generation API client.
 *
 * Documents are DERIVED ARTIFACTS generated on-demand from canonical backend aggregates.
 * All downloads use stream/download endpoints that return PDF blobs.
 *
 * TODO: Phase 3C — Signed URLs for document downloads
 * TODO: Phase 3C — Patient portal download history
 * TODO: Phase 3C — Email delivery trigger
 */

import { api } from './api';

/**
 * Helper to download a blob from the API and trigger a browser download.
 */
async function downloadBlob(
  url: string,
  _filename: string,
): Promise<Blob> {
  const response = await api.get(url, {
    responseType: 'blob',
  });
  return response.data as Blob;
}

/**
 * Trigger a browser file download from a Blob.
 */
function triggerDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

export const documentsApi = {
  /**
   * Download invoice PDF for the given bill.
   * GET /documents/invoice/{bill_id}
   */
  downloadInvoice: async (billId: string | number): Promise<Blob> => {
    return downloadBlob(`/documents/invoice/${billId}`, `invoice_${billId}.pdf`);
  },

  /**
   * Download patient financial statement PDF.
   * GET /documents/statement/{patient_id}
   */
  downloadPatientStatement: async (patientId: string | number): Promise<Blob> => {
    return downloadBlob(`/documents/statement/${patientId}`, `statement_${patientId}.pdf`);
  },

  /**
   * Download prescription PDF for the given appointment.
   * GET /documents/prescription/{appointment_id}
   */
  downloadPrescription: async (appointmentId: string | number): Promise<Blob> => {
    return downloadBlob(`/documents/prescription/${appointmentId}`, `prescription_${appointmentId}.pdf`);
  },

  /**
   * Download encounter summary PDF for the given appointment.
   * GET /documents/encounter-summary/{appointment_id}
   */
  downloadEncounterSummary: async (appointmentId: string | number): Promise<Blob> => {
    return downloadBlob(`/documents/encounter-summary/${appointmentId}`, `encounter_summary_${appointmentId}.pdf`);
  },

  /**
   * Trigger browser download for invoice PDF.
   */
  triggerInvoiceDownload: async (billId: string | number): Promise<void> => {
    const blob = await documentsApi.downloadInvoice(billId);
    triggerDownload(blob, `invoice_${billId}.pdf`);
  },

  /**
   * Trigger browser download for patient statement PDF.
   */
  triggerStatementDownload: async (patientId: string | number): Promise<void> => {
    const blob = await documentsApi.downloadPatientStatement(patientId);
    triggerDownload(blob, `statement_${patientId}.pdf`);
  },

  /**
   * Trigger browser download for prescription PDF.
   */
  triggerPrescriptionDownload: async (appointmentId: string | number): Promise<void> => {
    const blob = await documentsApi.downloadPrescription(appointmentId);
    triggerDownload(blob, `prescription_${appointmentId}.pdf`);
  },

  /**
   * Trigger browser download for encounter summary PDF.
   */
  triggerEncounterSummaryDownload: async (appointmentId: string | number): Promise<void> => {
    const blob = await documentsApi.downloadEncounterSummary(appointmentId);
    triggerDownload(blob, `encounter_summary_${appointmentId}.pdf`);
  },
};
