/**
 * Detection Pattern Distribution Chart Component
 *
 * Displays signal combination breakdown as a horizontal stacked bar chart.
 * Shows 4 categories: ML Only, Rule Only, Graph Only, Multi Signal
 */
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface DetectionPatternChartProps {
  data?: {
    ml_only: number;
    rule_only: number;
    graph_only: number;
    multi_signal: number;
  } | null;
}

const mockData = {
  ml_only: 120,
  rule_only: 80,
  graph_only: 50,
  multi_signal: 350,
};

const CATEGORIES = [
  { name: 'ML Only', key: 'ml_only', color: '#8b5cf6' },
  { name: 'Rule Only', key: 'rule_only', color: '#3b82f6' },
  { name: 'Graph Only', key: 'graph_only', color: '#06b6d4' },
  { name: 'Multi Signal', key: 'multi_signal', color: '#f472b6' },
];

export default function DetectionPatternChart({ data = mockData }: DetectionPatternChartProps) {
  // Transform data into chart format
  const chartData = CATEGORIES.map(cat => ({
    name: cat.name,
    value: data ? (data as any)[cat.key] ?? 0 : 0,
    color: cat.color
  })); // Always show all categories, even with 0 values

  const totalCases = chartData.reduce((sum, item) => sum + item.value, 0);

  if (totalCases === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        No pattern data available
      </div>
    );
  }

  // Add percentage to each item
  const dataWithPercentage = chartData.map(item => ({
    ...item,
    percentage: ((item.value / totalCases) * 100).toFixed(1),
  }));

  // Custom tooltip
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
          <div style={{ fontWeight: '500', marginBottom: '4px', color: data.color }}>
            {data.name}
          </div>
          <div style={{ color: '#64748b' }}>
            <span style={{ fontWeight: '500', color: '#334155' }}>{data.value}</span> accounts
          </div>
          <div style={{ color: '#64748b' }}>
            <span style={{ fontWeight: '500', color: '#334155' }}>{data.percentage}%</span> of total
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
          data={dataWithPercentage}
          layout="vertical"
          margin={{ top: 20, right: 60, left: 10, bottom: 20 }}
          maxBarSize={30}
        >
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
            width={100}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar
            dataKey="percentage"
            radius={[0, 4, 4, 0]}
          >
            {dataWithPercentage.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
