import { useEffect, useState } from 'react';
import { useAnalyticsStore } from '@/store/analyticsStore';
import { SpendingChart } from '@/components/SpendingChart';
import { CategoryPieChart } from '@/components/CategoryPieChart';
import { ShopBarChart } from '@/components/ShopBarChart';
import { LoadingSpinner } from '@/components/ui';

export function Analytics() {
    const {
        spendingTrend,
        categoryBreakdown,
        shopComparison,
        monthlyStats,
        loading,
        error,
        fetchAnalyticsData
    } = useAnalyticsStore();

    const [days, setDays] = useState(30);

    useEffect(() => {
        fetchAnalyticsData(days);
    }, [fetchAnalyticsData, days]);

    // Handle range change
    const ranges = [30, 60, 90];

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
            <div className="max-w-7xl mx-auto">
                <div className="flex flex-col md:flex-row md:items-center justify-between mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                        Analytics & Reports
                    </h1>
                    <div className="mt-4 md:mt-0 bg-white dark:bg-gray-800 rounded-lg shadow p-1 inline-flex">
                        {ranges.map((range) => (
                            <button
                                key={range}
                                onClick={() => setDays(range)}
                                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${days === range
                                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200'
                                        : 'text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
                                    }`}
                            >
                                {range} Days
                            </button>
                        ))}
                    </div>
                </div>

                {loading && !spendingTrend.length ? (
                    <div className="flex h-64 items-center justify-center">
                        <LoadingSpinner size="lg" />
                    </div>
                ) : error ? (
                    <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 mb-8">
                        <p className="text-red-700 dark:text-red-300">{error}</p>
                    </div>
                ) : (
                    <div className="space-y-8">
                        {/* Main Trend Chart */}
                        <SpendingChart data={spendingTrend} days={days} />

                        {/* Two column grid for Pie and Bar charts */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <CategoryPieChart data={categoryBreakdown} />
                            <ShopBarChart data={shopComparison} />
                        </div>

                        {/* Monthly Stats Table */}
                        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                                    Monthly Breakdown
                                </h3>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                    <thead className="bg-gray-50 dark:bg-gray-700">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Month
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Receipts
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Total Spending
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Avg / Receipt
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                        {monthlyStats.map((stat, idx) => (
                                            <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                                                    {stat.month}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                                    {stat.receipts_count}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                                                    {stat.total.toFixed(2)} PLN
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                                    {stat.avg_receipt.toFixed(2)} PLN
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
