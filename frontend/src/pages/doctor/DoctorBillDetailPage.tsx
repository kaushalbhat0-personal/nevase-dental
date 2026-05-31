import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, IndianRupee } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { buttonVariants } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { billingApi } from '../../services';
import { ErrorState } from '../../components/common';
import type { Bill } from '../../types';

function billStatusClass(status: Bill['status']): string {
  if (status === 'paid') return 'text-emerald-700 dark:text-emerald-400';
  if (status === 'unpaid') return 'text-amber-800 dark:text-amber-300';
  return '';
}

export function DoctorBillDetailPage() {
  const { billId } = useParams<{ billId: string }>();
  const [bill, setBill] = useState<Bill | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    if (!billId) {
      setError('Missing bill');
      setLoading(false);
      return;
    }
    let cancelled = false;
    setError(null);
    setLoading(true);
    void (async () => {
      try {
        const b = await billingApi.getById(billId);
        if (!cancelled) setBill(b);
      } catch {
        if (!cancelled) {
          setError('Could not load this bill.');
          setBill(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [billId, retryKey]);

  if (error && !loading) {
    return (
      <div className="space-y-4">
        <BackBar />
        <ErrorState
          title="Bill not found"
          description="It may have been removed or you may not have access."
          error={error}
          onRetry={() => setRetryKey((k) => k + 1)}
        />
      </div>
    );
  }

  if (loading || !bill) {
    return (
      <div className="space-y-4">
        <BackBar />
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  const stClass = billStatusClass(bill.status);
  const patientPath = bill.patient_id != null ? `/doctor/patients/${bill.patient_id}` : null;
  const apptPath =
    bill.appointment_id != null ? `/doctor/appointments/${bill.appointment_id}` : null;

  return (
    <div className="space-y-6">
      <BackBar />
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Bill</h1>
        <p className="text-sm text-muted-foreground mt-1">Invoice details</p>
      </div>

      <Card id={billId ? `bill-${billId}` : undefined}>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center gap-2 justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <IndianRupee className="h-4 w-4 text-muted-foreground" aria-hidden />
              <span className="font-semibold tabular-nums">
                {bill.currency} {Number(bill.amount).toFixed(2)}
              </span>
            </CardTitle>
            <Badge variant="outline" className={cn('capitalize', stClass)}>
              {bill.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          {bill.description && <p className="text-muted-foreground">{bill.description}</p>}
          {patientPath && (
            <p>
              <span className="text-muted-foreground">Patient: </span>
              <Link to={patientPath} className="text-primary font-medium hover:underline">
                Open patient
              </Link>
            </p>
          )}
          {apptPath && (
            <p>
              <span className="text-muted-foreground">Visit: </span>
              <Link to={apptPath} className="text-primary font-medium hover:underline">
                Open appointment
              </Link>
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function BackBar() {
  return (
    <div>
      <Link
        to="/doctor/bills"
        className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), '-ml-2 gap-1.5 h-8 text-muted-foreground')}
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        Bills
      </Link>
    </div>
  );
}
