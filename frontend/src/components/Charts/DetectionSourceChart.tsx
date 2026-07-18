/**
 * Detection Source Analysis Chart Component
 *
 * Displays detection source distribution bar chart.
 */
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

interface DetectionSourceChartProps {
  data?: Array<{ name: string; value: number; percentage: number; color: string }>;
}

const mockData = [
  { name: 'Rule Engine', value: 45, percentage: 30, color: '#3b82f6' },
  { name: 'LightGBM', value: 80, percentage: 55, color: '#8b5cf6' },
  { name: 'Graph Network', value: 25, percentage: 15, color: '#06b6d4' },
];

export default function DetectionSourceChart({ data = mockData }: DetectionSourceChartProps) {
  console.log('=== DetectionSourceChart Render ===');
  console.log('Props received:', { data });
  console.log('Data length:', data?.length);
  console.log('First item:', data?.[0]);
  console.log('All data items:', data);

  return (
    <div style={{ width: '100%', height: '250px', position: 'relative' }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 20, right: 40, left: 10, bottom: 20 }}
          maxBarSize={40}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={true} vertical={false} />
          <XAxis
            type="number"
            stroke="#64748b"
            tickFormatter={(value) => `${value}%`}
            domain={[0, 100]}
            tick={{ fontSize: 11 }}
            ticks={[0, 25, 50, 75, 100]}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#64748b"
            tick={{ fontSize: 12 }}
            width={120}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              padding: '8px 12px',
            }}
            formatter={(value: any) => [`${value}%`, 'Detection Rate']}
            labelFormatter={(label) => label}
          />
          <Bar
            dataKey="percentage"
            fill="#3b82f6"
            radius={[0, 4, 4, 0]}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
