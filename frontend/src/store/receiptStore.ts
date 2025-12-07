/**
 * Zustand store for receipt management.
 */

import { create } from 'zustand';
import apiClient from '@/lib/api';

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
      const response = await apiClient.get('/receipts', { params });
      // Backend might return list directly or wrapped. 
      // Based on receipts.py: return query.all() -> list.
      // So response.data is the list.
      // But receiptStore expects { receipts: data.receipts } ?
      // Let's assume the store was written for a wrapped response but checks backend.
      // If backend returns list, we set receipts: response.data.
      // Updating store expectation to match likely backend response (List[Receipt]).
      set({ receipts: Array.isArray(response.data) ? response.data : [], loading: false });
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
      const formData = new FormData();
      formData.append('file', file);
      const response = await apiClient.post('/receipts/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });
      set({ loading: false });
      return response.data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload receipt';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));

