import { Skeleton } from './Skeleton';

export function LoadingCard() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <Skeleton className="h-6 w-1/3 mb-4" variant="text" />
      <Skeleton className="h-4 w-full mb-2" variant="text" />
      <Skeleton className="h-4 w-5/6 mb-2" variant="text" />
      <Skeleton className="h-4 w-4/6" variant="text" />
    </div>
  );
}

