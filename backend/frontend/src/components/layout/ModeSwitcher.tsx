import { useNavigate } from 'react-router-dom';
import { Stethoscope, Building2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { useAppMode } from '../../contexts/AppModeContext';
import { buttonVariants } from '@/components/ui/button';
import type { User } from '../../types';
import { getEffectiveRoles, isDoctorAndOrgAdminRoles } from '../../utils/roles';

/**
 * Shown only for users with both `doctor` and org `admin` in effective roles.
 * UI mode does not change API permissions; it only changes navigation and theming.
 */
export function ModeSwitcher({ user }: { user: User | null }) {
  const { setMode, resolvedMode } = useAppMode();
  const navigate = useNavigate();

  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const showToggle = isDoctorAndOrgAdminRoles(getEffectiveRoles(user, token));

  if (!showToggle) {
    return null;
  }

  const go = (m: 'practice' | 'admin') => {
    setMode(m);
    if (m === 'practice') {
      navigate('/doctor/dashboard', { replace: true });
    } else {
      navigate('/admin/dashboard', { replace: true });
    }
  };

  return (
    <div
      className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-2"
      role="group"
      aria-label="Application mode"
    >
      <Badge
        variant="outline"
        className={cn(
          'font-medium normal-case max-sm:text-[0.65rem] max-sm:px-1.5',
          resolvedMode === 'practice' &&
            'border-emerald-500/50 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100',
          resolvedMode === 'admin' && 'border-slate-500/40 bg-slate-500/10 text-slate-800 dark:text-slate-100'
        )}
      >
        {resolvedMode === 'practice' ? 'Practice' : 'Admin'}
      </Badge>
      <div className="flex rounded-lg border border-border/80 bg-muted/40 p-0.5">
        <button
          type="button"
          onClick={() => go('practice')}
          className={cn(
            buttonVariants({ variant: 'ghost', size: 'sm' }),
            'h-8 gap-1.5 rounded-md px-2.5 text-xs',
            resolvedMode === 'practice'
              ? 'bg-white text-foreground shadow-sm dark:bg-card'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          <Stethoscope className="h-3.5 w-3.5" aria-hidden />
          Practice
        </button>
        <button
          type="button"
          onClick={() => go('admin')}
          className={cn(
            buttonVariants({ variant: 'ghost', size: 'sm' }),
            'h-8 gap-1.5 rounded-md px-2.5 text-xs',
            resolvedMode === 'admin'
              ? 'bg-white text-foreground shadow-sm dark:bg-card'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          <Building2 className="h-3.5 w-3.5" aria-hidden />
          Admin
        </button>
      </div>
    </div>
  );
}
