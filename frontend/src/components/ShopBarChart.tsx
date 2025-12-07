import { useMemo } from 'react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell
} from 'recharts';

interface ShopData {
    name: string;
    value: number;
}

interface ShopBarChartProps {
    data: ShopData[];
}

export function ShopBarChart({ data }: ShopBarChartProps) {
    const sortedData = useMemo(() => {
        return [...data].sort((a, b) => b.value - a.value).slice(0, 10); // Top 10 shops
    }, [data]);

    return (
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow h-80">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Top Shops by Spending
            </h3>
            <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                        data={sortedData}
                        layout="vertical"
                        margin={{
                            top: 5,
                            right: 30,
                            left: 20,
                            bottom: 5,
                        }}
                    >
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                        <XAxis type="number" stroke="#9ca3af" tickFormatter={(value) => `${value}`} />
                        <YAxis
                            type="category"
                            dataKey="name"
                            stroke="#9ca3af"
                            width={100}
                            tick={{ fontSize: 12 }}
                        />
                        <Tooltip
                            cursor={{ fill: 'transparent' }}
                            contentStyle={{ backgroundColor: '#fff', borderRadius: '0.5rem', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                            formatter={(value: number) => [`${value.toFixed(2)} PLN`, 'Total']}
                        />
                        <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]}>
                            {sortedData.map((_, index) => (
                                <Cell key={`cell-${index}`} fill={index < 3 ? '#2563eb' : '#60a5fa'} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
