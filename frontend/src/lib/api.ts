import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface SpendingSummary {
  period_days: number;
  total_spending: number;
  receipt_count: number;
  average_receipt: number;
}

export interface Receipt {
  id: number;
  shop_name: string;
  purchase_date: string;
  total_amount: number;
  status: string;
}

export interface Product {
  id: number;
  name: string;
  category_id: number | null;
  unit: string;
}

export interface Category {
  id: number;
  name: string;
  icon: string | null;
  color: string | null;
}

export const fetchSummary = async (): Promise<SpendingSummary> => {
  const response = await api.get('/analytics/summary');
  return response.data;
};

export const fetchRecentReceipts = async (limit: number = 5): Promise<Receipt[]> => {
  const response = await api.get(`/receipts?limit=${limit}`);
  // Backend returns { receipts: [...], total: ... }
  return response.data.receipts;
};

export const fetchReceipts = async (params?: any) => {
  const response = await api.get('/receipts', { params });
  return response.data; // Returns { receipts: [], total: ... }
};

export const fetchProducts = async (params?: any): Promise<Product[]> => {
  const response = await api.get('/products', { params });
  return response.data;
};

export const fetchCategories = async (): Promise<Category[]> => {
  const response = await api.get('/products/categories');
  return response.data;
};

export default api;
