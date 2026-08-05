/**
 * Risk Intelligence Platform
 *
 * Multi-Signal Risk Detection with Explainable Investigation.
 * Enterprise SaaS Risk Intelligence MVP.
 */
import { useState, useMemo, useEffect } from 'react';
import { Table, SimpleMetricTooltip } from '../components/UI';
import { DetectionSourceChart, RiskScoreDistributionChart, RiskScoreAnalyticsCard, DetectionPatternChart } from '../components/Charts';
import { RiskLevel } from '../types';
import { riskApi, RiskOverview } from '../services/api';

// ============================================
// SUB-COMPONENTS
// ============================================

// KPI Card Container with risk-themed colors and icons
interface KPICardProps {
  children: React.ReactNode;
  colorTheme: 'blue' | 'red' | 'purple' | 'yellow';
}

function KPICard({ children, colorTheme }: KPICardProps) {
  const colorStyles = {
    blue: 'bg-blue-50/80 border-blue-200',
    red: 'bg-red-50/80 border-red-200',
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
function KPICardIcon({ type }: { type: 'users' | 'warning' | 'network' | 'action' }) {
  const icons = {
    users: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
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
    users: 'text-blue-600 bg-blue-100',
    warning: 'text-red-600 bg-red-100',
    network: 'text-purple-600 bg-purple-100',
    action: 'text-yellow-600 bg-yellow-100',
  };

  return (
    <div className={`w-9 h-9 rounded-lg ${iconColors[type]} flex items-center justify-center flex-shrink-0`}>
      {icons[type]}
    </div>
  );
}

// Risk Level Composition with segmented horizontal bar
function RiskLevelComposition({ riskComposition }: { riskComposition: { critical: number; high: number; medium: number; low: number; total: number } }) {
  const { critical, high, medium, low, total } = riskComposition;

  const riskLevels = [
    { label: 'Critical', count: critical, color: '#EF4444', textColor: 'text-red-600' },
    { label: 'High', count: high, color: '#F97316', textColor: 'text-orange-600' },
    { label: 'Medium', count: medium, color: '#EAB308', textColor: 'text-yellow-600' },
    { label: 'Low', count: low, color: '#22C55E', textColor: 'text-green-600' },
  ];

  const getSegmentWidth = (count: number) => {
    return total > 0 ? (count / total) * 100 : 0;
  };

  const getPercentage = (count: number) => {
    if (total === 0) return '0';
    const pct = (count / total) * 100;
    // Use decimal places for very small percentages
    if (pct < 1) return pct.toFixed(1);
    if (pct < 10) return pct.toFixed(1);
    return pct.toFixed(0);
  };

  // Determine if we should show percentage inside bar or use tooltip
  const shouldShowInBar = (width: number) => width >= 5;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 h-[300px] flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-700">Risk Level Composition</h3>
      </div>
      <p className="text-xs text-slate-500 mb-4">Distribution of users across risk severity categories</p>

      {/* Segmented Bar */}
      <div className="flex-1 flex flex-col justify-center space-y-4">
        <div className="space-y-2">
          <div className="h-8 flex rounded-lg overflow-hidden">
            {riskLevels.map((level) => {
              const width = getSegmentWidth(level.count);
              return (
                <div
                  key={level.label}
                  className="flex items-center justify-center relative first:rounded-l-lg last:rounded-r-lg"
                  style={{
                    width: `${width}%`,
                    backgroundColor: level.color,
                  }}
                >
                  {shouldShowInBar(width) && (
                    <span className="text-xs font-semibold text-white">
                      {getPercentage(level.count)}%
                    </span>
                  )}
                </div>
              );
            })}
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

      {/* Note for small percentages - aligned with legend */}
      <div className="text-xs text-slate-500 text-center mt-2 pt-2 border-t border-slate-100">
        Percentages shown for segments ≥5%
      </div>
    </div>
  );
}

// ============================================
// MAIN PAGE COMPONENT
// ============================================

const PAGE_SIZE = 5;

export default function RiskCommandCenter() {
  const [riskOverview, setRiskOverview] = useState<RiskOverview | null>(null);
  const [investigationCases, setInvestigationCases] = useState<any[]>([]);
  const [totalCases, setTotalCases] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [riskFilter, setRiskFilter] = useState<RiskLevel | 'ALL'>('ALL');
  const [currentPage, setCurrentPage] = useState(1);

  // Load risk overview on component mount
  useEffect(() => {
    loadRiskOverview();
    loadInvestigationCases();
  }, []);

  // Reload cases when page changes
  useEffect(() => {
    if (riskOverview) {
      loadInvestigationCases();
    }
  }, [currentPage]);

  // Reload cases when filter changes (reset to page 1)
  useEffect(() => {
    if (riskOverview) {
      setCurrentPage(1);
      // Small delay to ensure page state is updated before API call
      setTimeout(() => {
        loadInvestigationCases();
      }, 0);
    }
  }, [riskFilter]);

  const loadRiskOverview = async () => {
    try {
      setLoading(true);
      const overview = await riskApi.getOverview();
      console.log('=== API Response ===');
      console.log('Full overview response:', overview);
      console.log('detection_sources from API:', overview?.detection_sources);
      setRiskOverview(overview);
    } catch (err) {
      console.error('Failed to load risk overview:', err);
      setError('Failed to load risk data. Please upload datasets first.');
    } finally {
      setLoading(false);
    }
  };

  const loadInvestigationCases = async () => {
    try {
      // Map risk filter to backend parameter
      const riskLevelParam = riskFilter === 'ALL' ? undefined : riskFilter;
      const response = await riskApi.getCases({
        page: currentPage,
        page_size: PAGE_SIZE,
        risk_level: riskLevelParam
      });
      console.log('=== Investigation Cases API Response ===');
      console.log('Filter:', riskFilter, '→ riskLevelParam:', riskLevelParam);
      console.log('Full response:', response);
      console.log('Items count:', response.items?.length);
      console.log('First item:', response.items?.[0]);
      setInvestigationCases(response.items);
      setTotalCases(response.total || 0);
    } catch (err) {
      console.error('Failed to load investigation cases:', err);
      // Set empty cases on error
      setInvestigationCases([]);
      setTotalCases(0);
    }
  };

  // Derived data from backend response (new structure)
  const summary = riskOverview?.summary || {
    analyzed_users: 0,
    high_risk_accounts: 0,
    fraud_networks: 0,
    risk_recommendations: 0,
  };

  const riskScoreDistribution = riskOverview?.risk_score_distribution || [];
  const riskScoreStatistics = riskOverview?.risk_score_statistics || {
    average: 0,
    median: 0,
    threshold: 80,
    maximum: 0,
  };

  const riskComposition = riskOverview?.risk_level_composition || {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    total: 0,
  };

  const detectionSources: Array<{ name: string; value: number; percentage: number; color: string }> = riskOverview?.detection_sources?.map((source: any) => ({
    name: source.method,
    value: source.account_count,
    percentage: source.percentage,
    color: source.color,
  })) || [
    { name: 'LightGBM Model', value: 0, percentage: 0, color: '#8b5cf6' },
    { name: 'Rule Engine', value: 0, percentage: 0, color: '#3b82f6' },
    { name: 'Graph Network', value: 0, percentage: 0, color: '#06b6d4' },
  ];

  // Transform backend detection sources to frontend format
  const transformedDetectionSources = useMemo(() => detectionSources, [detectionSources]);

  // Transform backend case data to frontend format
  const transformedCases = useMemo(() => {
    const cases = investigationCases.map((item, idx) => {
      // Generate unique case_id using global index (accounting for pagination)
      const globalIndex = (currentPage - 1) * PAGE_SIZE + idx + 1;
      return {
        case_id: `CASE-${String(globalIndex).padStart(5, '0')}`,
        user_id: item.user_id,
        risk_score: Number(item.risk_score),
        risk_level: item.risk_level as RiskLevel,
        detection_methods: item.detection_methods || [], // Use backend-generated detection methods
        recommended_action: item.recommended_action || 'Review case',
      };
    });
    console.log('=== Transformed Cases ===');
    console.log('Transformed cases:', cases);
    console.log('First transformed case:', cases[0]);
    return cases;
  }, [investigationCases, currentPage]);

  // Filter cases - now handled by backend API
  const filteredCases = transformedCases;

  // Use server-side pagination
  const paginatedCases = filteredCases;
  const totalPages = Math.ceil(totalCases / PAGE_SIZE);

  // Calculate Needs Review count (Critical + High + Medium)
  const needsReviewCount = riskComposition.critical + riskComposition.high + riskComposition.medium;

  // Filter buttons based on new definition
  const filterButtons = useMemo(() => [
    { label: 'Needs Review', level: 'ALL' as const, count: needsReviewCount },
    { label: 'Critical', level: 'CRITICAL' as RiskLevel, count: riskComposition.critical },
    { label: 'High', level: 'HIGH' as RiskLevel, count: riskComposition.high },
    { label: 'Medium', level: 'MEDIUM' as RiskLevel, count: riskComposition.medium },
  ], [needsReviewCount, riskComposition]);

  const getRiskLevelColor = (level: RiskLevel) => {
    switch (level) {
      case 'LOW': return 'bg-green-100 text-green-700 border border-green-200';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-700 border border-yellow-200';
      case 'HIGH': return 'bg-orange-100 text-orange-700 border border-orange-200';
      case 'CRITICAL': return 'bg-red-100 text-red-700 border border-red-300';
      default: return 'bg-slate-100 text-slate-700 border border-slate-200';
    }
  };

  const getDetectionBadge = (methods: string[]) => {
    if (!methods || methods.length === 0) {
      return <span className="px-2 py-1 text-xs font-medium bg-slate-100 text-slate-700 rounded-full border border-slate-200">Unknown</span>;
    }
    if (methods.length >= 2) {
      const labels = methods.map(m => m === 'LightGBM' ? 'ML' : m === 'Rule Engine' ? 'Rule' : 'Graph');
      return <span className="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-700 rounded-full border border-purple-200">{labels.join(' + ')}</span>;
    }
    // Single method
    const method = methods[0];
    if (method === 'LightGBM') {
      return <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full border border-blue-200">LightGBM</span>;
    }
    if (method === 'Graph Network') {
      return <span className="px-2 py-1 text-xs font-medium bg-cyan-100 text-cyan-700 rounded-full border border-cyan-200">Graph</span>;
    }
    return <span className="px-2 py-1 text-xs font-medium bg-slate-100 text-slate-700 rounded-full border border-slate-200">Rule Engine</span>;
  };

  const tableColumns = [
    { key: 'case_id', header: 'Case ID', className: 'font-medium text-sm' },
    { key: 'user_id', header: 'User ID', className: 'text-sm' },
    { key: 'risk_score', header: 'Risk Score', className: 'text-sm' },
    { key: 'risk_level', header: 'Risk Level', className: 'text-sm' },
    { key: 'detection_methods', header: 'Detection', className: 'text-sm' },
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
        <span className="font-semibold text-slate-900">{Number(item.risk_score).toFixed(2)}</span>
        <span className="text-xs text-slate-400">/100</span>
      </div>
    ),
    risk_level: (
      <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${getRiskLevelColor(item.risk_level)}`}>
        {item.risk_level}
      </span>
    ),
    detection_methods: getDetectionBadge(item.detection_methods),
    recommended_action: <span className="text-sm text-slate-700">{item.recommended_action}</span>,
  }));

  return (
    <div className="space-y-8">
      <div className="max-w-[1600px] mx-auto space-y-8">
        {/* ==================================== PAGE HEADER ==================================== */}
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Risk Intelligence Platform</h1>
          <p className="text-sm text-slate-500 mt-1">Multi-Signal Risk Detection with Explainable Investigation</p>
        </div>

        {/* ==================================== LOADING STATE ==================================== */}
        {loading && (
          <div className="bg-white border border-slate-200 rounded-lg p-8 text-center">
            <div className="text-slate-500">Loading risk data...</div>
          </div>
        )}

        {/* ==================================== ERROR STATE ==================================== */}
        {error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <div className="text-red-800 font-medium mb-2">Unable to load risk data</div>
            <div className="text-red-600 text-sm mb-4">{error}</div>
            <div className="text-red-600 text-xs">
              Please upload datasets through the Data Pipeline page to generate risk analytics.
            </div>
          </div>
        )}

        {/* ==================================== RISK ANALYTICS CONTENT ==================================== */}
        {!loading && !error && riskOverview && (
          <>
        {/* ==================================== SECTION 1: EXECUTIVE RISK SUMMARY ==================================== */}
        <section>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: High Risk Accounts */}
            <KPICard colorTheme="red">
              <div className="flex items-start gap-2 mb-3">
                <KPICardIcon type="warning" />
                <h3 className="text-sm font-semibold text-slate-700">High Risk Accounts</h3>
              </div>
              <div className="flex-1 flex items-end">
                <p className="text-4xl font-bold text-slate-900">{summary.high_risk_accounts.toLocaleString()}</p>
              </div>
              <p className="text-sm text-slate-500 mt-2 h-5">Users with Critical or High risk scores</p>
            </KPICard>

            {/* Card 2: Recommended Actions */}
            <KPICard colorTheme="yellow">
              <div className="flex items-start gap-2 mb-3">
                <KPICardIcon type="action" />
                <h3 className="text-sm font-semibold text-slate-700">Recommended Actions</h3>
              </div>
              <div className="flex-1 flex items-end">
                <p className="text-4xl font-bold text-slate-900">{summary.risk_recommendations.toLocaleString()}</p>
              </div>
              <p className="text-sm text-slate-500 mt-2 h-5">Users requiring model-recommended actions</p>
            </KPICard>

            {/* Card 3: Network-linked Accounts */}
            <KPICard colorTheme="purple">
              <div className="flex items-start gap-2 mb-3">
                <KPICardIcon type="network" />
                <SimpleMetricTooltip
                  metric="Network-linked Accounts"
                  definition="Number of accounts connected to suspicious networks through shared devices, IP addresses, or other graph relationships."
                >
                  <h3 className="text-sm font-semibold text-slate-700">Network-linked Accounts</h3>
                </SimpleMetricTooltip>
              </div>
              <div className="flex-1 flex items-end">
                <p className="text-4xl font-bold text-slate-900">{summary.fraud_networks}</p>
              </div>
              <p className="text-sm text-slate-500 mt-2 h-5">Accounts in suspicious network clusters</p>
            </KPICard>

            {/* Card 4: Analyzed Users */}
            <KPICard colorTheme="blue">
              <div className="flex items-start gap-2 mb-3">
                <KPICardIcon type="users" />
                <h3 className="text-sm font-semibold text-slate-700">Analyzed Users</h3>
              </div>
              <div className="flex-1 flex items-end">
                <p className="text-4xl font-bold text-slate-900">{summary.analyzed_users.toLocaleString()}</p>
              </div>
              <p className="text-sm text-slate-500 mt-2 h-5">Unique users analyzed from uploaded dataset</p>
            </KPICard>
          </div>
        </section>

        {/* ==================================== SECTION 2: RISK INTELLIGENCE OVERVIEW ==================================== */}
        <section>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Risk Intelligence Overview</h2>

          {/* Row 1: Risk Level Composition, Risk Score Analytics, Risk Score Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
            {/* Card 1: Risk Level Composition */}
            <SimpleMetricTooltip
              metric="Risk Level Composition"
              definition="Distribution of risk levels across accounts in the uploaded dataset."
            >
              <RiskLevelComposition riskComposition={riskComposition} />
            </SimpleMetricTooltip>

            {/* Card 2: Risk Score Analytics */}
            <SimpleMetricTooltip
              metric="Risk Score Analytics"
              definition="Statistical summary of model-generated risk scores including average, threshold, and maximum values."
            >
              <RiskScoreAnalyticsCard statistics={riskScoreStatistics} />
            </SimpleMetricTooltip>

            {/* Card 3: Risk Score Distribution */}
            <SimpleMetricTooltip
              metric="Risk Score Distribution"
              definition="Distribution of risk scores across users, showing how many users fall into each score range bucket."
            >
              <div className="bg-white border border-slate-200 rounded-lg p-5 h-[300px] flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-slate-700">Risk Score Distribution</h3>
                </div>
                <p className="text-xs text-slate-500 mb-4">User count distribution across score ranges</p>
                <div className="flex-1 min-h-0">
                  <RiskScoreDistributionChart
                    data={riskScoreDistribution}
                    highRiskThreshold={riskScoreStatistics.threshold}
                    totalUsers={summary.analyzed_users}
                  />
                </div>
              </div>
            </SimpleMetricTooltip>
          </div>
        </section>

        {/* ==================================== SECTION 3: DETECTION INTELLIGENCE ==================================== */}
        <section>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Detection Intelligence</h2>

          {/* Row: Risk Detection Sources & Detection Pattern Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Card 1: Risk Detection Sources */}
            <SimpleMetricTooltip
              metric="Risk Detection Sources"
              definition="Contribution of each detection method among identified risk cases."
            >
              <div className="bg-white border border-slate-200 rounded-lg p-5 h-[320px] flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-slate-700">Risk Detection Sources</h3>
                </div>
                <p className="text-xs text-slate-500 mb-3">Contribution of each detection method among identified risk cases</p>
                <div style={{ height: '250px', width: '100%' }}>
                  <DetectionSourceChart data={transformedDetectionSources} />
                </div>
              </div>
            </SimpleMetricTooltip>

            {/* Card 2: Detection Pattern Distribution */}
            <SimpleMetricTooltip
              metric="Detection Pattern Distribution"
              definition="Shows the overlap between detection methods - how many accounts were flagged by single methods vs multiple methods. Multi-signal accounts have 2 or more detection methods triggered simultaneously."
            >
              <div className="bg-white border border-slate-200 rounded-lg p-5 h-[320px] flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-slate-700">Detection Pattern Distribution</h3>
                </div>
                <p className="text-xs text-slate-500 mb-3">Distribution of single and multi-signal detected accounts</p>
                <div style={{ height: '250px', width: '100%' }}>
                  <DetectionPatternChart data={riskOverview?.signal_combination_breakdown} />
                </div>
              </div>
            </SimpleMetricTooltip>
          </div>
        </section>

        {/* ==================================== SECTION 4: RISK INVESTIGATION QUEUE ==================================== */}

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
          {totalCases > PAGE_SIZE && (
            <div className="flex items-center justify-between mt-4 px-2">
              <div className="text-sm text-slate-500">
                Showing {((currentPage - 1) * PAGE_SIZE) + 1} to {Math.min(currentPage * PAGE_SIZE, totalCases)} of {totalCases} cases
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
                  {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                    // Show pagination buttons smartly (1, ..., current-1, current, current+1, ..., last)
                    let pageNum;
                    if (totalPages <= 7) {
                      pageNum = i + 1;
                    } else if (currentPage <= 4) {
                      pageNum = i < 5 ? i + 1 : (i === 5 ? -1 : totalPages);
                    } else if (currentPage >= totalPages - 3) {
                      pageNum = i < 2 ? (i === 0 ? 1 : -1) : totalPages - 6 + i;
                    } else {
                      pageNum = i < 2 ? (i === 0 ? 1 : -1) : (i === 2 ? currentPage - 1 : (i === 3 ? currentPage : (i === 4 ? currentPage + 1 : -1)));
                      if (i === 6) pageNum = totalPages;
                    }

                    if (pageNum === -1) {
                      return <span key={`ellipsis-${i}`} className="px-2 text-slate-400">...</span>;
                    }

                    return (
                      <button
                        key={`page-${pageNum}`}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`px-3 py-1.5 text-sm font-medium rounded-lg border ${
                          currentPage === pageNum
                            ? 'bg-slate-900 text-white border-slate-900'
                            : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
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
        </>
      )}
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
