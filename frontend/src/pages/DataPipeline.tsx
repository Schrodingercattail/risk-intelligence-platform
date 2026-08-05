/**
 * Risk Data Pipeline Page
 *
 * Batch CSV upload and risk analysis pipeline monitoring interface.
 * This is a batch processing system, not a real-time platform.
 *
 * State Management: Backend is the single source of truth.
 * Frontend derives all state from backend API responses.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/UI';
import { pipelineApi, PipelineStatus } from '../services/api';
import SimpleMetricTooltip from '../components/UI/DataProvenanceTooltip';

// Required CSV datasets
const REQUIRED_DATASETS = [
  { key: 'users', label: 'User Data', icon: '👤', description: 'User accounts and profiles' },
  { key: 'devices', label: 'Device Data', icon: '📱', description: 'Device fingerprints' },
  { key: 'trades', label: 'Transaction Data', icon: '💳', description: 'Trade and transaction records' },
  { key: 'withdrawals', label: 'Withdrawal Data', icon: '🔔', description: 'Withdrawal requests' },
] as const;

// Pipeline stages - from dataset upload to risk decision
const PIPELINE_STAGES = [
  { id: 'data_sources', name: 'Data Sources', description: 'Upload CSV datasets', icon: '📊' },
  { id: 'validation', name: 'Data Validation', description: 'Quality checks and normalization', icon: '✅' },
  { id: 'features', name: 'Feature Engineering', description: 'Extract risk features from data', icon: '⚙️' },
  { id: 'scoring', name: 'ML Risk Scoring', description: 'LightGBM model predictions', icon: '🧠' },
  { id: 'graph', name: 'Graph Analysis', description: 'Network clustering and linkage', icon: '🕸️' },
  { id: 'decision', name: 'Risk Decision Engine', description: 'Rule-based risk decisions', icon: '⚖️' },
] as const;

type UploadStatus = 'INITIAL' | 'UPLOADING' | 'UPLOADED' | 'FAILED';

export default function DataPipeline() {
  const navigate = useNavigate();

  // Local UI state only
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('INITIAL');
  const [uploading, setUploading] = useState(false);
  const [runningPipeline, setRunningPipeline] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Backend state - single source of truth
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);

  // File selection state (only needed during upload process)
  const [files, setFiles] = useState<Record<string, File>>({});

  // Load pipeline status on component mount
  useEffect(() => {
    loadPipelineStatus();
  }, []);

  const loadPipelineStatus = async () => {
    try {
      const status = await pipelineApi.getStatus();
      setPipelineStatus(status);

      // Derive upload status from backend state
      if (status.upload_status === 'COMPLETED') {
        setUploadStatus('UPLOADED');
      } else if (status.upload_status === 'FAILED') {
        setUploadStatus('FAILED');
      }
    } catch (err) {
      console.error('Failed to load pipeline status:', err);
      setError('Failed to load pipeline status');
    }
  };

  // Check if all required files are selected
  const allFilesSelected = REQUIRED_DATASETS.every(d => files[d.key]);
  const allFilesValid = REQUIRED_DATASETS.every(d => {
    const file = files[d.key];
    return file && file.name.endsWith('.csv');
  });

  const canUpload = allFilesSelected && allFilesValid;
  const canRunPipeline = pipelineStatus?.upload_status === 'COMPLETED' && !runningPipeline;
  const showResetButton = pipelineStatus?.upload_status === 'COMPLETED' && !runningPipeline && !uploading;

  const handleFileChange = (key: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate CSV format
      if (!file.name.endsWith('.csv')) {
        setError(`${file.name} is not a CSV file`);
        return;
      }
      setError(null);
      setFiles(prev => ({ ...prev, [key]: file }));
    }
  };

  const handleUpload = async () => {
    if (!canUpload) return;

    try {
      setUploading(true);
      setUploadStatus('UPLOADING');
      setError(null);

      await pipelineApi.uploadData({
        users: files.users,
        devices: files.devices,
        trades: files.trades,
        withdrawals: files.withdrawals,
      });

      // Reload status from backend after successful upload
      await loadPipelineStatus();
      setUploadStatus('UPLOADED');
    } catch (err: any) {
      setError(err.message || 'Upload failed');
      setUploadStatus('FAILED');
    } finally {
      setUploading(false);
    }
  };

  const handleRunPipeline = async () => {
    if (!canRunPipeline) return;

    try {
      setRunningPipeline(true);
      setError(null);

      await pipelineApi.runPipeline({
        run_full_pipeline: true,
        generate_risk_events: true,
      });

      // Reload status from backend after pipeline completes
      await loadPipelineStatus();
    } catch (err: any) {
      setError(err.message || 'Pipeline execution failed');
    } finally {
      setRunningPipeline(false);
    }
  };

  const handleReset = async () => {
    try {
      setUploading(true);
      setError(null);

      await pipelineApi.resetPipeline();

      // Clear local state
      setFiles({});
      setUploadStatus('INITIAL');

      // Reload status from backend
      await loadPipelineStatus();
    } catch (err: any) {
      setError(err.message || 'Reset failed');
    } finally {
      setUploading(false);
    }
  };

  // Map backend status to frontend stages
  const getStageStatus = (stageId: string): 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' => {
    if (!pipelineStatus) return 'PENDING';

    const statusMap: Record<string, string> = {
      'data_sources': pipelineStatus.data_sources,
      'validation': pipelineStatus.dataset_validation,
      'features': pipelineStatus.feature_engineering,
      'scoring': pipelineStatus.ml_scoring,
      'graph': pipelineStatus.graph_analysis,
      'decision': pipelineStatus.ml_scoring === 'COMPLETED' ? 'COMPLETED' : 'PENDING',
    };

    const status = statusMap[stageId];
    return (status === 'PENDING' || status === 'RUNNING' || status === 'COMPLETED' || status === 'FAILED')
      ? status
      : 'PENDING';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatTimestamp = (isoString: string) => {
    return new Date(isoString).toLocaleString();
  };

  // Derive uploaded datasets info from backend
  const getUploadedDatasetInfo = (key: string) => {
    if (!pipelineStatus?.upload_counts) return null;
    const count = pipelineStatus.upload_counts[key as keyof typeof pipelineStatus.upload_counts];
    if (count === undefined || count === null) return null;  // Allow 0 records as valid upload

    return {
      name: `${key.charAt(0).toUpperCase() + key.slice(1)}.csv`,
      records: count,
      uploadedAt: pipelineStatus.upload_timestamp,
    };
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Risk Data Pipeline</h1>
          <p className="text-sm text-slate-600 mt-1">
            Batch CSV upload and risk analysis processing workflow
          </p>
        </div>
        {showResetButton && (
          <Button
            onClick={handleReset}
            disabled={uploading || runningPipeline}
            variant="secondary"
          >
            Reset Pipeline
          </Button>
        )}
      </div>

      {/* Data Upload Section */}
      <section className="bg-white rounded-lg border border-slate-200 p-6">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Data Ingestion</h2>
          <p className="text-sm text-slate-600 mt-1">
            Upload required CSV datasets for risk analysis processing
          </p>
        </div>

        {/* Required Dataset Upload Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {REQUIRED_DATASETS.map((dataset) => {
            // Check both backend uploaded state and local file selection
            const uploadedInfo = uploadStatus === 'UPLOADED' ? getUploadedDatasetInfo(dataset.key) : null;
            const isUploaded = !!uploadedInfo;
            const selectedFile = files[dataset.key];
            const isLocallySelected = !!selectedFile;

            return (
              <div
                key={dataset.key}
                className={`border rounded-lg p-4 transition-all flex flex-col ${
                  isUploaded ? 'border-green-300 bg-green-50/50' :
                  isLocallySelected ? 'border-blue-300 bg-blue-50/50' :
                  'border-slate-200'
                }`}
              >
                <div className="flex items-start gap-3 mb-3">
                  <div className="text-2xl shrink-0">{dataset.icon}</div>
                  <div className="flex-1 min-w-0">
                    <label className="block text-sm font-medium text-slate-900">{dataset.label}</label>
                    <p className="text-xs text-slate-500 leading-tight mt-0.5">{dataset.description}</p>
                  </div>
                  {isUploaded && (
                    <div className="text-green-600 text-sm shrink-0">✓</div>
                  )}
                  {isLocallySelected && !isUploaded && (
                    <div className="text-blue-600 text-sm shrink-0">📄</div>
                  )}
                </div>

                {isUploaded && uploadedInfo ? (
                  // Show uploaded info from backend
                  <div className="space-y-1 text-xs text-slate-600 mt-auto">
                    <div className="font-medium">{uploadedInfo.name}</div>
                    <div className="text-slate-500">
                      {uploadedInfo.records === 0
                        ? 'Empty dataset'
                        : `${uploadedInfo.records?.toLocaleString()} records`
                      }
                    </div>
                    {uploadedInfo.records === 0 && (
                      <div className="text-amber-600 mt-1">
                        {dataset.key === 'devices' && '⚠️ No device evidence available - device relationship analysis unavailable'}
                        {dataset.key === 'trades' && '⚠️ No transaction evidence available - trading analysis unavailable'}
                        {dataset.key === 'withdrawals' && '⚠️ No withdrawal evidence available - withdrawal analysis unavailable'}
                        {dataset.key === 'users' && '⚠️ No user evidence available - account analysis unavailable'}
                      </div>
                    )}
                    {uploadedInfo.uploadedAt && uploadedInfo.records > 0 && (
                      <div className="text-slate-500">{formatTimestamp(uploadedInfo.uploadedAt)}</div>
                    )}
                  </div>
                ) : isLocallySelected ? (
                  // Show locally selected file info
                  <div className="space-y-1 text-xs text-slate-600 mt-auto">
                    <div className="font-medium text-blue-700">{selectedFile.name}</div>
                    <div className="text-slate-500">{formatFileSize(selectedFile.size)}</div>
                    <button
                      onClick={() => {
                        setFiles(prev => {
                          const newFiles = { ...prev };
                          delete newFiles[dataset.key];
                          return newFiles;
                        });
                      }}
                      className="text-red-600 hover:text-red-700 underline"
                      disabled={uploading || runningPipeline}
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  // Show file input
                  <div className="mt-auto">
                    <input
                      type="file"
                      accept=".csv"
                      onChange={handleFileChange(dataset.key)}
                      disabled={uploading || runningPipeline || uploadStatus === 'UPLOADED'}
                      className="block w-full text-sm text-slate-500
                        file:mr-4 file:py-2 file:px-4
                        file:rounded-md file:border-0
                        file:text-sm file:font-semibold
                        file:bg-blue-50 file:text-blue-700
                        hover:file:bg-blue-100
                        disabled:opacity-50"
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-6 flex gap-3">
          <Button
            onClick={handleUpload}
            disabled={!canUpload || uploading || runningPipeline || uploadStatus === 'UPLOADED'}
            isLoading={uploading}
          >
            {uploadStatus === 'UPLOADED' ? 'Datasets Uploaded ✓' :
             uploading ? 'Uploading...' :
             'Upload Datasets'}
          </Button>
          {allFilesSelected && !allFilesValid && (
            <div className="flex items-center text-sm text-orange-700">
              ⚠ All files must be CSV format
            </div>
          )}
          {!allFilesSelected && uploadStatus === 'INITIAL' && (
            <div className="flex items-center text-sm text-slate-500">
              {REQUIRED_DATASETS.filter(d => !files[d.key]).length} datasets remaining
            </div>
          )}
        </div>
      </section>

      {/* Processing Pipeline */}
      <section>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Processing Pipeline</h2>
          <p className="text-sm text-slate-600 mt-1">
            Risk analysis workflow stages
          </p>
        </div>

        {/* Pipeline Stage Cards - Identical Dimensions */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {PIPELINE_STAGES.map((stage) => {
            const status = getStageStatus(stage.id);

            return (
              <div
                key={stage.id}
                className={`bg-white rounded-lg border p-4 h-[140px] flex flex-col transition-all ${
                  status === 'COMPLETED' ? 'border-green-200 bg-green-50/30' :
                  status === 'RUNNING' ? 'border-blue-400 bg-blue-50/30' :
                  status === 'FAILED' ? 'border-red-200 bg-red-50/30' :
                  'border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="text-xl">{stage.icon}</div>
                    <h3 className="font-semibold text-slate-900 text-sm">{stage.name}</h3>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs font-semibold border ${
                    status === 'COMPLETED' ? 'bg-green-100 text-green-800 border-green-200' :
                    status === 'RUNNING' ? 'bg-blue-100 text-blue-800 border-blue-200' :
                    status === 'FAILED' ? 'bg-red-100 text-red-800 border-red-200' :
                    'bg-slate-100 text-slate-600 border-slate-200'
                  }`}>
                    {status === 'COMPLETED' && '✓ '}
                    {status === 'RUNNING' && '⏳ '}
                    {status === 'FAILED' && '✗ '}
                    {status}
                  </div>
                </div>

                <div className="flex-1 flex flex-col justify-center">
                  <p className="text-xs text-slate-600 mb-2">{stage.description}</p>
                  {status === 'RUNNING' && (
                    <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                      <div className="bg-blue-600 h-full rounded-full animate-pulse" style={{ width: '60%' }}></div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Pipeline Run Summary */}
      {pipelineStatus?.results && (
        <section className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-start justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Pipeline Run Summary</h2>
            <button
              onClick={() => navigate('/')}
              className="text-sm text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-1"
            >
              Go to Risk Overview for charts and case queue
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border border-slate-200 p-4 h-[140px] flex flex-col">
              <div className="text-xs text-slate-600 mb-1">Total Records</div>
              <div className="text-xs text-slate-400 mb-2">Rows ingested from uploaded datasets</div>
              <div className="flex-1" />
              <div className="text-2xl font-bold text-slate-900">{pipelineStatus.results.total_records?.toLocaleString()}</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-4 h-[140px] flex flex-col">
              <div className="text-xs text-slate-600 mb-1">Users Processed</div>
              <div className="text-xs text-slate-400 mb-2">Unique accounts scored in this run</div>
              <div className="flex-1" />
              <div className="text-2xl font-bold text-slate-900">{pipelineStatus.results.feature_vectors_generated?.toLocaleString()}</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-4 h-[140px] flex flex-col">
              <SimpleMetricTooltip
                metric="Accounts in Suspicious Clusters"
                definition="Accounts linked to suspicious clusters via device/IP or behavioral patterns"
              >
                <div className="text-xs text-slate-600 mb-1">Accounts in Suspicious Clusters</div>
                <div className="text-xs text-slate-400 mb-2">Accounts linked to suspicious clusters via device/IP or behavioral patterns</div>
              </SimpleMetricTooltip>
              <div className="flex-1" />
              <div className="text-2xl font-bold text-red-600">{pipelineStatus.results.risky_accounts_detected?.toLocaleString()}</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-4 h-[140px] flex flex-col">
              <SimpleMetricTooltip
                metric="Suspicious Clusters Detected"
                definition="Distinct suspicious network clusters identified"
              >
                <div className="text-xs text-slate-600 mb-1">Suspicious Clusters Detected</div>
                <div className="text-xs text-slate-400 mb-2">Distinct suspicious network clusters identified</div>
              </SimpleMetricTooltip>
              <div className="flex-1" />
              <div className="text-2xl font-bold text-slate-900">{pipelineStatus.results.fraud_networks?.toLocaleString()}</div>
            </div>
          </div>
        </section>
      )}

      {/* Pipeline Execution */}
      <section className={`bg-white border rounded-lg p-6 ${
        pipelineStatus?.ml_scoring === 'COMPLETED'
          ? 'border-green-200 bg-green-50/30'
          : 'border-slate-200'
      }`}>
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Execute Risk Analysis Pipeline</h2>
            <p className="text-sm text-slate-600 mt-1">
              Run complete data processing workflow to generate risk scores and detect patterns
            </p>
          </div>
          <Button
            onClick={handleRunPipeline}
            disabled={!canRunPipeline}
            isLoading={runningPipeline}
          >
            {runningPipeline ? 'Processing...' : 'Run Pipeline'}
          </Button>
        </div>
      </section>
    </div>
  );
}
