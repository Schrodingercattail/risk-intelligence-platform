/**
 * Risk Score Distribution Histogram Component
 *
 * Displays risk score distribution across buckets with high risk threshold marker.
 */
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts';

interface Bucket {
  range: string;
  count: number;
  percentage: number;
}

interface RiskScoreDistributionChartProps {
  data?: Bucket[];
  highRiskThreshold?: number;
  totalUsers?: number;
}

const mockData: Bucket[] = [
  { range: '0-20', count: 320, percentage: 16.0 },
  { range: '20-40', count: 480, percentage: 24.0 },
  { range: '40-60', count: 560, percentage: 28.0 },
  { range: '60-80', count: 380, percentage: 19.0 },
  { range: '80-100', count: 260, percentage: 13.0 },
];

export default function RiskScoreDistributionChart({
  data = mockData,
  highRiskThreshold = 80,
  totalUsers,
}: RiskScoreDistributionChartProps) {
  // Find which bucket contains the threshold
  const thresholdBucketIndex = data.findIndex((bucket) => {
    const [max] = bucket.range.split('-').map(Number);
    return max === highRiskThreshold;
  });

  return (
    <div className="w-full h-full flex flex-col">
      <div className="flex-1 flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 20, right: 45, left: 45, bottom: 45 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="range"
              stroke="#64748b"
              style={{ fontSize: '12px' }}
              tick={{ fontSize: 12 }}
              interval={0}
              label={{ value: 'Risk Score Range', position: 'insideBottom', offset: -30, style: { fontSize: '11px', fill: '#64748b', textAnchor: 'middle' } }}
            />
            <YAxis
              stroke="#64748b"
              style={{ fontSize: '12px' }}
              tick={{ fontSize: 11 }}
              width={40}
              label={{ value: 'Users', angle: -90, position: 'insideLeft', offset: -5, style: { fontSize: '11px', fill: '#64748b' } }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '8px 12px',
              }}
              formatter={(value: number, _name: string, props: any) => [
                `${value} users (${props.payload.percentage}%)`,
                'Count',
              ]}
              labelFormatter={(label) => `Score: ${label}`}
            />
            {thresholdBucketIndex >= 0 && (
              <ReferenceLine
                x={data[thresholdBucketIndex].range}
                stroke="#ef4444"
                strokeWidth={2}
                strokeDasharray="5 5"
                label={{
                  value: 'High Risk',
                  position: 'insideTopRight',
                  fill: '#ef4444',
                  fontSize: 11,
                }}
              />
            )}
            <Bar
              dataKey="count"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
              maxBarSize={50}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {totalUsers !== undefined && (
        <div className="text-center text-xs text-slate-500 mt-1">
          Total: {totalUsers.toLocaleString()} users
        </div>
      )}
    </div>
  );
}
