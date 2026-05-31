import { SkeletonAvatar } from './SkeletonAvatar';
import { SkeletonText } from './SkeletonText';

interface SkeletonCardProps {
  showAvatar?: boolean;
  avatarSize?: 'sm' | 'md' | 'lg' | 'xl';
  lines?: number;
  className?: string;
  animate?: boolean;
}

export function SkeletonCard({
  showAvatar = true,
  avatarSize = 'lg',
  lines = 2,
  className = '',
  animate = true,
}: SkeletonCardProps) {
  return (
    <div
      className={`flex items-center gap-4 p-4 sm:p-6 bg-white border border-gray-200 rounded-2xl shadow-sm ${className}`}
    >
      {showAvatar && <SkeletonAvatar size={avatarSize} animate={animate} />}
      <div className="flex-1 min-w-0 space-y-2.5">
        <SkeletonText
          lines={lines}
          lineHeight="h-4 sm:h-5"
          width={['w-3/4', 'w-1/2', 'w-full']}
          animate={animate}
        />
      </div>
    </div>
  );
}
