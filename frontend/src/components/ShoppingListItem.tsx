import { CheckCircle2, Circle, Trash2 } from 'lucide-react';
import type { ShoppingListItem as ItemType } from '@/store/shoppingListStore';

interface Props {
  item: ItemType;
  onToggle: () => void;
  onRemove: () => void;
}

export function ShoppingListItem({ item, onToggle, onRemove }: Props) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
      <button onClick={onToggle} className="flex-shrink-0">
        {item.checked ? (
          <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
        ) : (
          <Circle className="w-5 h-5 text-gray-400" />
        )}
      </button>
      <div className="flex-1">
        <p className={`font-medium ${item.checked ? 'line-through text-gray-400' : 'text-gray-900 dark:text-white'}`}>
          {item.product_name}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {item.quantity} {item.unit}
        </p>
      </div>
      <button
        onClick={onRemove}
        className="flex-shrink-0 text-gray-400 hover:text-red-600 dark:hover:text-red-400"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
}

