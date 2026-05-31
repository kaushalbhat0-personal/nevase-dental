import type { InventoryItemWithStockDTO } from '../services/inventory';
import { getActiveTenantId } from './tenantIdForRequest';

let cache: { tenantKey: string; items: InventoryItemWithStockDTO[] } | null = null;

/** Returns cached clinic inventory list for the active tenant, if any. */
export function getTenantInventoryCache(): InventoryItemWithStockDTO[] | null {
  const tid = getActiveTenantId() ?? '';
  if (!cache || cache.tenantKey !== tid) return null;
  return cache.items;
}

export function setTenantInventoryCache(items: InventoryItemWithStockDTO[]): void {
  cache = { tenantKey: getActiveTenantId() ?? '', items };
}

export function invalidateTenantInventoryCache(): void {
  cache = null;
}
