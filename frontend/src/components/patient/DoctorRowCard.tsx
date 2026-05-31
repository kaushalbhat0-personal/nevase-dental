import { BadgeCheck, ChevronRight, MapPin, Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { initialsFromName } from '@/lib/patient/mockDoctorPresentation';

export type DoctorAvailabilityBadgeTone = 'today' | 'tomorrow' | 'muted';

export interface DoctorRowCardProps {
  name: string;
  subtitle: string;
  onPrimary?: () => void;
  /** Default: "Book Appointment" in patient flows. */
  primaryLabel?: string;
  onCardClick?: () => void;
  className?: string;
  /** e.g. 4.6 — shown when set */
  rating?: number;
  reviewCount?: number;
  /** e.g. "🟢 Available today" */
  availabilityLabel?: string;
  /** e.g. "Next slot: 10:30 AM" (shown under the chip when set) */
  availabilitySubLabel?: string;
  /** e.g. "2.3 km" — optional locality hint */
  distanceKm?: number;
  /** Visual weight for availability chip (green / red / neutral). */
  availabilityTone?: DoctorAvailabilityBadgeTone;
  /** Shorter width for horizontal rail */
  compact?: boolean;
  /** When false, CTA is hidden and card is non-interactive where applicable. */
  disabled?: boolean;
  /** Marketplace-approved clinician badge */
  showVerifiedBadge?: boolean;
  /** When true, rating/distance are labelled as illustrative (not verified patient data). */
  metricsAreSynthetic?: boolean;
}

/**
 * Mobile-first row card for doctor / provider discovery (Practo-style).
 */
export function DoctorRowCard({
  name,
  subtitle,
  onPrimary,
  primaryLabel = 'Book Appointment',
  onCardClick,
  className,
  rating,
  reviewCount,
  availabilityLabel,
  availabilitySubLabel,
  distanceKm,
  availabilityTone = 'today',
  compact,
  disabled,
  showVerifiedBadge,
  metricsAreSynthetic = true,
}: DoctorRowCardProps) {
  const interactive = Boolean(onCardClick) && !disabled;
  const showRating = typeof rating === 'number' && !Number.isNaN(rating);
  const showChevron = Boolean(onCardClick) && !onPrimary;

  return (
    <div
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={disabled ? undefined : onCardClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onCardClick?.();
              }
            }
          : undefined
      }
      className={cn(
        'relative z-0 rounded-xl border border-border/80 bg-white p-4 shadow-md transition-all duration-200',
        compact && 'p-3',
        'hover:border-primary/25 hover:shadow-lg',
        interactive && 'cursor-pointer',
        disabled && 'opacity-60',
        className
      )}
    >
      <div className={cn('flex min-w-0 flex-col', compact ? 'gap-3' : 'gap-4')}>
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'flex flex-shrink-0 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 text-sm font-bold text-primary ring-1 ring-primary/10',
              compact ? 'h-12 w-12 text-xs' : 'h-16 w-16'
            )}
            aria-hidden
          >
            {initialsFromName(name)}
          </div>

          <div className="min-w-0 flex-1 overflow-hidden">
            <h3
              className={cn(
                'font-semibold leading-tight text-foreground',
                compact ? 'truncate text-sm' : 'truncate text-base'
              )}
            >
              {name}
            </h3>
            <p
              className={cn(
                'text-muted-foreground',
                compact ? 'mt-0.5 truncate text-xs' : 'mt-0.5 truncate text-sm'
              )}
            >
              {subtitle}
            </p>
            {typeof distanceKm === 'number' && !Number.isNaN(distanceKm) && (
              <p className="mt-1 flex min-w-0 items-center gap-1 text-xs text-muted-foreground">
                <MapPin className="h-3.5 w-3.5 flex-shrink-0 text-primary" aria-hidden />
                <span className="min-w-0 truncate">
                  {metricsAreSynthetic ? (
                    <>
                      <span className="font-medium text-foreground/85">📍 Distance estimate</span>
                      <span className="text-muted-foreground/80"> (~{distanceKm.toFixed(1)} km illustrative)</span>
                    </>
                  ) : (
                    <>
                      <span className="font-medium text-foreground/85">{distanceKm.toFixed(1)} km away</span>
                      <span className="text-muted-foreground/80"> (approx.)</span>
                    </>
                  )}
                </span>
              </p>
            )}
          </div>

          <div className="flex flex-shrink-0 items-center gap-1 self-start">
            {showVerifiedBadge ? (
              <span
                className="inline-flex shrink-0 items-center gap-0.5 rounded-full bg-emerald-500/12 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 ring-1 ring-emerald-500/25 dark:text-emerald-400"
                title="Verified doctor"
              >
                <BadgeCheck className="h-3 w-3 flex-shrink-0" aria-hidden />
                Verified
              </span>
            ) : null}
            {showChevron ? (
              <ChevronRight className="h-5 w-5 flex-shrink-0 text-muted-foreground" aria-hidden />
            ) : null}
          </div>
        </div>

        <div className="flex min-w-0 flex-wrap items-center gap-3">
          {showRating && (
            <span className="inline-flex max-w-full min-w-0 items-center gap-0.5 text-xs text-muted-foreground">
              <Star className="h-3.5 w-3.5 flex-shrink-0 fill-amber-400 text-amber-500" aria-hidden />
              <span className="min-w-0 truncate font-medium text-amber-600">
                ⭐ {rating.toFixed(1)}{' '}
                {metricsAreSynthetic ? (
                  <span className="font-normal text-muted-foreground">(reviews coming soon)</span>
                ) : typeof reviewCount === 'number' ? (
                  <span className="font-normal">({reviewCount} reviews)</span>
                ) : null}
              </span>
            </span>
          )}
          {availabilityLabel && (
            <span
              className={cn(
                'inline-flex max-w-full shrink-0 rounded-full font-medium',
                disabled || availabilityTone === 'muted'
                  ? 'bg-muted px-2 py-0.5 text-[11px] text-muted-foreground'
                  : availabilityTone === 'tomorrow'
                    ? 'bg-destructive/10 px-2 py-0.5 text-[11px] text-destructive ring-1 ring-destructive/20'
                    : 'bg-green-50 px-3 py-1 text-xs text-green-700 dark:bg-green-950/40 dark:text-green-400'
              )}
            >
              {availabilityLabel}
            </span>
          )}
        </div>
        {availabilitySubLabel ? (
          <p className="min-w-0 truncate text-xs font-medium text-foreground/90">{availabilitySubLabel}</p>
        ) : null}

        {onPrimary && (
          <Button
            type="button"
            className="h-11 w-full rounded-xl px-5 text-base font-semibold shadow-md ring-2 ring-primary/15 transition-shadow hover:shadow-lg md:w-auto md:min-w-[min(100%,14rem)]"
            disabled={disabled}
            onClick={(e) => {
              e.stopPropagation();
              onPrimary();
            }}
          >
            {primaryLabel}
          </Button>
        )}
      </div>
    </div>
  );
}
