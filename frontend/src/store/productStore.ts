import { create } from 'zustand';
import { fetchProducts, fetchCategories } from '@/lib/api';
import type { Product, Category } from '@/lib/api';

interface ProductStore {
    products: Product[];
    categories: Category[];
    loading: boolean;
    error: string | null;
    fetchProducts: (params?: { search?: string; category_id?: number }) => Promise<void>;
    fetchCategories: () => Promise<void>;
}

export const useProductStore = create<ProductStore>((set) => ({
    products: [],
    categories: [],
    loading: false,
    error: null,

    fetchProducts: async (params) => {
        set({ loading: true, error: null });
        try {
            const data = await fetchProducts(params);
            set({ products: data, loading: false });
        } catch (error) {
            set({
                error: error instanceof Error ? error.message : 'Failed to fetch products',
                loading: false,
            });
        }
    },

    fetchCategories: async () => {
        // Categories usually don't need loading state as strictly, but good to have
        try {
            const data = await fetchCategories();
            set({ categories: data });
        } catch (error) {
            console.error('Failed to fetch categories', error);
        }
    },
}));
