/**
 * Zustand store for receipt management.
 */

import { create } from 'zustand';
import { apiClient } from '@/lib/api';

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
  loading: boolean;
  error: string | null;
  fetchReceipts: (params?: {
    skip?: number;
    limit?: number;
    shop_id?: number;
    start_date?: string;
    end_date?: string;
  }) => Promise<void>;
  uploadReceipt: (file: File) => Promise<{ receipt_id: number; status: string }>;
  clearError: () => void;
}

export const useReceiptStore = create<ReceiptStore>((set) => ({
  receipts: [],
  loading: false,
  error: null,

  fetchReceipts: async (params) => {
    set({ loading: true, error: null });
    try {
      const data = await apiClient.getReceipts(params);
      set({ receipts: data.receipts, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch receipts',
        loading: false,
      });
    }
  },

  uploadReceipt: async (file) => {
    set({ loading: true, error: null });
    try {
      const result = await apiClient.uploadReceipt(file);
      set({ loading: false });
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload receipt';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));

