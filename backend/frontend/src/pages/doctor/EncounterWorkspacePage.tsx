/**
 * EncounterWorkspacePage - Clinical workspace for patient visits/encounters
 *
 * This page consumes the canonical Encounter Aggregate API (GET /encounters/{appointment_id})
 * instead of assembling multiple requests client-side.
 *
 * Architecture principles:
 * - Appointment = Encounter anchor (NO separate Visit table)
 * - Single canonical payload from backend
 * - Clinical-first hierarchy (diagnosis > treatment > notes > medicines > billing)
 * - Reusable section components for extensibility
 * - Capability-based authorization (no role-based checks)
 * - Mobile-responsive design
 *
 * Invariants preserved:
 * - Tenant safety (all data scoped to current tenant)
 * - Idempotent completion
 * - Structured audit logging
 * - Timeline invariants
 * - Billing/inventory invariants
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import axios from 'axios';
import { CheckCircle2, FileText, Printer, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

import { ErrorState } from '../../components/common';
import {
  EncounterHeaderSection,
  EncounterVitalsSection,
  EncounterClinicalSection,
  EncounterPrescriptionsSection,
  EncounterMedicationSection,
  EncounterBillingSection,
  EncounterFollowUpSection,
  EncounterTimelineSection,
} from '../../components/encounter';
import { useDoctorWorkspace } from '../../contexts/DoctorWorkspaceContext';
import { useModalFocusTrap } from '../../hooks/useModalFocusTrap';
import { appointmentsApi, billingApi, documentsApi, encountersApi, inventoryApi } from '../../services';
import { useActiveWorkspace } from '../../workspace/useActiveWorkspace';
import { useAuth } from '../../hooks/useAuth';


import { DISPLAY_TIMEZONE } from '../../constants/time';
import { formatAppointmentDateTimeWithZoneLabel } from '../../utils/doctorSchedule';
import {
  getTenantInventoryCache,
  invalidateTenantInventoryCache,
  setTenantInventoryCache,
} from '../../utils/tenantInventoryCache';
import type {
  Bill,
  EncounterDetailAggregate,
  VisitAggregate,
} from '../../types';
import type { InventoryItemWithStockDTO } from '../../services/inventory';

// Import the completion modal component (extracted from legacy page)
import { CompleteVisitModal } from './components/CompleteVisitModal';

export function EncounterWorkspacePage() {
  const { appointmentId } = useParams<{ appointmentId: string }>();
  const { isIndependent, isReadOnly } = useDoctorWorkspace();
  const { user } = useAuth();
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const { isClinician, hasClinicianCapability } = useActiveWorkspace(user, token);

  // Core data state — single aggregate from the API
  const [aggregate, setAggregate] = useState<EncounterDetailAggregate | null>(null);

  // Historical data for timeline (still loaded separately for pagination)
  const [previousVisits, setPreviousVisits] = useState<VisitAggregate[]>([]);
  const [previousBills, setPreviousBills] = useState<Bill[]>([]);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [markBusy, setMarkBusy] = useState(false);
  const [completeOpen, setCompleteOpen] = useState(false);

  // Inventory cache for completion modal
  const [invItems, setInvItems] = useState<InventoryItemWithStockDTO[]>([]);
  const [invLoading, setInvLoading] = useState(false);
  const inventoryLoadErrorToastShown = useRef(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const completionIdempotencyRef = useRef('');

  useModalFocusTrap(modalRef, completeOpen);

  // Derive convenience references from the aggregate
  const appointment = aggregate?.appointment ?? null;
  const patient = aggregate?.patient ?? null;

  // Check if user can mark this encounter as complete
  // Clinical actions require: clinician capability (doctor role, normalized doctor role,
  // or linked Doctor record) + write access + scheduled status.
  // Workspace context does NOT block clinical actions — a tenant doctor in the Finance
  // workspace can still complete encounters because clinician capability exists.
  const canMarkComplete = useMemo(() => {
    return hasClinicianCapability && isIndependent && !isReadOnly && appointment?.status === 'scheduled';
  }, [hasClinicianCapability, isIndependent, isReadOnly, appointment?.status]);


  /**
   * Main data loading effect — consumes the canonical Encounter Aggregate API.
   * Single request replaces the previous multi-request pattern.
   */
  const loadEncounterData = useCallback(async () => {
    if (!appointmentId) {
      setError('Missing appointment ID');
      setLoading(false);
      return;
    }

    let cancelled = false;
    setError(null);
    setLoading(true);

    try {
      // SINGLE canonical request — replaces multiple client-side requests
      const encounter = await encountersApi.getById(appointmentId);
      if (cancelled) return;
      setAggregate(encounter);

      // Load patient history for timeline (still loaded separately for pagination/filtering)
      if (encounter.patient?.id) {
        try {
          const [patientAppointments, patientBills] = await Promise.all([
            appointmentsApi.getAll({
              patient_id: String(encounter.patient.id),
              skip: 0,
              limit: 50,
            }),
            billingApi.getAll({
              patient_id: String(encounter.patient.id),
              skip: 0,
              limit: 50,
            }),
          ]);

          if (!cancelled) {
            // Filter out current appointment from history
            const historyAppointments = patientAppointments.filter(
              (a) => String(a.id) !== String(encounter.appointment.id)
            );

            // Build VisitAggregates for history
            const historyVisits: VisitAggregate[] = historyAppointments.map((a) => {
              const linkedBill = patientBills.find(
                (b) => b.appointment_id && String(b.appointment_id) === String(a.id)
              );
              return {
                appointment: a,
                bill: linkedBill || null,
                inventoryUsage: a.inventory_usages,
              };
            });

            setPreviousVisits(historyVisits);

            // Bills not linked to appointments (orphaned)
            const linkedBillIds = new Set(
              patientAppointments
                .map((a) =>
                  patientBills.find(
                    (b) => b.appointment_id && String(b.appointment_id) === String(a.id)
                  )
                )
                .filter(Boolean)
                .map((b) => String(b!.id))
            );

            const orphanedBills = patientBills.filter(
              (b) => !linkedBillIds.has(String(b.id))
            );

            setPreviousBills(orphanedBills);
          }
        } catch (e) {
          // Non-critical: history loading failure shouldn't block the page
          console.warn('Failed to load patient history:', e);
        }
      }
    } catch (e) {
      if (!cancelled) {
        if (axios.isAxiosError(e) && e.response?.status === 404) {
          setError('Encounter not found');
        } else if (axios.isAxiosError(e) && e.response?.status === 403) {
          setError('Access denied');
        } else {
          setError('Could not load encounter data');
        }
        setAggregate(null);
      }
    } finally {
      if (!cancelled) setLoading(false);
    }

    return () => {
      cancelled = true;
    };
  }, [appointmentId, retryKey]);

  useEffect(() => {
    void loadEncounterData();
  }, [loadEncounterData]);
  
  /**
   * Load inventory items for completion modal
   */
  useEffect(() => {
    if (!canMarkComplete || !appointment) return;
    
    const cached = getTenantInventoryCache();
    if (cached && cached.length > 0) {
      setInvItems(cached);
      setInvLoading(false);
      return;
    }
    
    let cancelled = false;
    setInvLoading(true);
    
    void inventoryApi
      .listAllWithStock({ active_only: true })
      .then((rows) => {
        if (!cancelled) {
          inventoryLoadErrorToastShown.current = false;
          setInvItems(rows);
          setTenantInventoryCache(rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setInvItems([]);
          if (!inventoryLoadErrorToastShown.current) {
            toast.error('Could not load clinic inventory');
            inventoryLoadErrorToastShown.current = true;
          }
        }
      })
      .finally(() => {
        if (!cancelled) setInvLoading(false);
      });
      
    return () => {
      cancelled = true;
    };
  }, [canMarkComplete, appointment?.id]);
  
  /**
   * Handle encounter completion
   */
  const handleEncounterComplete = async (payload: {
    clinical_notes: string | null;
    diagnosis: string | null;
    treatment_summary: string | null;
    subjective_notes: string | null;
    objective_notes: string | null;
    assessment_notes: string | null;
    plan_notes: string | null;
    items: { item_id: string; quantity: number }[];
    prescriptions: {
      notes: string | null;
      items: {
        medicine_name: string;
        dosage?: string | null;
        frequency?: string | null;
        duration?: string | null;
        instructions?: string | null;
      }[];
    }[];
    vitals: {
      temperature?: number | null;
      bp_systolic?: number | null;
      bp_diastolic?: number | null;
      pulse?: number | null;
      respiratory_rate?: number | null;
      spo2?: number | null;
      weight?: number | null;
      height?: number | null;
      bmi?: number | null;
      notes?: string | null;
    } | null;
    generate_bill: boolean;
    bill_consultation_amount?: number;
  }) => {
    if (!appointmentId) return;
    
    setMarkBusy(true);
    try {
      const { appointment: updated } = await appointmentsApi.markCompleted(
        appointmentId,
        payload,
        { idempotencyKey: completionIdempotencyRef.current }
      );
      
      // Update the aggregate with the completed appointment
      setAggregate((prev) => {
        if (!prev) return prev;
        return { ...prev, appointment: updated };
      });
      invalidateTenantInventoryCache();
      setCompleteOpen(false);

      toast.success(
        payload.generate_bill
          ? 'Encounter completed and bill created'
          : 'Encounter marked complete'
      );

      // Refresh bill data
      const forAppt = await billingApi.getAll({
        appointment_id: String(updated.id),
        limit: 5,
      });
      setAggregate((prev) => {
        if (!prev) return prev;
        return { ...prev, bill: forAppt.length > 0 ? forAppt[0] : null };
      });
      
    } catch (e) {
      const msg = axios.isAxiosError(e) && e.response?.data 
        ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not complete encounter')
        : 'Could not complete encounter';
      toast.error(msg, { duration: 5000 });
    } finally {
      setMarkBusy(false);
    }
  };
  
  /**
   * Open completion modal with fresh idempotency key
   */
  const openCompleteModal = () => {
    completionIdempotencyRef.current =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random()}`;
    setCompleteOpen(true);
  };
  
  // The encounter aggregate comes directly from the API — no client-side assembly needed
  const encounterAggregate = aggregate;
  
  // Loading state
  if (loading && !encounterAggregate) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-32 bg-muted rounded" />
          <div className="h-40 bg-muted rounded-lg" />
          <div className="h-60 bg-muted rounded-lg" />
        </div>
      </div>
    );
  }
  
  // Error state
  if (error && !loading) {
    return (
      <div className="space-y-4">
        <ErrorState
          title={error === 'Encounter not found' ? 'Encounter not found' : 'Error loading encounter'}
          description={
            error === 'Encounter not found'
              ? 'This encounter may have been removed or you may not have access.'
              : 'We could not load this encounter. Please try again.'
          }
          error={error}
          onRetry={() => setRetryKey(k => k + 1)}
        />
      </div>
    );
  }
  
  // Missing data state
  if (!encounterAggregate || !appointment || !patient) {
    return (
      <div className="space-y-4">
        <ErrorState
          title="Data unavailable"
          description="Encounter data could not be loaded."
        />
      </div>
    );
  }
  
  const formattedDateTime = formatAppointmentDateTimeWithZoneLabel(
    appointment.appointment_time || appointment.scheduled_at || '',
    DISPLAY_TIMEZONE
  );
  
  return (
    <div 
      className="space-y-6 pb-8"
      id={appointmentId ? `encounter-${appointmentId}` : undefined}
    >
      {/* 
        PART 2: Encounter Workspace Layout
        Stable encounter sections with clear visual hierarchy
      */}
      
      {/* Section 1: Header - Visit status/time (Hierarchy #1) */}
      <EncounterHeaderSection
        appointment={encounterAggregate.appointment}
        patient={encounterAggregate.patient}
        doctor={encounterAggregate.doctor}
        formattedDateTime={formattedDateTime}
        backTo="/doctor/appointments"
        backLabel="Appointments"
        actions={
          <div className="flex flex-wrap gap-2">
            {/* Document download buttons — shown for completed encounters */}
            {appointment?.status === 'completed' && appointmentId && (
              <>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    void documentsApi.triggerPrescriptionDownload(appointmentId);
                  }}
                  className="gap-1.5"
                >
                  <FileText className="h-4 w-4" />
                  Prescription
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    void documentsApi.triggerEncounterSummaryDownload(appointmentId);
                  }}
                  className="gap-1.5"
                >
                  <Printer className="h-4 w-4" />
                  Summary
                </Button>
              </>
            )}
            {/* Complete encounter button — shown for scheduled encounters */}
            {canMarkComplete && (
              <Button
                type="button"
                size="sm"
                disabled={markBusy}
                onClick={openCompleteModal}
                className="gap-1.5"
              >
                <CheckCircle2 className="h-4 w-4" />
                Complete encounter
              </Button>
            )}
          </div>
        }

      />

      {/* 
        PART 3 — Workspace Context Banner
        Shown when user has clinician capability but is NOT in the clinician workspace.
        This is a calm informational banner, not an error.
      */}
      {!isClinician && hasClinicianCapability && appointment?.status === 'scheduled' && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <div className="flex items-center gap-2">
            <ArrowRight className="h-4 w-4 shrink-0" />
            <span>
              Switch to{' '}
              <span className="font-medium">Clinician workspace</span> to complete this encounter.
            </span>
          </div>
        </div>
      )}

      {/* 
        Mobile-responsive grid layout
        - Single column on mobile
        - Two columns on tablet/desktop
      */}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        
        {/* Left column: Clinical content (2/3 width on desktop) */}
        <div className="lg:col-span-2 space-y-4">
          
          {/* Section 1: Vitals (Hierarchy #1) */}
          <EncounterVitalsSection
            vitals={encounterAggregate.vitals}
            compact={false}
          />

          {/* Section 2: Clinical Documentation (Hierarchy #2-4) */}
          <EncounterClinicalSection
            appointment={encounterAggregate.appointment}
            compact={false}
          />

          {/* Section 3: Prescriptions (Hierarchy #5) */}
          <EncounterPrescriptionsSection
            prescriptions={encounterAggregate.prescriptions}
            compact={false}
          />
          
          {/* Section 4: Medicines Given (Hierarchy #6) */}
          {encounterAggregate.appointment.status === 'completed' && (
            <EncounterMedicationSection
              inventoryUsages={encounterAggregate.inventory_usage}
              inventoryMaterialsSellingTotal={
                encounterAggregate.appointment.inventory_materials_selling_total
              }
              compact={false}
            />
          )}
          
          {/* 
            TODO: Future Phase 2 clinical extensions
            Section placeholders for upcoming features:
          */}
          {/* 
          {encounterAggregate.vitals && (
            <EncounterVitalsSection vitals={encounterAggregate.vitals} />
          )}
          
          {encounterAggregate.prescriptions && (
            <EncounterPrescriptionsSection 
              prescriptions={encounterAggregate.prescriptions} 
            />
          )}
          
          {encounterAggregate.attachments && (
            <EncounterAttachmentsSection 
              attachments={encounterAggregate.attachments} 
            />
          )}
          
          {encounterAggregate.soapNotes && (
            <EncounterSoapNotesSection notes={encounterAggregate.soapNotes} />
          )}
          
          {encounterAggregate.aiSummary && (
            <EncounterAiSummarySection summary={encounterAggregate.aiSummary} />
          )}
          */}
          
        </div>
        
        {/* Right column: Billing & Context (1/3 width on desktop) */}
        <div className="space-y-4">
          
          {/* Section 4: Billing (Hierarchy #7 - secondary) */}
          <EncounterBillingSection
            bill={encounterAggregate.bill}
            inventoryMaterialsSellingTotal={
              encounterAggregate.appointment.inventory_materials_selling_total
            }
            secondary={true}
          />

          {/* Section 5: Follow-up Plan (Hierarchy #8) */}
          <EncounterFollowUpSection
            followUp={
              encounterAggregate.appointment.follow_up_date ||
              encounterAggregate.appointment.follow_up_notes
                ? {
                    follow_up_date: encounterAggregate.appointment.follow_up_date,
                    follow_up_notes: encounterAggregate.appointment.follow_up_notes,
                  }
                : undefined
            }
            compact={false}
          />
          
          {/* Section 6: Patient History Timeline */}
          <EncounterTimelineSection
            currentEncounter={encounterAggregate.appointment}
            previousVisits={previousVisits}
            previousBills={previousBills}
            limit={5}
          />
          
        </div>
      </div>
      
      {/* 
        PART 5: Future Extension Hooks
        Additional extension points for Phase 2:
      */}
      {/* TODO: Add follow-up plans section when implemented */}
      {/* TODO: Add referral management section when implemented */}
      {/* TODO: Add lab orders section when implemented */}
      
      {/* Complete Visit Modal */}
      {completeOpen && (
        <CompleteVisitModal
          ref={modalRef}
          appointment={appointment}
          inventoryItems={invItems}
          inventoryLoading={invLoading}
          isSubmitting={markBusy}
          onClose={() => setCompleteOpen(false)}
          onComplete={handleEncounterComplete}
          idempotencyKey={completionIdempotencyRef.current}
        />
      )}
    </div>
  );
}

export default EncounterWorkspacePage;
