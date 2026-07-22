/**
 * Detection Attribution Chart Component
 *
 * Displays detection source contribution as a horizontal bar chart.
 * Shows how many risky accounts were identified by each detection method.
 */
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

interface DetectionSourceChartProps {
  data?: Array<{ name: string; value: number; percentage: number; color: string }>;
}

const mockData = [
  { name: 'LightGBM Model', value: 400, percentage: 66.7, color: '#8b5cf6' },
  { name: 'Rule Engine', value: 350, percentage: 58.3, color: '#3b82f6' },
  { name: 'Graph Network', value: 250, percentage: 41.7, color: '#06b6d4' },
];

export default function DetectionSourceChart({ data = mockData }: DetectionSourceChartProps) {
  // Custom tooltip to show both account count and percentage
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div style={{
          backgroundColor: 'white',
          border: '1px solid #e2e8f0',
          borderRadius: '6px',
          padding: '8px 12px',
          fontSize: '12px',
        }}>
          <div style={{ fontWeight: '500', marginBottom: '4px' }}>{data.name}</div>
          <div style={{ color: '#64748b' }}>
            <span style={{ fontWeight: '500', color: '#334155' }}>{data.value}</span> accounts
          </div>
          <div style={{ color: '#64748b' }}>
            <span style={{ fontWeight: '500', color: '#334155' }}>{data.percentage}%</span> contribution
          </div>
        </div>
      );
    }
    return null;
  };

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
          <Tooltip content={<CustomTooltip />} />
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
