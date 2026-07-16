/**
 * Risk Trend Chart Component
 *
 * Displays risk activity trend from uploaded dataset.
 */
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface RiskTrendChartProps {
  data?: Array<{ date: string; events: number }>;
}

// Mock data using dataset-based time periods instead of relative dates
const mockData = [
  { date: 'Jan-Mar 2024', events: 142 },
  { date: 'Apr-Jun 2024', events: 158 },
  { date: 'Jul-Sep 2024', events: 135 },
  { date: 'Oct-Dec 2024', events: 167 },
  { date: 'Jan-Mar 2025', events: 151 },
  { date: 'Apr-Jun 2025', events: 173 },
  { date: 'Jul-Sep 2025', events: 148 },
];


export default function RiskTrendChart({ data = mockData }: RiskTrendChartProps) {
  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="date"
            stroke="#64748b"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#64748b"
            style={{ fontSize: '12px' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '8px 12px',
            }}
            formatter={(value: any) => [value, 'Risk Events']}
          />
          <Line
            type="monotone"
            dataKey="events"
            stroke="#2563eb"
            strokeWidth={2}
            dot={{ fill: '#2563eb', r: 4 }}
            activeDot={{ r: 6, stroke: '#2563eb', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
