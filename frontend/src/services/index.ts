// Central exports for all API services
export { api, retryRequest, isNetworkError, isColdStartError } from './api';
export { authApi, formatLoginError } from './auth';
export { doctorProfileApi, type DoctorStructuredProfileInput } from './doctorProfile';
export { patientsApi, type CreatePatientData, type PatientUpdatePayload, type PatientCreateResponse, type PatientAutoCredentials } from './patients';
export { appointmentsApi, encountersApi, type CreateAppointmentData } from './appointments';
export { billingApi, BillingApiError, type CreateBillData } from './billing';
export {
  doctorsApi,
  initDoctorSlotsCacheCrossTabSync,
  invalidateDoctorSlotsClientCache,
  SLOTS_CROSS_TAB_BROADCAST,
  SLOTS_INVALIDATE_STORAGE_KEY,
  shouldSyncSlotsCrossTab,
  type CreateDoctorData,
  type DoctorDayMeta,
  type DoctorScheduleDay,
  type DoctorSlot,
} from './doctors';
export type { DoctorAvailabilityWindow } from '../types';
export { dashboardApi } from './dashboard';
export {
  doctorVerificationAdminApi,
  type DoctorVerificationQueueItem,
  type DoctorVerificationQueuePage,
} from './doctorVerificationAdmin';
export { tenantsApi } from './tenants';
export { publicDiscoveryApi } from './publicDiscovery';
export { usersApi, type OrganizationUserCreatePayload } from './users';
export {
  inventoryApi,
  type InventoryItemDTO,
  type InventoryItemCreatePayload,
  type InventoryItemType,
  type InventoryItemWithStockDTO,
} from './inventory';
export { documentsApi } from './documents';
export {
  getOrganizationProfile,
  updateOrganizationProfile,
  getBrandingProfile,
  updateBrandingProfile,
  previewDocument,
  type TenantOrganizationProfile,
  type TenantOrganizationProfileUpdate,
  type TenantBrandingProfile,
  type TenantBrandingProfileUpdate,
} from './branding';

// Phase P3 — Daily Care Dashboard + Adherence Experience
export { dailyCareApi, type DailyCareDashboardAggregate } from './dailyCare';
export {
  medicationScheduleApi,
  type MedicationScheduleRead,
  type AdherenceActionPayload,
  type AdherenceActionResponse,
  type TodayAdherenceSummary,
  type MedicationScheduleListResponse,
} from './medicationSchedule';


