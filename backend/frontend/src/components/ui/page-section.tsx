/**
 * PageSection — a reusable section wrapper for dashboard pages.
 *
 * Provides consistent title, description, and optional action slot.
 * Mobile-first with responsive padding.
 */

import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PageSectionProps {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}

export function PageSection({ title, description, children, className, action }: PageSectionProps) {
  return (
    <section className={cn('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground sm:text-lg">{title}</h2>
          {description && (
            <p className="text-xs text-muted-foreground sm:text-sm">{description}</p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {children}
    </section>
  );
}
