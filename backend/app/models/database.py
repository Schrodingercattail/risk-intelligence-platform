"""
SQLAlchemy Database Models

All database tables are defined here using SQLAlchemy ORM.
These models represent the core data structure of the risk platform.
"""
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, DateTime, Text, ForeignKey, Index, Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

import enum


class RiskLevel(str, enum.Enum):
    """Risk level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CaseStatus(str, enum.Enum):
    """Case status enumeration."""
    NEW = "NEW"
    INVESTIGATING = "INVESTIGATING"
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    CLOSED = "CLOSED"


class ClusterType(str, enum.Enum):
    """Cluster detection type enumeration."""
    DEVICE_SHARING = "device_sharing"
    IP_SHARING = "ip_sharing"
    COORDINATED_TRADING = "coordinated_trading"
    WITHDRAWAL_PATTERN = "withdrawal_pattern"


# ============================================================
# Core Domain Models
# ============================================================

class User(Base):
    """User account information."""
    __tablename__ = "users"

    user_id = Column(String(50), primary_key=True)
    country = Column(String(10), nullable=True)
    kyc_level = Column(String(20), nullable=True)
    account_created_time = Column(DateTime(timezone=True), nullable=True)
    vip_level = Column(String(20), nullable=True)
    current_risk_score = Column(Numeric(5, 2), nullable=True)
    risk_level = Column(String(20), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    devices = relationship("Device", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    withdrawals = relationship("Withdrawal", back_populates="user")
    risk_events = relationship("RiskEvent", back_populates="user")
    cases = relationship("Case", back_populates="user")


class Device(Base):
    """Device and login information."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    device_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    location = Column(String(100), nullable=True)
    browser_fingerprint = Column(String(200), nullable=True)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="devices")


class Trade(Base):
    """Trading activity records."""
    __tablename__ = "trades"

    trade_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    price = Column(Numeric(20, 8), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    user = relationship("User", back_populates="trades")

    # Indexes for query optimization
    __table_args__ = (
        Index("idx_trades_user_timestamp", "user_id", "timestamp"),
        Index("idx_trades_symbol_time", "symbol", "timestamp"),
    )


class Withdrawal(Base):
    """Withdrawal activity records."""
    __tablename__ = "withdrawals"

    withdraw_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    asset = Column(String(20), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    address = Column(String(200), nullable=False)
    is_new_address = Column(Boolean, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    user = relationship("User", back_populates="withdrawals")


# ============================================================
# Risk Management Models
# ============================================================

class RiskEvent(Base):
    """Detected risk events for users."""
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=False)
    risk_probability = Column(Numeric(5, 4), nullable=False)
    risk_level = Column(String(20), nullable=False)
    primary_reason = Column(String(200), nullable=True)
    recommended_action = Column(String(100), nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String(50), nullable=True)

    # Component scores (for hybrid scoring)
    ml_score = Column(Numeric(5, 2), nullable=True)
    rule_score = Column(Numeric(5, 2), nullable=True)
    graph_score = Column(Numeric(5, 2), nullable=True)

    # Relationships
    user = relationship("User", back_populates="risk_events")
    risk_factors = relationship("RiskFactor", back_populates="risk_event", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_risk_events_user_detected", "user_id", "detected_at"),
    )


class RiskFactor(Base):
    """Individual risk factors contributing to a risk event."""
    __tablename__ = "risk_factors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    risk_event_id = Column(Integer, ForeignKey("risk_events.id"), nullable=False)
    factor_name = Column(String(100), nullable=False)
    factor_value = Column(Numeric(10, 4), nullable=True)
    factor_description = Column(Text, nullable=True)

    # Relationships
    risk_event = relationship("RiskEvent", back_populates="risk_factors")


class AccountCluster(Base):
    """Detected suspicious account clusters."""
    __tablename__ = "account_clusters"

    cluster_id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_name = Column(String(50), nullable=True)
    detection_type = Column(String(50), nullable=False)
    member_count = Column(Integer, nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    members = relationship("ClusterMember", back_populates="cluster", cascade="all, delete-orphan")


class ClusterMember(Base):
    """Members of suspicious account clusters."""
    __tablename__ = "cluster_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("account_clusters.cluster_id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    role_in_cluster = Column(String(50), nullable=True)  # hub, spoke, isolated
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    cluster = relationship("AccountCluster", back_populates="members")


class Case(Base):
    """Investigation cases for risk events."""
    __tablename__ = "cases"

    case_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    risk_event_id = Column(Integer, ForeignKey("risk_events.id"), nullable=True)
    status = Column(String(50), nullable=False, default=CaseStatus.NEW.value)
    assigned_analyst = Column(String(100), nullable=True)
    decision = Column(String(50), nullable=True)  # freeze, monitor, no_action
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="cases")


# ============================================================
# ML Model Metadata
# ============================================================

class ModelMetadata(Base):
    """Information about deployed ML models."""
    __tablename__ = "model_metadata"

    model_id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    auc_score = Column(Numeric(5, 4), nullable=True)
    ks_score = Column(Numeric(5, 4), nullable=True)
    psi_score = Column(Numeric(5, 4), nullable=True)
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    feature_importance = relationship("FeatureImportance", back_populates="model", cascade="all, delete-orphan")


class FeatureImportance(Base):
    """Feature importance scores for models."""
    __tablename__ = "feature_importance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("model_metadata.model_id"), nullable=False)
    feature_name = Column(String(100), nullable=False)
    importance_score = Column(Numeric(10, 6), nullable=False)
    rank = Column(Integer, nullable=False)

    # Relationships
    model = relationship("ModelMetadata", back_populates="feature_importance")

    __table_args__ = (
        Index("idx_feature_importance_model_rank", "model_id", "rank"),
    )


# ============================================================
# Feature Table (ML Features)
# ============================================================

class FeatureTable(Base):
    """
    ML feature table storing engineered features for each user.

    This table serves as the input for the ML model inference.
    """
    __tablename__ = "feature_table"

    user_id = Column(String(50), primary_key=True)

    # Device & Network Features
    shared_device_count = Column(Integer, nullable=True)
    linked_account_count = Column(Integer, nullable=True)
    unique_ip_count = Column(Integer, nullable=True)

    # Trading Features
    trade_frequency_24h = Column(Integer, nullable=True)
    trade_frequency_7d = Column(Integer, nullable=True)
    opposite_trade_ratio = Column(Numeric(5, 4), nullable=True)
    avg_trade_size = Column(Numeric(20, 8), nullable=True)
    trade_volume_24h = Column(Numeric(20, 8), nullable=True)

    # Temporal Features
    account_age_days = Column(Integer, nullable=True)
    active_days_count = Column(Integer, nullable=True)

    # Withdrawal Features
    withdrawal_risk_score = Column(Numeric(5, 4), nullable=True)
    withdrawal_frequency_24h = Column(Integer, nullable=True)
    withdrawal_volume_24h = Column(Numeric(20, 8), nullable=True)
    first_withdrawal_flag = Column(Boolean, nullable=True)

    # Cluster Features
    cluster_size = Column(Integer, nullable=True)
    cluster_risk_score = Column(Numeric(5, 2), nullable=True)

    # Labels (for supervised learning)
    is_risky = Column(Boolean, nullable=True)

    # Metadata
    feature_calculated_at = Column(DateTime(timezone=True), server_default=func.now())
