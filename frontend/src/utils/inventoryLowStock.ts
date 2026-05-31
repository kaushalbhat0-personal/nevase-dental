/** Fallback when `InventoryItem.low_stock_threshold` is unset — aligns with Inventory page UX */
export const DEFAULT_LOW_STOCK_FALLBACK = 10;

export function isLowStockRow(row: {
  quantity_available: number;
  low_stock_threshold?: number | null;
}): boolean {
  const th = row.low_stock_threshold ?? DEFAULT_LOW_STOCK_FALLBACK;
  return row.quantity_available <= th;
}

export function countLowStockRows<
  T extends { quantity_available: number; low_stock_threshold?: number | null },
>(rows: T[]): number {
  return rows.filter(isLowStockRow).length;
}
