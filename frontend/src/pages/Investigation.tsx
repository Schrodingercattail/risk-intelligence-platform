/**
 * Investigation Workspace Page
 *
 * Risk analyst investigation interface for detailed case analysis.
 * Two-panel layout: Investigation Queue (left) + Case Detail (right).
 *
 * MVP: Risk investigation workspace for analyst decision support.
 * NOT a Case Management System - no workflow or status tracking.
 */
import { useState, useMemo, useEffect } from 'react';
import { riskApi } from '../services/api';

interface InvestigationCase {
  case_id: string;
  user_id: string;
  risk_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  account_age: number | string;  // Can be number (days) or "N/A"
  total_volume: number | string;  // Can be number or "N/A"
  risk_factors: Array<{ name: string; severity: 'critical' | 'high' | 'medium' | 'low' }>;
  recommended_action: string;
  created_at: string;
  risk_explanation: {
    summary: string;
    contributingFactors: string[];
    signal_analysis: string;
    analyst_guidance: string;
  };
  detection_methods?: string[];
}

// Transform backend API data to InvestigationCase format
function transformToInvestigationCase(
  item: any,
  idx: number
): InvestigationCase {
  // Generate risk factors from primary_reason
  const riskFactors: Array<{ name: string; severity: 'critical' | 'high' | 'medium' | 'low' }> = item.primary_reason
    ? [{ name: item.primary_reason, severity: item.risk_level === 'CRITICAL' ? 'critical' : item.risk_level === 'HIGH' ? 'high' : 'medium' }]
    : [{ name: 'Risk signals detected', severity: 'medium' }];

  // Generate risk explanation based on scores
  const mlScore = item.ml_score || 0;
  const ruleScore = item.rule_score || 0;
  const graphScore = item.graph_score || 0;

  let summary = `This account received a ${item.risk_level.toLowerCase()} risk score (${Math.round(item.risk_score)}/100).`;
  const contributingFactors: string[] = [];

  if (mlScore > 0) {
    contributingFactors.push(`ML model detection with score ${Math.round(mlScore)}`);
  }
  if (ruleScore > 0) {
    contributingFactors.push(`Rule engine detection with score ${Math.round(ruleScore)}`);
  }
  if (graphScore > 0) {
    contributingFactors.push(`Graph network analysis with score ${Math.round(graphScore)}`);
  }

  if (contributingFactors.length === 0) {
    contributingFactors.push('Risk signals detected through analysis');
  }

  // Generate unique case_id from user_id
  // Extract numeric part from user_id (e.g., "U01401" -> "01401")
  const userIdNumber = item.user_id ? item.user_id.replace(/\D/g, '') : '';
  const caseIdNumber = userIdNumber || String(idx + 1).padStart(5, '0');

  return {
    case_id: `CASE-${caseIdNumber}`,
    user_id: item.user_id,
    risk_score: Math.round(item.risk_score),
    risk_level: item.risk_level,
    account_age: 0, // Placeholder - will be updated from detail API
    total_volume: 0, // Placeholder - will be updated from detail API
    risk_factors: riskFactors,
    recommended_action: item.recommended_action || 'Review case',
    created_at: item.detected_at || new Date().toISOString(),
    detection_methods: item.detection_methods || [],
    risk_explanation: {
      summary,
      contributingFactors: contributingFactors,
      signal_analysis: `Risk analysis based on multiple detection methods. ML score: ${mlScore.toFixed(1)}, Rule score: ${ruleScore.toFixed(1)}, Graph score: ${graphScore.toFixed(1)}.`,
      analyst_guidance: item.recommended_action || 'Review the risk factors and determine appropriate action based on investigation findings.'
    }
  };
}

export default function Investigation() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCase, setSelectedCase] = useState<InvestigationCase | null>(null);
  const [cases, setCases] = useState<InvestigationCase[]>([]);
  const [totalCases, setTotalCases] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 50; // Load 50 cases at a time

  // Fetch case detail for a selected case
  const fetchCaseDetail = async (caseItem: InvestigationCase) => {
    try {
      const detail = await riskApi.getUserDetail(caseItem.user_id);

      // Update the selected case with detail information
      setSelectedCase({
        ...caseItem,
        account_age: detail.account_age ?? 'N/A',
        total_volume: detail.total_volume ?? 'N/A',
      });
    } catch (err) {
      console.error('Failed to load case detail:', err);
      // Keep the original case if detail fetch fails
      setSelectedCase(caseItem);
    }
  };

  // Handle case selection with detail fetch
  const handleCaseSelect = (caseItem: InvestigationCase) => {
    setSelectedCase(caseItem); // Set immediately for UI responsiveness
    fetchCaseDetail(caseItem); // Fetch details in background
  };

  // Fetch cases from backend API
  useEffect(() => {
    const fetchCases = async () => {
      try {
        setLoading(true);
        setError(null);
        console.log('=== Investigation: Fetching cases from backend ===');

        const response = await riskApi.getCases({ page: 1, page_size: PAGE_SIZE });
        console.log('=== Investigation: API response ===', response);

        if (!response) {
          console.warn('=== Investigation: No response from API ===');
          setError('Failed to load cases: No response from server');
          setCases([]);
          return;
        }

        const items = response.items || [];
        const total = response.total || 0;
        console.log('=== Investigation: Response items ===', items);
        console.log('=== Investigation: Total count ===', total);
        console.log('=== Investigation: Items length ===', items.length);

        // Set total cases count from API
        setTotalCases(total);
        setCurrentPage(1);

        if (items.length === 0) {
          console.warn('=== Investigation: No items in response ===');
          setCases([]);
          setError(null); // No error, just no data
          return;
        }

        const transformedCases = items.map((item, idx) => transformToInvestigationCase(item, idx));
        console.log('=== Investigation: Transformed cases ===', transformedCases);
        setCases(transformedCases);

        // Auto-select first case if available and no case is currently selected
        if (transformedCases.length > 0 && !selectedCase) {
          handleCaseSelect(transformedCases[0]);
        }
      } catch (err) {
        console.error('=== Investigation: Failed to load cases ===', err);
        setError('Failed to load cases. Please upload datasets first.');
        setCases([]);
      } finally {
        setLoading(false);
      }
    };

    fetchCases();
  }, []);

  // Load more cases
  const loadMoreCases = async () => {
    try {
      setLoadingMore(true);
      const nextPage = currentPage + 1;
      console.log('=== Investigation: Loading more cases, page ===', nextPage);

      const response = await riskApi.getCases({ page: nextPage, page_size: PAGE_SIZE });

      if (!response || !response.items) {
        console.warn('=== Investigation: No response for load more ===');
        return;
      }

      const items = response.items;
      const transformedCases = items.map((item, idx) =>
        transformToInvestigationCase(item, idx + (currentPage * PAGE_SIZE))
      );

      setCases(prev => [...prev, ...transformedCases]);
      setCurrentPage(nextPage);
    } catch (err) {
      console.error('=== Investigation: Failed to load more cases ===', err);
    } finally {
      setLoadingMore(false);
    }
  };

  // Check if there are more cases to load
  const hasMoreCases = cases.length < totalCases;

  // Filter by search with smart matching
  const filteredCases = useMemo(() => {
    if (!searchQuery) return cases;
    const query = searchQuery.toLowerCase().trim();

    return cases.filter((c) => {
      const caseId = c.case_id.toLowerCase();
      const userId = c.user_id.toLowerCase();

      // Direct match with case_id or user_id
      if (caseId === query || userId === query) {
        return true;
      }

      // Numeric match: if searching for "01428", match "CASE-01428"
      const isNumericQuery = /^\d+$/.test(query);
      if (isNumericQuery) {
        const caseIdNumber = caseId.replace('case-', '');
        return caseIdNumber === query;
      }

      // CASE- prefix match: "case-01428" matches "CASE-01428"
      if (query.startsWith('case-') || query.startsWith('case_')) {
        return caseId === query;
      }

      // U prefix match: "u01428" matches "U01428"
      if (query.startsWith('u')) {
        return userId === query;
      }

      return false;
    });
  }, [cases, searchQuery]);

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
              placeholder="Search by case number, CASE-XXXXX, or User ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Smart search: case number, CASE-XXXXX, or User ID (UXXXXX) all work
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
                Showing {filteredCases.length} of {totalCases} cases • Sorted by risk score
              </p>
            </div>
            <div className="divide-y divide-slate-200 max-h-[600px] overflow-y-auto">
              {loading ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  Loading investigation cases...
                </div>
              ) : error ? (
                <div className="p-8 text-center text-red-500 text-sm">
                  {error}
                </div>
              ) : filteredCases.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  {searchQuery ? `No cases found matching "${searchQuery}"` : 'No cases available. Upload data to generate investigation cases.'}
                </div>
              ) : (
                <>
                  {filteredCases.map((caseItem) => (
                    <div
                      key={caseItem.case_id}
                      onClick={() => handleCaseSelect(caseItem)}
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
                  ))}

                  {/* Load More Button */}
                  {!searchQuery && hasMoreCases && (
                    <div className="p-3 border-t border-slate-200">
                      <button
                        onClick={loadMoreCases}
                        disabled={loadingMore}
                        className="w-full py-2 px-4 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loadingMore ? 'Loading...' : `Load More (${totalCases - filteredCases.length} remaining)`}
                      </button>
                    </div>
                  )}
                </>
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
                    {selectedCase.detection_methods && selectedCase.detection_methods.length > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Detection Methods</span>
                        <div className="flex gap-1">
                          {selectedCase.detection_methods.map(method => {
                            const isLightGBM = method === 'LightGBM';
                            const isGraph = method === 'Graph Network';
                            return (
                            <span key={method} className={`px-2 py-0.5 text-xs font-medium rounded ${
                              isLightGBM
                                ? 'bg-blue-100 text-blue-700 border border-blue-200'
                                : isGraph
                                ? 'bg-cyan-100 text-cyan-700 border border-cyan-200'
                                : 'bg-slate-100 text-slate-700 border border-slate-200'
                            }`}>
                              {isLightGBM ? 'ML' : isGraph ? 'Graph' : 'Rule'}
                            </span>
                          )})}
                        </div>
                      </div>
                    )}
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Account Age</span>
                      <span className="font-medium text-slate-900">
                        {typeof selectedCase.account_age === 'number'
                          ? `${selectedCase.account_age} days`
                          : selectedCase.account_age}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Total Volume</span>
                      <span className="font-medium text-slate-900">
                        {typeof selectedCase.total_volume === 'number'
                          ? `$${selectedCase.total_volume.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                          : selectedCase.total_volume}
                      </span>
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
                    {selectedCase.risk_explanation.contributingFactors.map((factor, index) => (
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
