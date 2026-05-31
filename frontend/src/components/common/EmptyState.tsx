import { PackageOpen, Search, FileX, type LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: 'package' | 'search' | 'file' | LucideIcon;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const iconMap: Record<string, LucideIcon> = {
  package: PackageOpen,
  search: Search,
  file: FileX,
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No data found',
  description = 'There are no items to display at the moment.',
  icon = 'package',
  action,
}) => {
  const IconComponent = typeof icon === 'string' ? iconMap[icon] : icon;

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="rounded-full bg-muted p-4 mb-4">
        <IconComponent className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-medium text-foreground mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm mb-4">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="inline-flex items-center gap-2 px-4 py-2 border border-transparent text-sm font-medium rounded-lg shadow-sm text-primary-foreground bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};
