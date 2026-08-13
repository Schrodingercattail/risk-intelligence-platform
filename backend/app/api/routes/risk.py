"""
Risk Command Center API Routes

Main API for risk event management and investigation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import time
import hashlib
from pathlib import Path
from collections import OrderedDict

from app.db.session import get_db
from app.services.risk_service import RiskScoringService
from app.services.graph_service import GraphAnalysisService
from app.services.llm_service import LLMExplanationService, sanitize_policy_quote
from app.services.policy_rag_service import PolicyRAGService
from app.services.explain_metrics import get_explain_metrics as _get_explain_metrics, log_explain_request
from app.services.citation_service import SimpleCitationService, create_simple_citation_service
from app.services.citation_retrieval_service import CitationRetrievalService, create_citation_retrieval_service
from app.services.data_quality_service import create_data_quality_service
from app.models.database import RiskEvent, User, RiskLevel, Case, CaseStatus
from app.models.schemas import (
    RiskOverviewResponse,
    RiskEventResponse,
    RiskEventDetailResponse,
    RiskEventListResponse,
    RiskFactorResponse,
    GraphDataResponse,
    ExplanationRequest,
    ExplanationResponse,
    ClusterInfo,
    RiskEvidenceResponse,
    PolicyCitation,
)
from sqlalchemy import select, func, desc, text
from app.config import settings
import logging

router = APIRouter(prefix="/risk", tags=["Risk"])
logger = logging.getLogger(__name__)


def _safe_increment_metrics(metrics, method_name: str) -> None:
    """
    Safely call a metrics increment method without breaking the flow.

    Args:
        metrics: The ExplainMetrics instance
        method_name: Name of the method to call (e.g., 'increment_requests')
    """
    try:
        getattr(metrics, method_name)()
    except Exception as e:
        logger.warning(f"Failed to track metrics ({method_name}): {e}")


def _safe_record_latency(metrics, latency_ms: float) -> None:
    """
    Safely record latency without breaking the flow.

    Args:
        metrics: The ExplainMetrics instance
        latency_ms: Latency in milliseconds
    """
    try:
        metrics.record_latency(latency_ms)
    except Exception as e:
        logger.warning(f"Failed to record latency: {e}")


def _record_explanation_source_metrics(metrics, explanation: dict) -> tuple[str, bool]:
    """
    Record explanation-source and fallback counters for a freshly-computed
    (non-cached) explanation, and return the values used for logging.

    Called exactly once per UNCACHED /api/risk/explain request, after the
    explanation is generated. Cache-hit responses skip this so the source and
    fallback totals are never double-counted for a single logical explanation.

    Counting matrix (exactly one branch per request, no double counting):

        LLM enabled | explanation_source | counters incremented
        ------------+---------------------+-------------------------------------
        No          | MODEL_FALLBACK      | llm_disabled_total, fallback_total
        Yes         | LLM                 | llm_total
        Yes         | MODEL_FALLBACK      | llm_failed_total, fallback_total

    What counts as a fallback: any response served by the model-based
    explanation - either because the LLM is disabled / has no API key
    (model-based by default) or because the LLM was attempted but failed or
    timed out. A successful LLM response is never a fallback.

    Note: increment_llm_disabled / increment_llm_failed each bump fallback_total
    internally (see ExplainMetrics); increment_llm does not. This helper is the
    only call site, so exactly one counter path runs per request.

    Returns:
        (explanation_source, fallback_used)
    """
    explanation_source = explanation.get("explanation_source", "MODEL_FALLBACK")
    llm_was_enabled = bool(settings.ENABLE_LLM_EXPLANATION and settings.ANTHROPIC_API_KEY)

    if llm_was_enabled:
        if explanation_source == "LLM":
            _safe_increment_metrics(metrics, "increment_llm")
        else:
            _safe_increment_metrics(metrics, "increment_llm_failed")
    else:
        _safe_increment_metrics(metrics, "increment_llm_disabled")

    fallback_used = explanation_source == "MODEL_FALLBACK"
    return explanation_source, fallback_used


# ============================================================
# In-Memory Cache for Explanation Results
# ============================================================

class ExplanationCache:
    """Simple in-memory TTL cache for explanation results."""

    def __init__(self, max_size: int = 1024, ttl_seconds: int = 600):
        self.cache: OrderedDict[str, tuple] = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.metrics = _get_explain_metrics()  # Get metrics instance

    def get(self, key: str) -> Optional[dict]:
        """Get cached entry if not expired. Tracks cache hit/miss metrics."""
        if key not in self.cache:
            # Cache miss (key not found)
            _safe_increment_metrics(self.metrics, "increment_cache_miss")
            return None

        timestamp, value = self.cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            # Cache miss (expired)
            del self.cache[key]
            _safe_increment_metrics(self.metrics, "increment_cache_miss")
            return None

        # Cache hit
        _safe_increment_metrics(self.metrics, "increment_cache_hit")
        # Move to end (LRU)
        self.cache.move_to_end(key)
        return value

    def set(self, key: str, value: dict) -> None:
        """Set cache entry with current timestamp."""
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cache.popitem(last=False)

        self.cache[key] = (time.time(), value)
        self.cache.move_to_end(key)


# Global cache instance
_explanation_cache = ExplanationCache(
    max_size=settings.EXPLAIN_CACHE_MAX_SIZE,
    ttl_seconds=settings.EXPLAIN_CACHE_TTL_SECONDS
)


# ============================================================
# Simple In-Memory Rate Limiter
# ============================================================

class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        # Track requests: {ip: [(timestamp, ...)]}
        self.requests: dict[str, list[tuple]] = {}
        self.metrics = _get_explain_metrics()  # Get metrics instance

    def is_allowed(self, client_id: str) -> tuple[bool, Optional[str]]:
        """Check if request is allowed. Returns (allowed, error_message)."""
        now = time.time()
        window_start = now - 60  # 1 minute window

        # Clean old entries
        if client_id in self.requests:
            # Remove requests outside the window
            self.requests[client_id] = [
                (ts, _) for (ts, _) in self.requests[client_id]
                if ts > window_start
            ]

        # Get current count
        if client_id not in self.requests:
            self.requests[client_id] = []
        current_count = len(self.requests[client_id])

        if current_count >= self.requests_per_minute:
            # Rate limit exceeded - track this
            _safe_increment_metrics(self.metrics, "increment_rate_limited")
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"

        # Add this request
        self.requests[client_id].append((now, None))
        return True, None


# Global rate limiter instance
_rate_limiter = RateLimiter(requests_per_minute=settings.EXPLAIN_RATE_LIMIT_PER_MIN)


def _get_policy_version() -> str:
    """Derive policy version from latest mtime of policy files."""
    try:
        policies_dir = Path(__file__).resolve().parents[3] / "policies"
        if not policies_dir.exists():
            return "no-policies"

        # Get latest mtime of any .md file
        latest_mtime = 0
        for p in policies_dir.glob("*.md"):
            mtime = p.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime

        return str(int(latest_mtime)) if latest_mtime > 0 else "empty-policies"
    except Exception:
        return "unknown"


def _generate_cache_key(user_id: str, audience: str, risk_event: dict, cache_buster: str = "") -> str:
    """Generate cache key from relevant fields."""
    # Use key identifiers that affect explanation output
    key_parts = [
        user_id,
        audience,
        str(risk_event.get('pipeline_run_id', 'no-run')),
        str(risk_event.get('model_version', 'no-model')),
        _get_policy_version(),
        cache_buster,  # For cache invalidation
    ]
    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()


def _safe_dump(obj):
    """
    Safely serialize an object to dict, handling various object types.

    Handles:
    - None: returns None
    - dict: returns as-is
    - Pydantic v2 models (model_dump method)
    - Pydantic v1 models (dict method)
    - Other objects: returns as-is

    This ensures robustness when the data source returns different types.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "dict"):
        return obj.dict()
    else:
        return obj


def _generate_model_based_explanation(
    risk_event: dict,
    factors: list[dict],
    graph_data: dict
) -> dict:
    """
    Generate model-based explanation from risk analysis outputs.

    This is the DEFAULT behavior when LLM is not enabled.
    Creates structured explanations from ML scores, rule hits, and graph signals.

    Args:
        risk_event: Risk event data with scores
        factors: List of risk factor details
        graph_data: Optional relationship graph data

    Returns:
        Dict with summary, key_findings, and recommended_action
    """
    # Extract scores
    ml_score = risk_event.get('ml_score', 0)
    rule_score = risk_event.get('rule_score', 0)
    graph_score = risk_event.get('graph_score', 0)
    risk_score = risk_event.get('risk_score', 0)
    risk_level = risk_event.get('risk_level', 'UNKNOWN')

    # Build summary from model outputs
    summary = (
        f"This account received a {risk_level.lower()} risk score ({risk_score:.2f}/100). "
        f"Primary concern: {risk_event.get('primary_reason', 'Suspicious activity detected')}."
    )

    # Build contributing factors from signal scores
    key_findings = []

    if ml_score > 0:
        key_findings.append(f"ML Signal Score: {ml_score:.2f}")

    if rule_score > 0:
        key_findings.append(f"Rule Engine Signal Score: {rule_score:.2f}")

    if graph_score > 0:
        key_findings.append(f"Graph Network Signal Score: {graph_score:.2f}")

    # Add specific risk factors if available
    for factor in factors[:3]:  # Top 3 factors
        factor_name = factor.get('factor_name', 'Unknown factor')
        key_findings.append(f"Elevated {factor_name}")

    # If no findings, add default
    if not key_findings:
        key_findings.append("Risk signals detected through analysis")

    # Build recommended action from risk event
    recommended_action = risk_event.get('recommended_action', 'Review case')

    return {
        "summary": summary,
        "key_findings": key_findings,
        "recommended_action": recommended_action
    }


def _get_detection_methods(
    ml_score: Optional[float],
    rule_score: Optional[float],
    graph_score: Optional[float]
) -> list[str]:
    """
    Get list of detection methods that contributed meaningful risk signals for this case.

    Detection attribution uses explicit thresholds defined in config:
    - LightGBM: ml_score >= DETECTION_ML_THRESHOLD
    - Rule Engine: rule_score >= DETECTION_RULE_THRESHOLD
    - Graph Network: graph_score >= DETECTION_GRAPH_THRESHOLD

    This represents detection attribution metadata, NOT score contribution or risk classification.
    """
    methods = []

    if ml_score is not None and ml_score >= settings.DETECTION_ML_THRESHOLD:
        methods.append("LightGBM")
    if rule_score is not None and rule_score >= settings.DETECTION_RULE_THRESHOLD:
        methods.append("Rule Engine")
    if graph_score is not None and graph_score >= settings.DETECTION_GRAPH_THRESHOLD:
        methods.append("Graph Network")

    return methods


@router.get("/overview", response_model=RiskOverviewResponse)
async def get_risk_overview(
    db: AsyncSession = Depends(get_db)
):
    """Get risk overview dashboard metrics."""

    # Total analyzed users
    total_users_result = await db.execute(
        select(func.count(User.user_id))
    )
    analyzed_users = total_users_result.scalar() or 0

    # High risk accounts (HIGH + CRITICAL)
    high_risk_result = await db.execute(
        select(func.count(User.user_id))
        .where(User.risk_level == RiskLevel.HIGH.value)
    )
    high_risk_accounts = high_risk_result.scalar() or 0

    # Add CRITICAL to high risk
    critical_result = await db.execute(
        select(func.count(User.user_id))
        .where(User.risk_level == RiskLevel.CRITICAL.value)
    )
    high_risk_accounts += critical_result.scalar() or 0

    # Fraud Networks - unique users linked to suspicious clusters
    # Count distinct users who are members of suspicious clusters detected through network analysis
    from app.models.database import ClusterMember
    fraud_networks_result = await db.execute(
        select(func.count(func.distinct(ClusterMember.user_id)))
    )
    fraud_networks = fraud_networks_result.scalar() or 0

    # Risk recommendations - users with AI-generated recommended actions
    # Count unique users with risk events that have recommended actions
    recommendations_result = await db.execute(
        select(func.count(func.distinct(RiskEvent.user_id)))
        .join(User, RiskEvent.user_id == User.user_id)
        .where(User.risk_level.in_([RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]))
        .where(RiskEvent.recommended_action.isnot(None))
    )
    risk_recommendations = recommendations_result.scalar() or 0

    # Executive summary
    executive_summary = {
        "analyzed_users": analyzed_users,
        "high_risk_accounts": high_risk_accounts,
        "fraud_networks": fraud_networks,
        "risk_recommendations": risk_recommendations
    }

    # Risk score distribution - bucketed histogram
    # Define buckets: 0-20, 20-40, 40-60, 60-70, 70-85, 85-100
    buckets = ["0-20", "20-40", "40-60", "60-70", "70-85", "85-100"]
    bucket_ranges = [(0, 20), (20, 40), (40, 60), (60, 70), (70, 85), (85, 100)]

    risk_score_distribution = []
    for bucket_label, (lower, upper) in zip(buckets, bucket_ranges):
        if upper == 100:
            # Last bucket includes upper bound
            count_result = await db.execute(
                select(func.count(User.user_id))
                .where(User.current_risk_score >= lower)
                .where(User.current_risk_score <= upper)
            )
        else:
            count_result = await db.execute(
                select(func.count(User.user_id))
                .where(User.current_risk_score >= lower)
                .where(User.current_risk_score < upper)
            )
        count = count_result.scalar() or 0
        percentage = round((count / analyzed_users * 100), 1) if analyzed_users > 0 else 0.0
        risk_score_distribution.append({
            "range": bucket_label,
            "count": count,
            "percentage": percentage
        })

    # Risk score statistics
    avg_score_result = await db.execute(
        select(func.avg(User.current_risk_score))
        .where(User.current_risk_score.is_not(None))
    )
    average_score = float(avg_score_result.scalar() or 0.0)

    max_score_result = await db.execute(
        select(func.max(User.current_risk_score))
        .where(User.current_risk_score.isnot(None))
    )
    max_score = float(max_score_result.scalar() or 0.0)

    risk_score_statistics = {
        "average": average_score,
        "threshold": settings.HIGH_RISK_THRESHOLD * 100,  # 70.0
        "maximum": max_score
    }

    # Risk level composition
    critical_count = await db.scalar(
        select(func.count(User.user_id))
        .where(User.risk_level == RiskLevel.CRITICAL.value)
    ) or 0

    high_count = await db.scalar(
        select(func.count(User.user_id))
        .where(User.risk_level == RiskLevel.HIGH.value)
    ) or 0

    medium_count = await db.scalar(
        select(func.count(User.user_id))
        .where(User.risk_level == RiskLevel.MEDIUM.value)
    ) or 0

    low_count = await db.scalar(
        select(func.count(User.user_id))
        .where(User.risk_level == RiskLevel.LOW.value)
    ) or 0

    total_accounts = critical_count + high_count + medium_count + low_count

    risk_level_composition = {
        "critical": critical_count,
        "high": high_count,
        "medium": medium_count,
        "low": low_count,
        "total": total_accounts
    }

    # Detection Attribution Analysis - read-only attribution from RiskEvent
    # NEW DEFINITION: Calculate from ALL accounts with at least one detection signal
    # NOT limited to HIGH/CRITICAL risk levels
    # Detection uses explicit thresholds defined in config

    # Step 1: Find all accounts where at least one signal meets the threshold
    from sqlalchemy import or_, and_
    detected_accounts_cte = await db.execute(
        select(func.distinct(User.user_id))
        .join(RiskEvent, RiskEvent.user_id == User.user_id)
        .where(
            or_(
                and_(RiskEvent.ml_score.isnot(None), RiskEvent.ml_score >= settings.DETECTION_ML_THRESHOLD),
                and_(RiskEvent.rule_score.isnot(None), RiskEvent.rule_score >= settings.DETECTION_RULE_THRESHOLD),
                and_(RiskEvent.graph_score.isnot(None), RiskEvent.graph_score >= settings.DETECTION_GRAPH_THRESHOLD)
            )
        )
    )
    detected_account_ids = [row[0] for row in detected_accounts_cte]
    total_detected_accounts = len(detected_account_ids)

    detection_sources = []
    signal_combination_breakdown = None

    if total_detected_accounts > 0:
        # Step 2: Calculate detection attribution per method
        # LightGBM: count detected users where ML signal triggered
        ml_detected_result = await db.execute(
            select(func.count(func.distinct(User.user_id)))
            .join(RiskEvent, RiskEvent.user_id == User.user_id)
            .where(User.user_id.in_(detected_account_ids))
            .where(RiskEvent.ml_score.isnot(None))
            .where(RiskEvent.ml_score >= settings.DETECTION_ML_THRESHOLD)
        )
        ml_detected = ml_detected_result.scalar() or 0

        # Rule Engine: count detected users where Rule signal triggered
        rule_detected_result = await db.execute(
            select(func.count(func.distinct(User.user_id)))
            .join(RiskEvent, RiskEvent.user_id == User.user_id)
            .where(User.user_id.in_(detected_account_ids))
            .where(RiskEvent.rule_score.isnot(None))
            .where(RiskEvent.rule_score >= settings.DETECTION_RULE_THRESHOLD)
        )
        rule_detected = rule_detected_result.scalar() or 0

        # Graph Network: count detected users where Graph signal triggered
        graph_detected_result = await db.execute(
            select(func.count(func.distinct(User.user_id)))
            .join(RiskEvent, RiskEvent.user_id == User.user_id)
            .where(User.user_id.in_(detected_account_ids))
            .where(RiskEvent.graph_score.isnot(None))
            .where(RiskEvent.graph_score >= settings.DETECTION_GRAPH_THRESHOLD)
        )
        graph_detected = graph_detected_result.scalar() or 0

        # Step 3: Calculate signal combination breakdown among detected accounts
        # Use GROUP BY with MAX() to ensure each user is counted only once,
        # even if they have multiple RiskEvent records
        from sqlalchemy import case, cast, Integer
        signal_query = await db.execute(
            select(
                User.user_id,
                func.max(cast(case((RiskEvent.ml_score >= settings.DETECTION_ML_THRESHOLD, True), else_=False), Integer)).label('has_ml'),
                func.max(cast(case((RiskEvent.rule_score >= settings.DETECTION_RULE_THRESHOLD, True), else_=False), Integer)).label('has_rule'),
                func.max(cast(case((RiskEvent.graph_score >= settings.DETECTION_GRAPH_THRESHOLD, True), else_=False), Integer)).label('has_graph')
            )
            .join(RiskEvent, RiskEvent.user_id == User.user_id)
            .where(User.user_id.in_(detected_account_ids))
            .group_by(User.user_id)
        )

        ml_only = 0
        rule_only = 0
        graph_only = 0
        multi_signal = 0

        for row in signal_query:
            has_ml = row.has_ml == 1
            has_rule = row.has_rule == 1
            has_graph = row.has_graph == 1

            signal_count = sum([has_ml, has_rule, has_graph])

            if signal_count == 1:
                if has_ml:
                    ml_only += 1
                elif has_rule:
                    rule_only += 1
                elif has_graph:
                    graph_only += 1
            elif signal_count >= 2:
                # Multi-signal accounts have 2 or more signals
                multi_signal += 1

        detection_sources = [
            {
                "method": "LightGBM Model",
                "account_count": ml_detected,
                "percentage": round((ml_detected / total_detected_accounts) * 100, 1),
                "color": "#8b5cf6"
            },
            {
                "method": "Rule Engine",
                "account_count": rule_detected,
                "percentage": round((rule_detected / total_detected_accounts) * 100, 1),
                "color": "#3b82f6"
            },
            {
                "method": "Graph Network",
                "account_count": graph_detected,
                "percentage": round((graph_detected / total_detected_accounts) * 100, 1),
                "color": "#06b6d4"
            }
        ]

        signal_combination_breakdown = {
            "ml_only": ml_only,
            "rule_only": rule_only,
            "graph_only": graph_only,
            "multi_signal": multi_signal
        }
    else:
        detection_sources = [
            {"method": "LightGBM Model", "account_count": 0, "percentage": 0.0, "color": "#8b5cf6"},
            {"method": "Rule Engine", "account_count": 0, "percentage": 0.0, "color": "#3b82f6"},
            {"method": "Graph Network", "account_count": 0, "percentage": 0.0, "color": "#06b6d4"}
        ]

        signal_combination_breakdown = {
            "ml_only": 0,
            "rule_only": 0,
            "graph_only": 0,
            "multi_signal": 0
        }

    return RiskOverviewResponse(
        summary=executive_summary,
        risk_score_distribution=risk_score_distribution,
        risk_score_statistics=risk_score_statistics,
        risk_level_composition=risk_level_composition,
        detection_sources=detection_sources,
        signal_combination_breakdown=signal_combination_breakdown
    )


@router.get("/events", response_model=RiskEventListResponse)
async def get_risk_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)"),
    pipeline_run_id: Optional[str] = Query(None, description="Filter by pipeline run ID - returns events from a specific batch"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of risk events.

    By default, returns the most recent events across all pipeline runs.
    Use pipeline_run_id to filter events from a specific batch.
    """
    query = select(RiskEvent).order_by(desc(RiskEvent.detected_at))

    if risk_level:
        query = query.where(RiskEvent.risk_level == risk_level)

    if pipeline_run_id:
        query = query.where(RiskEvent.pipeline_run_id == pipeline_run_id)

    # Get total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    events = result.scalars().all()

    items = [RiskEventResponse.model_validate(event) for event in events]

    return RiskEventListResponse(total=total, items=items)


@router.get("/events/{user_id}", response_model=RiskEventDetailResponse)
async def get_user_risk_detail(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed risk information for a specific user, including case context."""
    from datetime import datetime, timezone

    # Get latest risk event
    result = await db.execute(
        select(RiskEvent)
        .where(RiskEvent.user_id == user_id)
        .order_by(desc(RiskEvent.detected_at))
        .limit(1)
    )
    risk_event = result.scalar_one_or_none()

    if not risk_event:
        raise HTTPException(status_code=404, detail=f"Risk event not found for user {user_id}")

    # Get risk factors
    from app.models.database import RiskFactor
    factors_result = await db.execute(
        select(RiskFactor)
        .where(RiskFactor.risk_event_id == risk_event.id)
    )
    factors = factors_result.scalars().all()

    # Check for cluster membership
    from app.models.database import ClusterMember, AccountCluster
    cluster_result = await db.execute(
        select(ClusterMember, AccountCluster)
        .join(AccountCluster, ClusterMember.cluster_id == AccountCluster.cluster_id)
        .where(ClusterMember.user_id == user_id)
        .limit(1)
    )
    cluster_row = cluster_result.first()
    cluster_info = None
    if cluster_row:
        member, cluster = cluster_row
        cluster_info = ClusterInfo(
            cluster_id=cluster.cluster_id,
            member_count=cluster.member_count,
            risk_score=float(cluster.risk_score),
        )

    # Compute account_age from User.account_created_time
    user_result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = user_result.scalar_one_or_none()
    account_age = None
    if user and user.account_created_time:
        account_age = (datetime.now(timezone.utc) - user.account_created_time).days

    # Compute total_volume from Trade table (sum of price * quantity)
    from app.models.database import Trade
    volume_result = await db.execute(
        select(func.sum(Trade.price * Trade.quantity))
        .where(Trade.user_id == user_id)
    )
    total_volume = volume_result.scalar()

    return RiskEventDetailResponse(
        **RiskEventResponse.model_validate(risk_event).model_dump(),
        risk_factors=[RiskFactorResponse.model_validate(f) for f in factors],
        cluster=cluster_info,
        account_age=account_age,
        total_volume=float(total_volume) if total_volume else None,
    )


@router.get("/cases", response_model=RiskEventListResponse)
async def get_investigation_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: CRITICAL, HIGH, MEDIUM"),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of cases for investigation.

    Returns users requiring investigation based on their risk level.
    Default (Needs Review): CRITICAL, HIGH, and MEDIUM risk cases.
    Use risk_level parameter to filter specific levels.
    """
    # Determine which risk levels to include based on filter
    if risk_level:
        # Specific risk level requested
        allowed_levels = [risk_level.upper()]
    else:
        # Default: Needs Review = CRITICAL + HIGH + MEDIUM
        allowed_levels = [RiskLevel.CRITICAL.value, RiskLevel.HIGH.value, RiskLevel.MEDIUM.value]

    # Query for users with their risk levels
    query = (
        select(User)
        .where(User.risk_level.in_(allowed_levels))
        .order_by(desc(User.current_risk_score))
    )

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        search_lower = search_pattern.lower()
        count_result = await db.execute(
            select(func.count(User.user_id))
            .where(User.risk_level.in_(allowed_levels))
            .where(User.user_id.ilike(search_lower))
        )
        total = count_result.scalar() or 0
        query = query.where(User.user_id.ilike(search_pattern))
    else:
        # Get total count without search
        count_result = await db.execute(
            select(func.count(User.user_id))
            .where(User.risk_level.in_(allowed_levels))
        )
        total = count_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    # Build response items - get risk events for each user
    items = []
    for user in users:
        # Get the most recent risk event for this user
        risk_event_result = await db.execute(
            select(RiskEvent)
            .where(RiskEvent.user_id == user.user_id)
            .order_by(desc(RiskEvent.detected_at))
            .limit(1)
        )
        risk_event = risk_event_result.scalar_one_or_none()

        if risk_event:
            # Get primary risk factor as the display reason
            from app.models.database import RiskFactor
            factors_result = await db.execute(
                select(RiskFactor)
                .where(RiskFactor.risk_event_id == risk_event.id)
                .limit(3)
            )
            factors = factors_result.scalars().all()

            # Build risk event response
            event_response = RiskEventResponse(
                user_id=user.user_id,
                risk_score=float(user.current_risk_score or 0),
                risk_level=user.risk_level or "MEDIUM",
                risk_probability=float(risk_event.risk_probability),
                primary_reason=risk_event.primary_reason or "Risk signals detected",
                recommended_action=risk_event.recommended_action,
                detected_at=risk_event.detected_at.isoformat() if risk_event.detected_at else None,
                event_type=risk_event.event_type,
                ml_score=float(risk_event.ml_score) if risk_event.ml_score else None,
                rule_score=float(risk_event.rule_score) if risk_event.rule_score else None,
                graph_score=float(risk_event.graph_score) if risk_event.graph_score else None,
                detection_methods=_get_detection_methods(
                    float(risk_event.ml_score) if risk_event.ml_score else None,
                    float(risk_event.rule_score) if risk_event.rule_score else None,
                    float(risk_event.graph_score) if risk_event.graph_score else None,
                ),
            )
            items.append(event_response)

    return RiskEventListResponse(total=total, items=items)


@router.get("/graph/{user_id}", response_model=GraphDataResponse)
async def get_user_graph(
    user_id: str,
    depth: int = Query(2, ge=1, le=3),
    db: AsyncSession = Depends(get_db),
):
    """Get relationship graph for a user."""
    service = GraphAnalysisService(db)
    graph_data = await service.get_user_graph(user_id, depth=depth)

    return GraphDataResponse(**graph_data)


def _retrieve_finding_specific_citations(
    key_findings: List[str],
    ml_score: Optional[float],
    rule_score: Optional[float],
    graph_score: Optional[float],
    factors: List[dict],
    has_graph_evidence: bool,
    audience: str
) -> tuple[List[dict], dict]:
    """
    Retrieve finding-specific citations using evidence-aware mapping.

    For each finding, generates a targeted RAG query based on finding type
    and retrieves relevant policy citations. Uses CitationRegistry for
    deduplication and budget control.

    Args:
        key_findings: List of finding texts
        ml_score: ML signal score
        rule_score: Rule signal score
        graph_score: Graph signal score
        factors: Risk factor list
        has_graph_evidence: Whether graph evidence exists
        audience: Audience mode for quote redaction

    Returns:
        Tuple of (all_citations list, finding_to_citations dict)
    """
    # Initialize citation mapper and registry
    mapper = DomainAwareCitationMapper()
    registry = create_citation_registry(max_citations=10)

    # Map findings to citation queries
    queries = mapper.map_findings_to_queries(
        key_findings=key_findings,
        ml_score=ml_score,
        rule_score=rule_score,
        graph_score=graph_score,
        factors=factors,
        has_graph_evidence=has_graph_evidence
    )

    # Retrieve citations for each finding
    finding_to_citations = {}
    rag = PolicyRAGService()

    for finding_text, query_obj in zip(key_findings, queries):
        finding_citation_ids = []

        # Skip RAG for empty queries
        if not query_obj.query or query_obj.query.strip() == "":
            finding_to_citations[finding_text] = finding_citation_ids
            continue

        try:
            # Retrieve finding-specific citations
            chunks = rag.search(query_obj.query, top_k=query_obj.top_k)

            for chunk in chunks:
                # Apply audience-based quote redaction
                if audience == "business":
                    sanitized_quote = "[REDACTED]"
                else:
                    sanitized_quote = sanitize_policy_quote(chunk.text[:400].strip())

                # Register citation (deduplication happens here)
                citation_id = registry.register(
                    doc=chunk.doc,
                    section=chunk.section,
                    quote=sanitized_quote,
                    chunk_id=chunk.chunk_id,
                    finding_type=query_obj.finding_type.value if query_obj.finding_type else None
                )

                finding_citation_ids.append(citation_id)

        except Exception as e:
            # RAG failure for this finding — continue with others
            logger.warning(f"RAG retrieval failed for finding '{finding_text[:50]}...': {e}")

        finding_to_citations[finding_text] = finding_citation_ids

    # Get final citations within budget (deduplicated and prioritized)
    all_citations = registry.get_citation_dict()

    # Log registry stats for monitoring
    stats = registry.get_stats()
    final_count = len(all_citations)
    if stats["total_registered"] > final_count:
        # Budget was enforced - log the reduction
        logger.info(
            f"Citation registry: {stats['total_registered']} registered, "
            f"{final_count} in response (deduplication saved {stats['deduplication_saved']})"
        )

    return all_citations, finding_to_citations


@router.post("/explain", response_model=ExplanationResponse)
async def generate_explanation(
    payload: ExplanationRequest,
    request: Request,  # Inject actual HTTP Request for headers/client IP (must come before query params with defaults)
    audience: str = Query("investigator", description="Audience mode: 'investigator' (default, full detail) or 'business' (reduced sensitive detail)"),
    bypass_cache: bool = Query(False, description="Bypass cache and force fresh computation"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate risk explanation for investigation.

    Behavior:
    - Default: Returns model-based explanation from risk analysis outputs
    - Optional (ENABLE_LLM_EXPLANATION=true): Uses LLM for natural language summaries
    - audience parameter controls output granularity:
      - investigator: Full citations with redacted quotes, detailed key_findings
      - business: Redacted quotes, reduced sensitive phrasing in key_findings
    - Results are cached (TTL=600s) to reduce repeated computation
    - Set bypass_cache=true to force fresh computation (useful for testing)
    - Rate limited to 30 requests/minute per client IP

    The platform operates fully without LLM integration.
    NOTE: This is a demo audience-based output mode; production should enforce RBAC via gateway/SSO.
    """
    # Get metrics instance and start timing
    metrics = _get_explain_metrics()
    start_time = time.time()

    # Get client IP for rate limiting (from actual HTTP Request)
    # Prefer x-forwarded-for (take first IP if multiple)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.headers.get("x-real-ip", request.client.host or "unknown")

    if client_ip == "unknown":
        # Fallback to user_id if client IP cannot be determined
        client_ip = f"user:{payload.user_id}"

    # Check rate limit
    allowed, rate_error = _rate_limiter.is_allowed(client_ip)
    if not allowed:
        # Rate limit exceeded - metrics already tracked by RateLimiter
        _safe_increment_metrics(metrics, "increment_requests")
        _safe_increment_metrics(metrics, "increment_rate_limited")

        latency_ms = (time.time() - start_time) * 1000
        _safe_record_latency(metrics, latency_ms)

        log_explain_request(
            status_code=429,
            latency_ms=latency_ms,
            cache_hit=False,
            rate_limited=True,
            fallback_used=False,
            explanation_source=None,
            citations_count=0,
            audience=audience,
            user_id=payload.user_id,
        )
        raise HTTPException(status_code=429, detail=rate_error)

    # Track request start
    _safe_increment_metrics(metrics, "increment_requests")

    # Get risk event
    result = await db.execute(
        select(RiskEvent)
        .where(RiskEvent.user_id == payload.user_id)
        .order_by(desc(RiskEvent.detected_at))
        .limit(1)
    )
    risk_event = result.scalar_one_or_none()

    if not risk_event:
        _safe_increment_metrics(metrics, "increment_error")
        latency_ms = (time.time() - start_time) * 1000
        _safe_record_latency(metrics, latency_ms)

        log_explain_request(
            status_code=404,
            latency_ms=latency_ms,
            cache_hit=False,
            rate_limited=False,
            fallback_used=False,
            explanation_source=None,
            citations_count=0,
            audience=audience,
            user_id=payload.user_id,
        )
        raise HTTPException(status_code=404, detail=f"Risk event not found for user {payload.user_id}")

    # Get user record for account_age and other fields
    from app.models.database import User
    user_result = await db.execute(
        select(User).where(User.user_id == payload.user_id)
    )
    user = user_result.scalar_one_or_none()

    # Compute account_age from User.account_created_time
    account_age = None
    if user and user.account_created_time:
        from datetime import datetime, timezone
        account_age = (datetime.now(timezone.utc) - user.account_created_time).days

    # Check cache (before any expensive computation)
    # Generate cache buster if bypass_cache is True
    cache_buster = str(time.time()) if bypass_cache else ""
    cache_key = _generate_cache_key(payload.user_id, audience, _safe_dump(RiskEventResponse.model_validate(risk_event).model_dump()), cache_buster)
    cached_response = _explanation_cache.get(cache_key)
    if cached_response is not None:
        # Cache hit - metrics already tracked by cache.get()
        latency_ms = (time.time() - start_time) * 1000
        _safe_record_latency(metrics, latency_ms)
        _safe_increment_metrics(metrics, "increment_success")

        log_explain_request(
            status_code=200,
            latency_ms=latency_ms,
            cache_hit=True,
            rate_limited=False,
            fallback_used=False,
            explanation_source=cached_response.get("explanation_source"),
            citations_count=len(cached_response.get("citations", [])),
            audience=audience,
            user_id=payload.user_id,
        )
        return ExplanationResponse(**cached_response)

    # Get risk factors
    from app.models.database import RiskFactor
    factors_result = await db.execute(
        select(RiskFactor)
        .where(RiskFactor.risk_event_id == risk_event.id)
    )
    factors = [RiskFactorResponse.model_validate(f) for f in factors_result.scalars().all()]

    # Get graph data
    graph_service = GraphAnalysisService(db)
    graph_data = await graph_service.get_user_graph(payload.user_id, depth=1)

    # Determine if graph evidence exists
    has_graph_evidence = bool(
        graph_data and
        graph_data.get('nodes') and
        len(graph_data['nodes']) > 1  # More than just the user
    )

    # Generate explanation first (needed for finding-specific citation retrieval)
    # Default behavior: model-based explanation (no LLM dependency)
    if settings.ENABLE_LLM_EXPLANATION and settings.ANTHROPIC_API_KEY:
        # LLM-enabled: Use LLM service for natural language summaries
        llm_service = LLMExplanationService()
        explanation = await llm_service.generate_explanation(
            user_id=payload.user_id,
            risk_event=_safe_dump(RiskEventResponse.model_validate(risk_event)),
            risk_factors=[_safe_dump(f) for f in factors],
            graph_data=_safe_dump(graph_data),
        )
    else:
        # Default: Generate model-based explanation from risk outputs
        explanation = _generate_model_based_explanation(
            risk_event=_safe_dump(RiskEventResponse.model_validate(risk_event)),
            factors=[_safe_dump(f) for f in factors],
            graph_data=_safe_dump(graph_data),
        )

    # ============================================================
    # CITATION GENERATION WITH DOMAIN ENFORCEMENT
    # ============================================================
    # Uses CitationRetrievalService with strict domain constraints
    # One primary citation per finding
    # Citations built ONLY from marks used in text
    # Domain-specific RAG queries (enforced BEFORE retrieval)
    # Metadata chunks filtered out

    key_findings = explanation.get("key_findings", [])
    # Save original findings BEFORE attaching citation marks
    # This is needed later for proper citation re-ordering
    original_key_findings = [f for f in key_findings if isinstance(f, str)]
    citation_service = create_citation_retrieval_service()

    logger.info(f"Processing {len(key_findings)} key_findings for citation generation")

    # Generate citations with domain enforcement
    retrieval_result = citation_service.retrieve_citations(
        key_findings=key_findings,
        ml_score=risk_event.ml_score,
        rule_score=risk_event.rule_score,
        graph_score=risk_event.graph_score,
        factors=[_safe_dump(f) for f in factors],
        has_graph_evidence=has_graph_evidence,
        audience=audience,
        max_citations=5
    )

    citations = retrieval_result.citations
    finding_to_citation = {}
    for finding_text, ids_list in retrieval_result.finding_to_citations.items():
        if ids_list:
            finding_to_citation[finding_text] = ids_list[0]  # Take first ID

    logger.info(f"Generated {len(citations)} citations for {len(key_findings)} findings")

    # Convert Citation objects to dicts for API response
    citations_dict = []
    for cit in citations:
        citations_dict.append({
            "id": cit.id,
            "doc": cit.doc,
            "section": cit.section,
            "quote": cit.quote,
            "chunk_id": cit.chunk_id
        })

    # Attach citation marks to key_findings
    # Skip citation for score summaries (they are model output metrics, not policy-backed hypotheses)
    if isinstance(explanation.get("key_findings"), list):
        key_findings = explanation["key_findings"]

        for i, finding_text in enumerate(key_findings):
            if isinstance(finding_text, str):
                # Skip citation attachment for score summaries
                # Check if the finding starts with any score summary pattern
                is_score_summary = (
                    finding_text.startswith("ML Signal Score:") or
                    finding_text.startswith("Rule Engine Signal Score:") or
                    finding_text.startswith("Graph Network Signal Score:")
                )

                if is_score_summary:
                    logger.info(f"Skipped citation for score summary: '{finding_text}'")
                    continue

                citation_id = finding_to_citation.get(finding_text)

                if citation_id:
                    key_findings[i] = finding_text.rstrip() + f" [{citation_id}]"
                    logger.debug(f"Attached citation [{citation_id}] to finding '{finding_text[:50]}...'")
                else:
                    logger.warning(f"No citation for finding: '{finding_text[:50]}...'")

    # ============================================================
    # CITATION FILTERING
    # ============================================================
    # Remove generic citations that should not appear in Policy-backed Narrative
    # Generic citations to filter:
    # - Risk_Scoring_Explainability_Guide.md / Explanation Objectives
    # - AML_Suspicious_Indicators.md / Scope
    filtered_citations = []
    removed_ids = set()

    for cit in citations_dict:
        doc = cit.get("doc", "")
        section = cit.get("section", "")

        # Filter out generic citations
        is_generic = False
        if "Risk_Scoring_Explainability_Guide" in doc and "Explanation Objectives" in section:
            is_generic = True
            logger.debug(f"Filtered generic citation: {doc} - {section}")
        elif "AML_Suspicious_Indicators" in doc and " / 1. Scope" in section:
            is_generic = True
            logger.debug(f"Filtered generic citation: {doc} - {section}")

        if not is_generic:
            filtered_citations.append(cit)
        else:
            removed_ids.add(cit["id"])

    # ============================================================
    # RE-ORDER CITATIONS FOR FRONTEND DISPLAY
    # ============================================================
    # Frontend filters out score-related findings from "Top Risk Hypotheses"
    # Goals:
    # 1. Citations should be [1], [2], [3]... without gaps in visible content
    # 2. Citations list should be sorted by ID
    # 3. Citation IDs assigned by chunk's FIRST appearance order (multiple findings can share same ID)

    def is_score_related_finding(finding_text: str) -> bool:
        """Check if a finding is score-related (filtered by frontend)."""
        score_keywords = ['score', 'signal', 'ml ', 'rule ', 'graph ', 'probability', 'threshold']
        finding_lower = finding_text.lower()
        # Match the frontend's filterKeyFindings logic
        return any(keyword in finding_lower for keyword in score_keywords)

    # Build old_to_new_id mapping based on ORDER of chunk's FIRST appearance in visible findings
    old_to_new_id = {}
    next_new_id = 1
    seen_chunks = set()

    # Use original_key_findings (saved before citation marks were attached)
    for finding_text in original_key_findings:
        if not isinstance(finding_text, str):
            continue

        # Only process visible (non-score) findings
        if is_score_related_finding(finding_text):
            continue

        # Get the old citation ID (which maps to a citation chunk)
        old_citation_id = finding_to_citation.get(finding_text)
        if old_citation_id and old_citation_id not in seen_chunks:
            # First time we see this citation chunk - assign next sequential ID
            old_to_new_id[old_citation_id] = next_new_id
            seen_chunks.add(old_citation_id)
            next_new_id += 1

    # Filter and renumber citations
    visible_citations = []
    for cit in filtered_citations:
        old_id = cit["id"]
        if old_id in old_to_new_id:
            cit["id"] = old_to_new_id[old_id]
            visible_citations.append(cit)

    # Track the next available ID for SOP citation
    next_sop_id = next_new_id  # next_new_id was already incremented after last unique chunk
    filtered_citations = visible_citations

    # Build finding citation references using new IDs
    updated_finding_to_citation = {}
    for finding_text in original_key_findings:
        old_id = finding_to_citation.get(finding_text)
        if old_id in old_to_new_id:
            updated_finding_to_citation[finding_text] = old_to_new_id[old_id]

    # Update citation marks in key_findings with new IDs
    if isinstance(explanation.get("key_findings"), list):
        key_findings = explanation["key_findings"]
        for i, finding_text in enumerate(key_findings):
            if isinstance(finding_text, str):
                # Remove existing citation marks and re-attach with new IDs
                import re
                clean_text = re.sub(r'\s*\[\d+\]$', '', finding_text)

                # Skip citation attachment for score summaries
                is_score_summary = (
                    clean_text.startswith("ML Signal Score:") or
                    clean_text.startswith("Rule Engine Signal Score:") or
                    clean_text.startswith("Graph Network Signal Score:")
                )

                new_citation_id = updated_finding_to_citation.get(clean_text)
                if new_citation_id and not is_score_summary:
                    key_findings[i] = clean_text.rstrip() + f" [{new_citation_id}]"
                else:
                    key_findings[i] = clean_text

    # Apply audience-based output shaping for key_findings
    if audience == "business" and isinstance(explanation.get("key_findings"), list):
        key_findings = explanation["key_findings"]
        for i, item in enumerate(key_findings):
            if isinstance(item, str):
                sanitized_item = item
                replacements = [
                    ("shared devices", "shared access signals"),
                    ("shared IPs", "shared access signals"),
                    ("shared device", "shared access signal"),
                    ("shared IP", "shared access signal"),
                    ("connected to ", "related to "),
                    (r"connected to \d+ other account", "connected to multiple related accounts"),
                    (r"connected to \d+ additional account", "connected to multiple related accounts"),
                ]
                for old, new in replacements:
                    if isinstance(new, str):
                        sanitized_item = sanitized_item.replace(old, new)
                    else:
                        import re
                        sanitized_item = re.sub(new[0], new[1], sanitized_item)
                key_findings[i] = sanitized_item

    # ============================================================
    # ADD SOP CITATION FOR ACTIONS
    # ============================================================
    # Add Investigation_and_Action_SOP.md citation for recommended_action
    if filtered_citations and isinstance(explanation.get("recommended_action"), str):
        # Try to retrieve an SOP citation for the action recommendation
        try:
            rag = PolicyRAGService()
            sop_chunks = rag.search(
                query="investigation action review procedure",
                top_k=3,
                allowed_docs=["Investigation_and_Action_SOP.md"]
            )

            if sop_chunks:
                # Find the best SOP chunk that passes validation
                for chunk in sop_chunks:
                    chunk_section = chunk.section.lower() if chunk.section else ""
                    # Skip generic scope/intro sections
                    if any(keyword in chunk_section for keyword in ["scope", "introduction", "purpose"]):
                        continue

                    # Sanitize quote
                    quote = chunk.text[:400].strip()
                    if audience == "business":
                        quote = "[REDACTED]"
                    else:
                        quote = sanitize_policy_quote(quote)

                    # Add SOP citation with next available ID (pre-calculated as next_sop_id)
                    sop_citation_id = next_sop_id
                    sop_citation = {
                        "id": sop_citation_id,
                        "doc": chunk.doc,
                        "section": chunk.section,
                        "quote": quote,
                        "chunk_id": chunk.chunk_id
                    }
                    filtered_citations.append(sop_citation)

                    # Attach citation marker to recommended_action
                    if isinstance(explanation.get("recommended_action"), str):
                        import re
                        action_text = explanation["recommended_action"]
                        # Remove any existing citation marks
                        clean_action = re.sub(r'\s*\[\d+\]$', '', action_text).rstrip()
                        explanation["recommended_action"] = clean_action + f" [{sop_citation_id}]"
                        logger.info(f"Attached SOP citation [{sop_citation_id}] to recommended_action")

                    logger.info(f"Added SOP citation for actions: {chunk.doc} - {chunk.section[:50]}...")
                    break
        except Exception as e:
            logger.warning(f"Failed to retrieve SOP citation for actions: {e}")

    # Add citations to response (as dicts) - use filtered list, sorted by ID
    explanation["citations"] = sorted(filtered_citations, key=lambda c: c["id"])

    # ============================================================
    # GENERATE MISSING_INFO FROM ACTUAL EVIDENCE GAPS
    # ============================================================
    # Delegated to DataQualityService.
    # This checks evidence availability only.
    # It does NOT use:
    # - risk level
    # - findings
    # - citations
    # - policy documents
    
    # Check transaction evidence availability
    has_transactions = False

    try:
        from app.models.database import Trade

        tx_result = await db.execute(
            select(Trade)
            .where(Trade.user_id == payload.user_id)
            .limit(1)
        )

        has_transactions = (
            tx_result.scalar_one_or_none() is not None
        )

    except Exception:
        has_transactions = False

    # ============================================================
    # COLLECT EVIDENCE AVAILABILITY FOR DATA QUALITY CHECK
    # ============================================================

    # Transaction evidence
    has_transactions = False

    try:
        from app.models.database import Trade

        tx_result = await db.execute(
            select(Trade)
            .where(Trade.user_id == payload.user_id)
            .limit(1)
        )

        has_transactions = (
            tx_result.scalar_one_or_none() is not None
        )

    except Exception:
        has_transactions = False


    # Device evidence from database
    has_device_evidence = False

    try:
        from app.models.database import Device

        device_result = await db.execute(
            select(Device)
            .where(Device.user_id == payload.user_id)
            .limit(1)
        )

        has_device_evidence = (
            device_result.scalar_one_or_none() is not None
        )

    except Exception:
        has_device_evidence = False


    # Graph device/IP evidence
    has_graph_device_evidence = False

    if graph_data and graph_data.get("nodes"):
        for node in graph_data["nodes"]:
            if node.get("user_id") == payload.user_id:
                if (
                    node.get("device_fingerprints")
                    or node.get("shared_ips")
                ):
                    has_graph_device_evidence = True
                    break

    data_quality_service = create_data_quality_service()

    missing_info = data_quality_service.generate_missing_info(
        user=user,
        trades_exist=has_transactions,
        device_exists=has_device_evidence,
        graph_device_evidence_exists=has_graph_device_evidence,
    )

    explanation["missing_info"] = missing_info

    # Store in cache for future requests
    _explanation_cache.set(cache_key, explanation)

    # Track completion metrics
    latency_ms = (time.time() - start_time) * 1000
    _safe_record_latency(metrics, latency_ms)
    _safe_increment_metrics(metrics, "increment_success")

    # Track explanation source / fallback counters (single call site, no double
    # counting). Cache-hit responses skip this so each explanation is counted once.
    explanation_source, fallback_used = _record_explanation_source_metrics(metrics, explanation)

    # Log structured JSON
    log_explain_request(
        status_code=200,
        latency_ms=latency_ms,
        cache_hit=False,
        rate_limited=False,
        fallback_used=fallback_used,
        explanation_source=explanation_source,
        citations_count=len(citations),
        audience=audience,
        user_id=payload.user_id,
    )

    return ExplanationResponse(**explanation)


@router.get("/cases/{user_id}/evidence", response_model=RiskEvidenceResponse)
async def get_case_evidence(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get explainable evidence for a risk case.

    Returns aggregated evidence from transactions, network, rules, and features.
    This is a READ-ONLY endpoint that does not modify risk scores.

    Evidence sources:
    - Transaction evidence: Top suspicious trades by value
    - Withdrawal evidence: Large withdrawals, especially to new addresses
    - Network evidence: Cluster membership and related accounts
    - Risk factor evidence: Detailed factors from risk event
    - Feature evidence: ML feature values that contributed to score
    - Rule evidence: Derived triggered rules based on feature values
    """
    from app.services.evidence_service import EvidenceService
    from app.models.schemas import RiskEvidenceResponse

    service = EvidenceService(db)
    evidence = await service.get_case_evidence(user_id)

    return RiskEvidenceResponse(**evidence)


@router.get("/cases/{user_id}/network-signals")
async def get_network_signals(
    user_id: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed network signals showing entity-level relationships.

    Returns actionable investigation evidence showing:
    - Which specific accounts are connected to this user
    - What relationship types connect them (shared device, shared IP)
    - The evidence entities (device IDs, IP addresses)
    - Each related account's risk level and score

    This is a READ-ONLY endpoint that does not modify risk scores.
    It only aggregates existing network relationship data.

    Args:
        user_id: User to get network signals for
        limit: Maximum number of connected accounts to return (default: 5)

    Returns:
        Network signals with connected accounts details
    """
    from app.services.evidence_service import EvidenceService

    service = EvidenceService(db)
    signals = await service.get_network_signals(user_id, limit)

    if not signals:
        return {"connected_account_count": 0, "connected_accounts": []}

    return signals


# ============================================================
# Metrics Endpoint for /api/risk/explain
# ============================================================

@router.get("/metrics/explain")
async def explain_metrics():
    """
    Get metrics for the /api/risk/explain endpoint.

    Returns:
        Dict with:
        - Request counters: requests_total, success_total, error_total, rate_limited_total
        - Cache metrics: cache_hit_rate (computed), cache_hit_total, cache_miss_total
        - Fallback metrics: fallback_rate (computed), fallback_total, llm_total
        - Latency metrics: latency_ms_p50, latency_ms_p95, latency_ms_avg
    """
    metrics = _get_explain_metrics()
    return metrics.get_metrics()
