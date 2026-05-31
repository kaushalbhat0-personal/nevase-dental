interface SkeletonTextProps {
  lines?: number;
  lineHeight?: string;
  width?: string | string[];
  className?: string;
  animate?: boolean;
}

export function SkeletonText({
  lines = 1,
  lineHeight = 'h-4',
  width = 'w-full',
  className = '',
  animate = true,
}: SkeletonTextProps) {
  const getWidth = (index: number): string => {
    if (typeof width === 'string') return width;
    return width[index % width.length] || 'w-full';
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className={`bg-gray-200 rounded ${lineHeight} ${getWidth(index)} ${
            animate ? 'animate-pulse' : ''
          }`}
        />
      ))}
    </div>
  );
}
