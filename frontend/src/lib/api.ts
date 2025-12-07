import axios from 'axios';

import { useAuthStore } from '../store/authStore';
import type {
  ReceiptListResponse,
  ReceiptDetailsResponse,
  ProductResponse,
  CategoryResponse,
  SpendingSummaryResponse,
  LoginResponse,
  UserResponse
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export { WS_BASE_URL };

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

// Legacy interfaces for backward compatibility (deprecated, use types/api.ts)
export type SpendingSummary = SpendingSummaryResponse;
export type Receipt = ReceiptResponse;
export type Product = ProductResponse;
export type Category = CategoryResponse;

export const fetchSummary = async (): Promise<SpendingSummaryResponse> => {
  const response = await api.get('/analytics/summary');
  return response.data;
};

export const fetchRecentReceipts = async (limit: number = 5): Promise<ReceiptResponse[]> => {
  const response = await api.get(`/receipts?limit=${limit}`);
  // Backend returns { receipts: [...], total: ... }
  return response.data.receipts;
};

export interface ReceiptListParams {
  skip?: number;
  limit?: number;
  shop_id?: number;
  start_date?: string;
  end_date?: string;
}

export const fetchReceipts = async (params?: ReceiptListParams): Promise<ReceiptListResponse> => {
  const response = await api.get('/receipts', { params });
  return response.data;
};

export interface ProductListParams {
  search?: string;
  category_id?: number;
  skip?: number;
  limit?: number;
}

export const fetchProducts = async (params?: ProductListParams): Promise<ProductResponse[]> => {
  const response = await api.get('/products', { params });
  return response.data;
};

export const fetchCategories = async (): Promise<CategoryResponse[]> => {
  const response = await api.get('/products/categories');
  return response.data;
};

export const getReceipt = async (id: number): Promise<ReceiptDetailsResponse> => {
  const response = await api.get(`/receipts/${id}`);
  return response.data;
};

// Auth
export interface RegisterData {
  email: string;
  password: string;
  full_name?: string;
}

export const login = async (formData: FormData): Promise<LoginResponse> => {
  const response = await api.post('/auth/token', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const register = async (data: RegisterData): Promise<UserResponse> => {
  const response = await api.post('/auth/register', data);
  return response.data;
};

export const fetchMe = async (): Promise<UserResponse> => {
  const response = await api.get('/auth/users/me');
  return response.data;
}

export default api;
