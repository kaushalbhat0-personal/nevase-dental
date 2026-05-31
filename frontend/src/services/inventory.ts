import { api, retryRequest } from './api';

export type InventoryItemType = 'medicine' | 'consumable' | 'equipment';

export interface InventoryItemDTO {
  id: string;
  tenant_id: string;
  name: string;
  type: InventoryItemType;
  unit: string;
  cost_price: number;
  selling_price: number;
  is_active: boolean;
  /** Server-side threshold for low-stock warnings */
  low_stock_threshold?: number | null;
  created_at: string;
}

export interface InventoryItemWithStockDTO extends InventoryItemDTO {
  quantity_available: number;
}

export interface InventoryItemCreatePayload {
  name: string;
  type: InventoryItemType;
  unit: string;
  cost_price: number;
  selling_price: number;
  is_active?: boolean;
  low_stock_threshold?: number | null;
}

export interface StockOperationResultDTO {
  item_id: string;
  doctor_id: string | null;
  quantity: number;
  movement_id: string;
}

/** Server rejects `limit` above this value (`le=200`). */
export const MAX_LIMIT = 200;
export const DEFAULT_LIMIT = 100;

export function capInventoryLimit(limit?: number): number {
  return Math.min(limit ?? DEFAULT_LIMIT, MAX_LIMIT);
}

/** GET /inventory — items with per-location stock counts. */
export async function getInventory(params?: {
  skip?: number;
  limit?: number;
  active_only?: boolean;
  search?: string;
}) {
  const limit = capInventoryLimit(params?.limit);

  return api.get<InventoryItemWithStockDTO[]>('/inventory', {
    params: {
      skip: params?.skip ?? 0,
      limit,
      active_only: params?.active_only,
      search: params?.search,
    },
  });
}

export async function getInventoryItems(params?: {
  skip?: number;
  limit?: number;
  active_only?: boolean;
  type?: InventoryItemType;
}) {
  const limit = capInventoryLimit(params?.limit);

  return api.get<InventoryItemDTO[]>('/inventory/items', {
    params: {
      skip: params?.skip ?? 0,
      limit,
      active_only: params?.active_only,
      type: params?.type,
    },
  });
}

async function fetchAllInventoryWithStockImpl(opts?: { active_only?: boolean; search?: string }) {
  const pageSize = capInventoryLimit(DEFAULT_LIMIT);
  const accumulated: InventoryItemWithStockDTO[] = [];
  let skip = 0;
  while (true) {
    const rows = await retryRequest(() =>
      getInventory({
        skip,
        limit: pageSize,
        active_only: opts?.active_only,
        search: opts?.search,
      }).then((r) => r.data)
    );
    accumulated.push(...rows);
    if (rows.length < pageSize) break;
    skip += pageSize;
  }
  return accumulated;
}

async function fetchAllInventoryItemsImpl(opts?: {
  active_only?: boolean;
  type?: InventoryItemType;
}) {
  const pageSize = capInventoryLimit(DEFAULT_LIMIT);
  const accumulated: InventoryItemDTO[] = [];
  let skip = 0;
  while (true) {
    const rows = await retryRequest(() =>
      getInventoryItems({
        skip,
        limit: pageSize,
        active_only: opts?.active_only,
        type: opts?.type,
      }).then((r) => r.data)
    );
    accumulated.push(...rows);
    if (rows.length < pageSize) break;
    skip += pageSize;
  }
  return accumulated;
}

export const inventoryApi = {
  /** Items with clinic (tenant) stock counts — for doctor read-only list. */
  listWithStock(params?: {
    skip?: number;
    limit?: number;
    active_only?: boolean;
    search?: string;
  }) {
    return retryRequest(() => getInventory(params).then((r) => r.data));
  },

  /**
   * Load every page from GET /inventory until a short page is returned.
   * Use instead of a single oversized `limit`.
   */
  listAllWithStock(opts?: { active_only?: boolean; search?: string }) {
    return fetchAllInventoryWithStockImpl(opts);
  },

  listItems(params?: { skip?: number; limit?: number; active_only?: boolean; type?: InventoryItemType }) {
    return retryRequest(() => getInventoryItems(params).then((r) => r.data));
  },

  listAllItems(opts?: { active_only?: boolean; type?: InventoryItemType }) {
    return fetchAllInventoryItemsImpl(opts);
  },

  /** Single bulk fetch; merge with items on the client. */
  getBulkStockMap(doctorId?: string | null, tenantStockOnly?: boolean) {
    const params: Record<string, unknown> = { as_map: true };
    if (doctorId) params.doctor_id = doctorId;
    if (tenantStockOnly) params.tenant_stock_only = true;
    return retryRequest(() => api.get<Record<string, number>>('/inventory/stock/bulk', { params })).then(
      (r) => r.data
    );
  },

  /**
   * Legacy admin-only manual debit (doctors use POST /appointments/:id/mark-completed).
   */
  consumeForAppointment(body: { appointment_id: string; items: { item_id: string; quantity: number }[] }) {
    return api.post<{ ok: boolean; appointment_id: string }>('/inventory/use', body).then((r) => r.data);
  },

  addStockAdmin(body: { item_id: string; quantity: number }) {
    return api.post<StockOperationResultDTO>('/inventory/add', body).then((r) => r.data);
  },

  addStock(body: { item_id: string; quantity: number; doctor_id?: string | null }) {
    return api.post<StockOperationResultDTO>('/inventory/stock/add', body).then((r) => r.data);
  },

  adjustStock(body: { item_id: string; quantity: number; doctor_id?: string | null }) {
    return api.post<StockOperationResultDTO>('/inventory/stock/adjust', body).then((r) => r.data);
  },

  createItem(body: InventoryItemCreatePayload) {
    return api.post<InventoryItemDTO>('/inventory/items', body).then((r) => r.data);
  },
};
