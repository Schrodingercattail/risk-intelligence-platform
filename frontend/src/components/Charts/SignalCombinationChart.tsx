/**
 * Signal Combination Breakdown Donut Chart Component
 *
 * Displays the breakdown of signal combinations using a donut chart.
 * Shows 4 categories: ML Only, Rule Only, Graph Only, Multi Signal
 */
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface SignalCombinationChartProps {
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
  { name: 'ML Only', key: 'ml_only', color: '#8b5cf6' },  // Purple
  { name: 'Rule Only', key: 'rule_only', color: '#3b82f6' },  // Blue
  { name: 'Graph Only', key: 'graph_only', color: '#06b6d4' },  // Cyan
  { name: 'Multi Signal', key: 'multi_signal', color: '#f472b6' },  // Pink
];

export default function SignalCombinationChart({ data = mockData }: SignalCombinationChartProps) {
  // Transform data into chart format - always include all categories
  const chartData = CATEGORIES.map(cat => ({
    name: cat.name,
    value: data ? (data as any)[cat.key] ?? 0 : 0,
    color: cat.color
  }));

  const totalAccounts = chartData.reduce((sum, item) => sum + item.value, 0);

  if (totalAccounts === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        No signal data available
      </div>
    );
  }

  // Custom tooltip to show both count and percentage
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const entry = payload[0].payload;
      const percentage = ((entry.value / totalAccounts) * 100).toFixed(1);
      return (
        <div style={{
          backgroundColor: 'white',
          border: '1px solid #e2e8f0',
          borderRadius: '6px',
          padding: '8px 12px',
          fontSize: '12px',
        }}>
          <div style={{ fontWeight: '500', marginBottom: '4px', color: entry.color }}>
            {entry.name}
          </div>
          <div style={{ color: '#64748b' }}>
            <span style={{ fontWeight: '500', color: '#334155' }}>{entry.value}</span> accounts
          </div>
          <div style={{ color: '#64748b' }}>
            <span style={{ fontWeight: '500', color: '#334155' }}>{percentage}%</span> of total
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: '250px', position: 'relative' }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
          <Pie
            data={chartData}
            cx="50%"
            cy="42%"
            innerRadius={45}
            outerRadius={75}
            paddingAngle={2}
            dataKey="value"
            label={(entry) => {
              if (entry.value === 0) return '';
              const percentage = ((entry.value / totalAccounts) * 100).toFixed(1);
              return `${percentage}%`;
            }}
            labelLine={false}
            style={{ fontSize: '11px' }}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} stroke={entry.value === 0 ? '#e2e8f0' : undefined} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="bottom"
            height={55}
            iconType="circle"
            formatter={(value) => (
              <span style={{ color: '#475569', fontSize: '11px', fontWeight: '500' }}>
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
