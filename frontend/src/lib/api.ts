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

export const fetchSummary = async (): Promise<SpendingSummary> => {
  const response = await api.get('/analytics/summary');
  return response.data;
};

export const fetchRecentReceipts = async (limit: number = 5): Promise<Receipt[]> => {
  const response = await api.get(`/receipts?limit=${limit}`);
  return response.data;
};

export default api;
