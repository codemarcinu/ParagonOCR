import { create } from 'zustand';
import apiClient from '@/lib/api';

interface CategoryData {
    name: string;
    value: number;
    color?: string;
}

interface DailySpending {
    date: string;
    amount: number;
}

interface MonthlyStats {
    month: string;
    total: number;
    receipts_count: number;
    avg_receipt: number;
}

interface AnalyticsStore {
    spendingTrend: DailySpending[];
    categoryBreakdown: CategoryData[];
    shopComparison: CategoryData[];
    monthlyStats: MonthlyStats[];
    loading: boolean;
    error: string | null;

    fetchAnalyticsData: (days?: number) => Promise<void>;
}

export const useAnalyticsStore = create<AnalyticsStore>((set) => ({
    spendingTrend: [],
    categoryBreakdown: [],
    shopComparison: [],
    monthlyStats: [],
    loading: false,
    error: null,

    fetchAnalyticsData: async (days = 30) => {
        set({ loading: true, error: null });
        try {
            // In a real app, these might be separate parallel calls or one aggregated call
            // For MVP, simulating aggregation or fetching from specific endpoints
            // Assuming endpoints: /api/analytics/trend, /api/analytics/categories, etc.

            const [trendRes, catRes, shopRes, monthlyRes] = await Promise.all([
                apiClient.get('/analytics/trend', { params: { days } }),
                apiClient.get('/analytics/categories', { params: { days } }),
                apiClient.get('/analytics/shops', { params: { days } }),
                apiClient.get('/analytics/monthly')
            ]);

            set({
                spendingTrend: trendRes.data,
                categoryBreakdown: catRes.data,
                shopComparison: shopRes.data,
                monthlyStats: monthlyRes.data,
                loading: false
            });
        } catch (error) {
            console.error(error);
            // Fallback to sample data if backend not fully ready for all chart endpoints yet?
            // Or just show error.
            set({
                error: error instanceof Error ? error.message : 'Failed to fetch analytics',
                loading: false
            });
        }
    }
}));
