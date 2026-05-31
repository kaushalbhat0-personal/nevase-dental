import { useEffect, useState } from 'react';
import { Receipt } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { billingApi } from '../../services';
import type { Bill } from '../../types';
import { formatCurrency, formatDateSafe } from '../../utils';
import { ErrorState } from '../../components/common';

function statusVariant(status: Bill['status']): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'paid') return 'default';
  if (status === 'unpaid') return 'secondary';
  return 'secondary';
}

export function PatientBills() {
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const list = await billingApi.getAll({ limit: 100 });
        if (!cancelled) setBills(list);
      } catch {
        if (!cancelled) setError('Unable to load bills.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <ErrorState title="Bills" description={error} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Bills</h1>
        <p className="text-muted-foreground text-sm mt-1">Statements and payment status.</p>
      </div>

      {loading ? (
        <div className="space-y-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-6 w-32 rounded-md bg-muted animate-pulse" />
                <div className="h-4 w-full max-w-md rounded-md bg-muted animate-pulse mt-2" />
              </CardHeader>
            </Card>
          ))}
        </div>
      ) : bills.length === 0 ? (
        <Card className="border-dashed">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <Receipt className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle className="text-base pt-2">No bills yet</CardTitle>
            <CardDescription>When you have charges, they will appear here.</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <ul className="space-y-6">
          {bills.map((b) => (
            <Card key={b.id}>
              <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2 space-y-0">
                <div>
                  <CardTitle className="text-base font-medium">
                    {formatCurrency(b.amount, b.currency)}
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {b.description || 'Medical bill'}
                    {b.due_date && ` · Due ${formatDateSafe(b.due_date)}`}
                  </CardDescription>
                </div>
                <Badge variant={statusVariant(b.status)} className="capitalize shrink-0">
                  {b.status}
                </Badge>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                Issued {formatDateSafe(b.created_at)}
                {b.paid_at && ` · Paid ${formatDateSafe(b.paid_at)}`}
              </CardContent>
            </Card>
          ))}
        </ul>
      )}
    </div>
  );
}
