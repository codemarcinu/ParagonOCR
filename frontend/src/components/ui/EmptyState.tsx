import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils'; // Assuming this utility exists, if not standard class string

interface EmptyStateProps {
    icon?: LucideIcon;
    title: string;
    description?: string;
    action?: React.ReactNode;
    className?: string;
}

export function EmptyState({
    icon: Icon,
    title,
    description,
    action,
    className
}: EmptyStateProps) {
    return (
        <div className={cn(
            "flex flex-col items-center justify-center py-12 px-4 text-center rounded-lg border-2 border-dashed border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/20",
            className
        )}>
            {Icon && (
                <div className="bg-gray-100 p-4 rounded-full dark:bg-gray-800 mb-4">
                    <Icon className="h-8 w-8 text-gray-500 dark:text-gray-400" />
                </div>
            )}
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                {title}
            </h3>
            {description && (
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-6">
                    {description}
                </p>
            )}
            {action && (
                <div className="mt-2">
                    {action}
                </div>
            )}
        </div>
    );
}
