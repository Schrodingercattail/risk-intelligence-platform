/**
 * Model Monitoring Page
 *
 * Enterprise model monitoring dashboard with performance metrics,
 * population stability monitoring, and feature drift analysis.
 *
 * This page displays model evaluation results from uploaded dataset analysis.
 */
import { useState, useEffect } from 'react';
import { modelApi, FeatureImportance, ModelMonitoringData } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import UITooltip from '../components/UI/Tooltip';

// ============================================================================
// FEATURE DEFINITIONS
// ============================================================================

// Explicit sparse feature configuration
// Only these features can show "(sparse distribution)" annotation
// These features have zero-inflated distributions by design
const SPARSE_FEATURES = [
  'shared_device_count',
  'linked_account_count',
  'unique_ip_count',
] as const;

// Feature type definitions
type FeatureType = 'Behavioral' | 'Account' | 'Network' | 'Withdrawal';

const FEATURE_TYPES: Record<string, FeatureType> = {
  // Behavioral features - trading and activity patterns
  trade_frequency_7d: 'Behavioral',
  trade_frequency_24h: 'Behavioral',
  trade_volume_24h: 'Behavioral',
  avg_trade_size: 'Behavioral',
  opposite_trade_ratio: 'Behavioral',
  active_days_count: 'Behavioral',

  // Account features - user characteristics
  account_age_days: 'Account',

  // Network features - device and connection patterns
  shared_device_count: 'Network',
  linked_account_count: 'Network',
  unique_ip_count: 'Network',

  // Withdrawal features - cash-out behavior
  withdrawal_frequency_24h: 'Withdrawal',
  withdrawal_volume_24h: 'Withdrawal',
  withdrawal_risk_score: 'Withdrawal',
};

// Enhanced feature explanations with business context
const FEATURE_EXPLANATIONS: Record<string, string> = {
  // Behavioral features
  trade_frequency_7d: 'Weekly trading volume. Changes may indicate shifts in user engagement patterns.',
  trade_frequency_24h: 'Daily trading activity. Large changes may signal anomalous behavior or bot activity.',
  trade_volume_24h: 'Daily trade amounts. Changes in transaction scale may indicate risk pattern evolution.',
  avg_trade_size: 'Average transaction amount. Monetary feature with naturally skewed distribution. Interpret drift together with business context.',
  opposite_trade_ratio: 'Trading balance (buy vs sell mix). Changes indicate strategy shifts.',
  active_days_count: 'Platform engagement level. Changes in user activity patterns.',

  // Account features
  account_age_days: 'Account tenure. Newer user cohorts may have different risk characteristics.',

  // Network features (sparse distributions)
  shared_device_count: 'Device sharing footprint. Sparse distribution naturally creates larger PSI movement.',
  linked_account_count: 'Graph relationship feature. Large PSI may indicate changes in account linkage patterns.',
  unique_ip_count: 'IP connection diversity. Sparse distribution naturally creates larger PSI movement.',

  // Withdrawal features
  withdrawal_frequency_24h: 'Cash-out frequency. Changes indicate withdrawal pattern evolution.',
  withdrawal_volume_24h: 'Withdrawal amounts. Changes in risk transfer patterns.',
  withdrawal_risk_score: 'Withdrawal risk indicators. Changes in cash-out risk behavior.',
};

// Feature count constants for product consistency
// Risk features exclude user_id and other identifiers - only predictive model inputs
const RISK_FEATURE_COUNT = 13;    // Number of risk features used by LightGBM model

// ============================================================================
// UI CONSTANTS
// ============================================================================

// Status colors for PSI drift analysis
const PSI_STATUS_COLORS = {
  stable: 'bg-green-100 text-green-800 border-green-200',
  warning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  drift: 'bg-orange-100 text-orange-800 border-orange-200',
  unknown: 'bg-slate-100 text-slate-800 border-slate-200',
};

// (Removed unused ModelHealthStatus type)

// ============================================================================
// TOOLTIP COMPONENTS
// ============================================================================

// Overall PSI Tooltip - Updated with v2_diverse baseline context
const OverallPSITooltip = () => (
  <UITooltip
    position="left"
    content={
      <div className="text-sm max-w-xs text-left">
        <p className="font-semibold mb-2">Population Stability Index (PSI)</p>
        <p className="mb-2 text-xs text-slate-600">
          Latest PSI snapshot - compares current population against the v2_diverse training baseline.
        </p>
        <div className="text-xs space-y-1 mb-2">
          <div><span className="font-medium text-green-700">&lt; 0.10:</span> Stable</div>
          <div><span className="font-medium text-yellow-700">0.10 - 0.25:</span> Minor drift</div>
          <div><span className="font-medium text-orange-700">&gt; 0.25:</span> Significant drift detected</div>
        </div>
        <p className="text-xs text-slate-500 italic border-t pt-2 mt-2">
          PSI measures feature distribution changes between current data and the original training baseline.
          It is used to detect population drift after deployment, not model validation performance.
        </p>
      </div>
    }
  >
    <button className="text-slate-400 hover:text-slate-600">
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
          clipRule="evenodd"
        />
      </svg>
    </button>
  </UITooltip>
);

// Feature Drift Analysis Tooltip
const FeatureDriftTooltip = () => (
  <UITooltip
    content={
      <div className="text-sm max-w-xs">
        <p className="font-semibold mb-2">Feature-Level PSI Analysis</p>
        <p className="mb-2 text-xs text-slate-600">
          Identifies which user attributes contribute most to population changes from the training baseline.
        </p>
        <div className="text-xs space-y-1 mb-2">
          <div><span className="font-medium text-green-700">PSI &lt; 0.1:</span> Stable</div>
          <div><span className="font-medium text-yellow-700">PSI 0.1 - 0.25:</span> Minor drift</div>
          <div><span className="font-medium text-orange-700">PSI &gt; 0.25:</span> Significant drift detected</div>
        </div>
        <p className="text-xs text-slate-500 italic border-t pt-2 mt-2">
          Features marked with "(sparse distribution)" have zero-inflated distributions which naturally create larger PSI movement.
        </p>
      </div>
    }
  >
    <button className="text-slate-400 hover:text-slate-600">
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
          clipRule="evenodd"
        />
      </svg>
    </button>
  </UITooltip>
);

// Feature Count Tooltip
const FeatureCountTooltip = () => (
  <UITooltip
    position="top"
    content={
      <div className="text-sm max-w-xs">
        <p className="font-semibold mb-2">Risk Features Count</p>
        <div className="text-xs space-y-1">
          <div><span className="font-medium">Total:</span> {RISK_FEATURE_COUNT} risk features</div>
          <div className="text-slate-500 italic mt-2">
            Risk features are predictive model input features. Excludes identifiers like user_id and metadata columns.
          </div>
        </div>
      </div>
    }
  >
    <button className="text-slate-400 hover:text-slate-600">
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
          clipRule="evenodd"
        />
      </svg>
    </button>
  </UITooltip>
);

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

// Check if a feature is sparse (zero-inflated distribution)
const isSparseFeature = (featureName: string): boolean => {
  return SPARSE_FEATURES.includes(featureName as any);
};

// Get feature type
const getFeatureType = (featureName: string): FeatureType => {
  return FEATURE_TYPES[featureName] || 'Behavioral';
};

// Get feature type color
const getFeatureTypeColor = (type: FeatureType): string => {
  switch (type) {
    case 'Behavioral': return 'bg-blue-100 text-blue-800';
    case 'Account': return 'bg-purple-100 text-purple-800';
    case 'Network': return 'bg-amber-100 text-amber-800';
    case 'Withdrawal': return 'bg-emerald-100 text-emerald-800';
    default: return 'bg-slate-100 text-slate-800';
  }
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function ModelMonitoring() {
  const [metrics, setMetrics] = useState<ModelMonitoringData>({
    model_name: '',
    version: '',
    metrics: { auc: null, ks: null, psi: null },
    psi_status: 'unknown',
    psi_features: [],
  });
  const [psiFeatures, setPsiFeatures] = useState<FeatureImportance[]>([]);
  const [featureImportance, setFeatureImportance] = useState<FeatureImportance[]>([]);
  const [loading, setLoading] = useState(true);

  // Model retraining state
  const [showRetrainModal, setShowRetrainModal] = useState(false);
  const [showTrainingResultModal, setShowTrainingResultModal] = useState(false);
  const [trainingResult, setTrainingResult] = useState<any>(null);
  const [isTraining, setIsTraining] = useState(false);
  const [trainingDataset, setTrainingDataset] = useState<'historical' | 'current'>('historical');  // Default: historical

  useEffect(() => {
    loadCompleteMonitoring();
  }, []);

  const loadCompleteMonitoring = async () => {
    try {
      setLoading(true);
      const data = await modelApi.getMonitoring();
      setMetrics(data);

      // Extract PSI features for drift analysis
      if (data.psi_features && data.psi_features.length > 0) {
        setPsiFeatures(
          data.psi_features.map((f: any) => ({
            name: f.feature,
            importance: f.psi || 0,
            rank: 0,
            status: f.status,
          }))
        );
      }

      // Fetch feature importance separately
      try {
        const importanceData = await modelApi.getFeatureImportance();
        if (importanceData.features && importanceData.features.length > 0) {
          setFeatureImportance(importanceData.features);
        }
      } catch (error) {
        console.error('Failed to load feature importance:', error);
        setFeatureImportance([]);
      }
    } catch (error) {
      console.error('Failed to load model data:', error);
      // Ensure component still renders even on error
      setMetrics({
        model_name: 'LightGBM Risk Engine',
        version: 'v1.0',
        metrics: { auc: null, ks: null, psi: null },
        psi_status: 'unknown',
        psi_features: [],
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle model training
  const handleRetrainModel = async () => {
    try {
      setIsTraining(true);
      setShowRetrainModal(false);

      const result = await modelApi.trainModel(trainingDataset);

      if (result.status === 'completed') {
        setTrainingResult(result);
        setShowTrainingResultModal(true);

        // Reload monitoring data to show the new model
        await loadCompleteMonitoring();
      } else {
        setTrainingResult({
          status: 'failed',
          error: result.error || 'Training failed',
        });
        setShowTrainingResultModal(true);
      }
    } catch (error: any) {
      console.error('Training error:', error);
      setTrainingResult({
        status: 'failed',
        error: error.message || 'Training failed',
      });
      setShowTrainingResultModal(true);
    } finally {
      setIsTraining(false);
    }
  };

  // Handle model activation
  const handleActivateModel = async () => {
    if (!trainingResult || !trainingResult.model_id) {
      return;
    }

    try {
      const result = await modelApi.activateModel(trainingResult.model_id);

      if (result.status === 'success') {
        // Close the training result modal
        setShowTrainingResultModal(false);

        // Reload monitoring data to reflect activation
        await loadCompleteMonitoring();
      }
    } catch (error: any) {
      console.error('Activation error:', error);
    }
  };

  // Prepare chart data
  const psiChartData = psiFeatures.map((f) => ({
    name: f.name,
    psi: f.importance,
    status: f.status,
    isSparse: isSparseFeature(f.name),
    featureType: getFeatureType(f.name),
  }));

  const importanceChartData = featureImportance.map((f) => ({
    name: f.name,
    fullName: f.name,
    importance: f.importance ?? 0,  // Database stores values as percentages (0-100), no multiplication needed
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading model metrics...</div>
      </div>
    );
  }

  const overallStatusColor = PSI_STATUS_COLORS[metrics.psi_status as keyof typeof PSI_STATUS_COLORS] || PSI_STATUS_COLORS.drift;
  const hasBaseline = metrics.metrics?.psi !== null && metrics.metrics?.psi !== undefined;

  // Get PSI timestamp if available (optional field)
  const psiTimestamp = (metrics as any).psi_calculated_at ? new Date((metrics as any).psi_calculated_at).toLocaleString() : null;

  return (
    <div className="space-y-8">
      {/* Page Header - Simplified */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Model Health</h1>
        <p className="text-sm text-slate-600 mt-1">
          Model performance and population stability monitoring
        </p>
      </div>

      {/* Model Overview Card - Simplified Header */}
      <section className="bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 rounded-lg p-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl flex items-center justify-center bg-gradient-to-br from-blue-600 to-indigo-700 shadow-lg">
            <span className="text-white text-xl font-bold">ML</span>
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-semibold text-slate-900">
              {metrics.model_name || 'LightGBM Risk Model'}
            </h1>
            <p className="text-sm text-slate-600 mt-0.5">
              Version {metrics.version || 'v1.0'} • {metrics.algorithm || 'LightGBM'}
            </p>
          </div>
          <button
            onClick={() => setShowRetrainModal(true)}
            disabled={isTraining}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isTraining ? 'Training...' : 'Retrain Model'}
          </button>
        </div>
      </section>

      {/* Model Configuration Card - Compact metadata */}
      <section className="bg-white rounded-lg border border-slate-200 p-5">
        <h2 className="text-sm font-semibold text-slate-900 mb-4">Model Configuration</h2>
        <div className="flex flex-col md:flex-row gap-5">
          <div className="flex-1 flex flex-col min-w-0">
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-1 h-4">Training Dataset</div>
            <div className="text-sm font-medium text-slate-900">v2_diverse</div>
          </div>
          <div className="flex-1 flex flex-col min-w-0">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 uppercase tracking-wide mb-1 h-4">
              <span>Training Features</span>
              <FeatureCountTooltip />
            </div>
            <div className="text-sm font-medium text-slate-900">{RISK_FEATURE_COUNT} risk features</div>
          </div>
          <div className="flex-1 flex flex-col min-w-0">
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-1 h-4">Algorithm</div>
            <div className="text-sm font-medium text-slate-900">LightGBM</div>
          </div>
          <div className="flex-1 flex flex-col min-w-0">
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-1 h-4">Training Date</div>
            <div className="text-sm font-medium text-slate-900">
              {metrics.deployed_at ? new Date(metrics.deployed_at).toLocaleDateString() : 'N/A'}
            </div>
          </div>
          <div className="flex-1 flex flex-col min-w-0">
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-1 h-4">Purpose</div>
            <div className="text-sm font-medium text-slate-900">Production baseline</div>
          </div>
        </div>
      </section>

      {/* Model Performance Section */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Model Performance</h2>
          <UITooltip
            content={
              <div className="text-sm max-w-xs">
                <p className="font-semibold mb-1">Model Performance Metrics</p>
                <p className="text-xs text-slate-600 mb-2">
                  <span className="font-medium text-blue-700">Model Performance:</span> AUC and KS measure predictive quality during validation.
                </p>
                <p className="text-xs text-slate-600">
                  <span className="font-medium text-blue-700">Model Stability:</span> PSI measures population drift between current dataset and training baseline.
                </p>
              </div>
            }
          >
            <button className="text-slate-400 hover:text-slate-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
          </UITooltip>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-700">AUC Score</h3>
              <UITooltip
                position="left"
                content={
                  <div className="text-sm max-w-xs">
                    <p className="font-semibold mb-1">Area Under ROC Curve</p>
                    <p className="text-xs text-slate-600">
                      Measures the model's ability to distinguish risky and non-risky users.
                      Higher values indicate better ranking performance.
                    </p>
                  </div>
                }
              >
                <button className="text-slate-400 hover:text-slate-600">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </button>
              </UITooltip>
            </div>
            <div className="text-3xl font-bold text-slate-900">
              {(metrics.metrics?.auc ?? 0).toFixed(3)}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Validated on v2_diverse training dataset
            </p>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-700">KS Statistic</h3>
              <UITooltip
                position="left"
                content={
                  <div className="text-sm max-w-xs">
                    <p className="font-semibold mb-1">Kolmogorov-Smirnov Statistic</p>
                    <p className="text-xs text-slate-600">
                      Measures the maximum separation between risky and normal users.
                      Higher values indicate stronger discrimination.
                    </p>
                  </div>
                }
              >
                <button className="text-slate-400 hover:text-slate-600">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </button>
              </UITooltip>
            </div>
            <div className="text-3xl font-bold text-slate-900">
              {(metrics.metrics?.ks ?? 0).toFixed(3)}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Validated on v2_diverse training dataset
            </p>
          </div>
        </div>
      </section>

      {/* Model Performance Metrics Section - Removed, now using Validation Metrics above */}

      {/* Model Stability Section - Redesigned with clear hierarchy */}
      <section>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Model Stability</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Baseline Integrity Card - Engineering validation (smaller, secondary) */}
          <div className="bg-slate-50 rounded-lg border border-slate-200 p-6">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="font-semibold text-slate-700 text-sm">Baseline Integrity</h3>
              <UITooltip content="Technical validation that PSI baseline was generated correctly (engineering metric, not production KPI)">
                <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </UITooltip>
            </div>

            {metrics.baseline_validation_psi !== null && metrics.baseline_validation_psi !== undefined ? (
              <>
                <div className="flex items-baseline gap-2 mb-2">
                  <p className="text-2xl font-semibold text-slate-700">
                    {Number(metrics.baseline_validation_psi).toFixed(4)}
                  </p>
                  <div className={`px-2 py-0.5 rounded text-xs font-semibold border ${
                    metrics.baseline_validation_status === 'passed'
                      ? 'bg-green-100 text-green-700 border-green-200'
                      : metrics.baseline_validation_status === 'failed'
                      ? 'bg-red-100 text-red-700 border-red-200'
                      : 'bg-slate-100 text-slate-600 border-slate-200'
                  }`}>
                    {metrics.baseline_validation_status === 'passed' && 'Passed'}
                    {metrics.baseline_validation_status === 'failed' && 'Failed'}
                    {metrics.baseline_validation_status === 'not_validated' && 'Pending'}
                  </div>
                </div>
                <p className="text-xs text-slate-500">
                  Training baseline matches saved feature distribution
                </p>
              </>
            ) : (
              <div className="text-center py-3">
                <p className="text-xs text-slate-500">No validation data</p>
              </div>
            )}
          </div>

          {/* Production Drift Monitoring Card - Main KPI (larger, prominent) */}
          <div className="md:col-span-2 bg-gradient-to-br from-slate-50 to-blue-50 rounded-lg border-2 border-slate-200 p-6">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="font-semibold text-slate-900">Production Drift Monitoring</h3>
              <OverallPSITooltip />
            </div>
            <p className="text-xs text-slate-600 mb-4">
              Current population compared with v2_diverse training baseline
            </p>

            {hasBaseline && metrics.metrics?.psi !== null && metrics.metrics?.psi !== undefined ? (
              <div className="flex items-center gap-6">
                <div className="flex items-baseline gap-3">
                  <p className="text-4xl font-bold text-slate-900">
                    {Number(metrics.metrics.psi).toFixed(4)}
                  </p>
                  <div className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${overallStatusColor}`}>
                    {metrics.psi_status === 'stable' && '✓ Stable'}
                    {metrics.psi_status === 'warning' && '⚠ Minor Drift'}
                    {metrics.psi_status === 'drift' && '⚠ Drift Detected'}
                    {metrics.psi_status === 'unknown' && 'Unknown'}
                  </div>
                </div>
                <div className="text-xs text-slate-600">
                  {psiTimestamp && (
                    <p>Calculated: {psiTimestamp}</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-sm text-slate-500">
                  {hasBaseline
                    ? 'Run monitoring to calculate production PSI'
                    : 'Requires training baseline to monitor drift'}
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Model Drift Monitoring Section */}
      <section>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Feature Distribution Analysis</h2>
        <p className="text-sm text-slate-600 mb-4">
          Detailed feature-level PSI breakdown for drift identification
        </p>

        {/* Feature-Level PSI Analysis */}
        {!hasBaseline ? (
          // Empty state
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-sm font-semibold text-slate-900 mb-1">No PSI Baseline Available</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mb-2">
                PSI monitoring requires comparison between current uploaded data and training baseline.
              </p>
              <p className="text-xs text-slate-400">
                Training data (v2_diverse) serves as the reference baseline for drift detection.
              </p>
            </div>
          </div>
        ) : null}

        {/* Feature-Level PSI Analysis */}
        {hasBaseline && psiChartData.length > 0 && (
          <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-slate-900 flex items-center gap-2">
                Feature Distribution Changes
                <FeatureDriftTooltip />
              </h3>
              <span className="text-xs text-slate-500">
                {psiChartData.length} features monitored
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Feature
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider w-64">
                      Business Meaning
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                      PSI Value
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-slate-200">
                  {psiChartData
                    .filter(f => f.psi > 0.05)
                    .sort((a, b) => b.psi - a.psi)
                    .slice(0, 10)
                    .map((feature) => (
                    <tr key={feature.name} className={feature.psi > 1.0 && feature.isSparse ? 'bg-amber-50' : ''}>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-slate-900">
                        {feature.name}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getFeatureTypeColor(feature.featureType)}`}>
                          {feature.featureType}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 max-w-xs">
                        {FEATURE_EXPLANATIONS[feature.name] || 'Feature contribution to risk prediction'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900 text-center font-mono">
                        {feature.psi.toFixed(3)}
                        {feature.isSparse && feature.psi > 1.0 && (
                          <span className="ml-2 text-xs text-amber-600 italic">(sparse distribution)</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                            PSI_STATUS_COLORS[feature.status as keyof typeof PSI_STATUS_COLORS] ||
                              'bg-slate-100 text-slate-800 border-slate-200'
                          }`}
                        >
                          {feature.status === 'stable' && 'Stable'}
                          {feature.status === 'warning' && 'Minor Drift'}
                          {feature.status === 'drift' && 'Significant Drift'}
                          {!feature.status && 'Unknown'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {psiChartData.filter(f => f.isSparse && f.psi > 1.0).length > 0 && (
              <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-md">
                <p className="text-xs text-amber-800">
                  <span className="font-medium">Note:</span> Features marked with "(sparse distribution)" have zero-inflated distributions
                  (most users have zero values) which naturally creates larger PSI movement. This is expected behavior for network-related features.
                </p>
              </div>
            )}
          </div>
        )}

        {/* PSI by Feature Chart */}
        {hasBaseline && psiChartData.length > 0 && (
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-slate-900">PSI Distribution by Feature</h3>
              <div className="flex items-center gap-3 text-xs">
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-green-500"></div>
                  <span className="text-slate-600">Stable (&lt;0.1)</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-yellow-500"></div>
                  <span className="text-slate-600">Minor Drift (0.1-0.25)</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-orange-500"></div>
                  <span className="text-slate-600">Significant Drift (&gt;0.25)</span>
                </div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={psiChartData} layout="vertical" margin={{ left: 20, right: 50, top: 5, bottom: 5 }}>
                <XAxis
                  type="number"
                  stroke="#64748b"
                  style={{ fontSize: '12px' }}
                  tickFormatter={(value) => value.toFixed(2)}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={160}
                  tick={{ fontSize: 11 }}
                  stroke="#64748b"
                  interval={0}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    padding: '8px 12px',
                  }}
                  formatter={(value: any, name: string) => [
                    name === 'psi' ? Number(value).toFixed(3) : value,
                    name === 'psi' ? 'PSI Value' : name
                  ]}
                />
                <Bar
                  dataKey="psi"
                  maxBarSize={28}
                  radius={[0, 6, 6, 0]}
                  cursor="default"
                >
                  {psiChartData.map((entry) => {
                    const psi = entry.psi;
                    // Color coding based on PSI value
                    const color =
                      psi > 0.25 ? '#f97316' :     // Significant drift - orange
                      psi > 0.10 ? '#f59e0b' :     // Minor drift - yellow
                      '#10b981';                   // Stable - green
                    return <Cell key={entry.name} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {/* Risk Drivers - Feature Importance */}
      <section className="bg-white rounded-lg border border-slate-200 p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Risk Drivers</h2>
            <p className="text-sm text-slate-600 mt-1">
              Feature importance from model analysis (contribution to risk prediction)
            </p>
          </div>
        </div>
        {importanceChartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={importanceChartData} layout="vertical" margin={{ left: 20, right: 50, top: 5, bottom: 5 }}>
              <XAxis
                type="number"
                stroke="#64748b"
                style={{ fontSize: '12px' }}
                tickFormatter={(value) => `${value}%`}
              />
              <YAxis
                dataKey="name"
                type="category"
                width={160}
                tick={{ fontSize: 11 }}
                stroke="#64748b"
                interval={0}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '8px 12px',
                }}
                formatter={(value: any) => [`${Number(value).toFixed(1)}%`, 'Contribution']}
              />
              <Bar
                dataKey="importance"
                name="Contribution"
                maxBarSize={30}
                radius={[0, 6, 6, 0]}
                cursor="default"
              >
                {importanceChartData.map((_, index) => (
                  <Cell key={index} fill={index % 2 === 0 ? '#3b82f6' : '#6366f1'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center py-12 bg-slate-50 rounded-lg">
            <div className="text-slate-500 text-sm">No risk driver data available</div>
            <p className="text-xs text-slate-400 mt-1">Feature importance will appear after model evaluation</p>
          </div>
        )}
      </section>

      {/* Retrain Model Modal */}
      {showRetrainModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg border border-slate-200 p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">Retrain Risk Model</h3>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Training Dataset</label>
                <select
                  value={trainingDataset}
                  onChange={(e) => setTrainingDataset(e.target.value as 'historical' | 'current')}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="historical">Historical training dataset (v2_diverse)</option>
                  <option value="current">Current uploaded dataset</option>
                </select>
                <p className="text-xs text-slate-500 mt-2">
                  {trainingDataset === 'historical' ? (
                    <>
                      Uses official baseline training data (test_data/v2_diverse) with diverse fraud scenarios.
                      This is the recommended dataset for model training.
                    </>
                  ) : (
                    <>
                      Uses feature data currently loaded in the database (FeatureTable).
                      Labels are generated from behavioral signals during training.
                    </>
                  )}
                </p>
              </div>

              <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-600">
                <div className="font-medium mb-1">Training Configuration:</div>
                <div>Algorithm: LightGBM</div>
                <div>Features: {RISK_FEATURE_COUNT} risk features</div>
                <div>Labels: Generated from behavioral signals</div>
                <div>Output: Model artifact + metadata registry entry</div>
              </div>
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowRetrainModal(false)}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRetrainModel}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
              >
                Start Training
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Training Result Modal */}
      {showTrainingResultModal && trainingResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg border border-slate-200 p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              {trainingResult.status === 'completed' ? 'Training Completed' : 'Training Failed'}
            </h3>

            {trainingResult.status === 'completed' ? (
              <div className="space-y-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="text-sm text-green-800 font-medium mb-2">Model Version</div>
                  <div className="text-lg font-bold text-slate-900">{trainingResult.model_version}</div>
                </div>

                <div>
                  <div className="text-sm font-medium text-slate-700 mb-2">Performance Metrics</div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-slate-50 rounded p-2">
                      <div className="text-xs text-slate-500">AUC</div>
                      <div className="font-medium text-slate-900">
                        {trainingResult.metrics?.auc ? trainingResult.metrics.auc.toFixed(3) : 'N/A'}
                      </div>
                    </div>
                    <div className="bg-slate-50 rounded p-2">
                      <div className="text-xs text-slate-500">KS</div>
                      <div className="font-medium text-slate-900">
                        {trainingResult.metrics?.ks ? trainingResult.metrics.ks.toFixed(3) : 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="text-sm text-slate-600">
                  <div>Algorithm: {trainingResult.algorithm || 'LightGBM'}</div>
                  <div>Feature Count: {trainingResult.feature_count || RISK_FEATURE_COUNT}</div>
                </div>

                <div className="flex gap-3 justify-end">
                  <button
                    onClick={() => setShowTrainingResultModal(false)}
                    className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleActivateModel}
                    className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
                  >
                    Activate Model
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="text-sm text-red-800">{trainingResult.error}</div>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={() => setShowTrainingResultModal(false)}
                    className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
