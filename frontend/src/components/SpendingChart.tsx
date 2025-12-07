import { useMemo } from 'react';
import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area
} from 'recharts';

interface SpendingData {
    date: string;
    amount: number;
}

interface SpendingChartProps {
    data: SpendingData[];
    days?: number;
}

export function SpendingChart({ data, days = 30 }: SpendingChartProps) {
    // Format data for chart if needed, or assume pre-formatted
    // Sort by date
    const chartData = useMemo(() => {
        return [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    }, [data]);

    return (
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow h-80">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Trend Wydatków ({days} dni)
            </h3>
            <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                        data={chartData}
                        margin={{
                            top: 5,
                            right: 20,
                            left: 0,
                            bottom: 5,
                        }}
                    >
                        <defs>
                            <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                        <XAxis
                            dataKey="date"
                            tickFormatter={(date) => new Date(date).toLocaleDateString('pl-PL', { month: 'short', day: 'numeric' })}
                            stroke="#9ca3af"
                            tick={{ fontSize: 12 }}
                        />
                        <YAxis
                            stroke="#9ca3af"
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => `${value} PLN`}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#fff', borderRadius: '0.5rem', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                            formatter={(value: number) => [`${value.toFixed(2)} PLN`, 'Kwota']}
                            labelFormatter={(label) => new Date(label).toLocaleDateString('pl-PL')}
                        />
                        <Area
                            type="monotone"
                            dataKey="amount"
                            stroke="#3b82f6"
                            fillOpacity={1}
                            fill="url(#colorAmount)"
                            strokeWidth={2}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
