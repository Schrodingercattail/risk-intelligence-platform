/**
 * Risk Distribution Chart Component
 *
 * Displays risk level distribution pie chart.
 */
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface RiskDistributionChartProps {
  data?: Array<{ name: string; value: number; color: string }>;
}

const mockData = [
  { name: 'Critical', value: 32, color: '#ef4444' },
  { name: 'High', value: 176, color: '#f97316' },
  { name: 'Medium', value: 390, color: '#eab308' },
  { name: 'Low', value: 845, color: '#22c55e' },
];

export default function RiskDistributionChart({ data = mockData }: RiskDistributionChartProps) {
  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '8px 12px',
            }}
          />
          <Legend 
            verticalAlign="bottom" 
            height={36}
            iconType="circle"
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
