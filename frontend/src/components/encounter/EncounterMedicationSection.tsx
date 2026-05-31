import { Pill, Package, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { AppointmentInventoryUsageLine } from '../../types';

interface EncounterMedicationSectionProps {
  inventoryUsages?: AppointmentInventoryUsageLine[];
  /** Total selling price of medicines (for billing parity display) */
  inventoryMaterialsSellingTotal?: string | number | null;
  /** Mobile-optimized compact mode */
  compact?: boolean;
}

/**
 * EncounterMedicationSection - Medicines and materials used during encounter
 * 
 * Clinical-first hierarchy element #5: Medicines used
 * Displays inventory consumption (medicines given during the visit).
 * 
 * Future extension hooks (Phase 2):
 * - TODO: Integrate with formal Prescription module
 * - TODO: Add dosage tracking
 * - TODO: Add medication administration records (MAR)
 * - TODO: Add drug interaction warnings
 * 
 * Mobile considerations:
 * - List format for readability
 * - Clear quantity indicators
 * - Selling total shown if available
 */
export function EncounterMedicationSection({
  inventoryUsages,
  inventoryMaterialsSellingTotal,
  compact = false,
}: EncounterMedicationSectionProps) {
  const hasUsages = inventoryUsages && inventoryUsages.length > 0;
  
  if (!hasUsages) {
    return (
      <Card className={cn('bg-muted/30', compact && 'opacity-75')}>
        <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
          <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
            <Pill className="h-4 w-4 text-primary shrink-0" aria-hidden />
            Medicines Given
          </CardTitle>
        </CardHeader>
        <CardContent className={cn(compact && 'p-3 pt-0')}>
          <p className="text-sm text-muted-foreground italic">
            No medicines recorded for this encounter.
          </p>
        </CardContent>
      </Card>
    );
  }

  const total = inventoryMaterialsSellingTotal != null 
    ? Number(inventoryMaterialsSellingTotal) 
    : null;

  return (
    <Card className={cn('overflow-hidden', compact && 'text-sm')}>
      <CardHeader className={cn('pb-2', compact && 'p-3 pb-2')}>
        <CardTitle className={cn('flex items-center gap-2', compact && 'text-sm')}>
          <Pill className="h-4 w-4 text-primary shrink-0" aria-hidden />
          Medicines Given
          {hasUsages && (
            <span className="text-xs font-normal text-muted-foreground ml-auto">
              {inventoryUsages.length} item{inventoryUsages.length !== 1 ? 's' : ''}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      
      <CardContent className={cn('space-y-3', compact && 'p-3 pt-0 space-y-2')}>
        {/* Medicines List */}
        <ul className={cn(
          'space-y-2',
          compact ? 'text-sm' : 'text-sm'
        )}>
          {inventoryUsages.map((usage) => (
            <li 
              key={usage.item_id}
              className="flex items-start gap-2 p-2 rounded-md bg-muted/30"
            >
              <Package className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" aria-hidden />
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 flex-wrap">
                  <span className="font-medium truncate">
                    {usage.item_name || 'Unknown Item'}
                  </span>
                  <span className="text-muted-foreground tabular-nums">
                    × {usage.quantity}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>

        {/* Total (if available) */}
        {total != null && total > 0 && (
          <div className="border-t border-border/50 pt-2 flex items-center justify-between">
            <span className="text-sm text-muted-foreground flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5" aria-hidden />
              Total medicines value
            </span>
            <span className="font-semibold tabular-nums text-foreground">
              ₹{total.toFixed(2)}
            </span>
          </div>
        )}

        {/*
          TODO: Future Phase 2 - Prescription Integration
          
          When prescriptions module is implemented:
          - Link to formal prescription record
          - Show prescribed vs dispensed comparison
          - Add refill information
          - Include dosage instructions
          
          Example:
          {prescription && (
            <div className="border-t border-border/50 pt-3">
              <h4 className="text-xs font-medium text-muted-foreground mb-2">
                Linked Prescription
              </h4>
              <Link 
                to={`/doctor/prescriptions/${prescription.id}`}
                className="text-sm text-primary hover:underline"
              >
                View Prescription #{prescription.id}
              </Link>
            </div>
          )}
        */}
      </CardContent>
    </Card>
  );
}
