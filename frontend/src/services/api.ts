/**
 * API Client Service
 *
 * Handles all backend API communication with proper typing.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  get: async <T = any>(endpoint: string): Promise<T> => {
    const response = await fetch(`${API_URL}${endpoint}`);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  },

  post: async <T = any>(endpoint: string, data?: any): Promise<T> => {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  },

  upload: async <T = any>(endpoint: string, formData: FormData): Promise<T> => {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  },
};

// API endpoints
export const riskApi = {
  getOverview: () => api.get<RiskOverview>('/api/risk/overview'),
  getCases: (params?: { page?: number; page_size?: number; risk_level?: string }) => {
    const queryParams: Record<string, any> = {};
    if (params?.page) queryParams.page = params.page;
    if (params?.page_size) queryParams.page_size = params.page_size;
    if (params?.risk_level) queryParams.risk_level = params.risk_level;
    const query = new URLSearchParams(queryParams).toString();
    return api.get<RiskEventList>(`/api/risk/cases${query ? `?${query}` : ''}`);
  },
  getEvents: (params?: { page?: number; page_size?: number; risk_level?: string }) => {
    const query = new URLSearchParams(params as any).toString();
    return api.get<RiskEventList>(`/api/risk/events${query ? `?${query}` : ''}`);
  },
  getUserDetail: (userId: string) => api.get<RiskEventDetail>(`/api/risk/events/${userId}`),
  getUserGraph: (userId: string, depth?: number) => {
    const query = depth ? `?depth=${depth}` : '';
    return api.get<GraphData>(`/api/risk/graph/${userId}${query}`);
  },
  getCaseEvidence: (userId: string) => api.get<RiskEvidence>(`/api/risk/cases/${userId}/evidence`),
  getNetworkSignals: (userId: string, limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get<NetworkSignals>(`/api/risk/cases/${userId}/network-signals${query}`);
  },
  generateExplanation: (userId: string) =>
    api.post<Explanation>('/api/risk/explain', { user_id: userId }),
};

export const pipelineApi = {
  getStatus: () => api.get<PipelineStatus>('/api/pipeline/status'),
  uploadData: (files: { users?: File; devices?: File; trades?: File; withdrawals?: File }) => {
    const formData = new FormData();
    if (files.users) formData.append('users', files.users);
    if (files.devices) formData.append('devices', files.devices);
    if (files.trades) formData.append('trades', files.trades);
    if (files.withdrawals) formData.append('withdrawals', files.withdrawals);
    return api.upload<DataUploadResponse>('/api/pipeline/upload', formData);
  },
  runPipeline: (options: { run_full_pipeline?: boolean; generate_risk_events?: boolean }) =>
    api.post<PipelineRunResult>('/api/pipeline/run', options),
};

export const casesApi = {
  create: (userId: string, riskEventId?: number) =>
    api.post<{ case_id: string; status: string }>(`/api/cases/${userId}`, {
      risk_event_id: riskEventId,
    }),
  get: (userId: string) => api.get<Case>(`/api/cases/${userId}`),
  submitDecision: (
    caseId: string,
    _status: string,
    _decision?: string,
    _notes?: string,
    _assigned_analyst?: string
  ) =>
    api.post<{ case_id: string; status: string }>(`/api/cases/${caseId}/decision`, null),
};

export const modelApi = {
  getMetrics: () => api.get<ModelMetrics>('/api/model/metrics'),
  getFeatureImportance: () => api.get<FeatureImportanceList>('/api/model/feature-importance'),
  getMonitoring: () => api.get<ModelMonitoringData>('/api/model/monitoring'),
};

// Type definitions
export interface RiskOverview {
  // Executive Risk Summary
  summary: {
    analyzed_users: number;
    high_risk_accounts: number;
    fraud_networks: number;
    risk_recommendations: number;
  };
  // Risk score distribution (histogram buckets)
  risk_score_distribution: Array<{
    range: string;
    count: number;
    percentage: number;
  }>;
  // Risk score statistics
  risk_score_statistics: {
    average: number;
    median: number;
    threshold: number;
    maximum: number;
  };
  // Risk level composition
  risk_level_composition: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
  };
  // Detection source analysis
  detection_sources: Array<{
    method: string;
    detected_accounts: number;
    detection_rate: number;
    color: string;
  }>;
}

export interface RiskEvent {
  user_id: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_probability: number;
  primary_reason: string | null;
  recommended_action: string | null;
  detected_at: string;
  event_type: string | null;
  ml_score: number | null;
  rule_score: number | null;
  graph_score: number | null;
  detection_methods: string[];
}

export interface RiskEventList {
  total: number;
  items: RiskEvent[];
}

export interface RiskFactor {
  id: number;
  factor_name: string;
  factor_value: number | null;
  factor_description: string | null;
}

export interface ClusterInfo {
  cluster_id: number;
  member_count: number;
  risk_score: number;
}

export interface RiskEventDetail extends RiskEvent {
  risk_factors: RiskFactor[];
  cluster: ClusterInfo | null;
  account_age?: number;  // Account age in days
  total_volume?: number;  // Total trading volume
}

export interface GraphNode {
  id: string;
  type: string;
  risk_level?: string;
  label?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Explanation {
  summary: string;
  key_findings: string[];
  recommended_action: string;
}

export interface PipelineStatus {
  dataset_validation: string;
  feature_engineering: string;
  ml_scoring: string;
  graph_analysis: string;
}

export interface DataUploadResponse {
  message: string;
  files_processed: string[];
  records_imported: Record<string, number>;
}

export interface PipelineRunResult {
  started_at: string;
  steps: Record<string, any>;
  final_counts: Record<string, any>;
  completed_at?: string;
  success?: boolean;
  error?: string;
}

export interface Case {
  case_id: string;
  user_id: string;
  risk_event_id: number | null;
  status: string;
  assigned_analyst: string | null;
  decision: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  closed_at: string | null;
}

export interface ModelMetrics {
  model_name: string;
  version: string;
  metrics: {
    auc: number | null;
    ks: number | null;
    psi: number | null;
  };
}

export interface FeatureImportance {
  name: string;
  importance: number;
  rank: number;
  status?: 'stable' | 'warning' | 'drift';
}

export interface FeatureImportanceList {
  features: FeatureImportance[];
}

export interface PSIFeature {
  feature: string;
  psi: number;
  status: 'stable' | 'warning' | 'drift';
}

export interface ModelMonitoringData {
  model_name: string;
  version: string;
  algorithm?: string | null;
  model_type?: string | null;
  feature_count?: number | null;
  deployed_at?: string;
  metrics: {
    auc: number | null;
    ks: number | null;
    psi: number | null;
  };
  psi_status: 'stable' | 'warning' | 'drift' | 'unknown';
  psi_features: PSIFeature[];
}

// Risk Evidence Explainability Types
export interface RiskSummary {
  risk_level: string;
  risk_score: number;
  primary_reason?: string;
  recommended_action?: string;
  detection_methods: string[];
  detected_at?: string;
  ml_score?: number;
  rule_score?: number;
  graph_score?: number;
}

export interface TransactionEvidence {
  transaction_id: string;
  symbol: string;
  side: string;
  price: number;
  quantity: number;
  value: number;
  timestamp?: string;
  risk_reason: string;
}

export interface WithdrawalEvidence {
  withdrawal_id: string;
  asset: string;
  amount: number;
  address: string;
  is_new_address?: boolean;
  timestamp?: string;
  risk_reason: string;
}

export interface NetworkEvidence {
  cluster_id: number;
  cluster_name: string;
  detection_type: string;
  member_count: number;
  cluster_risk_score: number;
  role_in_cluster?: string;
  related_accounts_count: number;
  related_accounts: string[];
  shared_devices: string[];
}

export interface ConnectedAccountSignal {
  user_id: string;
  relationship_type: string[];  // shared_device, shared_ip
  device_fingerprints: string[];
  shared_ips: string[];
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';
  risk_score: number;
}

export interface NetworkSignals {
  connected_account_count: number;
  connected_accounts: ConnectedAccountSignal[];
}

export interface RiskFactorEvidence {
  factor_id: number;
  factor_name: string;
  factor_value?: number;
  factor_description?: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface FeatureEvidence {
  shared_device_count?: number;
  linked_account_count?: number;
  unique_ip_count?: number;
  trade_frequency_24h?: number;
  trade_frequency_7d?: number;
  opposite_trade_ratio?: number;
  avg_trade_size?: number;
  trade_volume_24h?: number;
  account_age_days?: number;
  active_days_count?: number;
  withdrawal_risk_score?: number;
  withdrawal_frequency_24h?: number;
  withdrawal_volume_24h?: number;
}

export interface RuleEvidence {
  rule_name: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
}

export interface RiskEvidence {
  user_id: string;
  risk_summary: RiskSummary;
  transaction_evidence: TransactionEvidence[];
  withdrawal_evidence: WithdrawalEvidence[];
  network_evidence?: NetworkEvidence;
  risk_factor_evidence: RiskFactorEvidence[];
  feature_evidence?: FeatureEvidence;
  rule_evidence: RuleEvidence[];
}
