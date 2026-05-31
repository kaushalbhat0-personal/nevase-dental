import type { ReactNode } from 'react';

interface SkeletonBaseProps {
  children: ReactNode;
  className?: string;
  animate?: boolean;
}

export function SkeletonBase({
  children,
  className = '',
  animate = true,
}: SkeletonBaseProps) {
  return (
    <div
      className={`bg-gray-200 rounded ${animate ? 'animate-pulse' : ''} ${className}`}
    >
      {children}
    </div>
  );
}
