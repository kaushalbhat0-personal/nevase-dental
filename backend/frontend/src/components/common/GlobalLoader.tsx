import { Loader2 } from 'lucide-react';

interface GlobalLoaderProps {
  message?: string;
  fullscreen?: boolean;
}

export const GlobalLoader: React.FC<GlobalLoaderProps> = ({
  message = 'Loading...',
  fullscreen = false,
}) => {
  const containerClasses = fullscreen
    ? 'fixed inset-0 z-50 bg-white/80 backdrop-blur-sm'
    : 'absolute inset-0 z-40 bg-white/60 backdrop-blur-sm';

  return (
    <div className={`${containerClasses} flex items-center justify-center`}>
      <div className="flex flex-col items-center gap-3 p-6 bg-white rounded-lg shadow-lg">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <p className="text-sm text-gray-600 font-medium">{message}</p>
      </div>
    </div>
  );
};

// Hook for managing loading state with automatic cleanup
export const useLoadingState = () => {
  // This is a placeholder for a more sophisticated loading state manager
  // that could be integrated with global state (Zustand, Redux, etc.)
  return {
    startLoading: (message?: string) => {
      if (import.meta.env.DEV) {
        console.log('[Loading]', message || 'Started');
      }
    },
    stopLoading: () => {
      if (import.meta.env.DEV) {
        console.log('[Loading]', 'Stopped');
      }
    },
  };
};
