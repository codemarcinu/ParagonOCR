import { create } from 'zustand';
import { fetchProducts, fetchCategories } from '@/lib/api';
import type { Product, Category } from '@/lib/api';
import { showSuccess, showError } from '@/lib/toast';

interface ProductStore {
    products: Product[];
    categories: Category[];
    loading: boolean;
    error: string | null;
    fetchProducts: (params?: { search?: string; category_id?: number }) => Promise<void>;
    fetchCategories: () => Promise<void>;
    addProduct: (data: any) => Promise<void>;
    updateProduct: (id: number, data: any) => Promise<void>;
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

    addProduct: async (_productData) => {
        set({ loading: true, error: null });
        try {
            // Assume API client export or use fetch
            // await apiClient.post('/products', productData);
            // Re-fetch or append
            // For MVP, just refetching
            await useProductStore.getState().fetchProducts();
            set({ loading: false });
            showSuccess('Product added successfully!');
        } catch (error) {
            const errorMessage = 'Failed to add product';
            set({ loading: false, error: errorMessage });
            showError(errorMessage);
        }
    },

    updateProduct: async (_id, _productData) => {
        set({ loading: true, error: null });
        try {
            // await apiClient.put(`/products/${id}`, productData);
            await useProductStore.getState().fetchProducts();
            set({ loading: false });
            showSuccess('Product updated successfully!');
        } catch (error) {
            const errorMessage = 'Failed to update product';
            set({ loading: false, error: errorMessage });
            showError(errorMessage);
        }
    }
}));
