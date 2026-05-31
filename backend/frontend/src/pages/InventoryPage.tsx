import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import axios from 'axios';
import {
  Loader2,
  MoreHorizontal,
  Package,
  Plus,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useDoctorWorkspace } from '../contexts/DoctorWorkspaceContext';
import { TENANT_ID_STORAGE_EVENT } from '../utils/tenantIdForRequest';
import { useModalFocusTrap } from '../hooks/useModalFocusTrap';
import {
  inventoryApi,
  type InventoryItemDTO,
  type InventoryItemCreatePayload,
  type InventoryItemType,
} from '../services/inventory';
import { cn } from '@/lib/utils';
import { DEFAULT_LOW_STOCK_FALLBACK } from '../utils/inventoryLowStock';

type MergedItem = InventoryItemDTO & { stock: number };

function sortItemsForDisplay(items: MergedItem[]): MergedItem[] {
  return [...items].sort((a, b) => {
    const tier = (stock: number, th: number) => (stock === 0 ? 0 : stock <= th ? 1 : 2);
    const ta = tier(a.stock, a.low_stock_threshold ?? DEFAULT_LOW_STOCK_FALLBACK);
    const tb = tier(b.stock, b.low_stock_threshold ?? DEFAULT_LOW_STOCK_FALLBACK);
    if (ta !== tb) return ta - tb;
    return a.name.localeCompare(b.name);
  });
}

interface InventoryListProps {
  title: string;
  /** When set, bulk stock + mutations use this doctor scope; otherwise tenant-level. */
  doctorStockScopeId: string | null;
  canMutate: boolean;
  canCreateItem: boolean;
}

function InventoryList({ title, doctorStockScopeId, canMutate, canCreateItem }: InventoryListProps) {
  const [items, setItems] = useState<InventoryItemDTO[]>([]);
  const [stockMap, setStockMap] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [lowOnly, setLowOnly] = useState(false);

  const [addSheetItem, setAddSheetItem] = useState<MergedItem | null>(null);
  const [addQty, setAddQty] = useState('1');
  const [addSubmitting, setAddSubmitting] = useState(false);

  const [adjustItem, setAdjustItem] = useState<MergedItem | null>(null);
  const [adjustDelta, setAdjustDelta] = useState('0');
  const [adjustSubmitting, setAdjustSubmitting] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    type: 'medicine' as InventoryItemType,
    unit: '',
    cost_price: '',
    selling_price: '',
  });

  const [actionMenuId, setActionMenuId] = useState<string | null>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const adjustRef = useRef<HTMLDivElement>(null);
  const createRef = useRef<HTMLDivElement>(null);

  useModalFocusTrap(sheetRef, Boolean(addSheetItem));
  useModalFocusTrap(adjustRef, Boolean(adjustItem));
  useModalFocusTrap(createRef, createOpen);

  const merged: MergedItem[] = useMemo(
    () => items.map((item) => ({ ...item, stock: stockMap[item.id] ?? 0 })),
    [items, stockMap]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let list = merged;
    if (q) list = list.filter((i) => i.name.toLowerCase().includes(q));
    if (lowOnly)
      list = list.filter((i) => i.stock <= (i.low_stock_threshold ?? DEFAULT_LOW_STOCK_FALLBACK));
    return sortItemsForDisplay(list);
  }, [merged, search, lowOnly]);

  const lowCount = useMemo(
    () => merged.filter((i) => i.stock <= (i.low_stock_threshold ?? DEFAULT_LOW_STOCK_FALLBACK)).length,
    [merged]
  );

  const fetchItems = useCallback(async () => {
    const data = await inventoryApi.listAllItems({ active_only: false });
    setItems(data);
  }, []);

  const fetchStockMap = useCallback(async () => {
    const map = await inventoryApi.getBulkStockMap(doctorStockScopeId);
    setStockMap(map);
  }, [doctorStockScopeId]);

  const loadAll = useCallback(async (opts?: { isMounted?: () => boolean }) => {
    const alive = opts?.isMounted ?? (() => true);
    setLoadError(null);
    setLoading(true);
    try {
      await fetchItems();
      if (!alive()) return;
      await fetchStockMap();
      if (!alive()) return;
      setLoadError(null);
    } catch (e) {
      if (!alive()) return;
      const msg =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not load inventory')
          : 'Could not load inventory';
      setLoadError(msg);
    } finally {
      if (alive()) setLoading(false);
    }
  }, [fetchItems, fetchStockMap]);

  useEffect(() => {
    let mounted = true;
    void loadAll({ isMounted: () => mounted });
    return () => {
      mounted = false;
    };
  }, [loadAll]);

  useEffect(() => {
    const onTenant = () => void loadAll();
    window.addEventListener(TENANT_ID_STORAGE_EVENT, onTenant);
    return () => window.removeEventListener(TENANT_ID_STORAGE_EVENT, onTenant);
  }, [loadAll]);

  useEffect(() => {
    if (!actionMenuId) return;
    const onDoc = (ev: MouseEvent) => {
      const t = ev.target as Element;
      if (t.closest(`[data-inv-action="${actionMenuId}"]`)) return;
      setActionMenuId(null);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [actionMenuId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      setAddSheetItem(null);
      setAdjustItem(null);
      setCreateOpen(false);
      setActionMenuId(null);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const doctorIdForApi = doctorStockScopeId;

  const submitAddStock = async () => {
    if (!addSheetItem) return;
    const n = parseInt(addQty, 10);
    if (Number.isNaN(n) || n < 1) {
      toast.error('Enter a quantity of at least 1');
      return;
    }
    setAddSubmitting(true);
    const prev = stockMap[addSheetItem.id] ?? 0;
    setStockMap((m) => ({ ...m, [addSheetItem.id]: prev + n }));
    try {
      await inventoryApi.addStock({
        item_id: addSheetItem.id,
        quantity: n,
        doctor_id: doctorIdForApi,
      });
      toast.success('Stock added');
      setAddSheetItem(null);
      setAddQty('1');
      await fetchStockMap();
    } catch (e) {
      setStockMap((m) => ({ ...m, [addSheetItem.id]: prev }));
      const detail =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not add stock')
          : 'Could not add stock';
      toast.error(detail, { duration: 5000 });
    } finally {
      setAddSubmitting(false);
    }
  };

  const submitAdjust = async () => {
    if (!adjustItem) return;
    const n = parseInt(adjustDelta, 10);
    if (Number.isNaN(n) || n === 0) {
      toast.error('Enter a non-zero adjustment (+/-)');
      return;
    }
    setAdjustSubmitting(true);
    const prev = stockMap[adjustItem.id] ?? 0;
    setStockMap((m) => ({ ...m, [adjustItem.id]: Math.max(0, prev + n) }));
    try {
      await inventoryApi.adjustStock({
        item_id: adjustItem.id,
        quantity: n,
        doctor_id: doctorIdForApi,
      });
      toast.success('Stock updated');
      setAdjustItem(null);
      setAdjustDelta('0');
      await fetchStockMap();
    } catch (e) {
      setStockMap((m) => ({ ...m, [adjustItem.id]: prev }));
      const detail =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not adjust stock')
          : 'Could not adjust stock';
      toast.error(detail, { duration: 5000 });
    } finally {
      setAdjustSubmitting(false);
    }
  };

  const submitCreate = async () => {
    const name = createForm.name.trim();
    const unit = createForm.unit.trim();
    const cost = parseFloat(createForm.cost_price);
    const sell = parseFloat(createForm.selling_price);
    if (!name || !unit) {
      toast.error('Name and unit are required');
      return;
    }
    if (Number.isNaN(cost) || cost < 0 || Number.isNaN(sell) || sell < 0) {
      toast.error('Enter valid prices (≥ 0)');
      return;
    }
    setCreateSubmitting(true);
    try {
      const payload: InventoryItemCreatePayload = {
        name,
        type: createForm.type,
        unit,
        cost_price: cost,
        selling_price: sell,
        is_active: true,
      };
      await inventoryApi.createItem(payload);
      toast.success('Item created');
      setCreateOpen(false);
      setCreateForm({ name: '', type: 'medicine', unit: '', cost_price: '', selling_price: '' });
      await fetchItems();
      await fetchStockMap();
    } catch (e) {
      const detail =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not create item')
          : 'Could not create item';
      toast.error(detail, { duration: 5000 });
    } finally {
      setCreateSubmitting(false);
    }
  };

  const openAddSheet = (item: MergedItem) => {
    setAddQty('1');
    setAddSheetItem(item);
  };

  const openAdjust = (item: MergedItem) => {
    setAdjustDelta('0');
    setAdjustItem(item);
    setActionMenuId(null);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
            <Package className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h1 className="text-lg font-semibold tracking-tight truncate">{title}</h1>
            <p className="text-xs text-muted-foreground">
              {lowCount > 0 ? `${lowCount} low or out of stock` : 'All items adequately stocked'}
              {doctorStockScopeId ? ' · Your stock' : ' · Clinic stock'}
            </p>
          </div>
        </div>
        {canCreateItem && (
          <Button size="sm" className="shrink-0 w-full sm:w-auto" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Add item
          </Button>
        )}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search items…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search inventory"
          />
        </div>
        <Button
          type="button"
          variant={lowOnly ? 'default' : 'outline'}
          size="sm"
          className="shrink-0 justify-center"
          onClick={() => setLowOnly((v) => !v)}
        >
          <SlidersHorizontal className="h-4 w-4 mr-1" />
          Low stock
        </Button>
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading inventory…
        </div>
      )}

      {!loading && loadError && (
          <Card className="border-destructive/40">
          <CardContent className="text-sm text-destructive">{loadError}</CardContent>
        </Card>
      )}

      {!loading && !loadError && filtered.length === 0 && (
        <Card>
          <CardContent className="text-center text-sm text-muted-foreground">
            No items match your filters.
          </CardContent>
        </Card>
      )}

      {!loading && !loadError && filtered.length > 0 && (
        <ul className="space-y-2">
          {filtered.map((item) => {
            const disabled = !item.is_active || !canMutate;
            const lowTh = item.low_stock_threshold ?? DEFAULT_LOW_STOCK_FALLBACK;
            return (
              <li key={item.id}>
                <Card
                  className={cn(
                    'overflow-hidden transition-opacity',
                    !item.is_active && 'opacity-55'
                  )}
                >
                  <CardContent>
                    <div className="flex gap-2 items-start">
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                          <p className="font-semibold text-foreground truncate">{item.name}</p>
                          {!item.is_active && (
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                              Inactive
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">{item.unit}</p>
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                          <span className="text-2xl font-semibold tabular-nums leading-none">
                            {item.stock}
                          </span>
                          {item.stock === 0 && (
                            <span className="text-lg" title="Out of stock" aria-hidden>
                              🔴
                            </span>
                          )}
                          {item.stock > 0 && item.stock <= lowTh && (
                            <span className="text-lg" title="Low stock" aria-hidden>
                              ⚠️
                            </span>
                          )}
                          {item.stock === 0 && (
                            <Badge variant="destructive" className="text-[10px]">
                              Out
                            </Badge>
                          )}
                          {item.stock > 0 && item.stock <= lowTh && (
                            <Badge
                              variant="outline"
                              className="text-[10px] bg-amber-100 text-amber-950 border-amber-300 dark:bg-amber-950/50 dark:text-amber-100 dark:border-amber-800"
                            >
                              Low
                            </Badge>
                          )}
                        </div>
                      </div>
                      <div className="flex items-start gap-1 shrink-0 pt-0.5">
                        <Button
                          type="button"
                          size="icon"
                          variant="secondary"
                          className="h-9 w-9 rounded-full"
                          disabled={disabled}
                          aria-label={`Add stock for ${item.name}`}
                          onClick={() => !disabled && openAddSheet(item)}
                        >
                          <Plus className="h-4 w-4" />
                        </Button>
                        <div className="relative" data-inv-action={item.id}>
                          <Button
                            type="button"
                            size="icon"
                            variant="ghost"
                            className="h-9 w-9"
                            disabled={disabled}
                            aria-label={`More actions for ${item.name}`}
                            aria-expanded={actionMenuId === item.id}
                            onClick={() => setActionMenuId((id) => (id === item.id ? null : item.id))}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                          {actionMenuId === item.id && (
                            <div
                              className="absolute right-0 top-full mt-1 z-50 min-w-[160px] rounded-md border border-border bg-popover text-popover-foreground shadow-md py-1"
                              role="menu"
                            >
                              <button
                                type="button"
                                className="w-full text-left px-3 py-2 text-sm hover:bg-muted"
                                role="menuitem"
                                onClick={() => openAdjust(item)}
                              >
                                Adjust stock…
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      )}

      {/* Add stock bottom sheet */}
      {addSheetItem && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center sm:items-center sm:p-4">
          <button
            type="button"
            className="absolute inset-0 bg-black/40 sm:bg-black/50"
            aria-label="Close"
            onClick={() => !addSubmitting && setAddSheetItem(null)}
          />
          <div
            ref={sheetRef}
            className="relative w-full sm:max-w-md rounded-t-2xl sm:rounded-xl border border-border bg-card shadow-lg p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:pb-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-stock-title"
          >
            <div className="flex items-start justify-between gap-2 mb-3">
              <div className="min-w-0">
                <h2 id="add-stock-title" className="font-semibold">
                  Add stock
                </h2>
                <p className="text-sm text-muted-foreground truncate">{addSheetItem.name}</p>
              </div>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="shrink-0"
                disabled={addSubmitting}
                onClick={() => setAddSheetItem(null)}
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Quantity</label>
            <Input
              type="number"
              min={1}
              inputMode="numeric"
              value={addQty}
              onChange={(e) => setAddQty(e.target.value)}
              className="mb-4"
            />
            {doctorIdForApi && (
              <p className="text-xs text-muted-foreground mb-4">
                Applied to your doctor stock scope.
              </p>
            )}
            <Button
              type="button"
              className="w-full"
              disabled={addSubmitting}
              onClick={() => void submitAddStock()}
            >
              {addSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Add stock'}
            </Button>
          </div>
        </div>
      )}

      {/* Adjust stock modal */}
      {adjustItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            type="button"
            className="absolute inset-0 bg-black/50"
            aria-label="Close"
            onClick={() => !adjustSubmitting && setAdjustItem(null)}
          />
          <div
            ref={adjustRef}
            className="relative w-full max-w-md rounded-xl border border-border bg-card shadow-lg p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="adjust-title"
          >
            <div className="flex items-start justify-between gap-2 mb-3">
              <div className="min-w-0">
                <h2 id="adjust-title" className="font-semibold">
                  Adjust stock
                </h2>
                <p className="text-sm text-muted-foreground truncate">{adjustItem.name}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Current: <span className="font-medium text-foreground">{adjustItem.stock}</span> — use
                  +10 or -5 style deltas.
                </p>
              </div>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                disabled={adjustSubmitting}
                onClick={() => setAdjustItem(null)}
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Quantity (+ / -)
            </label>
            <Input
              type="number"
              inputMode="numeric"
              value={adjustDelta}
              onChange={(e) => setAdjustDelta(e.target.value)}
              className="mb-4"
            />
            <Button
              type="button"
              className="w-full"
              disabled={adjustSubmitting}
              onClick={() => void submitAdjust()}
            >
              {adjustSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Apply adjustment'}
            </Button>
          </div>
        </div>
      )}

      {/* Create item modal */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            type="button"
            className="absolute inset-0 bg-black/50"
            aria-label="Close"
            onClick={() => !createSubmitting && setCreateOpen(false)}
          />
          <div
            ref={createRef}
            className="relative w-full max-w-md rounded-xl border border-border bg-card shadow-lg p-4 max-h-[90vh] overflow-y-auto"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-item-title"
          >
            <div className="flex items-start justify-between gap-2 mb-3">
              <h2 id="create-item-title" className="font-semibold">
                New inventory item
              </h2>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                disabled={createSubmitting}
                onClick={() => setCreateOpen(false)}
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Name</label>
                <Input
                  className="mt-1"
                  value={createForm.name}
                  onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Type</label>
                <select
                  className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={createForm.type}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, type: e.target.value as InventoryItemType }))
                  }
                >
                  <option value="medicine">Medicine</option>
                  <option value="consumable">Consumable</option>
                  <option value="equipment">Equipment</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Unit</label>
                <Input
                  className="mt-1"
                  placeholder="strip, box, piece…"
                  value={createForm.unit}
                  onChange={(e) => setCreateForm((f) => ({ ...f, unit: e.target.value }))}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Cost price</label>
                  <Input
                    className="mt-1"
                    type="number"
                    min={0}
                    step="0.01"
                    value={createForm.cost_price}
                    onChange={(e) => setCreateForm((f) => ({ ...f, cost_price: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Selling price</label>
                  <Input
                    className="mt-1"
                    type="number"
                    min={0}
                    step="0.01"
                    value={createForm.selling_price}
                    onChange={(e) => setCreateForm((f) => ({ ...f, selling_price: e.target.value }))}
                  />
                </div>
              </div>
            </div>
            <Button
              type="button"
              className="w-full mt-4"
              disabled={createSubmitting}
              onClick={() => void submitCreate()}
            >
              {createSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Create item'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/** /doctor/inventory — doctor-scoped stock when profile resolves; else tenant-level. */
export function DoctorInventoryPage() {
  const { selfDoctor, isReadOnly, isIndependent } = useDoctorWorkspace();
  const doctorStockScopeId = selfDoctor ? String(selfDoctor.id) : null;
  const canMutate = !isReadOnly;
  const canCreateItem = isIndependent && !isReadOnly;

  return (
    <InventoryList
      title="Inventory"
      doctorStockScopeId={doctorStockScopeId}
      canMutate={canMutate}
      canCreateItem={canCreateItem}
    />
  );
}

/** /admin/inventory — tenant-level stock; full admin create. */
export function AdminInventoryPage() {
  return (
    <InventoryList
      title="Inventory"
      doctorStockScopeId={null}
      canMutate
      canCreateItem
    />
  );
}
