/**
 * API client for ParagonOCR Web Edition.
 * 
 * Handles all HTTP requests to the backend API with proper error handling.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
          // Server responded with error
          const message = (error.response.data as any)?.detail || error.message;
          throw new Error(message);
        } else if (error.request) {
          // Request made but no response
          throw new Error('No response from server. Check if backend is running.');
        } else {
          // Error setting up request
          throw new Error(error.message);
        }
      }
    );
  }

  /**
   * Upload a receipt file.
   */
  async uploadReceipt(file: File): Promise<{ receipt_id: number; status: string; message: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post('/api/receipts/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  /**
   * Get list of receipts.
   */
  async getReceipts(params?: {
    skip?: number;
    limit?: number;
    shop_id?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<{
    receipts: Array<{
      id: number;
      shop: string | null;
      purchase_date: string | null;
      purchase_time: string | null;
      total_amount: number;
      items_count: number;
      created_at: string | null;
    }>;
    total: number;
    skip: number;
    limit: number;
  }> {
    const response = await this.client.get('/api/receipts', { params });
    return response.data;
  }

  /**
   * Get receipt details by ID.
   */
  async getReceipt(receiptId: number): Promise<{
    id: number;
    shop: {
      id: number | null;
      name: string | null;
      location: string | null;
    };
    purchase_date: string | null;
    purchase_time: string | null;
    total_amount: number;
    subtotal: number | null;
    tax: number | null;
    items: Array<{
      id: number;
      product: {
        id: number | null;
        name: string | null;
      };
      raw_name: string;
      quantity: number;
      unit: string | null;
      unit_price: number | null;
      total_price: number;
      discount: number | null;
    }>;
    source_file: string;
    created_at: string | null;
  }> {
    const response = await this.client.get(`/api/receipts/${receiptId}`);
    return response.data;
  }
}

export const apiClient = new ApiClient();

