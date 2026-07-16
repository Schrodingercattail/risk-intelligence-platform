/**
 * Risk Data Pipeline Page
 *
 * Batch CSV upload and risk analysis pipeline monitoring interface.
 * This is a batch processing system, not a real-time platform.
 */
import { useState } from 'react';
import { Button } from '../components/UI';

// Required CSV datasets
const REQUIRED_DATASETS = [
  { key: 'users', label: 'User Data', icon: '👤', description: 'User accounts and profiles' },
  { key: 'devices', label: 'Device Data', icon: '📱', description: 'Device fingerprints' },
  { key: 'transactions', label: 'Transaction Data', icon: '💳', description: 'Trade and transaction records' },
  { key: 'withdrawals', label: 'Withdrawal Data', icon: '🔔', description: 'Withdrawal requests' },
] as const;

// Pipeline stages - from dataset upload to risk decision
const PIPELINE_STAGES = [
  { id: 'data_sources', name: 'Data Sources', description: 'Uploaded CSV datasets', icon: '📊' },
  { id: 'validation', name: 'Data Validation', description: 'Quality checks and normalization', icon: '✅' },
  { id: 'features', name: 'Feature Engineering', description: 'Extract risk features from data', icon: '⚙️' },
  { id: 'scoring', name: 'ML Risk Scoring', description: 'LightGBM model predictions', icon: '🧠' },
  { id: 'graph', name: 'Graph Analysis', description: 'Network clustering and linkage', icon: '🕸️' },
  { id: 'decision', name: 'Risk Decision Engine', description: 'Rule-based risk decisions', icon: '⚖️' },
] as const;

interface UploadedDataset {
  name: string;
  records?: number;
  uploadedAt?: string;
  fileSize?: number;
}

interface PipelineState {
  currentStage: string;
  stages: Record<string, 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'>;
  results?: {
    totalRecords?: number;
    highRiskCount?: number;
    fraudNetworks?: number;
    generatedAt?: string;
  };
}

export default function DataPipeline() {
  const [uploadedDatasets, setUploadedDatasets] = useState<Record<string, UploadedDataset>>({});
  const [files, setFiles] = useState<Record<string, File>>({});
  const [pipelineState, setPipelineState] = useState<PipelineState>({
    currentStage: '',
    stages: PIPELINE_STAGES.reduce((acc, stage) => ({ ...acc, [stage.id]: 'PENDING' }), {}),
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check if all required files are uploaded and valid
  const allFilesUploaded = REQUIRED_DATASETS.every(d => files[d.key]);
  const allFilesValid = REQUIRED_DATASETS.every(d => {
    const file = files[d.key];
    return file && file.name.endsWith('.csv');
  });

  const canRunPipeline = allFilesUploaded && allFilesValid;

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
      setUploadedDatasets(prev => ({
        ...prev,
        [key]: {
          name: file.name,
          fileSize: file.size,
        },
      }));
    }
  };

  const handleUpload = async () => {
    if (!canRunPipeline) return;

    try {
      setLoading(true);
      setError(null);

      // TODO: Replace with actual API call
      // const result = await pipelineApi.uploadDatasets(files);
      // setUploadedDatasets(result.datasets);

      // Mock successful upload
      const now = new Date().toISOString();
      setUploadedDatasets(
        REQUIRED_DATASETS.reduce((acc, ds) => ({
          ...acc,
          [ds.key]: {
            name: files[ds.key]!.name,
            fileSize: files[ds.key]!.size,
            uploadedAt: now,
          },
        }), {})
      );

      // Set initial pipeline state
      setPipelineState({
        currentStage: 'data_sources',
        stages: {
          data_sources: 'COMPLETED',
          validation: 'PENDING',
          features: 'PENDING',
          scoring: 'PENDING',
          graph: 'PENDING',
          decision: 'PENDING',
        },
      });
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRunPipeline = async () => {
    if (!canRunPipeline) return;

    try {
      setLoading(true);
      setError(null);

      // TODO: Replace with actual API call
      // await pipelineApi.runPipeline();
      // Poll for status updates

      // Mock pipeline execution
      const stages = ['validation', 'features', 'scoring', 'graph', 'decision'];

      for (const stageId of stages) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate processing
        setPipelineState(prev => ({
          currentStage: stageId,
          stages: { ...prev.stages, [stageId]: 'RUNNING' },
        }));

        await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate processing
        setPipelineState(prev => ({
          currentStage: stageId,
          stages: { ...prev.stages, [stageId]: 'COMPLETED' },
        }));
      }

      // Set final results
      setPipelineState(prev => ({
        ...prev,
        currentStage: '',
        results: {
          totalRecords: 71920,
          highRiskCount: 598,
          fraudNetworks: 225,
          generatedAt: new Date().toISOString(),
        },
      }));
    } catch (err: any) {
      setError(err.message || 'Pipeline execution failed');
      // Set failed stage
      setPipelineState(prev => ({
        ...prev,
        stages: { ...prev.stages, [prev.currentStage]: 'FAILED' },
      }));
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatTimestamp = (isoString: string) => {
    return new Date(isoString).toLocaleString();
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Risk Data Pipeline</h1>
        <p className="text-sm text-slate-600 mt-1">
          Batch CSV upload and risk analysis processing workflow
        </p>
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
            const uploaded = uploadedDatasets[dataset.key];

            return (
              <div
                key={dataset.key}
                className={`border rounded-lg p-4 transition-all ${
                  uploaded ? 'border-green-300 bg-green-50/50' : 'border-slate-200'
                }`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="text-2xl">{dataset.icon}</div>
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-slate-900">{dataset.label}</label>
                    <p className="text-xs text-slate-500">{dataset.description}</p>
                  </div>
                  {uploaded && (
                    <div className="text-green-600 text-sm">✓</div>
                  )}
                </div>

                {uploaded ? (
                  <div className="space-y-1 text-xs text-slate-600">
                    <div className="font-medium">{uploaded.name}</div>
                    {uploaded.fileSize && (
                      <div className="text-slate-500">{formatFileSize(uploaded.fileSize)}</div>
                    )}
                    {uploaded.uploadedAt && (
                      <div className="text-slate-500">{formatTimestamp(uploaded.uploadedAt)}</div>
                    )}
                  </div>
                ) : (
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange(dataset.key)}
                    disabled={loading}
                    className="block w-full text-sm text-slate-500
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-md file:border-0
                      file:text-sm file:font-semibold
                      file:bg-blue-50 file:text-blue-700
                      hover:file:bg-blue-100
                      disabled:opacity-50"
                  />
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
            disabled={!canRunPipeline || loading}
            isLoading={loading}
          >
            {loading ? 'Uploading...' : 'Upload Datasets'}
          </Button>
          {allFilesUploaded && !allFilesValid && (
            <div className="flex items-center text-sm text-orange-700">
              ⚠ All files must be CSV format
            </div>
          )}
          {!allFilesUploaded && (
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
            const status = pipelineState.stages[stage.id];
            const isRunning = pipelineState.currentStage === stage.id;

            return (
              <div
                key={stage.id}
                className={`bg-white rounded-lg border p-4 h-[140px] flex flex-col transition-all ${
                  isRunning ? 'border-blue-400 bg-blue-50/30' : 'border-slate-200'
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
                  {isRunning && (
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

      {/* Pipeline Results */}
      {pipelineState.results && (
        <section className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Pipeline Results</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="text-xs text-slate-600 mb-1">Total Records</div>
              <div className="text-2xl font-bold text-slate-900">{pipelineState.results.totalRecords?.toLocaleString()}</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="text-xs text-slate-600 mb-1">High Risk Accounts</div>
              <div className="text-2xl font-bold text-red-600">{pipelineState.results.highRiskCount?.toLocaleString()}</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="text-xs text-slate-600 mb-1">Fraud Networks</div>
              <div className="text-2xl font-bold text-slate-900">{pipelineState.results.fraudNetworks?.toLocaleString()}</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="text-xs text-slate-600 mb-1">Generated</div>
              <div className="text-sm font-medium text-slate-900">
                {pipelineState.results.generatedAt ? formatTimestamp(pipelineState.results.generatedAt) : '-'}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Pipeline Execution */}
      <section className={`bg-white border rounded-lg p-6 ${
        Object.values(pipelineState.stages).some(s => s === 'COMPLETED')
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
            disabled={!canRunPipeline || loading}
            isLoading={loading}
          >
            {loading ? 'Processing...' : 'Run Pipeline'}
          </Button>
        </div>
      </section>
    </div>
  );
}
