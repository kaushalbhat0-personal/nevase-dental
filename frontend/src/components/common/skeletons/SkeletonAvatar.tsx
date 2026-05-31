interface SkeletonAvatarProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  animate?: boolean;
}

const sizeMap = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-14 h-14',
  xl: 'w-16 h-16',
};

export function SkeletonAvatar({
  size = 'md',
  className = '',
  animate = true,
}: SkeletonAvatarProps) {
  return (
    <div
      className={`bg-gray-200 rounded-full ${sizeMap[size]} ${
        animate ? 'animate-pulse' : ''
      } ${className}`}
    />
  );
}
