"""
Pydantic Schemas for API Request/Response Validation

These schemas define the structure of API requests and responses,
providing validation and serialization.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal


# ============================================================
# Base Schemas
# ============================================================

class UserBase(BaseModel):
    """Base user schema."""
    country: Optional[str] = None
    kyc_level: Optional[str] = None
    account_created_time: Optional[datetime] = None
    vip_level: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""
    user_id: str


class UserResponse(UserBase):
    """Schema for user response."""
    user_id: str
    current_risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# Device Schemas
# ============================================================

class DeviceCreate(BaseModel):
    """Schema for creating a device record."""
    user_id: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    browser_fingerprint: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


class DeviceResponse(DeviceCreate):
    """Schema for device response."""
    id: int

    class Config:
        from_attributes = True


# ============================================================
# Trade Schemas
# ============================================================

class TradeCreate(BaseModel):
    """Schema for creating a trade record."""
    trade_id: str
    user_id: str
    symbol: str
    side: str  # BUY, SELL
    price: Decimal
    quantity: Decimal
    timestamp: datetime


class TradeResponse(TradeCreate):
    """Schema for trade response."""
    class Config:
        from_attributes = True


# ============================================================
# Withdrawal Schemas
# ============================================================

class WithdrawalCreate(BaseModel):
    """Schema for creating a withdrawal record."""
    withdraw_id: str
    user_id: str
    asset: str
    amount: Decimal
    address: str
    is_new_address: Optional[bool] = None
    timestamp: datetime


class WithdrawalResponse(WithdrawalCreate):
    """Schema for withdrawal response."""
    class Config:
        from_attributes = True


# ============================================================
# Risk Event Schemas
# ============================================================

class RiskFactorResponse(BaseModel):
    """Schema for risk factor response."""
    id: int
    factor_name: str
    factor_value: Optional[float] = None
    factor_description: Optional[str] = None

    class Config:
        from_attributes = True


class ClusterInfo(BaseModel):
    """Schema for cluster information in risk response."""
    cluster_id: int
    member_count: int
    risk_score: float


class RiskEventResponse(BaseModel):
    """Schema for risk event response."""
    user_id: str
    risk_score: float
    risk_level: str
    risk_probability: float
    primary_reason: Optional[str] = None
    recommended_action: Optional[str] = None
    detected_at: datetime
    event_type: Optional[str] = None
    ml_score: Optional[float] = None
    rule_score: Optional[float] = None
    graph_score: Optional[float] = None
    detection_methods: List[str] = []

    class Config:
        from_attributes = True


class RiskEventDetailResponse(RiskEventResponse):
    """Detailed risk event response with factors, cluster, and case context."""
    risk_factors: List[RiskFactorResponse] = []
    cluster: Optional[ClusterInfo] = None
    account_age: Optional[int] = None  # Account age in days
    total_volume: Optional[float] = None  # Total trading volume (sum of price * quantity)


class RiskScoreDistributionBucket(BaseModel):
    """Risk score distribution bucket for histogram."""
    range: str  # e.g., "0-20", "20-40", etc.
    count: int = 0
    percentage: float = 0.0


class RiskScoreStatistics(BaseModel):
    """Risk score statistics for analytics."""
    average: float = 0.0
    threshold: float = 80.0
    maximum: float = 0.0


class RiskLevelComposition(BaseModel):
    """Risk level composition data."""
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    total: int = 0


class DetectionSourceData(BaseModel):
    """Detection source analysis data showing detection coverage rate."""
    method: str  # Detection method name
    detected_accounts: int  # Number of high-risk accounts detected by this method
    detection_rate: float  # Percentage of high-risk accounts detected (0-100)
    color: str = "#3b82f6"


class ExecutiveSummary(BaseModel):
    """Executive risk summary KPIs."""
    analyzed_users: int = 0
    high_risk_accounts: int = 0
    fraud_networks: int = 0
    risk_recommendations: int = 0


class RiskOverviewResponse(BaseModel):
    """Schema for risk overview dashboard."""
    # Executive Risk Summary
    summary: ExecutiveSummary
    # Risk score distribution (histogram buckets)
    risk_score_distribution: List[RiskScoreDistributionBucket] = []
    # Risk score statistics
    risk_score_statistics: RiskScoreStatistics = None
    # Risk level composition
    risk_level_composition: RiskLevelComposition = None
    # Detection source analysis
    detection_sources: List[DetectionSourceData] = []


class RiskEventListResponse(BaseModel):
    """Schema for paginated risk event list."""
    total: int
    items: List[RiskEventResponse]


# ============================================================
# Graph Schemas
# ============================================================

class GraphNode(BaseModel):
    """Schema for graph node."""
    id: str
    type: str  # user, device, ip, wallet
    risk_level: Optional[str] = None
    label: Optional[str] = None


class GraphEdge(BaseModel):
    """Schema for graph edge."""
    source: str
    target: str
    type: str  # uses, connected_to, traded_with


class GraphDataResponse(BaseModel):
    """Schema for relationship graph data."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ============================================================
# Case Management Schemas
# ============================================================

class CaseCreate(BaseModel):
    """Schema for creating a case."""
    case_id: str
    user_id: str
    risk_event_id: Optional[int] = None


class CaseUpdate(BaseModel):
    """Schema for updating a case."""
    status: Optional[str] = None
    assigned_analyst: Optional[str] = None
    decision: Optional[str] = None
    notes: Optional[str] = None


class CaseResponse(BaseModel):
    """Schema for case response."""
    case_id: str
    user_id: str
    risk_event_id: Optional[int] = None
    status: str
    assigned_analyst: Optional[str] = None
    decision: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# Pipeline Schemas
# ============================================================

class PipelineStatusResponse(BaseModel):
    """Schema for pipeline status."""
    dataset_validation: str = "PENDING"
    feature_engineering: str = "PENDING"
    ml_scoring: str = "PENDING"
    graph_analysis: str = "PENDING"


class PipelineRunRequest(BaseModel):
    """Schema for triggering pipeline run."""
    run_full_pipeline: bool = True
    generate_risk_events: bool = True


class ModelTrainingResponse(BaseModel):
    """Schema for model training response."""
    status: str
    model_version: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    train_size: Optional[int] = None
    test_size: Optional[int] = None
    positive_ratio: Optional[float] = None
    feature_importance_count: Optional[int] = None
    baseline_saved: Optional[str] = None
    model_id: Optional[int] = None
    error: Optional[str] = None


# ============================================================
# Model Monitoring Schemas
# ============================================================

class ModelMetricsResponse(BaseModel):
    """Schema for model metrics."""
    model_name: str
    version: str
    metrics: dict[str, float]


class FeatureImportanceResponse(BaseModel):
    """Schema for feature importance."""
    name: str
    importance: float
    rank: int


class FeatureImportanceListResponse(BaseModel):
    """Schema for feature importance list."""
    features: List[FeatureImportanceResponse]


# ============================================================
# LLM Explanation Schemas
# ============================================================

class ExplanationRequest(BaseModel):
    """Schema for requesting LLM explanation."""
    user_id: str


class ExplanationResponse(BaseModel):
    """Schema for LLM explanation response."""
    summary: str
    key_findings: List[str] = []
    recommended_action: str


# ============================================================
# Risk Evidence Explainability Schemas
# ============================================================

class RiskSummary(BaseModel):
    """Risk summary from latest risk event."""
    risk_level: str
    risk_score: float
    primary_reason: Optional[str] = None
    recommended_action: Optional[str] = None
    detection_methods: List[str] = []
    detected_at: Optional[str] = None
    ml_score: Optional[float] = None
    rule_score: Optional[float] = None
    graph_score: Optional[float] = None


class TransactionEvidence(BaseModel):
    """Suspicious transaction evidence."""
    transaction_id: str
    symbol: str
    side: str
    price: float
    quantity: float
    value: float
    timestamp: Optional[str] = None
    risk_reason: str


class WithdrawalEvidence(BaseModel):
    """Suspicious withdrawal evidence."""
    withdrawal_id: str
    asset: str
    amount: float
    address: str
    is_new_address: Optional[bool] = None
    timestamp: Optional[str] = None
    risk_reason: str


class NetworkEvidence(BaseModel):
    """Network/graph evidence from cluster membership."""
    cluster_id: int
    cluster_name: str
    detection_type: str
    member_count: int
    cluster_risk_score: float
    role_in_cluster: Optional[str] = None
    related_accounts_count: int
    related_accounts: List[str] = []
    shared_devices: List[str] = []


class ConnectedAccountSignal(BaseModel):
    """Detailed signal for a connected account in the network."""
    user_id: str
    relationship_type: List[str] = []  # shared_device, shared_ip
    device_fingerprints: List[str] = []
    shared_ips: List[str] = []
    risk_level: str
    risk_score: float


class NetworkSignalsResponse(BaseModel):
    """Network signals showing entity-level relationship evidence."""
    connected_account_count: int
    connected_accounts: List[ConnectedAccountSignal] = []


class RiskFactorEvidence(BaseModel):
    """Detailed risk factor evidence."""
    factor_id: int
    factor_name: str
    factor_value: Optional[float] = None
    factor_description: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical


class FeatureEvidence(BaseModel):
    """Feature evidence from feature table."""
    shared_device_count: Optional[int] = None
    linked_account_count: Optional[int] = None
    unique_ip_count: Optional[int] = None
    trade_frequency_24h: Optional[int] = None
    trade_frequency_7d: Optional[int] = None
    opposite_trade_ratio: Optional[float] = None
    avg_trade_size: Optional[float] = None
    trade_volume_24h: Optional[float] = None
    account_age_days: Optional[int] = None
    active_days_count: Optional[int] = None
    withdrawal_risk_score: Optional[float] = None
    withdrawal_frequency_24h: Optional[int] = None
    withdrawal_volume_24h: Optional[float] = None


class RuleEvidence(BaseModel):
    """Rule evidence derived from feature values."""
    rule_name: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str


class RiskEvidenceResponse(BaseModel):
    """Complete risk evidence response for investigation."""
    user_id: str
    risk_summary: RiskSummary
    transaction_evidence: List[TransactionEvidence] = []
    withdrawal_evidence: List[WithdrawalEvidence] = []
    network_evidence: Optional[NetworkEvidence] = None
    risk_factor_evidence: List[RiskFactorEvidence] = []
    feature_evidence: Optional[FeatureEvidence] = None
    rule_evidence: List[RuleEvidence] = []


# ============================================================
# Data Upload Schemas
# ============================================================

class DataUploadResponse(BaseModel):
    """Schema for data upload response."""
    message: str
    files_processed: List[str] = []
    records_imported: dict[str, int] = {}
