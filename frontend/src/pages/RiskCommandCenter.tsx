/**
 * AI Risk Command Center
 *
 * AI-powered risk assessment and analytics platform.
 * Enterprise SaaS Risk Intelligence MVP.
 */
import { useState, useMemo } from 'react';
import { Table, DataProvenanceTooltip, MetricProvenanceIcon } from '../components/UI';
import { DetectionSourceChart } from '../components/Charts';
import { RiskLevel } from '../types';

// ============================================
// CENTRALIZED MOCK DATA
// ============================================

const MOCK_DATA = {
  // Risk Score Statistics
  riskStatistics: {
    averageScore: 42.6,
    medianScore: 38,
    highRiskThreshold: 80,
    maxScore: 99.5,
  },

  // Risk Level Composition (single source of truth)
  riskComposition: {
    critical: 32,
    high: 176,
    medium: 390,
    low: 845,
    total: 1443,
  },

  // High Risk Accounts (Critical + High)
  highRiskAccounts: 598,

  // Fraud Networks
  fraudNetworks: 225,

  // Risk Recommendations
  recommendationsCount: 2990,

  // Historical data availability
  hasHistoricalData: false,

  // Investigation cases (no status field - MVP)
  investigationCases: [
    {
      case_id: 'CASE-10291',
      user_id: 'user_1248',
      risk_score: 94,
      risk_level: 'CRITICAL' as RiskLevel,
      detection_method: 'ML + Graph',
      risk_factors: ['Shared Device', 'Abnormal Location', 'Rapid Withdrawal'],
      recommended_action: 'Review withdrawal activity',
    },
    {
      case_id: 'CASE-10290',
      user_id: 'user_0847',
      risk_score: 87,
      risk_level: 'CRITICAL' as RiskLevel,
      detection_method: 'LightGBM',
      risk_factors: ['Account Linkage', 'Suspicious Pattern'],
      recommended_action: 'Investigate account linkage',
    },
    {
      case_id: 'CASE-10289',
      user_id: 'user_1923',
      risk_score: 82,
      risk_level: 'HIGH' as RiskLevel,
      detection_method: 'Rule Engine',
      risk_factors: ['Transaction Velocity'],
      recommended_action: 'Enhanced monitoring',
    },
    {
      case_id: 'CASE-10288',
      user_id: 'user_3456',
      risk_score: 78,
      risk_level: 'HIGH' as RiskLevel,
      detection_method: 'ML + Graph',
      risk_factors: ['Device Fingerprint Mismatch', 'Multiple Accounts'],
      recommended_action: 'Enhanced monitoring',
    },
    {
      case_id: 'CASE-10287',
      user_id: 'user_7890',
      risk_score: 75,
      risk_level: 'HIGH' as RiskLevel,
      detection_method: 'LightGBM',
      risk_factors: ['Unusual Trading Pattern'],
      recommended_action: 'Monitor',
    },
    {
      case_id: 'CASE-10286',
      user_id: 'user_4567',
      risk_score: 68,
      risk_level: 'MEDIUM' as RiskLevel,
      detection_method: 'Rule Engine',
      risk_factors: ['New Device Login'],
      recommended_action: 'Monitor',
    },
  ],

  // Detection Sources
  detectionSources: [
    { name: 'Rule Engine', value: 45, percentage: 45, color: '#3b82f6' },
    { name: 'LightGBM Model', value: 35, percentage: 35, color: '#8b5cf6' },
    { name: 'Graph Network', value: 20, percentage: 20, color: '#06b6d4' },
  ],
};

// Data Provenance Configuration
const DATA_PROVENANCE = {
  dataSource: 'Uploaded Risk Dataset',
  processingMethod: 'Risk Analytics Pipeline',
  updateMethod: 'Manual upload',
  generated: 'Jul 15, 2026 14:32',
};

// ============================================
// SUB-COMPONENTS
// ============================================

// KPI Card Container with risk-themed colors and icons
interface KPICardProps {
  children: React.ReactNode;
  colorTheme: 'red' | 'orange' | 'purple' | 'yellow';
}

function KPICard({ children, colorTheme }: KPICardProps) {
  const colorStyles = {
    red: 'bg-red-50/80 border-red-200',
    orange: 'bg-orange-50/80 border-orange-200',
    purple: 'bg-purple-50/80 border-purple-200',
    yellow: 'bg-yellow-50/80 border-yellow-200',
  };

  return (
    <div className={`${colorStyles[colorTheme]} border rounded-lg p-6 h-[180px] flex flex-col`}>
      {children}
    </div>
  );
}

// KPI Icon component
function KPICardIcon({ type }: { type: 'warning' | 'chart' | 'network' | 'action' }) {
  const icons = {
    warning: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    chart: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    network: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    action: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
  };

  const iconColors = {
    warning: 'text-red-600 bg-red-100',
    chart: 'text-orange-600 bg-orange-100',
    network: 'text-purple-600 bg-purple-100',
    action: 'text-yellow-600 bg-yellow-100',
  };

  return (
    <div className={`w-9 h-9 rounded-lg ${iconColors[type]} flex items-center justify-center flex-shrink-0`}>
      {icons[type]}
    </div>
  );
}

// Empty State for Historical Data
function HistoricalEmptyState() {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-8 h-[300px] flex flex-col items-center justify-center">
      <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      </div>
      <p className="text-sm font-medium text-slate-700 mb-1">No historical baseline available</p>
      <p className="text-xs text-slate-500 text-center">Upload additional datasets to enable trend analysis</p>
    </div>
  );
}

// Risk Level Composition with segmented horizontal bar
function RiskLevelComposition() {
  const { critical, high, medium, low, total } = MOCK_DATA.riskComposition;

  const riskLevels = [
    { label: 'Critical', count: critical, color: '#EF4444', textColor: 'text-red-600' },
    { label: 'High', count: high, color: '#F97316', textColor: 'text-orange-600' },
    { label: 'Medium', count: medium, color: '#EAB308', textColor: 'text-yellow-600' },
    { label: 'Low', count: low, color: '#22C55E', textColor: 'text-green-600' },
  ];

  const getSegmentWidth = (count: number) => {
    return (count / total) * 100;
  };

  const getPercentage = (count: number) => {
    return ((count / total) * 100).toFixed(0);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 h-[300px] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700">Risk Level Composition</h3>
        <MetricProvenanceIcon />
      </div>

      {/* Segmented Bar */}
      <div className="flex-1 flex flex-col justify-center space-y-6">
        <div className="space-y-2">
          <div className="h-8 flex rounded-lg overflow-hidden">
            {riskLevels.map((level) => (
              <div
                key={level.label}
                className="flex items-center justify-center relative first:rounded-l-lg last:rounded-r-lg"
                style={{
                  width: `${getSegmentWidth(level.count)}%`,
                  backgroundColor: level.color,
                }}
              >
                {getSegmentWidth(level.count) >= 8 && (
                  <span className="text-xs font-semibold text-white">
                    {getPercentage(level.count)}%
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Level Counts */}
        <div className="grid grid-cols-4 gap-3">
          {riskLevels.map((level) => (
            <div key={level.label} className="flex flex-col items-center">
              <div className={`text-sm font-semibold ${level.textColor}`}>
                {level.count}
              </div>
              <div className="text-xs text-slate-500">{level.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================
// MAIN PAGE COMPONENT
// ============================================

const PAGE_SIZE = 5;

export default function RiskCommandCenter() {
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [riskFilter, setRiskFilter] = useState<RiskLevel | 'ALL'>('ALL');
  const [currentPage, setCurrentPage] = useState(1);

  // Filter and pagination
  const filteredCases = useMemo(() => {
    if (riskFilter === 'ALL') return MOCK_DATA.investigationCases;
    return MOCK_DATA.investigationCases.filter(item => item.risk_level === riskFilter);
  }, [riskFilter]);

  const totalPages = Math.ceil(filteredCases.length / PAGE_SIZE);
  const paginatedCases = useMemo(() => {
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    return filteredCases.slice(startIndex, startIndex + PAGE_SIZE);
  }, [filteredCases, currentPage]);

  useMemo(() => setCurrentPage(1), [riskFilter]);

  const filterButtons = [
    { label: 'All', level: 'ALL' as const, count: MOCK_DATA.investigationCases.length },
    { label: 'Critical', level: 'CRITICAL' as RiskLevel, count: MOCK_DATA.investigationCases.filter(c => c.risk_level === 'CRITICAL').length },
    { label: 'High', level: 'HIGH' as RiskLevel, count: MOCK_DATA.investigationCases.filter(c => c.risk_level === 'HIGH').length },
    { label: 'Medium', level: 'MEDIUM' as RiskLevel, count: MOCK_DATA.investigationCases.filter(c => c.risk_level === 'MEDIUM').length },
    { label: 'Low', level: 'LOW' as RiskLevel, count: MOCK_DATA.investigationCases.filter(c => c.risk_level === 'LOW').length },
  ];

  const getRiskLevelColor = (level: RiskLevel) => {
    switch (level) {
      case 'LOW': return 'bg-green-100 text-green-700 border border-green-200';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-700 border border-yellow-200';
      case 'HIGH': return 'bg-orange-100 text-orange-700 border border-orange-200';
      case 'CRITICAL': return 'bg-red-100 text-red-700 border border-red-300';
      default: return 'bg-slate-100 text-slate-700 border border-slate-200';
    }
  };

  const getDetectionBadge = (method: string) => {
    if (method.includes('ML') && method.includes('Graph')) {
      return <span className="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-700 rounded-full border border-purple-200">ML + Graph</span>;
    }
    if (method.includes('LightGBM') || method.includes('ML')) {
      return <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full border border-blue-200">LightGBM</span>;
    }
    if (method.includes('Graph')) {
      return <span className="px-2 py-1 text-xs font-medium bg-cyan-100 text-cyan-700 rounded-full border border-cyan-200">Graph</span>;
    }
    return <span className="px-2 py-1 text-xs font-medium bg-slate-100 text-slate-700 rounded-full border border-slate-200">Rule Engine</span>;
  };

  const tableColumns = [
    { key: 'case_id', header: 'Case ID', className: 'font-medium text-sm' },
    { key: 'user_id', header: 'User ID', className: 'text-sm' },
    { key: 'risk_score', header: 'Risk Score', className: 'text-sm' },
    { key: 'risk_level', header: 'Risk Level', className: 'text-sm' },
    { key: 'detection_method', header: 'Detection', className: 'text-sm' },
    { key: 'risk_factors', header: 'Risk Signals', className: 'text-sm' },
    { key: 'recommended_action', header: 'Recommended Action', className: 'text-sm' },
  ];

  const tableData = paginatedCases.map((item) => ({
    case_id: (
      <div className="flex items-center gap-2">
        <span className="font-medium text-slate-900">{item.case_id}</span>
        {item.risk_level === 'CRITICAL' && <span className="text-red-500">●</span>}
      </div>
    ),
    user_id: <span className="text-sm text-slate-700 font-mono">{item.user_id}</span>,
    risk_score: (
      <div className="flex items-center gap-1">
        <span className="font-semibold text-slate-900">{item.risk_score}</span>
        <span className="text-xs text-slate-400">/100</span>
      </div>
    ),
    risk_level: (
      <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${getRiskLevelColor(item.risk_level)}`}>
        {item.risk_level}
      </span>
    ),
    detection_method: getDetectionBadge(item.detection_method),
    risk_factors: (
      <div className="flex flex-wrap gap-1">
        {item.risk_factors.slice(0, 2).map((factor, idx) => (
          <span key={idx} className="text-xs text-slate-600">• {factor}</span>
        ))}
        {item.risk_factors.length > 2 && (
          <span className="text-xs text-slate-400">+{item.risk_factors.length - 2}</span>
        )}
      </div>
    ),
    recommended_action: <span className="text-sm text-slate-700">{item.recommended_action}</span>,
  }));

  return (
    <div className="space-y-8" style={{ backgroundColor: '#F8FAFC', minHeight: '100vh', padding: '24px' }}>
      <div className="max-w-[1600px] mx-auto space-y-8">
        {/* ==================================== PAGE HEADER ==================================== */}
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">AI Risk Command Center</h1>
          <p className="text-sm text-slate-500 mt-1">AI-powered risk assessment and analytics platform</p>
        </div>

        {/* ==================================== SECTION 1: EXECUTIVE RISK SUMMARY ==================================== */}
        <section>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            {/* Card 1: High Risk Accounts */}
            <DataProvenanceTooltip
              metric="High Risk Accounts"
              definition="Accounts with risk score ≥ 70 requiring immediate review or action."
              {...DATA_PROVENANCE}
            >
              <KPICard colorTheme="red">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <KPICardIcon type="warning" />
                    <h3 className="text-sm font-semibold text-slate-700">High Risk Accounts</h3>
                  </div>
                  <MetricProvenanceIcon />
                </div>
                <div className="flex-1 flex items-end">
                  <p className="text-4xl font-bold text-slate-900">{MOCK_DATA.highRiskAccounts}</p>
                </div>
                <p className="text-sm text-slate-500 mt-2">Detected from uploaded dataset</p>
              </KPICard>
            </DataProvenanceTooltip>

            {/* Card 2: Risk Score Statistics */}
            <DataProvenanceTooltip
              metric="Risk Score Statistics"
              definition="Model scoring metrics including average, median, and threshold values."
              {...DATA_PROVENANCE}
            >
              <KPICard colorTheme="orange">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <KPICardIcon type="chart" />
                    <h3 className="text-sm font-semibold text-slate-700">Risk Score Statistics</h3>
                  </div>
                  <MetricProvenanceIcon />
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 flex-1">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-500">Average</span>
                    <span className="text-sm font-semibold text-slate-900">{MOCK_DATA.riskStatistics.averageScore}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-500">Median</span>
                    <span className="text-sm font-semibold text-slate-900">{MOCK_DATA.riskStatistics.medianScore}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-500">Threshold</span>
                    <span className="text-sm font-semibold text-slate-900">≥{MOCK_DATA.riskStatistics.highRiskThreshold}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-500">Max</span>
                    <span className="text-sm font-semibold text-slate-900">{MOCK_DATA.riskStatistics.maxScore}</span>
                  </div>
                </div>
              </KPICard>
            </DataProvenanceTooltip>

            {/* Card 3: Fraud Networks */}
            <DataProvenanceTooltip
              metric="Fraud Networks"
              definition="Suspicious account clusters identified through graph network analysis."
              {...DATA_PROVENANCE}
            >
              <KPICard colorTheme="purple">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <KPICardIcon type="network" />
                    <h3 className="text-sm font-semibold text-slate-700">Fraud Networks</h3>
                  </div>
                  <MetricProvenanceIcon />
                </div>
                <div className="flex-1 flex items-end">
                  <p className="text-4xl font-bold text-slate-900">{MOCK_DATA.fraudNetworks}</p>
                </div>
                <p className="text-sm text-slate-500 mt-2">Graph-based suspicious clusters</p>
              </KPICard>
            </DataProvenanceTooltip>

            {/* Card 4: Risk Recommendations */}
            <DataProvenanceTooltip
              metric="Risk Recommendations"
              definition="System-generated risk mitigation recommendations requiring analyst review. Generated from LightGBM Risk Model, Rule Engine, and Graph Network Analysis."
              dataSource="Uploaded Risk Dataset"
              processingMethod="LightGBM Risk Model, Rule Engine, Graph Network Analysis"
              updateMethod="Manual upload"
              generated="Jul 15, 2026 14:32"
            >
              <KPICard colorTheme="yellow">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <KPICardIcon type="action" />
                    <h3 className="text-sm font-semibold text-slate-700">Risk Recommendations</h3>
                  </div>
                  <MetricProvenanceIcon />
                </div>
                <div className="flex-1 flex items-end">
                  <p className="text-4xl font-bold text-slate-900">{MOCK_DATA.recommendationsCount.toLocaleString()}</p>
                </div>
                <p className="text-sm text-slate-500 mt-2">Recommended actions from uploaded dataset</p>
              </KPICard>
            </DataProvenanceTooltip>
          </div>
        </section>

        {/* ==================================== SECTION 2: RISK INTELLIGENCE OVERVIEW ==================================== */}
        <section>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Risk Intelligence Overview</h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Card 1: Risk Activity Trend */}
            <DataProvenanceTooltip
              metric="Risk Activity Trend"
              definition="Risk event counts from uploaded dataset across available date range."
              {...DATA_PROVENANCE}
            >
              {MOCK_DATA.hasHistoricalData ? (
                <div className="bg-white border border-slate-200 rounded-lg p-6 h-[280px] flex flex-col">
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">Risk Activity Trend</h3>
                  <p className="text-xs text-slate-500 mb-4">(Jul 8 - Jul 15)</p>
                </div>
              ) : (
                <HistoricalEmptyState />
              )}
            </DataProvenanceTooltip>

            {/* Card 2: Risk Level Composition */}
            <DataProvenanceTooltip
              metric="Risk Level Composition"
              definition="Distribution of risk levels across accounts in the uploaded dataset."
              {...DATA_PROVENANCE}
            >
              <RiskLevelComposition />
            </DataProvenanceTooltip>

            {/* Card 3: Detection Source Analysis */}
            <DataProvenanceTooltip
              metric="Detection Source Analysis"
              definition="Distribution of risk detection methods across uploaded dataset."
              dataSource="Uploaded Risk Dataset"
              processingMethod="Multi-Engine Detection Pipeline (LightGBM, Rule Engine, Graph Network)"
              updateMethod="Manual upload"
              generated="Jul 15, 2026 14:32"
            >
              <div className="bg-white border border-slate-200 rounded-lg p-5 h-[300px] flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-slate-700">Detection Source Analysis</h3>
                  <MetricProvenanceIcon />
                </div>
                <p className="text-xs text-slate-500 mb-6">Detection method distribution from uploaded dataset</p>
                <div className="flex-1 flex items-center justify-center min-h-0">
                  <DetectionSourceChart data={MOCK_DATA.detectionSources} />
                </div>
              </div>
            </DataProvenanceTooltip>
          </div>
        </section>

        {/* ==================================== SECTION 3: RISK INVESTIGATION QUEUE ==================================== */}
        <section>
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Risk Investigation Queue</h2>
            <p className="text-sm text-slate-500">Risk cases requiring analyst review</p>
          </div>

          {/* Filter Pills */}
          <div className="flex gap-2 mb-4">
            {filterButtons.map((btn) => (
              <button
                key={btn.level}
                onClick={() => setRiskFilter(btn.level)}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-all ${
                  riskFilter === btn.level
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                {btn.label} ({btn.count})
              </button>
            ))}
          </div>

          {/* Investigation Table */}
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <Table
              columns={tableColumns}
              data={tableData}
              onRowClick={(row) => {
                const match = row.case_id?.toString?.()?.match(/user_[0-9]+/);
                if (match) setSelectedUser(match[0]);
              }}
              emptyMessage="No risk signals detected"
            />
          </div>

          {/* Pagination */}
          {filteredCases.length > PAGE_SIZE && (
            <div className="flex items-center justify-between mt-4 px-2">
              <div className="text-sm text-slate-500">
                Showing {((currentPage - 1) * PAGE_SIZE) + 1} to {Math.min(currentPage * PAGE_SIZE, filteredCases.length)} of {filteredCases.length} cases
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-1.5 text-sm font-medium rounded-lg border ${
                        currentPage === pageNum
                          ? 'bg-slate-900 text-white border-slate-900'
                          : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* ==================================== USER DETAIL MODAL ==================================== */}
      {selectedUser && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setSelectedUser(null)}>
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-slate-900">Investigation Detail</h3>
              <button onClick={() => setSelectedUser(null)} className="text-slate-400 hover:text-slate-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-sm text-slate-600">
              Full investigation workspace for <span className="font-mono font-medium text-slate-900">{selectedUser}</span>.
            </p>
            <p className="text-sm text-slate-600 mt-2">
              Navigate to the <span className="text-blue-600 font-medium">Investigation</span> page for detailed analysis.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
