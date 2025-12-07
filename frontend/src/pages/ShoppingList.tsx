import { useEffect, useState } from 'react';
import { useShoppingListStore } from '@/store/shoppingListStore';
import { Plus } from 'lucide-react';
import { ShoppingListItem } from '@/components/ShoppingListItem';
import { LoadingSpinner, Skeleton } from '@/components/ui';

export function ShoppingList() {
  const {
    lists,
    currentList,
    loading,
    error,
    fetchLists,
    createList,
    selectList,
    addItem,
    toggleItem,
    removeItem,
    completeList
  } = useShoppingListStore();
  
  const [newItemName, setNewItemName] = useState('');
  const [newItemQuantity, setNewItemQuantity] = useState('1');
  const [showNewListModal, setShowNewListModal] = useState(false);
  const [newListTitle, setNewListTitle] = useState('');
  
  useEffect(() => {
    fetchLists();
  }, [fetchLists]);
  
  useEffect(() => {
    if (lists.length > 0 && !currentList) {
      selectList(lists[0].id);
    }
  }, [lists, currentList, selectList]);
  
  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemName.trim() || !currentList) return;
    
    await addItem({
      product_name: newItemName,
      quantity: parseFloat(newItemQuantity) || 1,
      unit: 'szt',
      priority: 'medium'
    });
    
    setNewItemName('');
    setNewItemQuantity('1');
  };
  
  const handleCreateList = async () => {
    if (!newListTitle.trim()) return;
    await createList(newListTitle);
    setNewListTitle('');
    setShowNewListModal(false);
  };
  
  const checkedCount = currentList?.items.filter(i => i.checked).length || 0;
  const totalCount = currentList?.items.length || 0;
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Shopping Lists
          </h1>
          <button
            onClick={() => setShowNewListModal(true)}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Plus className="w-5 h-5 mr-2" />
            New List
          </button>
        </div>
        
        {/* Lists Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4">Your Lists</h2>
              {loading && lists.length === 0 ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-16 w-full" variant="rectangular" />
                  ))}
                </div>
              ) : (
                lists.map((list) => (
                  <button
                    key={list.id}
                    onClick={() => selectList(list.id)}
                    className={`w-full text-left p-3 rounded-md mb-2 transition-colors ${
                      currentList?.id === list.id
                        ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <p className="font-medium text-gray-900 dark:text-white">{list.title}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {list.items.length} items
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>
          
          {/* Current List */}
          <div className="lg:col-span-2">
            {loading && !currentList ? (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <LoadingSpinner size="lg" />
              </div>
            ) : currentList ? (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex justify-between items-center">
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                        {currentList.title}
                      </h2>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        {checkedCount} / {totalCount} completed
                      </p>
                    </div>
                    {currentList.completed_at ? (
                      <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-sm">
                        Completed
                      </span>
                    ) : (
                      <button
                        onClick={completeList}
                        className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                      >
                        Mark Complete
                      </button>
                    )}
                  </div>
                </div>
                
                {/* Add Item Form */}
                <form onSubmit={handleAddItem} className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newItemName}
                      onChange={(e) => setNewItemName(e.target.value)}
                      placeholder="Item name..."
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                    />
                    <input
                      type="number"
                      value={newItemQuantity}
                      onChange={(e) => setNewItemQuantity(e.target.value)}
                      placeholder="Qty"
                      className="w-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                    />
                    <button
                      type="submit"
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    >
                      <Plus className="w-5 h-5" />
                    </button>
                  </div>
                </form>
                
                {/* Items List */}
                <div className="p-4">
                  {error && (
                    <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                      <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                    </div>
                  )}
                  {currentList.items.length === 0 ? (
                    <p className="text-center text-gray-500 dark:text-gray-400 py-8">
                      No items yet. Add your first item above!
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {currentList.items.map((item) => (
                        <ShoppingListItem
                          key={item.id}
                          item={item}
                          onToggle={() => toggleItem(item.id)}
                          onRemove={() => removeItem(item.id)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
                <p className="text-gray-500 dark:text-gray-400">
                  Select a list or create a new one to get started
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* New List Modal */}
      {showNewListModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4">Create New List</h3>
            <input
              type="text"
              value={newListTitle}
              onChange={(e) => setNewListTitle(e.target.value)}
              placeholder="List title..."
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white mb-4"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleCreateList();
                } else if (e.key === 'Escape') {
                  setShowNewListModal(false);
                }
              }}
            />
            <div className="flex gap-2">
              <button
                onClick={() => setShowNewListModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateList}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
