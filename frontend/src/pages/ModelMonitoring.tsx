/**
 * AI Model Health Page
 *
 * Enterprise model monitoring dashboard with performance metrics,
 * explainability, and governance information.
 *
 * This page displays model evaluation results from uploaded dataset analysis.
 * NOT a real-time production monitoring system.
 */
import { useState, useEffect } from 'react';
import { modelApi, FeatureImportance, ModelMonitoringData } from '../services/api';
import { MetricCard } from '../components/UI';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import UITooltip from '../components/UI/Tooltip';

// Status colors for PSI drift analysis
const PSI_STATUS_COLORS = {
  stable: 'bg-green-100 text-green-800 border-green-200',
  warning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  drift: 'bg-red-100 text-red-800 border-red-200',
  unknown: 'bg-slate-100 text-slate-800 border-slate-200',
};

// Model health status types
type ModelHealthStatus = 'HEALTHY' | 'WARNING' | 'NEEDS_REVIEW' | 'UNAVAILABLE';

// Tooltip component for model health status
const ModelHealthTooltip = () => (
  <UITooltip
    position="left"
    content={
      <div className="text-sm max-w-xs text-left">
        <p className="font-semibold mb-2">Model Health Status</p>
        <div className="space-y-2 text-xs">
          <div>
            <span className="font-medium text-green-700">Healthy:</span>
            <span className="ml-1">Model operating normally, performance metrics within expected range.</span>
          </div>
          <div>
            <span className="font-medium text-yellow-700">Warning:</span>
            <span className="ml-1">Some indicators require attention (e.g., increasing PSI, performance degradation).</span>
          </div>
          <div>
            <span className="font-medium text-red-700">Needs Review:</span>
            <span className="ml-1">Significant issue detected, manual investigation required.</span>
          </div>
          <div>
            <span className="font-medium text-slate-600">Unavailable:</span>
            <span className="ml-1">Not enough evaluation data available.</span>
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

// Tooltip component for Feature Drift
const FeatureDriftTooltip = () => (
  <UITooltip
    content={
      <div className="text-sm max-w-xs">
        <p className="font-semibold mb-2">Feature Distribution Drift</p>
        <p className="mb-2 text-xs">
          Feature-level PSI identifies which input variables contribute most to population distribution changes.
        </p>
        <div className="text-xs opacity-80 space-y-1">
          <div><span className="font-medium text-green-700">PSI &lt; 0.1:</span> Stable</div>
          <div><span className="font-medium text-yellow-700">PSI 0.1 - 0.25:</span> Warning</div>
          <div><span className="font-medium text-red-700">PSI &gt; 0.25:</span> Significant Drift</div>
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

// Tooltip for Feature Dimension
const FeatureDimensionTooltip = () => (
  <UITooltip
    position="top"
    content={
      <div className="text-sm max-w-xs">
        <p className="font-semibold mb-1">Feature Dimension</p>
        <p className="text-xs">
          Number of engineered risk features used as model inputs during training.
          Current feature set includes: device patterns, trading behavior, account characteristics,
          and network relationships.
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
  const [modelHealth, setModelHealth] = useState<{
    status: ModelHealthStatus;
    reason?: string;
  }>({ status: 'UNAVAILABLE', reason: 'Waiting for evaluation data' });

  useEffect(() => {
    loadCompleteMonitoring();
  }, []);

  const loadCompleteMonitoring = async () => {
    try {
      setLoading(true);
      const data = await modelApi.getMonitoring();
      setMetrics(data);

      // Determine model health from metrics
      if (data.metrics?.auc && data.metrics?.ks) {
        if (data.metrics.auc >= 0.8 && data.metrics.ks >= 0.4) {
          setModelHealth({ status: 'HEALTHY' });
        } else if (data.metrics.auc >= 0.7 && data.metrics.ks >= 0.3) {
          setModelHealth({ status: 'WARNING', reason: 'Performance metrics below optimal range' });
        } else {
          setModelHealth({ status: 'NEEDS_REVIEW', reason: 'Significant performance degradation detected' });
        }
      } else {
        setModelHealth({ status: 'UNAVAILABLE', reason: 'Insufficient evaluation data' });
      }

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
      setModelHealth({ status: 'UNAVAILABLE', reason: 'Failed to load model data' });
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

  // Prepare chart data with proper labels
  const psiChartData = psiFeatures.map((f) => ({
    name: f.name,
    psi: f.importance,
    status: f.status,
  }));

  const importanceChartData = featureImportance.map((f) => ({
    name: f.name,
    fullName: f.name,
    importance: (f.importance ?? 0) * 100, // Convert to percentage
  }));

  // Get model health display info
  const getModelHealthDisplay = () => {
    switch (modelHealth.status) {
      case 'HEALTHY':
        return { label: 'Healthy', color: 'green', bgColor: 'bg-green-50', textColor: 'text-green-800', borderColor: 'border-green-200' };
      case 'WARNING':
        return { label: 'Warning', color: 'yellow', bgColor: 'bg-yellow-50', textColor: 'text-yellow-800', borderColor: 'border-yellow-200' };
      case 'NEEDS_REVIEW':
        return { label: 'Needs Review', color: 'red', bgColor: 'bg-red-50', textColor: 'text-red-800', borderColor: 'border-red-200' };
      case 'UNAVAILABLE':
      default:
        return { label: 'Unavailable', color: 'slate', bgColor: 'bg-slate-50', textColor: 'text-slate-800', borderColor: 'border-slate-200' };
    }
  };

  const healthDisplay = getModelHealthDisplay();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading model metrics...</div>
      </div>
    );
  }

  const overallStatusColor = PSI_STATUS_COLORS[metrics.psi_status as keyof typeof PSI_STATUS_COLORS] || PSI_STATUS_COLORS.unknown;

  // Check if PSI baseline exists
  const hasBaseline = metrics.metrics?.psi !== null && metrics.metrics?.psi !== undefined;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">AI Model Health</h1>
        <p className="text-sm text-slate-600 mt-1">
          Model performance analysis from uploaded dataset evaluation
        </p>
      </div>

      {/* LightGBM Risk Engine Card */}
      <section className={`bg-gradient-to-br from-blue-50 to-indigo-50 border rounded-lg p-6 ${
        modelHealth.status === 'HEALTHY' ? 'border-blue-200' :
        modelHealth.status === 'WARNING' ? 'border-yellow-300' :
        modelHealth.status === 'NEEDS_REVIEW' ? 'border-red-300' :
        'border-slate-200'
      }`}>
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center gap-4">
              <div className={`w-16 h-16 rounded-xl flex items-center justify-center shadow-lg ${
                modelHealth.status === 'HEALTHY' ? 'bg-gradient-to-br from-blue-600 to-indigo-700' :
                modelHealth.status === 'WARNING' ? 'bg-gradient-to-br from-yellow-500 to-orange-600' :
                modelHealth.status === 'NEEDS_REVIEW' ? 'bg-gradient-to-br from-red-500 to-red-700' :
                'bg-gradient-to-br from-slate-400 to-slate-600'
              }`}>
                <span className="text-white text-2xl font-bold">AI</span>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  {metrics.model_name || 'AI Risk Model'}
                </h2>
                <p className="text-sm text-slate-600 mt-1">
                  Version {metrics.version || 'v1.0'} • {metrics.feature_count || 'N/A'} risk features • {metrics.algorithm || 'LightGBM'}
                </p>
              </div>
            </div>
            {modelHealth.reason && (
              <p className="text-sm text-slate-600 mt-2">{modelHealth.reason}</p>
            )}
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2 mb-2">
              <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium border ${healthDisplay.bgColor} ${healthDisplay.textColor} ${healthDisplay.borderColor}`}>
                <div className={`w-2 h-2 rounded-full ${
                  modelHealth.status === 'HEALTHY' ? 'bg-green-500' :
                  modelHealth.status === 'WARNING' ? 'bg-yellow-500' :
                  modelHealth.status === 'NEEDS_REVIEW' ? 'bg-red-500' :
                  'bg-slate-500'
                }`}></div>
                {healthDisplay.label}
              </div>
              <ModelHealthTooltip />
            </div>
            <p className="text-xs text-slate-500">
              Based on latest evaluation
            </p>
          </div>
        </div>
      </section>

      {/* Model Performance Metrics */}
      <section>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Model Performance Metrics</h2>
        <p className="text-sm text-slate-600 mb-4">
          Technical model performance indicators from latest dataset evaluation
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            title="AUC Score"
            value={(metrics.metrics?.auc ?? 0).toFixed(3)}
            subtitle="Measures the model's ability to distinguish between risky and non-risky cases (higher is better)"
            color="blue"
            variant="premium"
          />
          <MetricCard
            title="KS Statistic"
            value={(metrics.metrics?.ks ?? 0).toFixed(3)}
            subtitle="Measures the separation between high-risk and low-risk populations (higher is better)"
            color="purple"
            variant="premium"
          />
          <MetricCard
            title="PSI Value"
            value={Number(metrics.metrics?.psi ?? 0).toFixed(4)}
            subtitle="Measures data distribution stability and model drift (lower is better)"
            color="green"
            variant="premium"
          />
        </div>
      </section>

      {/* AI Risk Drivers */}
      <section className="bg-white rounded-lg border border-slate-200 p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">AI Risk Drivers</h2>
            <p className="text-sm text-slate-600 mt-1">
              Feature importance from model analysis (contribution to risk prediction)
            </p>
          </div>
        </div>
        {importanceChartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
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

      {/* Population Stability Monitoring */}
      <section>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Population Stability Monitoring</h2>
          <p className="text-sm text-slate-600 mt-1">
            Track model drift and distribution changes over time
          </p>
        </div>

        {/* Overall PSI Status */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
          {!hasBaseline ? (
            // Empty state for first upload
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-sm font-semibold text-slate-900 mb-1">No PSI Baseline Available</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                PSI monitoring requires comparison between current and historical dataset distributions.
                A baseline will be established after processing additional datasets.
              </p>
              <p className="text-xs text-slate-400 mt-2">
                First upload: Current dataset will serve as initial baseline.
              </p>
            </div>
          ) : (
            // Show PSI status when baseline exists
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="font-medium text-slate-900 mb-1">Overall Population Stability Index</h3>
                <p className="text-3xl font-bold text-slate-900">
                  {Number(metrics.metrics?.psi ?? 0).toFixed(4)}
                </p>
                <p className="text-sm text-slate-500 mt-2">
                  {metrics.psi_status === 'stable' && 'Current data distribution is consistent with reference baseline.'}
                  {metrics.psi_status === 'warning' && 'Data distribution is beginning to shift from reference baseline.'}
                  {metrics.psi_status === 'drift' && 'Data distribution has significantly changed from reference baseline.'}
                  {metrics.psi_status === 'unknown' && 'Unable to determine stability status.'}
                </p>
              </div>
              <div className={`px-6 py-3 rounded-lg text-sm font-semibold border ${overallStatusColor}`}>
                {metrics.psi_status?.charAt(0).toUpperCase() + metrics.psi_status?.slice(1) || 'Unknown'}
              </div>
            </div>
          )}
        </div>

        {/* Feature-Level Drift Analysis */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
          <h3 className="font-medium text-slate-900 mb-4 flex items-center gap-2">
            Feature-Level Drift Analysis
            <FeatureDriftTooltip />
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Feature
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                    PSI Value
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {!hasBaseline || psiFeatures.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-6 py-8 text-center">
                      <div className="text-sm text-slate-500">No drift analysis available</div>
                      <p className="text-xs text-slate-400 mt-1">Drift analysis requires baseline established from previous dataset</p>
                    </td>
                  </tr>
                ) : (
                  psiFeatures.map((feature) => (
                    <tr key={feature.name}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        {feature.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 text-center font-medium">
                        {Number(feature.importance ?? 0).toFixed(4)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                            PSI_STATUS_COLORS[feature.status as keyof typeof PSI_STATUS_COLORS] ||
                              PSI_STATUS_COLORS.unknown
                          }`}
                        >
                          {feature.status ? feature.status.charAt(0).toUpperCase() + feature.status.slice(1) : 'Unknown'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* PSI by Feature Chart - Only show when data available */}
        {hasBaseline && psiChartData.length > 0 && (
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h3 className="font-medium text-slate-900 mb-4">PSI by Feature</h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={psiChartData} layout="vertical" margin={{ left: 20, right: 50, top: 5, bottom: 5 }}>
                <XAxis
                  type="number"
                  stroke="#64748b"
                  style={{ fontSize: '12px' }}
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
                  formatter={(value: any) => [`${Number(value).toFixed(4)}`, 'PSI Value']}
                />
                <Bar
                  dataKey="psi"
                  maxBarSize={30}
                  radius={[0, 6, 6, 0]}
                  cursor="default"
                >
                  {psiChartData.map((entry) => {
                    const color =
                      entry.status === 'drift'
                        ? '#ef4444'
                        : entry.status === 'warning'
                        ? '#f59e0b'
                        : '#10b981';
                    return <Cell key={entry.name} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {/* Model Metadata */}
      <section className="bg-white rounded-lg border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Model Metadata</h2>
        <p className="text-xs text-slate-500 mb-4">
          Model training metadata (separate from uploaded dataset metadata)
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Model Identity */}
          <div className="space-y-3">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Model Identity</p>
            <div className="space-y-2">
              <div>
                <span className="text-xs text-slate-500">Model Name</span>
                <p className="text-sm font-medium text-slate-900">{metrics.model_name || 'LightGBM Risk Model'}</p>
              </div>
              <div>
                <span className="text-xs text-slate-500">Version</span>
                <p className="text-sm font-medium text-slate-900">{metrics.version || 'v1.0'}</p>
              </div>
            </div>
          </div>

          {/* Algorithm */}
          <div className="space-y-3">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Algorithm</p>
            <div className="space-y-2">
              <div>
                <span className="text-xs text-slate-500">Algorithm</span>
                <p className="text-sm font-medium text-slate-900">{metrics.algorithm || 'N/A'}</p>
              </div>
              <div>
                <span className="text-xs text-slate-500">Model Type</span>
                <p className="text-sm font-medium text-slate-900">{metrics.model_type || 'N/A'}</p>
              </div>
            </div>
          </div>

          {/* Training Configuration */}
          <div className="space-y-3">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Training Configuration</p>
            <div className="space-y-2">
              <div>
                <span className="text-xs text-slate-500">Training Date</span>
                <p className="text-sm font-medium text-slate-900">
                  {metrics.deployed_at ? new Date(metrics.deployed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A'}
                </p>
              </div>
              <div>
                <span className="text-xs text-slate-500">Deployed Date</span>
                <p className="text-sm font-medium text-slate-900">
                  {metrics.deployed_at ? new Date(metrics.deployed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A'}
                </p>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-xs text-slate-500">Feature Dimension</span>
                <FeatureDimensionTooltip />
                <p className="text-sm font-medium text-slate-900">
                  {metrics.feature_count || 'N/A'} risk features
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
