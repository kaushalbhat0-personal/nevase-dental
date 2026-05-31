import { forwardRef, useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode, type Ref } from 'react';
import { cn } from '@/lib/utils';

const SWIPE_ACTION_THRESHOLD = 80;
const MAX_DRAG = 100;
const AXIS_LOCK_PX = 12;

type Axis = 'none' | 'undecided' | 'x' | 'y';

function mergeRefs<T>(...refs: (Ref<T> | undefined)[]) {
  return (value: T) => {
    for (const r of refs) {
      if (typeof r === 'function') r(value);
      else if (r && 'current' in r) (r as { current: T | null }).current = value;
    }
  };
}

export interface SwipeableSlotActionsProps {
  children: ReactNode;
  onComplete: () => void;
  onCancel: () => void;
  /** When true, swipe and touch handlers are disabled. */
  disabled?: boolean;
  /** If false, renders a static card (e.g. desktop) — use buttons for actions. */
  swipeEnabled: boolean;
  className: string;
  dataTestId?: string;
  onKeyDown?: (e: KeyboardEvent) => void;
}

/**
 * List appointment card with optional touch swipe: right → complete, left → cancel.
 * Reveals green (complete) on the left and red (cancel) on the right under the card while dragging.
 */
export const SwipeableSlotActions = forwardRef<HTMLDivElement, SwipeableSlotActionsProps>(function SwipeableSlotActions(
  { children, onComplete, onCancel, disabled, swipeEnabled, className, dataTestId, onKeyDown },
  ref
) {
  const [tx, setTx] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const startX = useRef(0);
  const startY = useRef(0);
  const axis = useRef<Axis>('none');
  const raf = useRef<number | null>(null);
  const onCompleteRef = useRef(onComplete);
  const onCancelRef = useRef(onCancel);
  onCompleteRef.current = onComplete;
  onCancelRef.current = onCancel;

  const commitTx = useCallback((t: number) => {
    if (raf.current != null) cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => {
      raf.current = null;
      setTx(Math.round(Math.max(-MAX_DRAG, Math.min(MAX_DRAG, t)) * 10) / 10);
    });
  }, []);

  useEffect(
    () => () => {
      if (raf.current != null) cancelAnimationFrame(raf.current);
    },
    []
  );

  const resetPosition = useCallback(() => {
    setIsDragging(false);
    axis.current = 'none';
    setTx(0);
  }, []);

  useEffect(() => {
    if (!swipeEnabled || disabled) return;
    const el = surfaceRef.current;
    if (!el) return;

    const onStart = (e: TouchEvent) => {
      if (disabled) return;
      if (e.touches.length !== 1) return;
      const target = e.target;
      if (target instanceof Element && target.closest('a[href], button, [role="button"]')) {
        return;
      }
      startX.current = e.touches[0].clientX;
      startY.current = e.touches[0].clientY;
      axis.current = 'undecided';
      setIsDragging(true);
    };

    const onMove = (e: TouchEvent) => {
      if (disabled || e.touches.length !== 1) return;
      const cx = e.touches[0].clientX;
      const cy = e.touches[0].clientY;
      const dx = cx - startX.current;
      const dy = cy - startY.current;

      if (axis.current === 'undecided') {
        if (Math.abs(dx) < AXIS_LOCK_PX && Math.abs(dy) < AXIS_LOCK_PX) return;
        if (Math.abs(dy) > Math.abs(dx) * 1.15) {
          axis.current = 'y';
          setIsDragging(false);
          setTx(0);
          return;
        }
        axis.current = 'x';
      }
      if (axis.current !== 'x') return;
      e.preventDefault();
      commitTx(dx);
    };

    const onEnd = (e: TouchEvent) => {
      if (axis.current !== 'x') {
        resetPosition();
        return;
      }
      const touch = e.changedTouches[0];
      const d = touch ? touch.clientX - startX.current : 0;
      if (d > SWIPE_ACTION_THRESHOLD) {
        onCompleteRef.current();
      } else if (d < -SWIPE_ACTION_THRESHOLD) {
        onCancelRef.current();
      }
      resetPosition();
    };

    const onCancelTouch = () => {
      if (axis.current === 'x') resetPosition();
      else {
        setIsDragging(false);
        axis.current = 'none';
      }
    };

    const opts: AddEventListenerOptions = { passive: false };
    el.addEventListener('touchstart', onStart, opts);
    el.addEventListener('touchmove', onMove, opts);
    el.addEventListener('touchend', onEnd);
    el.addEventListener('touchcancel', onCancelTouch);
    return () => {
      el.removeEventListener('touchstart', onStart);
      el.removeEventListener('touchmove', onMove);
      el.removeEventListener('touchend', onEnd);
      el.removeEventListener('touchcancel', onCancelTouch);
    };
  }, [swipeEnabled, disabled, commitTx, resetPosition]);

  const transitionClass = isDragging ? '' : 'transition-transform duration-200 ease-out';

  if (!swipeEnabled) {
    return (
      <div
        ref={ref}
        data-testid={dataTestId}
        role="listitem"
        tabIndex={0}
        onKeyDown={onKeyDown}
        className={className}
      >
        {children}
      </div>
    );
  }

  return (
    <div className="relative w-full touch-pan-y overflow-hidden rounded-xl">
      <div className="pointer-events-none absolute inset-0 z-0 flex" aria-hidden>
        <div className="flex flex-1 items-center justify-end bg-emerald-600/90 pr-3 text-xs font-medium text-white">
          Complete
        </div>
        <div className="flex flex-1 items-center justify-start bg-red-600/90 pl-3 text-xs font-medium text-white">
          Cancel
        </div>
      </div>
      <div
        ref={mergeRefs(surfaceRef, ref)}
        data-testid={dataTestId}
        role="listitem"
        tabIndex={0}
        onKeyDown={onKeyDown}
        style={{ transform: `translateX(${tx}px)` }}
        className={cn(
          className,
          'relative z-10 w-full will-change-transform',
          transitionClass,
          disabled && 'pointer-events-none opacity-70'
        )}
      >
        {children}
      </div>
    </div>
  );
});
