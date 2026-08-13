/**
 * Investigation Workspace Page
 *
 * Risk analyst investigation interface for detailed case analysis.
 * Two-panel layout: Investigation Queue (left) + Case Detail (right).
 *
 * MVP: Risk investigation workspace for analyst decision support.
 * NOT a Case Management System - no workflow or status tracking.
 */
import { useState, useEffect } from 'react';
import { riskApi, PolicyCitation, Explanation } from '../services/api';

// Simple tooltip component
function Tooltip({ content, children }: { content: string; children: React.ReactNode }) {
  return (
    <div className="group relative inline-block">
      {children}
      <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-64 bg-slate-900 text-white text-xs rounded-lg p-3 shadow-lg z-50">
        <div className="font-semibold mb-1">Cluster Risk Score</div>
        <div className="text-slate-300">{content}</div>
        <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-slate-900"></div>
      </div>
    </div>
  );
}

// Citation Modal Component
function CitationModal({ citation, onClose }: { citation: PolicyCitation | null; onClose: () => void }) {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-slate-200 flex justify-between items-start">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-slate-900">Policy Citation [{citation.id}]</h3>
            <p className="text-sm text-slate-600 mt-1">Source: {citation.doc}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-1">Section</h4>
            <p className="text-sm text-slate-900 bg-slate-50 px-3 py-2 rounded">{citation.section}</p>
          </div>
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-1">Quote</h4>
            <p className="text-sm text-slate-900 bg-slate-50 px-3 py-2 rounded whitespace-pre-wrap">{citation.quote}</p>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-1">Reference ID</h4>
            <p className="text-xs text-slate-500 font-mono bg-slate-50 px-3 py-2 rounded">{citation.chunk_id}</p>
          </div>
        </div>
        <div className="p-4 border-t border-slate-200 bg-slate-50">
          <button
            onClick={onClose}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// Helper to render text with clickable citations
function renderTextWithCitations(
  text: string,
  citations: PolicyCitation[],
  onCitationClick: (citation: PolicyCitation) => void
) {
  if (!citations || citations.length === 0) {
    return <span>{text}</span>;
  }

  // Split text by citation patterns like [1], [2], etc.
  const parts = text.split(/(\[\d+\])/g);

  return (
    <>
      {parts.map((part, idx) => {
        const match = part.match(/\[(\d+)\]/);
        if (match) {
          const citationId = parseInt(match[1], 10);
          const citation = citations.find((c) => c.id === citationId);
          if (citation) {
            return (
              <button
                key={idx}
                onClick={() => onCitationClick(citation)}
                className="inline-flex items-center text-blue-600 hover:text-blue-800 underline cursor-pointer text-xs font-medium"
              >
                [{citationId}]
              </button>
            );
          }
        }
        return <span key={idx}>{part}</span>;
      })}
    </>
  );
}

// Check if a finding is score-related (for filtering in Policy-backed Narrative)
function isScoreRelatedFinding(finding: string): boolean {
  const scoreKeywords = ['score', 'signal', 'ml ', 'rule ', 'graph ', 'probability', 'threshold'];
  const lowerFinding = finding.toLowerCase();
  return scoreKeywords.some(keyword => lowerFinding.includes(keyword));
}

// Filter findings to prioritize non-score content for Policy-backed Narrative
function filterKeyFindings(findings: string[]): { nonScoreFindings: string[]; scoreFindings: string[] } {
  const nonScoreFindings: string[] = [];
  const scoreFindings: string[] = [];

  findings.forEach(finding => {
    if (isScoreRelatedFinding(finding)) {
      scoreFindings.push(finding);
    } else {
      nonScoreFindings.push(finding);
    }
  });

  return { nonScoreFindings, scoreFindings };
}

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

  let summary = `This account received a ${item.risk_level.toLowerCase()} risk score (${Number(item.risk_score).toFixed(2)}/100).`;
  const contributingFactors: string[] = [];

  if (mlScore > 0) {
    contributingFactors.push(`ML Signal Score: ${Number(mlScore).toFixed(2)}`);
  }
  if (ruleScore > 0) {
    contributingFactors.push(`Rule Engine Signal Score: ${Number(ruleScore).toFixed(2)}`);
  }
  if (graphScore > 0) {
    contributingFactors.push(`Graph Network Signal Score: ${Number(graphScore).toFixed(2)}`);
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
    risk_score: Number(item.risk_score),
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
      signal_analysis: `Risk analysis based on multiple detection methods. ML score: ${Number(mlScore).toFixed(2)}, Rule score: ${Number(ruleScore).toFixed(2)}, Graph score: ${Number(graphScore).toFixed(2)}.`,
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

  // Explanation state
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [explanationError, setExplanationError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<PolicyCitation | null>(null);
  const [activeTab, setActiveTab] = useState<'evidence' | 'policy'>('evidence');

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

  // Fetch explanation for a selected case
  const fetchExplanation = async (userId: string) => {
    try {
      setLoadingExplanation(true);
      setExplanationError(null);
      // Use cached explanations in the investigation workflow.
      // Evaluation scripts can bypass cache when testing fresh generation.
      const explanationData = await riskApi.generateExplanation(userId, false);
      console.log('=== Explanation Debug ===');
      console.log('Total citations:', explanationData?.citations?.length);
      console.log('Citation IDs:', explanationData?.citations?.map((c: any) => c.id));
      console.log('Explanation:', explanationData);
      setExplanation(explanationData);
    } catch (err) {
      console.error('Failed to load explanation:', err);
      setExplanationError('Failed to load explanation. The case will still show other evidence.');
    } finally {
      setLoadingExplanation(false);
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
    setDisplayedNetworkCount(3); // Reset to show top 3 network connections initially
    setExpandedNetworkAccounts(new Set()); // Reset expanded accounts
    fetchCaseDetail(caseItem); // Fetch details in background
    fetchCaseEvidence(caseItem.user_id); // Fetch evidence in background
    fetchNetworkSignals(caseItem.user_id, true); // Fetch network signals in background (initial load)
    fetchExplanation(caseItem.user_id); // Fetch explanation in background
  };

  // Fetch cases from backend API (uses server-side search when searchQuery is set)
  useEffect(() => {
    const fetchCases = async () => {
      try {
        setLoading(true);
        setError(null);
        console.log('=== Investigation: Fetching cases from backend ===');

        // Use server-side search if search query exists
        const apiParams: { page: number; page_size: number; search?: string } = { page: 1, page_size: searchQuery ? 100 : PAGE_SIZE };
        if (searchQuery.trim()) {
          apiParams.search = searchQuery.trim();
        }

        const response = await riskApi.getCases(apiParams);
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
  }, [searchQuery]); // Re-fetch when search query changes

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

  // Filter by search (server-side search is used, so cases are already filtered)
  const filteredCases = cases;

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


  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Investigation Workspace</h1>
        <p className="text-sm text-slate-600 mt-1">
          Review risk cases with multi-signal evidence, policy-backed explanations, and investigation context
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
                Showing {filteredCases.length} of {totalCases} cases requiring review • Sorted by risk score (highest first)
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
                        <span className="font-bold text-slate-900">{Number(caseItem.risk_score).toFixed(2)}/100</span>
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
                    <div className="text-3xl font-bold text-red-600">{Number(selectedCase.risk_score).toFixed(2)}</div>
                    <div className="text-xs text-slate-500">Risk Score /100</div>
                  </div>
                </div>
              </div>

              {/* User Profile Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Account Information */}
                <div className="bg-white rounded-lg border border-slate-200 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <h3 className="text-sm font-semibold text-slate-900">User Profile</h3>
                  </div>
                  <p className="text-xs text-slate-500 mb-3 -mt-2">Account metrics and trading statistics from uploaded dataset</p>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Risk Level</span>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getRiskLevelColor(selectedCase.risk_level)}`}>
                        {selectedCase.risk_level}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Risk Score</span>
                      <span className="font-medium text-slate-900">{Number(selectedCase.risk_score).toFixed(2)}/100</span>
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

              {/* Case Explanation (Unified Card with Tabs) */}
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">Case Explanation</h3>
                    <p className="text-xs text-slate-500 mt-1">
                      Evidence-based explanation with optional policy-backed narrative (read-only).
                    </p>
                  </div>
                  {/* Source Badge */}
                  {explanation && activeTab === 'policy' && (
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        explanation.explanation_source === 'LLM'
                          ? 'bg-purple-100 text-purple-700 border border-purple-200'
                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}>
                        Source: {explanation.explanation_source === 'LLM' ? 'LLM' : 'Model (Fallback)'}
                      </span>
                      {explanation.llm_error && (
                        <span className="text-amber-500" title={explanation.llm_error}>
                          ⚠
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Tab Control (Segmented Control) */}
                <div className="flex gap-2 mb-4 bg-slate-100 p-1 rounded-lg">
                  <button
                    onClick={() => setActiveTab('evidence')}
                    className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                      activeTab === 'evidence'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Evidence (Model Explainability)
                  </button>
                  <button
                    onClick={() => setActiveTab('policy')}
                    className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                      activeTab === 'policy'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Policy-backed Narrative (Citations)
                  </button>
                </div>

                {/* Tab 1: Evidence (Model Explainability) */}
                {activeTab === 'evidence' && (
                  <div className="space-y-4">
                    {/* Summary */}
                    <div>
                      <h4 className="text-xs font-semibold text-slate-700 mb-1">Risk Summary</h4>
                      <p className="text-sm text-slate-600">{selectedCase.risk_explanation.summary}</p>
                    </div>

                    {/* Contributing Factors */}
                    <div>
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

                    {/* Analyst Guidance */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <h4 className="text-xs font-semibold text-blue-900 mb-1">Recommended Analyst Action</h4>
                      <p className="text-xs text-blue-800">{selectedCase.risk_explanation.analyst_guidance}</p>
                    </div>

                    <p className="text-xs text-slate-500 italic">
                      This explanation is generated by the risk analysis model to support analyst decision-making. The final determination and action are made by the reviewing analyst.
                    </p>
                  </div>
                )}

                {/* Tab 2: Policy-backed Narrative (Citations) */}
                {activeTab === 'policy' && (
                  <div className="space-y-4">
                    {loadingExplanation ? (
                      <div className="text-center py-6 text-slate-500 text-sm">
                        Loading policy-backed narrative...
                      </div>
                    ) : explanationError ? (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                        <p className="text-sm text-yellow-800">{explanationError}</p>
                        <p className="text-xs text-yellow-700 mt-2">
                          You can still view the Evidence tab for model-generated analysis.
                        </p>
                      </div>
                    ) : explanation ? (
                      <div className="space-y-4">
                        {/* A. What this means (Policy-backed) */}
                        <div>
                          <h4 className="text-xs font-semibold text-slate-700 mb-2">What this means (Policy-backed)</h4>
                          <p className="text-sm text-slate-600">
                            {renderTextWithCitations(explanation.summary, explanation.citations, setSelectedCitation)}
                          </p>
                        </div>

                        {/* B. Top risk hypotheses */}
                        {explanation.key_findings && explanation.key_findings.length > 0 && (
                          <div>
                            <h4 className="text-xs font-semibold text-slate-700 mb-2">Top Risk Hypotheses</h4>
                            <ul className="space-y-2">
                              {(() => {
                                const { nonScoreFindings, scoreFindings } = filterKeyFindings(explanation.key_findings);

                                // Show non-score findings first
                                const displayFindings = nonScoreFindings.length > 0
                                  ? nonScoreFindings
                                  : explanation.key_findings.slice(0, 2);

                                return (
                                  <>
                                    {displayFindings.map((finding, index) => (
                                      <li key={index} className="text-sm text-slate-600 flex items-start gap-2">
                                        <span className="text-blue-600 font-medium flex-shrink-0">{index + 1}.</span>
                                        <span className="flex-1">
                                          {renderTextWithCitations(finding, explanation.citations, setSelectedCitation)}
                                        </span>
                                      </li>
                                    ))}
                                    {scoreFindings.length > 0 && nonScoreFindings.length > 0 && (
                                      <li className="text-xs text-slate-500 italic mt-2">
                                        See Evidence tab for detailed score breakdown.
                                      </li>
                                    )}
                                  </>
                                );
                              })()}
                            </ul>
                          </div>
                        )}

                        {/* C. Next actions (SOP-aligned) */}
                        {explanation.recommended_action && (
                          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                            <h4 className="text-xs font-semibold text-blue-900 mb-2">Next Actions (SOP-aligned)</h4>
                            <p className="text-sm text-blue-800 mb-2">
                              {renderTextWithCitations(explanation.recommended_action, explanation.citations, setSelectedCitation)}
                            </p>
                            <ul className="space-y-1 text-xs text-blue-700">
                              <li>• Manual review of account activity and relationships</li>
                              <li>• Request additional account context if needed</li>
                              <li>• Enhanced due diligence for high-risk cases</li>
                            </ul>
                            <p className="text-xs text-blue-600 italic mt-2">
                              These recommendations are non-automated; final decision by the reviewing analyst.
                            </p>
                          </div>
                        )}

                        {/* D. Missing info to confirm */}
                        {explanation?.missing_info && explanation.missing_info.length > 0 && (
                          <div>
                            <h4 className="text-xs font-semibold text-slate-700 mb-2">Missing Info to Confirm</h4>
                            <p className="text-xs text-slate-500 mb-2">
                              The following evidence gaps were identified in this case:
                            </p>
                            <ul className="space-y-1">
                              {explanation.missing_info.map((item, index) => (
                                <li key={index} className="text-xs text-slate-600 flex items-start gap-2">
                                  <span className="text-amber-600">•</span>
                                  <span>{item}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* E. Sources */}
                        {explanation.citations && explanation.citations.length > 0 && (
                          <div className="border-t border-slate-200 pt-3">
                            <details className="text-xs text-slate-600">
                              <summary className="cursor-pointer hover:text-slate-900 font-medium">
                                {explanation.citations.length} policy citation{explanation.citations.length > 1 ? 's' : ''} available. Click to view sources.
                              </summary>
                              <ul className="mt-2 space-y-1 pl-4">
                                {explanation.citations.map((citation) => (
                                  <li key={citation.id} className="flex items-start gap-2">
                                    <span className="text-blue-600 font-medium">[{citation.id}]</span>
                                    <span>
                                      <span className="font-medium">{citation.doc}</span>
                                      <span className="text-slate-500"> — {citation.section}</span>
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            </details>
                            <p className="text-xs text-slate-500 italic mt-2">
                              Click citation numbers in text above to view full details.
                            </p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-6 text-slate-500 text-sm">
                        No policy-backed narrative available for this case.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Risk Evidence Section */}
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <div className="flex items-center gap-2 mb-4">
                  <h3 className="text-sm font-semibold text-slate-900">Risk Evidence</h3>
                  <span className="text-xs text-slate-500">
                    Detailed evidence from database records supporting the risk assessment
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
                                <Tooltip content="Cluster Risk Score represents the overall risk level of the connected account group. It is calculated at the cluster level by considering all accounts and relationships within the network. This may differ from Graph Network Signal Score because: Graph Network Signal Score measures this individual account's risk contribution in the network, while Cluster Risk Score measures the overall risk of the connected account group.">
                                  <span className="text-slate-500 underline decoration-dotted decoration-slate-400 cursor-help">Cluster Risk Score:</span>
                                </Tooltip>
                                <span className="font-medium text-red-700 ml-1">{caseEvidence.network_evidence.cluster_risk_score.toFixed(2)}/100</span>
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
                              Network relationship evidence from graph analysis. Connected to {networkSignals.connected_account_count} account{networkSignals.connected_account_count > 1 ? 's' : ''} through shared devices or IPs.
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
                                    <div className="font-bold text-slate-900">{Number(account.risk_score).toFixed(2)}</div>
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
                            No network relationships detected in uploaded dataset.
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
                    No evidence available from database records
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
                evidence from uploaded data, and recommended actions.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Citation Modal */}
      {selectedCitation && (
        <CitationModal
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />
      )}
    </div>
  );
}
