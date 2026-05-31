import { api } from './api';
import { safeArray } from '../utils';
import type { Bill } from '../types';

export interface CreateBillData {
  patient_id: string;
  appointment_id?: string;
  amount: number;
  currency: string;
  description?: string;
  due_date?: string;
}

export class BillingApiError extends Error {
  statusCode?: number;
  detail?: unknown;

  constructor(message: string, statusCode?: number, detail?: unknown) {
    super(message);
    this.name = 'BillingApiError';
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

const handleApiError = (error: unknown): never => {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { status?: number; data?: unknown } };
    const status = axiosError.response?.status;
    const detail = axiosError.response?.data;
    
    let message = 'Billing operation failed';
    if (detail && typeof detail === 'object' && 'detail' in detail) {
      message = String((detail as { detail?: string }).detail);
    } else if (typeof detail === 'string') {
      message = detail;
    }
    
    throw new BillingApiError(message, status, detail);
  }
  
  if (error instanceof Error) {
    throw new BillingApiError(error.message);
  }
  
  throw new BillingApiError('An unexpected error occurred');
};

export const billingApi = {
  getById: async (id: string): Promise<Bill> => {
    try {
      const response = await api.get<Bill>(`/bills/${id}`);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
  getAll: async (params?: {
    skip?: number;
    limit?: number;
    patient_id?: string;
    appointment_id?: string;
    status?: string;
  }): Promise<Bill[]> => {
    try {
      const response = await api.get('/bills', { params: { skip: 0, limit: 100, ...params } });
      // Debug log in development
      if (import.meta.env.DEV) {
        console.log('[billingApi.getAll] Response:', response.data);
      }
      // Safe array extraction - handles { data: [...] } or direct array
      return safeArray<Bill>(response.data);
    } catch (error) {
      console.error('[billingApi.getAll] Error:', error);
      throw handleApiError(error);
    }
  },
  create: async (bill: CreateBillData) => {
    try {
      const response = await api.post('/bills', bill);
      return response.data;
    } catch (error) {
      console.error('[billingApi.create] Error:', error);
      throw handleApiError(error);
    }
  },
  pay: async (billId: string, paymentMethod?: string) => {
    try {
      const response = await api.post(`/bills/${billId}/pay`, { payment_method: paymentMethod });
      return response.data;
    } catch (error) {
      console.error('[billingApi.pay] Error:', error);
      throw handleApiError(error);
    }
  },
  delete: async (billId: string) => {
    try {
      const response = await api.delete(`/bills/${billId}`);
      return response.data;
    } catch (error) {
      console.error('[billingApi.delete] Error:', error);
      throw handleApiError(error);
    }
  },
};
