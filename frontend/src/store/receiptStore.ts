/**
 * Zustand store for receipt management.
 */

import { create } from 'zustand';
import apiClient from '@/lib/api';
import { showSuccess, showError } from '@/lib/toast';

export interface Receipt {
  id: number;
  shop: string | null;
  purchase_date: string | null;
  purchase_time: string | null;
  total_amount: number;
  items_count: number;
  created_at: string | null;
}

interface ReceiptStore {
  receipts: Receipt[];
  total: number;
  limit: number;
  skip: number;
  filters: {
    shop_id?: number;
    start_date?: string;
    end_date?: string;
  };
  loading: boolean;
  error: string | null;
  fetchReceipts: (params?: {
    skip?: number;
    limit?: number;
    shop_id?: number;
    start_date?: string;
    end_date?: string;
  }) => Promise<void>;
  setFilters: (filters: { shop_id?: number; start_date?: string; end_date?: string }) => void;
  resetFilters: () => void;
  setPage: (page: number) => void;
  uploadReceipt: (file: File) => Promise<{ receipt_id: number; status: string }>;
  clearError: () => void;
}

export const useReceiptStore = create<ReceiptStore>((set) => ({
  receipts: [],
  loading: false,
  error: null,

  total: 0,
  limit: 50,
  skip: 0,
  filters: {},

  fetchReceipts: async (params) => {
    set({ loading: true, error: null });
    try {
      // Merge current filters with new params if provided
      const currentFilters = useReceiptStore.getState().filters;
      const currentSkip = useReceiptStore.getState().skip;
      const currentLimit = useReceiptStore.getState().limit;

      const queryParams = {
        skip: currentSkip,
        limit: currentLimit,
        ...currentFilters,
        ...params,
      };

      const response = await apiClient.get('/receipts', { params: queryParams });
      const data = response.data;

      // Handle response structure { receipts: [], total: ... }
      const receiptsList = Array.isArray(data) ? data : (data.receipts || []);
      const totalCount = data.total || receiptsList.length;

      set({
        receipts: receiptsList,
        total: totalCount,
        loading: false,
        skip: queryParams.skip,
        limit: queryParams.limit,
        filters: {
          shop_id: queryParams.shop_id,
          start_date: queryParams.start_date,
          end_date: queryParams.end_date
        }
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch receipts',
        loading: false,
      });
    }
  },

  setFilters: (filters) => {
    set((state) => ({ filters: { ...state.filters, ...filters }, skip: 0 }));
    useReceiptStore.getState().fetchReceipts({ skip: 0 });
  },

  resetFilters: () => {
    set({ filters: {}, skip: 0 });
    useReceiptStore.getState().fetchReceipts({ skip: 0 });
  },

  setPage: (page: number) => {
    const { limit } = useReceiptStore.getState();
    const newSkip = (page - 1) * limit;
    set({ skip: newSkip });
    useReceiptStore.getState().fetchReceipts({ skip: newSkip });
  },

  uploadReceipt: async (file) => {
    set({ loading: true, error: null });
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await apiClient.post('/receipts/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });
      set({ loading: false });
      showSuccess('Receipt uploaded successfully!');
      return response.data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload receipt';
      set({ error: errorMessage, loading: false });
      showError(errorMessage);
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));

