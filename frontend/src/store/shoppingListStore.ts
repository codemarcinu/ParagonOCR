import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import apiClient from '@/lib/api';
import { showSuccess, showError } from '@/lib/toast';

export interface ShoppingListItem {
  id: number;
  product_id: number | null;
  product_name: string;
  quantity: number;
  unit: string;
  checked: boolean;
  priority: 'low' | 'medium' | 'high';
  notes?: string;
}

export interface ShoppingList {
  id: number;
  title: string;
  items: ShoppingListItem[];
  created_at: string;
  completed_at: string | null;
}

interface ShoppingListStore {
  lists: ShoppingList[];
  currentList: ShoppingList | null;
  loading: boolean;
  error: string | null;

  fetchLists: () => Promise<void>;
  createList: (title: string) => Promise<void>;
  selectList: (id: number) => Promise<void>;
  addItem: (item: Omit<ShoppingListItem, 'id' | 'checked'>) => Promise<void>;
  toggleItem: (itemId: number) => Promise<void>;
  removeItem: (itemId: number) => Promise<void>;
  completeList: () => Promise<void>;
  generateFromMealPlan: () => Promise<void>; // Future: AI-generated list
}

export const useShoppingListStore = create<ShoppingListStore>()(
  persist(
    (set, get) => ({
      lists: [],
      currentList: null,
      loading: false,
      error: null,

      fetchLists: async () => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.get('/shopping-lists');
          set({ lists: response.data, loading: false });
        } catch (error) {
          set({ loading: false, error: 'Failed to fetch shopping lists' });
        }
      },

      createList: async (title: string) => {
        set({ loading: true });
        try {
          const response = await apiClient.post('/shopping-lists', { title, items: [] });
          const newList = response.data;
          set((state) => ({
            lists: [newList, ...state.lists],
            currentList: newList,
            loading: false
          }));
          showSuccess('Shopping list created successfully!');
        } catch (error) {
          const errorMessage = 'Failed to create list';
          set({ loading: false, error: errorMessage });
          showError(errorMessage);
        }
      },

      selectList: async (id: number) => {
        set({ loading: true });
        try {
          const response = await apiClient.get(`/shopping-lists/${id}`);
          set({ currentList: response.data, loading: false });
        } catch (error) {
          set({ loading: false, error: 'Failed to load list' });
        }
      },

      addItem: async (item) => {
        // Optimistic update could be added here too
        const { currentList } = get();
        if (!currentList) return;

        set({ loading: true });
        try {
          const response = await apiClient.post(`/shopping-lists/${currentList.id}/items`, item);
          set((state) => ({
            currentList: {
              ...state.currentList!,
              items: [...state.currentList!.items, response.data]
            },
            loading: false
          }));
          showSuccess('Item added to list!');
        } catch (error) {
          const errorMessage = 'Failed to add item';
          set({ loading: false, error: errorMessage });
          showError(errorMessage);
        }
      },

      toggleItem: async (itemId: number) => {
        const { currentList } = get();
        if (!currentList) return;

        const item = currentList.items.find(i => i.id === itemId);
        if (!item) return;

        // Optimistic update
        set((state) => ({
          currentList: {
            ...state.currentList!,
            items: state.currentList!.items.map(i =>
              i.id === itemId ? { ...i, checked: !i.checked } : i
            )
          }
        }));

        try {
          await apiClient.patch(`/shopping-lists/${currentList.id}/items/${itemId}`, {
            checked: !item.checked
          });
        } catch (error) {
          // Revert on error
          set((state) => ({
            currentList: {
              ...state.currentList!,
              items: state.currentList!.items.map(i =>
                i.id === itemId ? { ...i, checked: item.checked } : i
              )
            },
            error: 'Failed to update item'
          }));
        }
      },

      removeItem: async (itemId: number) => {
        const { currentList } = get();
        if (!currentList) return;

        // Optimistic update
        const previousItems = currentList.items;
        set((state) => ({
          currentList: {
            ...state.currentList!,
            items: state.currentList!.items.filter(i => i.id !== itemId)
          }
        }));

        try {
          await apiClient.delete(`/shopping-lists/${currentList.id}/items/${itemId}`);
        } catch (error) {
          // Revert
          set((state) => ({
            currentList: {
              ...state.currentList!,
              items: previousItems
            },
            error: 'Failed to remove item'
          }));
        }
      },

      completeList: async () => {
        const { currentList } = get();
        if (!currentList) return;

        try {
          await apiClient.patch(`/shopping-lists/${currentList.id}`, {
            completed_at: new Date().toISOString()
          });
          set((state) => ({
            currentList: {
              ...state.currentList!,
              completed_at: new Date().toISOString()
            }
          }));
          showSuccess('Shopping list completed!');
        } catch (error) {
          const errorMessage = 'Failed to complete list';
          set({ error: errorMessage });
          showError(errorMessage);
        }
      },

      generateFromMealPlan: async () => {
        // Future: AI-generated shopping list from meal plan
        set({ error: 'Not implemented yet' });
      }
    }),
    {
      name: 'shopping-list-storage',
      partialize: (state) => ({ lists: state.lists, currentList: state.currentList }), // specific fields to persist
    }
  )
);
