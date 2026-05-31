import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Loader2, Package, Search } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { TENANT_ID_STORAGE_EVENT } from '../../utils/tenantIdForRequest';
import {
  inventoryApi,
  type InventoryItemDTO,
  type InventoryItemWithStockDTO,
} from '../../services/inventory';
import { cn } from '@/lib/utils';

const LOW_STOCK_THRESHOLD = 10;

function sortForDoctor(items: InventoryItemWithStockDTO[]): InventoryItemWithStockDTO[] {
  return [...items].sort((a, b) => {
    const tier = (s: number) => (s === 0 ? 0 : s < LOW_STOCK_THRESHOLD ? 1 : 2);
    const ta = tier(a.quantity_available);
    const tb = tier(b.quantity_available);
    if (ta !== tb) return ta - tb;
    return a.name.localeCompare(b.name);
  });
}

/**
 * Practice → Inventory: read-only clinic stock (tenant-level). Admins manage stock elsewhere.
 */
export function PatientInventory() {
  const [rows, setRows] = useState<InventoryItemWithStockDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const load = useCallback(async (opts?: { isMounted?: () => boolean }) => {
    const alive = opts?.isMounted ?? (() => true);
    setError(null);
    setLoading(true);
    try {
      const data = await inventoryApi.listAllWithStock({ active_only: false });
      if (!alive()) return;
      setRows(data);
      setError(null);
    } catch (e) {
      if (!alive()) return;
      const msg =
        axios.isAxiosError(e) && e.response?.data && typeof e.response.data === 'object'
          ? String((e.response.data as { detail?: unknown }).detail ?? 'Could not load inventory')
          : 'Could not load inventory';
      setError(msg);
    } finally {
      if (alive()) setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    void load({ isMounted: () => mounted });
    return () => {
      mounted = false;
    };
  }, [load]);

  useEffect(() => {
    const onTenant = () => void load();
    window.addEventListener(TENANT_ID_STORAGE_EVENT, onTenant);
    return () => window.removeEventListener(TENANT_ID_STORAGE_EVENT, onTenant);
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let list = rows;
    if (q) list = list.filter((i) => i.name.toLowerCase().includes(q));
    return sortForDoctor(list);
  }, [rows, search]);

  const lowCount = useMemo(
    () => rows.filter((i) => i.quantity_available < LOW_STOCK_THRESHOLD).length,
    [rows]
  );

  const categoryLabel = (t: InventoryItemDTO['type']) => {
    if (t === 'medicine') return 'Medicine';
    if (t === 'consumable') return 'Consumable';
    return 'Equipment';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 min-w-0">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
          <Package className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h1 className="text-lg font-semibold tracking-tight">Inventory</h1>
          <p className="text-xs text-muted-foreground">
            {lowCount > 0
              ? `${lowCount} low or out of stock (clinic)`
              : 'Clinic stock — view only'}
          </p>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Search items…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search inventory"
        />
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading inventory…
        </div>
      )}

      {!loading && error && (
        <Card className="border-destructive/40">
          <CardContent className="text-sm text-destructive py-4">{error}</CardContent>
        </Card>
      )}

      {!loading && !error && filtered.length === 0 && (
        <Card>
          <CardContent className="text-center text-sm text-muted-foreground py-8">
            No items match your search.
          </CardContent>
        </Card>
      )}

      {!loading && !error && filtered.length > 0 && (
        <ul className="space-y-2">
          {filtered.map((item) => {
            const s = item.quantity_available;
            return (
              <li key={item.id}>
                <Card
                  className={cn(
                    'overflow-hidden transition-opacity',
                    !item.is_active && 'opacity-55'
                  )}
                >
                  <CardContent className="py-3">
                    <div className="flex gap-3 items-start justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                          <p className="font-semibold text-foreground truncate">{item.name}</p>
                          <Badge variant="outline" className="text-[10px] capitalize shrink-0">
                            {categoryLabel(item.type)}
                          </Badge>
                          {!item.is_active && (
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                              Inactive
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {item.unit}
                          {item.selling_price != null && (
                            <span className="ml-2">
                              · List {Number(item.selling_price).toFixed(2)}
                            </span>
                          )}
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="flex items-center justify-end gap-2 flex-wrap">
                          <span className="text-xl font-semibold tabular-nums">{s}</span>
                          {s === 0 && (
                            <Badge variant="destructive" className="text-[10px]">
                              Out
                            </Badge>
                          )}
                          {s > 0 && s < LOW_STOCK_THRESHOLD && (
                            <Badge
                              variant="outline"
                              className="text-[10px] bg-amber-100 text-amber-950 border-amber-300 dark:bg-amber-950/50 dark:text-amber-100 dark:border-amber-800"
                            >
                              Low
                            </Badge>
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
    </div>
  );
}
