import { useState } from 'react';
import { Link } from 'react-router-dom';
import { IndianRupee, FileText, CreditCard, Receipt, ExternalLink, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { billingApi } from '../../services/billing';
import type { Bill } from '../../types';

interface EncounterBillingSectionProps {
  bill?: Bill | null;
  /** Additional line items from inventory (for total calculation) */
  inventoryMaterialsSellingTotal?: string | number | null;
  /** Mobile-optimized compact mode */
  compact?: boolean;
  /** Show as secondary/less prominent (billing is secondary to clinical) */
  secondary?: boolean;
}

function billStatusVariant(status: Bill['status']): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'paid') return 'secondary';
  if (status === 'unpaid') return 'outline';
  return 'default';
}

function billStatusLabel(status: Bill['status']): string {
  if (status === 'paid') return 'Paid';
  if (status === 'unpaid') return 'Unpaid';
  return status;
}

/**
 * EncounterBillingSection - Billing summary for the encounter
 * 
 * Clinical-first hierarchy element #6 (secondary): Billing summary
 * Billing remains visually secondary to clinical information.
 * 
 * Design principles:
 * - Visually lighter than clinical sections
 * - Clear status indication
 * - Quick link to full bill details
 * 
 * Mobile considerations:
 * - Compact currency display
 * - Status badge prominently displayed
 * - Single-tap access to bill detail
 */
export function EncounterBillingSection({
  bill,
  inventoryMaterialsSellingTotal,
  compact = false,
  secondary = true,
}: EncounterBillingSectionProps) {
  const [isMarkingPaid, setIsMarkingPaid] = useState(false);

  const handleMarkPaid = async () => {
    if (!bill) return;
    setIsMarkingPaid(true);
    try {
      await billingApi.pay(bill.id);
      // The bill status will be updated via props or refetch
      window.location.reload(); // Simple refresh for now
    } catch (error) {
      console.error('Failed to mark bill as paid:', error);
      // TODO: Show error toast
    } finally {
      setIsMarkingPaid(false);
    }
  };
  if (!bill) {
    return (
      <Card className={cn(
        'bg-muted/20',
        secondary && 'border-muted',
        compact && 'opacity-75'
      )}>
        <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
          <CardTitle className={cn(
            'flex items-center gap-2',
            compact && 'text-sm',
            secondary && 'text-muted-foreground'
          )}>
            <Receipt className="h-4 w-4 shrink-0" aria-hidden />
            Billing
          </CardTitle>
        </CardHeader>
        <CardContent className={cn(compact && 'p-3 pt-0')}>
          <p className="text-sm text-muted-foreground italic">
            No bill generated for this encounter.
          </p>
        </CardContent>
      </Card>
    );
  }

  const amount = Number(bill.amount);
  const invTotal = inventoryMaterialsSellingTotal != null 
    ? Number(inventoryMaterialsSellingTotal) 
    : null;

  return (
    <Card className={cn(
      'overflow-hidden',
      secondary && 'border-muted/60 bg-muted/10',
      compact && 'text-sm'
    )}>
      <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
        <CardTitle className={cn(
          'flex items-center gap-2',
          compact && 'text-sm',
          secondary && 'text-muted-foreground'
        )}>
          <Receipt className="h-4 w-4 shrink-0" aria-hidden />
          Billing Summary
          <Badge 
            variant={billStatusVariant(bill.status)}
            className="ml-auto capitalize text-xs"
          >
            {billStatusLabel(bill.status)}
          </Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent className={cn('space-y-3', compact && 'p-3 pt-0 space-y-2')}>
        {/* Amount */}
        <div className="flex items-baseline gap-1.5">
          <IndianRupee className={cn(
            'shrink-0',
            compact ? 'h-4 w-4' : 'h-5 w-5'
          )} aria-hidden />
          <span className={cn(
            'font-bold tabular-nums',
            compact ? 'text-xl' : 'text-2xl'
          )}>
            {amount.toFixed(2)}
          </span>
          <span className="text-sm text-muted-foreground ml-1">
            {bill.currency}
          </span>
        </div>

        {/* Bill Details */}
        <div className="space-y-1.5 text-sm">
          {bill.description && (
            <p className="text-muted-foreground">{bill.description}</p>
          )}
          
          {/* Inventory breakdown (if different from bill amount) */}
          {invTotal != null && Math.abs(invTotal - amount) > 0.01 && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <FileText className="h-3.5 w-3.5" aria-hidden />
              <span>Medicines: ₹{invTotal.toFixed(2)}</span>
              <span className="text-border">|</span>
              <span>Other: ₹{(amount - invTotal).toFixed(2)}</span>
            </div>
          )}

          {/* Due date (if unpaid) */}
          {bill.status === 'unpaid' && bill.due_date && (
            <div className="flex items-center gap-2 text-xs">
              <CreditCard className="h-3.5 w-3.5 text-amber-500" aria-hidden />
              <span className="text-amber-700 dark:text-amber-400">
                Due: {new Date(bill.due_date).toLocaleDateString('en-IN')}
              </span>
            </div>
          )}

          {/* Paid info (if paid) */}
          {bill.status === 'paid' && bill.paid_at && (
            <div className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400">
              <CreditCard className="h-3.5 w-3.5" aria-hidden />
              <span>
                Paid {new Date(bill.paid_at).toLocaleDateString('en-IN')}
                {bill.payment_method && ` via ${bill.payment_method}`}
              </span>
            </div>
          )}
        </div>

        {/* Mark Paid Button (if unpaid) */}
        {bill.status === 'unpaid' && (
          <div className="border-t border-border/50 pt-2">
            <Button
              onClick={handleMarkPaid}
              disabled={isMarkingPaid}
              size="sm"
              className="w-full"
            >
              {isMarkingPaid ? (
                <>
                  <CheckCircle className="h-4 w-4 mr-2 animate-spin" />
                  Marking Paid...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark Paid
                </>
              )}
            </Button>
          </div>
        )}

        {/* View Full Bill Link */}
        <div className={cn('border-t border-border/50 pt-2', bill.status === 'unpaid' && 'border-t-0 pt-0')}>
          <Link
            to={`/doctor/bills/${bill.id}`}
            className="inline-flex items-center gap-1.5 text-sm text-primary font-medium hover:underline"
          >
            View full bill
            <ExternalLink className="h-3 w-3" aria-hidden />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
