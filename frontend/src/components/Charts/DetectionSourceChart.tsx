/**
 * Detection Source Chart Component
 *
 * Displays detection source distribution bar chart.
 */
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

interface DetectionSourceChartProps {
  data?: Array<{ name: string; value: number; percentage: number; color: string }>;
}

const mockData = [
  { name: 'Rule Engine', value: 45, percentage: 45, color: '#3b82f6' },
  { name: 'ML Model', value: 35, percentage: 35, color: '#8b5cf6' },
  { name: 'Graph Network', value: 20, percentage: 20, color: '#06b6d4' },
];

export default function DetectionSourceChart({ data = mockData }: DetectionSourceChartProps) {
  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="95%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 50, left: 50, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            type="number"
            stroke="#64748b"
            style={{ fontSize: '12px' }}
            tickFormatter={(value) => `${value}%`}
            domain={[0, 100]}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#64748b"
            style={{ fontSize: '12px' }}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '8px 12px',
            }}
            formatter={(value: any) => [`${value}%`, 'Detection Rate']}
          />
          <Bar dataKey="percentage" maxBarSize={35} radius={[0, 6, 6, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
