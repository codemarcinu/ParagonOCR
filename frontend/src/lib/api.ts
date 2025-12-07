import axios from 'axios';

import { useAuthStore } from '../store/authStore';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      // Optional: Redirect to login if not already there, but Router usually handles this via ProtectedRoute
    }
    return Promise.reject(error);
  }
);

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

export const getReceipt = async (id: number) => {
  const response = await api.get(`/receipts/${id}`);
  return response.data;
};

// Auth
export const login = async (formData: FormData) => {
  const response = await api.post('/auth/token', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data; // { access_token, token_type }
};

export const register = async (data: any) => {
  const response = await api.post('/auth/register', data);
  return response.data;
};

export const fetchMe = async () => {
  const response = await api.get('/auth/users/me');
  return response.data;
}

export default api;
