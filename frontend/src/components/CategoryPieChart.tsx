import { useMemo } from 'react';
import {
    PieChart,
    Pie,
    Cell,
    Tooltip,
    ResponsiveContainer,
    Legend
} from 'recharts';

interface CategoryData {
    name: string;
    value: number;
    color?: string;
}

interface CategoryPieChartProps {
    data: CategoryData[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658'];

export function CategoryPieChart({ data }: CategoryPieChartProps) {
    const chartData = useMemo(() => {
        return data.map((item, index) => ({
            ...item,
            color: item.color || COLORS[index % COLORS.length]
        }));
    }, [data]);

    return (
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow h-80">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Spending by Category
            </h3>
            <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={chartData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey="value"
                            label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                        >
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Pie>
                        <Tooltip
                            formatter={(value: number) => [`${value.toFixed(2)} PLN`, 'Amount']}
                            contentStyle={{ backgroundColor: '#fff', borderRadius: '0.5rem', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                        />
                        <Legend layout="vertical" align="right" verticalAlign="middle" />
                    </PieChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
