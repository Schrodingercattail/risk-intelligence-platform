/**
 * Risk Score Analytics Card Component
 *
 * Displays risk score statistics with visual indicators.
 */

interface RiskScoreStatistics {
  average: number;
  threshold: number;
  maximum: number;
}

interface RiskScoreAnalyticsCardProps {
  statistics?: RiskScoreStatistics;
}

const mockStatistics: RiskScoreStatistics = {
  average: 52.3,
  threshold: 70.0,
  maximum: 98.2,
};

// Helper to calculate score position percentage for bar visualization
const getScorePercentage = (score: number, maxScore = 100) => {
  return Math.min((score / maxScore) * 100, 100);
};

export default function RiskScoreAnalyticsCard({
  statistics = mockStatistics,
}: RiskScoreAnalyticsCardProps) {
  const { average, threshold, maximum } = statistics;

  const metrics = [
    {
      label: 'Average Risk Score',
      value: average,
      description: 'Mean risk score across all analyzed users',
      icon: 'μ',
      isStatistic: true,
    },
    {
      label: 'High Risk Threshold',
      value: threshold,
      description: 'Score threshold used to classify high-risk users',
      icon: '!',
      isThreshold: true,
    },
    {
      label: 'Maximum Risk Score',
      value: maximum,
      description: 'Highest risk score among analyzed users',
      icon: '↑',
    },
  ];

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 h-[300px] flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-700">Risk Score Analytics</h3>
      </div>
      <p className="text-xs text-slate-500 mb-4">Overview of model scoring range and risk threshold positioning</p>

      <div className="flex-1 flex flex-col justify-center space-y-2 overflow-visible">
        {metrics.map((metric) => (
          <div key={metric.label} className="space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`w-5 h-5 rounded flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                  metric.isThreshold ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-600'
                }`}>
                  {metric.icon}
                </div>
                <span className="text-xs text-slate-600 truncate">{metric.label}</span>
              </div>
              <span className={`text-sm font-semibold flex-shrink-0 ${
                metric.isThreshold ? 'text-red-600' : 'text-slate-900'
              }`}>
                {metric.value.toFixed(2)}
              </span>
            </div>
            {/* Bar visualization */}
            <div className="relative h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`absolute top-0 left-0 h-full rounded-full transition-all ${
                  metric.isThreshold ? 'bg-red-400' : 'bg-blue-400'
                }`}
                style={{ width: `${getScorePercentage(metric.value)}%` }}
              />
              {/* Threshold marker */}
              {!metric.isThreshold && metric.value < threshold && (
                <div
                  className="absolute top-0 h-full w-0.5 bg-red-400"
                  style={{ left: `${getScorePercentage(threshold)}%` }}
                />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-2 pt-2 border-t border-slate-100 flex-shrink-0">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-blue-400" />
          <span className="text-xs text-slate-500">Score value</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-red-400" />
          <span className="text-xs text-slate-500">High risk threshold</span>
        </div>
      </div>
    </div>
  );
}
