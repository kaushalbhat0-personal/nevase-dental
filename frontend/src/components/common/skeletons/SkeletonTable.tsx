interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  showHeader?: boolean;
  className?: string;
  animate?: boolean;
}

export function SkeletonTable({
  rows = 5,
  columns = 5,
  showHeader = true,
  className = '',
  animate = true,
}: SkeletonTableProps) {
  const pulseClass = animate ? 'animate-pulse' : '';

  return (
    <div
      className={`bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm ${className}`}
    >
      <table className="w-full min-w-[600px]">
        {showHeader && (
          <thead>
            <tr className="bg-gray-50">
              {Array.from({ length: columns }).map((_, index) => (
                <th key={index} className="px-4 py-3 text-left">
                  <div
                    className={`h-4 bg-gray-200 rounded w-20 ${pulseClass}`}
                  />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr
              key={rowIndex}
              className={rowIndex !== rows - 1 ? 'border-b border-gray-100' : ''}
            >
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex} className="px-4 py-4">
                  <div
                    className={`h-4 bg-gray-200 rounded ${
                      colIndex === 0 ? 'w-32' : 'w-24'
                    } ${pulseClass}`}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
