/**
 * Investigation Workspace Page
 *
 * Risk analyst investigation interface for detailed case analysis.
 * Two-panel layout: Investigation Queue (left) + Case Detail (right).
 *
 * MVP: Risk investigation workspace for analyst decision support.
 * NOT a Case Management System - no workflow or status tracking.
 */
import { useState, useMemo } from 'react';

interface InvestigationCase {
  case_id: string;
  user_id: string;
  risk_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  account_age: string;
  total_volume: string;
  risk_factors: Array<{ name: string; severity: 'critical' | 'high' | 'medium' | 'low' }>;
  recommended_action: string;
  created_at: string;
  risk_explanation: {
    summary: string;
    contributing_factors: string[];
    signal_analysis: string;
    analyst_guidance: string;
  };
}

// Mock investigation cases - risk candidates from uploaded dataset
const mockCases: InvestigationCase[] = [
  {
    case_id: 'CASE-10291',
    user_id: 'user_1248',
    risk_score: 94,
    risk_level: 'CRITICAL',
    account_age: '47 days',
    total_volume: '$124,830',
    risk_factors: [
      { name: 'Shared Device with 3 high-risk users', severity: 'critical' },
      { name: 'Abnormal Location Login', severity: 'high' },
      { name: 'Rapid Withdrawal Pattern', severity: 'critical' },
    ],
    recommended_action: 'Freeze Withdrawal',
    created_at: '2025-01-15T10:16:00Z',
    risk_explanation: {
      summary: 'This account received a critical risk score (94/100) due to multiple high-severity signals detected within a short timeframe. The combination of device-sharing with known high-risk users, unusual login location, and rapid withdrawal pattern indicates potential account compromise or fraudulent activity.',
      contributing_factors: [
        'Device shared with 3 accounts having risk scores >80',
        'Login from previously unseen location',
        '5 withdrawals completed within 8 minutes',
        'Account age only 47 days with high transaction velocity'
      ],
      signal_analysis: 'The detected signals are strongly correlated with fraudulent patterns in the training dataset. Device-sharing with high-risk users has the highest feature importance (0.34), followed by rapid withdrawal velocity (0.28) and location anomaly (0.22). The confluence of these signals within a short timeframe significantly elevates risk.',
      analyst_guidance: 'Given the critical risk level and multiple high-severity signals, immediate review is recommended. Verify account ownership, review withdrawal destinations, and consider temporary withdrawal suspension until investigation completes.'
    },
  },
  {
    case_id: 'CASE-10290',
    user_id: 'user_0847',
    risk_score: 87,
    risk_level: 'CRITICAL',
    account_age: '23 days',
    total_volume: '$67,420',
    risk_factors: [
      { name: 'Account Linkage Detected', severity: 'high' },
      { name: 'Suspicious Trading Pattern', severity: 'high' },
    ],
    recommended_action: 'Manual Review',
    created_at: '2025-01-15T09:45:00Z',
    risk_explanation: {
      summary: 'This account received a critical risk score (87/100) primarily due to graph network analysis revealing connections to known suspicious accounts. The account linkage combined with unusual trading patterns suggests potential coordinated activity.',
      contributing_factors: [
        'Graph network identified 2 direct connections to flagged accounts',
        'Trading volume 4x higher than account age peer group',
        'Account age only 23 days with elevated activity levels',
        'Pattern similarity to known fraud cases (78%)'
      ],
      signal_analysis: 'Network linkage is the primary risk driver (feature importance 0.41). Trading pattern anomaly contributed significantly (0.33). The combination of new account establishment followed by rapid high-volume activity matches historical fraud patterns.',
      analyst_guidance: 'Review the linked accounts in the graph network to understand potential coordinated activity. Verify trading legitimacy and consider enhanced monitoring for connected accounts.'
    },
  },
  {
    case_id: 'CASE-10289',
    user_id: 'user_1923',
    risk_score: 82,
    risk_level: 'HIGH',
    account_age: '156 days',
    total_volume: '$234,100',
    risk_factors: [
      { name: 'Transaction Velocity Anomaly', severity: 'medium' },
      { name: 'New Device Login', severity: 'medium' },
    ],
    recommended_action: 'Enhanced Monitoring',
    created_at: '2025-01-15T08:20:00Z',
    risk_explanation: {
      summary: 'This account received a high risk score (82/100) due to elevated transaction velocity combined with new device access. While individual signals are moderate, their combination warrants attention.',
      contributing_factors: [
        'Transaction velocity 3x higher than historical baseline',
        'Login from previously unseen device fingerprint',
        'Velocity spike occurred immediately after new device login',
        'Account age 156 days - established but pattern deviation detected'
      ],
      signal_analysis: 'Transaction velocity anomaly is the primary contributor (feature importance 0.38). New device login on an established account is also significant (0.29). The temporal correlation between these signals increases risk weight.',
      analyst_guidance: 'Enhanced monitoring recommended. Verify the legitimacy of the new device login. Monitor transaction patterns for the next 7-14 days for further anomalies.'
    },
  },
  {
    case_id: 'CASE-10288',
    user_id: 'user_3456',
    risk_score: 78,
    risk_level: 'HIGH',
    account_age: '89 days',
    total_volume: '$156,780',
    risk_factors: [
      { name: 'Device Fingerprint Mismatch', severity: 'high' },
      { name: 'Multiple Accounts', severity: 'medium' },
    ],
    recommended_action: 'Enhanced Monitoring',
    created_at: '2025-01-15T07:30:00Z',
    risk_explanation: {
      summary: 'This account received a high risk score (78/100) primarily due to device fingerprint inconsistency and potential account linkage. The device change combined with multi-account indicators suggests investigation is warranted.',
      contributing_factors: [
        'Device fingerprint changed from previous sessions',
        'IP address associated with 2 other accounts',
        'Account age 89 days with moderate activity levels',
        'Device change coincided with increased transaction volume'
      ],
      signal_analysis: 'Device fingerprint mismatch is the primary risk factor (feature importance 0.35). Multi-account association from same IP contributed (0.26). The timing correlation with activity increase elevates concern.',
      analyst_guidance: 'Verify device ownership and user identity. Review the other accounts associated with the same IP address. Consider device re-verification.'
    },
  },
  {
    case_id: 'CASE-10287',
    user_id: 'user_7890',
    risk_score: 75,
    risk_level: 'HIGH',
    account_age: '34 days',
    total_volume: '$89,450',
    risk_factors: [
      { name: 'Unusual Trading Pattern', severity: 'medium' },
    ],
    recommended_action: 'Monitor',
    created_at: '2025-01-15T06:45:00Z',
    risk_explanation: {
      summary: 'This account received a high risk score (75/100) due to unusual trading patterns detected by the ML model. The pattern deviation from established behavior warrants monitoring.',
      contributing_factors: [
        'Trading pattern 67% similar to historical fraud cases',
        'Account age 34 days with accelerating activity',
        'Unusual timing of trades (outside normal hours)',
        'Volume concentration in specific instruments'
      ],
      signal_analysis: 'Pattern similarity to known fraud cases is the main driver (feature importance 0.42). The combination of new account status and anomalous timing patterns increases risk weight.',
      analyst_guidance: 'Monitor trading patterns for continued anomalies. Verify user understanding of trading risks. No immediate action required but continued monitoring advised.'
    },
  },
  {
    case_id: 'CASE-10286',
    user_id: 'user_4567',
    risk_score: 68,
    risk_level: 'MEDIUM',
    account_age: '201 days',
    total_volume: '$312,000',
    risk_factors: [
      { name: 'New Device Login', severity: 'low' },
    ],
    recommended_action: 'Monitor',
    created_at: '2025-01-15T05:20:00Z',
    risk_explanation: {
      summary: 'This account received a medium risk score (68/100) due to a new device login on an established account. While device changes are common, the established account status with significant volume warrants noting.',
      contributing_factors: [
        'Login from previously unseen device',
        'Account age 201 days - established user',
        'No other risk signals detected',
        'Transaction volume within normal range for account age'
      ],
      signal_analysis: 'New device login on an established account has low risk weight (feature importance 0.15). Absence of other contributing signals keeps overall risk at medium level.',
      analyst_guidance: 'Standard monitoring sufficient. Device change noted for context. No immediate action required.'
    },
  },
];

export default function Investigation() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCase, setSelectedCase] = useState<InvestigationCase | null>(null);

  // Sort by risk score (descending) and filter by search
  const sortedCases = useMemo(() => {
    return [...mockCases].sort((a, b) => b.risk_score - a.risk_score);
  }, []);

  const filteredCases = useMemo(() => {
    if (!searchQuery) return sortedCases;
    const query = searchQuery.toLowerCase();
    return sortedCases.filter(
      (c) =>
        c.case_id.toLowerCase().includes(query) ||
        c.user_id.toLowerCase().includes(query)
    );
  }, [sortedCases, searchQuery]);

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'LOW':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'CRITICAL':
        return 'bg-red-100 text-red-900 border-red-300';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-50 border-red-200 text-red-900';
      case 'high':
        return 'bg-orange-50 border-orange-200 text-orange-900';
      case 'medium':
        return 'bg-yellow-50 border-yellow-200 text-yellow-900';
      default:
        return 'bg-slate-50 border-slate-200 text-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Investigation Workspace</h1>
        <p className="text-sm text-slate-600 mt-1">
          Risk investigation and analysis workspace for risk analysts
        </p>
      </div>

      {/* Search Section */}
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <div className="flex gap-4 items-center">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search by Case ID or User ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Search filters cases from the current uploaded dataset
        </p>
      </div>

      {/* Two-Panel Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel: Investigation Queue */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg border border-slate-200">
            <div className="p-4 border-b border-slate-200">
              <h2 className="text-lg font-semibold text-slate-900">Investigation Queue</h2>
              <p className="text-xs text-slate-600 mt-1">
                {sortedCases.length} cases requiring analyst review • Sorted by risk score
              </p>
            </div>
            <div className="divide-y divide-slate-200 max-h-[600px] overflow-y-auto">
              {filteredCases.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No cases found matching "{searchQuery}"
                </div>
              ) : (
                filteredCases.map((caseItem) => (
                  <div
                    key={caseItem.case_id}
                    onClick={() => setSelectedCase(caseItem)}
                    className={`p-4 cursor-pointer transition-colors ${
                      selectedCase?.case_id === caseItem.case_id
                        ? 'bg-blue-50 border-l-4 border-l-blue-600'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900">{caseItem.case_id}</span>
                        {caseItem.risk_level === 'CRITICAL' && <span className="text-red-500">★</span>}
                      </div>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getRiskLevelColor(caseItem.risk_level)}`}>
                        {caseItem.risk_level}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-slate-600">{caseItem.user_id}</span>
                      <span className="font-bold text-slate-900">{caseItem.risk_score}/100</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {caseItem.recommended_action}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Panel: Case Detail */}
        <div className="lg:col-span-2">
          {selectedCase ? (
            <div className="space-y-6">
              {/* Case Header */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <h2 className="text-xl font-semibold text-slate-900">{selectedCase.case_id}</h2>
                      <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${getRiskLevelColor(selectedCase.risk_level)}`}>
                        {selectedCase.risk_level}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600">
                      User ID: <span className="font-mono font-medium text-slate-900">{selectedCase.user_id}</span>
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-red-600">{selectedCase.risk_score}</div>
                    <div className="text-xs text-slate-500">Risk Score /100</div>
                  </div>
                </div>
              </div>

              {/* Risk Profile Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Account Information */}
                <div className="bg-white rounded-lg border border-slate-200 p-4">
                  <h3 className="text-sm font-semibold text-slate-900 mb-3">Risk Profile</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Risk Level</span>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getRiskLevelColor(selectedCase.risk_level)}`}>
                        {selectedCase.risk_level}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Risk Score</span>
                      <span className="font-medium text-slate-900">{selectedCase.risk_score}/100</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Account Age</span>
                      <span className="font-medium text-slate-900">{selectedCase.account_age}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Total Volume</span>
                      <span className="font-medium text-slate-900">{selectedCase.total_volume}</span>
                    </div>
                  </div>
                </div>

                {/* Recommended Action */}
                <div className="bg-white rounded-lg border border-slate-200 p-4">
                  <h3 className="text-sm font-semibold text-slate-900 mb-3">Recommended Action</h3>
                  <div className={`p-3 rounded-lg border ${
                    selectedCase.risk_level === 'CRITICAL'
                      ? 'bg-red-50 border-red-200'
                      : 'bg-blue-50 border-blue-200'
                  }`}>
                    <p className="font-semibold text-slate-900">{selectedCase.recommended_action}</p>
                    <p className="text-xs text-slate-600 mt-1">
                      {selectedCase.risk_level === 'CRITICAL'
                        ? 'Immediate action required due to critical risk indicators'
                        : 'Monitor and review as part of standard procedures'}
                    </p>
                  </div>
                  <p className="text-xs text-slate-500 mt-3">
                    Analyst should review risk signals and determine appropriate action
                  </p>
                </div>
              </div>

              {/* Risk Signals */}
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <h3 className="text-sm font-semibold text-slate-900 mb-3">Risk Signals</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {selectedCase.risk_factors.map((factor, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border ${getSeverityColor(factor.severity)}`}
                    >
                      <div className="flex items-start justify-between mb-1">
                        <p className="font-medium text-sm">{factor.name}</p>
                        <span className="text-xs capitalize px-2 py-0.5 rounded bg-white/50">
                          {factor.severity}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI Risk Explanation */}
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="text-sm font-semibold text-slate-900">AI Risk Explanation</h3>
                  <span className="text-xs text-slate-500">
                    Risk analysis insights for analyst review
                  </span>
                </div>

                {/* Summary */}
                <div className="mb-4">
                  <h4 className="text-xs font-semibold text-slate-700 mb-1">Risk Summary</h4>
                  <p className="text-sm text-slate-600">{selectedCase.risk_explanation.summary}</p>
                </div>

                {/* Contributing Factors */}
                <div className="mb-4">
                  <h4 className="text-xs font-semibold text-slate-700 mb-2">Key Contributing Factors</h4>
                  <ul className="space-y-1">
                    {selectedCase.risk_explanation.contributing_factors.map((factor, index) => (
                      <li key={index} className="text-xs text-slate-600 flex items-start gap-2">
                        <span className="text-blue-600 font-medium">{index + 1}.</span>
                        <span>{factor}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Signal Analysis */}
                <div className="mb-4">
                  <h4 className="text-xs font-semibold text-slate-700 mb-1">How Signals Relate to Risk</h4>
                  <p className="text-xs text-slate-600">{selectedCase.risk_explanation.signal_analysis}</p>
                </div>

                {/* Analyst Guidance */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <h4 className="text-xs font-semibold text-blue-900 mb-1">Recommended Analyst Action</h4>
                  <p className="text-xs text-blue-800">{selectedCase.risk_explanation.analyst_guidance}</p>
                </div>

                <p className="text-xs text-slate-500 mt-3 italic">
                  This explanation is generated by the risk analysis model to support analyst decision-making. The final determination and action are made by the reviewing analyst.
                </p>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-slate-200 p-8 text-center">
              <div className="text-4xl mb-4">🔍</div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Select a Case to Investigate</h3>
              <p className="text-sm text-slate-600">
                Choose a case from the investigation queue to view detailed risk analysis,
                evidence timeline, and recommended actions.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
