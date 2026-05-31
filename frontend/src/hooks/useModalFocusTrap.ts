import { useEffect, type RefObject } from 'react';

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

let bodyScrollLockCount = 0;
let bodyScrollPreviousOverflow = '';

function getFocusable(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
}

/**
 * Prevents page scroll behind a modal. Nested modals are supported via a ref count.
 */
function useBodyScrollLock(locked: boolean) {
  useEffect(() => {
    if (!locked) return;
    if (bodyScrollLockCount === 0) {
      bodyScrollPreviousOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
    }
    bodyScrollLockCount += 1;
    return () => {
      bodyScrollLockCount = Math.max(0, bodyScrollLockCount - 1);
      if (bodyScrollLockCount === 0) {
        document.body.style.overflow = bodyScrollPreviousOverflow;
      }
    };
  }, [locked]);
}

/**
 * Keeps keyboard focus inside `containerRef` while `active` is true (modal pattern).
 */
export function useModalFocusTrap(containerRef: RefObject<HTMLElement | null>, active: boolean) {
  useBodyScrollLock(active);
  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    const previousActive = document.activeElement as HTMLElement | null;

    const focusables = getFocusable(container);
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    first?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab' || focusables.length === 0) return;
      if (!container.contains(document.activeElement)) {
        e.preventDefault();
        first?.focus();
        return;
      }
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else if (document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown, true);
    return () => {
      document.removeEventListener('keydown', onKeyDown, true);
      if (previousActive?.focus) {
        previousActive.focus();
      }
    };
  }, [active, containerRef]);
}
