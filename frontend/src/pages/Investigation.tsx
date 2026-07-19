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
  const [caseEvidence, setCaseEvidence] = useState<any>(null);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [networkSignals, setNetworkSignals] = useState<any>(null);
  const [loadingNetworkSignals, setLoadingNetworkSignals] = useState(false);
  const [loadingMoreNetworkSignals, setLoadingMoreNetworkSignals] = useState(false);
  const [displayedNetworkCount, setDisplayedNetworkCount] = useState(3);
  const [displayedTransactionCount, setDisplayedTransactionCount] = useState(3);
  const [expandedNetworkAccounts, setExpandedNetworkAccounts] = useState<Set<string>>(new Set());
  const PAGE_SIZE = 50; // Load 50 cases at a time

  // Load more transactions
  const loadMoreTransactions = () => {
    setDisplayedTransactionCount(prev => prev + 3);
  };

  // Load more network signals
  const loadMoreNetworkSignals = async () => {
    if (!networkSignals || !selectedCase) return;
    setLoadingMoreNetworkSignals(true);
    // Increase displayed count by 3, up to total available
    const newCount = Math.min(displayedNetworkCount + 3, networkSignals.connected_account_count);
    setDisplayedNetworkCount(newCount);
    setLoadingMoreNetworkSignals(false);
  };

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

  // Fetch case evidence for a selected case
  const fetchCaseEvidence = async (userId: string) => {
    try {
      setLoadingEvidence(true);
      const evidence = await riskApi.getCaseEvidence(userId);
      setCaseEvidence(evidence);
    } catch (err) {
      console.error('Failed to load case evidence:', err);
      setCaseEvidence(null);
    } finally {
      setLoadingEvidence(false);
    }
  };

  // Fetch network signals for a selected case
  const fetchNetworkSignals = async (userId: string, initialLoad: boolean = true) => {
    try {
      setLoadingNetworkSignals(initialLoad);
      if (initialLoad) {
        setDisplayedNetworkCount(3); // Reset to show top 3 initially
      }
      // Always fetch more than we need to support load more
      const signals = await riskApi.getNetworkSignals(userId, 50);
      setNetworkSignals(signals);
    } catch (err) {
      console.error('Failed to load network signals:', err);
      setNetworkSignals(null);
    } finally {
      setLoadingNetworkSignals(false);
    }
  };

  // Toggle network account expansion
  const toggleNetworkAccount = (userId: string) => {
    const newExpanded = new Set(expandedNetworkAccounts);
    if (newExpanded.has(userId)) {
      newExpanded.delete(userId);
    } else {
      newExpanded.add(userId);
    }
    setExpandedNetworkAccounts(newExpanded);
  };

  // Handle case selection with detail fetch
  const handleCaseSelect = (caseItem: InvestigationCase) => {
    setSelectedCase(caseItem); // Set immediately for UI responsiveness
    setDisplayedTransactionCount(3); // Reset to show top 3 transactions initially
    fetchCaseDetail(caseItem); // Fetch details in background
    fetchCaseEvidence(caseItem.user_id); // Fetch evidence in background
    fetchNetworkSignals(caseItem.user_id, true); // Fetch network signals in background (initial load)
    setExpandedNetworkAccounts(new Set()); // Reset expanded accounts
    setExpandedNetworkAccounts(new Set()); // Reset expanded accounts
    fetchCaseEvidence(caseItem.user_id); // Fetch evidence in background
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

              {/* Risk Evidence Section */}
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <div className="flex items-center gap-2 mb-4">
                  <h3 className="text-sm font-semibold text-slate-900">Risk Evidence</h3>
                  <span className="text-xs text-slate-500">
                    Detailed evidence from transactions, network, rules, and features
                  </span>
                </div>

                {loadingEvidence ? (
                  <div className="text-center py-8 text-slate-500 text-sm">
                    Loading risk evidence...
                  </div>
                ) : caseEvidence ? (
                  <div className="space-y-4">
                    {/* Transaction Evidence */}
                    {caseEvidence.transaction_evidence && caseEvidence.transaction_evidence.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-2">
                          💳 Transaction Signals
                          <span className="text-xs text-slate-400 font-normal">
                            {caseEvidence.transaction_evidence.length} suspicious transactions
                            {caseEvidence.transaction_evidence.length > 3 && (
                              <span> Showing top {Math.min(displayedTransactionCount, caseEvidence.transaction_evidence.length)}.</span>
                            )}
                          </span>
                        </h4>
                        <div className="bg-slate-50 rounded-lg p-3 space-y-2">
                          {caseEvidence.transaction_evidence.slice(0, displayedTransactionCount).map((tx: any) => (
                            <div key={tx.transaction_id} className="flex justify-between items-center text-xs border-b border-slate-100 pb-2 last:border-0 last:pb-0">
                              <div className="flex-1">
                                <span className="font-medium text-slate-900">{tx.symbol} {tx.side}</span>
                                <span className="text-slate-500 ml-2">{tx.transaction_id}</span>
                              </div>
                              <div className="text-right">
                                <div className="font-medium text-slate-900">${tx.value.toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                                <div className="text-slate-500">{tx.risk_reason}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                        {/* Load More Button for Transactions */}
                        {displayedTransactionCount < caseEvidence.transaction_evidence.length && (
                          <div className="pt-2">
                            <button
                              onClick={loadMoreTransactions}
                              className="w-full py-2 px-4 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
                            >
                              Load More ({caseEvidence.transaction_evidence.length - displayedTransactionCount} more transactions)
                            </button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Network Evidence - Enhanced with detailed account relationships */}
                    {(caseEvidence.network_evidence || networkSignals) && (
                      <div>
                        <h4 className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-2">
                          🕸️ Network Signals
                          {networkSignals && (
                            <span className="text-xs text-slate-400 font-normal">
                              {networkSignals.connected_account_count} connected accounts
                            </span>
                          )}
                        </h4>

                        {/* Cluster summary */}
                        {caseEvidence.network_evidence && (
                          <div className="bg-purple-50 rounded-lg p-3 mb-3">
                            <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                              <div>
                                <span className="text-slate-500">Cluster:</span>
                                <span className="font-medium text-slate-900 ml-1">{caseEvidence.network_evidence.cluster_name}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Type:</span>
                                <span className="font-medium text-slate-900 ml-1 capitalize">{caseEvidence.network_evidence.detection_type.replace('_', ' ')}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Members:</span>
                                <span className="font-medium text-slate-900 ml-1">{caseEvidence.network_evidence.member_count}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Cluster Risk:</span>
                                <span className="font-medium text-red-700 ml-1">{caseEvidence.network_evidence.cluster_risk_score.toFixed(1)}/100</span>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Detailed account relationships */}
                        {loadingNetworkSignals ? (
                          <div className="text-center py-4 text-slate-500 text-xs">
                            Loading network relationships...
                          </div>
                        ) : networkSignals && networkSignals.connected_accounts.length > 0 ? (
                          <div className="space-y-2">
                            <div className="text-xs text-slate-600 mb-2">
                              Suspicious network relationship detected. Connected to {networkSignals.connected_account_count} related accounts.
                              {networkSignals.connected_account_count > 3 && (
                                <span> Showing top {Math.min(displayedNetworkCount, networkSignals.connected_account_count)} riskiest connections.</span>
                              )}
                            </div>
                            {networkSignals.connected_accounts.slice(0, displayedNetworkCount).map((account: any) => (
                              <div key={account.user_id} className="bg-slate-50 rounded-lg border border-slate-200 overflow-hidden">
                                {/* Account header - always visible */}
                                <div
                                  onClick={() => toggleNetworkAccount(account.user_id)}
                                  className="flex items-center justify-between p-3 cursor-pointer hover:bg-slate-100 transition-colors"
                                >
                                  <div className="flex items-center gap-3">
                                    <span className="text-slate-400">
                                      {expandedNetworkAccounts.has(account.user_id) ? '▼' : '▶'}
                                    </span>
                                    <div>
                                      <div className="flex items-center gap-2">
                                        <span className="font-medium text-slate-900 text-sm">{account.user_id}</span>
                                        <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getRiskLevelColor(account.risk_level)}`}>
                                          {account.risk_level}
                                        </span>
                                      </div>
                                      <div className="text-xs text-slate-500 mt-1">
                                        {account.relationship_type.map((rt: string) => {
                                          if (rt === 'shared_device') return 'Shared Device Fingerprint';
                                          if (rt === 'shared_ip') return 'Shared IP Address';
                                          return rt;
                                        }).join(' • ')}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="text-right">
                                    <div className="font-bold text-slate-900">{account.risk_score}</div>
                                    <div className="text-xs text-slate-500">Risk Score</div>
                                  </div>
                                </div>

                                {/* Expanded details */}
                                {expandedNetworkAccounts.has(account.user_id) && (
                                  <div className="px-3 pb-3 pt-0 border-t border-slate-200">
                                    <div className="text-xs space-y-2 mt-2">
                                      {/* Device fingerprints */}
                                      {account.device_fingerprints && account.device_fingerprints.length > 0 && (
                                        <div className="flex items-start gap-2">
                                          <span className="text-slate-500 font-medium">Device ID:</span>
                                          <span className="font-mono text-slate-900">{account.device_fingerprints[0]}</span>
                                          {account.device_fingerprints.length > 1 && (
                                            <span className="text-slate-500">+{account.device_fingerprints.length - 1} more</span>
                                          )}
                                        </div>
                                      )}

                                      {/* Shared IPs */}
                                      {account.shared_ips && account.shared_ips.length > 0 && (
                                        <div className="flex items-start gap-2">
                                          <span className="text-slate-500 font-medium">IP Address:</span>
                                          <span className="font-mono text-slate-900">{account.shared_ips[0]}</span>
                                          {account.shared_ips.length > 1 && (
                                            <span className="text-slate-500">+{account.shared_ips.length - 1} more</span>
                                          )}
                                        </div>
                                      )}

                                      {/* No evidence */}
                                      {(!account.device_fingerprints || account.device_fingerprints.length === 0) &&
                                       (!account.shared_ips || account.shared_ips.length === 0) && (
                                        <div className="text-slate-500 italic">
                                          No evidence details available
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                            {/* Load More Button */}
                            {displayedNetworkCount < networkSignals.connected_account_count && (
                              <div className="pt-2">
                                <button
                                  onClick={loadMoreNetworkSignals}
                                  disabled={loadingMoreNetworkSignals}
                                  className="w-full py-2 px-4 text-sm font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                  {loadingMoreNetworkSignals
                                    ? 'Loading...'
                                    : `Load More (${networkSignals.connected_account_count - displayedNetworkCount} more accounts)`
                                  }
                                </button>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="text-xs text-slate-600">
                            No suspicious network relationships detected.
                          </div>
                        )}
                      </div>
                    )}

                    {/* Rule Evidence */}
                    {caseEvidence.rule_evidence && caseEvidence.rule_evidence.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-2">
                          ⚖️ Rule Signals
                        </h4>
                        <div className="space-y-2">
                          {caseEvidence.rule_evidence.map((rule: any, idx: number) => (
                            <div key={idx} className={`p-3 rounded-lg border ${
                              rule.severity === 'HIGH' || rule.severity === 'CRITICAL'
                                ? 'bg-red-50 border-red-200'
                                : 'bg-yellow-50 border-yellow-200'
                            }`}>
                              <div className="flex justify-between items-start mb-1">
                                <span className="font-medium text-sm text-slate-900">{rule.rule_name}</span>
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                  rule.severity === 'HIGH' || rule.severity === 'CRITICAL'
                                    ? 'bg-red-100 text-red-700'
                                    : 'bg-yellow-100 text-yellow-700'
                                }`}>
                                  {rule.severity}
                                </span>
                              </div>
                              <p className="text-xs text-slate-600">{rule.description}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Risk Drivers (from Feature Evidence) */}
                    {caseEvidence.feature_evidence && (
                      <div>
                        <h4 className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-2">
                          📊 Risk Drivers
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {[
                            { name: 'Shared Devices', value: caseEvidence.feature_evidence.shared_device_count, icon: '📱' },
                            { name: 'Linked Accounts', value: caseEvidence.feature_evidence.linked_account_count, icon: '🔗' },
                            { name: 'Trade Freq (24h)', value: caseEvidence.feature_evidence.trade_frequency_24h, icon: '📈' },
                            { name: 'Withdrawal Freq', value: caseEvidence.feature_evidence.withdrawal_frequency_24h, icon: '💸' },
                            { name: 'Account Age', value: caseEvidence.feature_evidence.account_age_days, suffix: ' days', icon: '📅' },
                            { name: 'Opposite Trade Ratio', value: caseEvidence.feature_evidence.opposite_trade_ratio, suffix: '%', icon: '🔄' },
                          ].map((driver, idx) => (
                            driver.value !== null && driver.value !== undefined && (
                              <div key={idx} className="bg-slate-50 rounded-lg p-2 text-center">
                                <div className="text-lg mb-1">{driver.icon}</div>
                                <div className="font-medium text-slate-900 text-sm">
                                  {driver.suffix === '%'
                                    ? `${(driver.value * 100).toFixed(0)}%`
                                    : driver.suffix === ' days'
                                    ? `${driver.value}d`
                                    : driver.value}
                                </div>
                                <div className="text-xs text-slate-500">{driver.name}</div>
                              </div>
                            )
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500 text-sm">
                    No evidence data available
                  </div>
                )}
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
