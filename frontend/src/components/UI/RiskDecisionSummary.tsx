/**
 * RiskDecisionSummary Component
 *
 * Lightweight display of risk recommendations for key accounts.
 * Shows account, risk score, recommended action, and risk signals.
 * MVP-appropriate: displays system-generated recommendations, not automated decisions.
 */

export interface RiskRecommendation {
  account: string;
  riskScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  recommendedAction: string;
  riskSignals: string[];
  generatedTime: string;
}

interface RiskDecisionSummaryProps {
  recommendations?: RiskRecommendation[];
}

const getRiskLevelColor = (level: string) => {
  switch (level) {
    case 'LOW':
      return 'bg-green-50 text-green-800 border-green-200';
    case 'MEDIUM':
      return 'bg-yellow-50 text-yellow-800 border-yellow-200';
    case 'HIGH':
      return 'bg-orange-50 text-orange-800 border-orange-200';
    case 'CRITICAL':
      return 'bg-red-50 text-red-900 border-red-300';
    default:
      return 'bg-slate-50 text-slate-800 border-slate-200';
  }
};

const getActionColor = (action: string) => {
  if (action.includes('Freeze') || action.includes('Block')) {
    return 'text-red-700 bg-red-50 border-red-200';
  }
  if (action.includes('Review') || action.includes('Investigate')) {
    return 'text-orange-700 bg-orange-50 border-orange-200';
  }
  if (action.includes('Monitor')) {
    return 'text-blue-700 bg-blue-50 border-blue-200';
  }
  return 'text-green-700 bg-green-50 border-green-200';
};

// Mock risk recommendations
const mockRecommendations: RiskRecommendation[] = [
  {
    account: 'user_1248',
    riskScore: 94,
    riskLevel: 'CRITICAL',
    recommendedAction: 'Review withdrawal activity',
    riskSignals: ['Shared Device', 'Abnormal Location'],
    generatedTime: 'Jul 15 10:32',
  },
  {
    account: 'user_0847',
    riskScore: 87,
    riskLevel: 'CRITICAL',
    recommendedAction: 'Investigate account linkage',
    riskSignals: ['Account Linkage', 'Suspicious Pattern'],
    generatedTime: 'Jul 15 09:45',
  },
  {
    account: 'user_3456',
    riskScore: 72,
    riskLevel: 'HIGH',
    recommendedAction: 'Enhanced monitoring recommended',
    riskSignals: ['Transaction Velocity'],
    generatedTime: 'Jul 15 08:30',
  },
];

export default function RiskDecisionSummary({ recommendations = mockRecommendations }: RiskDecisionSummaryProps) {
  return (
    <div className="space-y-5">
      {recommendations.map((rec, index) => (
        <div
          key={index}
          className="bg-white rounded-lg border border-slate-200 p-6 hover:shadow-sm transition-shadow"
        >
          {/* Header: Account ID and Risk Level Badge */}
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <span className="font-mono text-base font-semibold text-slate-900">
                {rec.account}
              </span>
              <span className={`px-3 py-1 text-sm font-semibold rounded-full border ${getRiskLevelColor(rec.riskLevel)}`}>
                {rec.riskLevel} RISK
              </span>
            </div>
            <div className="text-xs text-slate-400">
              Generated: {rec.generatedTime}
            </div>
          </div>

          {/* Risk Score */}
          <div className="mb-5">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Risk Score</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-3xl font-bold text-slate-900">{rec.riskScore}</span>
              <span className="text-sm text-slate-500">/100</span>
            </div>
          </div>

          {/* Recommended Action */}
          <div className="mb-4">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Recommended Action</span>
            <div className="mt-1">
              <span className={`inline-block px-3 py-1.5 text-sm font-medium rounded-lg border ${getActionColor(rec.recommendedAction)}`}>
                {rec.recommendedAction}
              </span>
            </div>
          </div>

          {/* Risk Signals */}
          <div>
            <span className="text-xs text-slate-500 uppercase tracking-wider">Risk Signals</span>
            <div className="flex flex-wrap gap-2 mt-2">
              {rec.riskSignals.map((signal, signalIndex) => (
                <span
                  key={signalIndex}
                  className="inline-flex items-center px-3 py-1 text-sm font-medium rounded-lg bg-slate-100 text-slate-700 border border-slate-200"
                >
                  • {signal}
                </span>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
