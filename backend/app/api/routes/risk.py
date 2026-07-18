"""
Risk Command Center API Routes

Main API for risk event management and investigation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.services.risk_service import RiskScoringService
from app.services.graph_service import GraphAnalysisService
from app.services.llm_service import LLMExplanationService
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
)
from sqlalchemy import select, func, desc, text
from app.config import settings

router = APIRouter(prefix="/risk", tags=["Risk"])


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
    # Define buckets: 0-20, 20-40, 40-60, 60-80, 80-100
    buckets = ["0-20", "20-40", "40-60", "60-80", "80-100"]
    bucket_ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]

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
        "average": round(average_score, 1),
        "threshold": 80.0,
        "maximum": round(max_score, 1)
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

    # Detection Source Analysis - read-only attribution from RiskEvent
    # Detection Coverage Rate = (High-risk accounts detected by method / Total high-risk accounts) * 100
    # Each bar shows independent coverage - users can be detected by multiple methods
    # Detection attribution uses explicit thresholds defined in config
    # Bars do NOT need to sum to 100%
    total_high_risk = high_risk_accounts  # Already calculated as critical + high

    detection_sources = []
    if total_high_risk > 0:
        # LightGBM: count HIGH/CRITICAL users where ML method triggered (ml_score >= threshold)
        ml_detected_result = await db.execute(
            select(func.count(func.distinct(User.user_id)))
            .join(RiskEvent, RiskEvent.user_id == User.user_id)
            .where(User.risk_level.in_([RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]))
            .where(RiskEvent.ml_score.isnot(None))
            .where(RiskEvent.ml_score >= settings.DETECTION_ML_THRESHOLD)
        )
        ml_detected = ml_detected_result.scalar() or 0

        # Rule Engine: count HIGH/CRITICAL users where Rule method triggered (rule_score >= threshold)
        rule_detected_result = await db.execute(
            select(func.count(func.distinct(User.user_id)))
            .join(RiskEvent, RiskEvent.user_id == User.user_id)
            .where(User.risk_level.in_([RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]))
            .where(RiskEvent.rule_score.isnot(None))
            .where(RiskEvent.rule_score >= settings.DETECTION_RULE_THRESHOLD)
        )
        rule_detected = rule_detected_result.scalar() or 0

        # Graph Network: count HIGH/CRITICAL users where Graph method triggered (graph_score >= threshold)
        graph_detected_result = await db.execute(
            select(func.count(func.distinct(User.user_id)))
            .join(RiskEvent, RiskEvent.user_id == User.user_id)
            .where(User.risk_level.in_([RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]))
            .where(RiskEvent.graph_score.isnot(None))
            .where(RiskEvent.graph_score >= settings.DETECTION_GRAPH_THRESHOLD)
        )
        graph_detected = graph_detected_result.scalar() or 0

        detection_sources = [
            {
                "method": "Rule Engine",
                "detected_accounts": rule_detected,
                "detection_rate": round((rule_detected / total_high_risk) * 100, 1),
                "color": "#3b82f6"
            },
            {
                "method": "LightGBM Model",
                "detected_accounts": ml_detected,
                "detection_rate": round((ml_detected / total_high_risk) * 100, 1),
                "color": "#8b5cf6"
            },
            {
                "method": "Graph Network",
                "detected_accounts": graph_detected,
                "detection_rate": round((graph_detected / total_high_risk) * 100, 1),
                "color": "#06b6d4"
            }
        ]
    else:
        detection_sources = [
            {"method": "Rule Engine", "detected_accounts": 0, "detection_rate": 0.0, "color": "#3b82f6"},
            {"method": "LightGBM Model", "detected_accounts": 0, "detection_rate": 0.0, "color": "#8b5cf6"},
            {"method": "Graph Network", "detected_accounts": 0, "detection_rate": 0.0, "color": "#06b6d4"}
        ]

    return RiskOverviewResponse(
        summary=executive_summary,
        risk_score_distribution=risk_score_distribution,
        risk_score_statistics=risk_score_statistics,
        risk_level_composition=risk_level_composition,
        detection_sources=detection_sources
    )


@router.get("/events", response_model=RiskEventListResponse)
async def get_risk_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    risk_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of risk events."""
    query = select(RiskEvent).order_by(desc(RiskEvent.detected_at))

    if risk_level:
        query = query.where(RiskEvent.risk_level == risk_level)

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


@router.post("/explain", response_model=ExplanationResponse)
async def generate_explanation(
    request: ExplanationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered investigation explanation."""
    # Get risk event
    result = await db.execute(
        select(RiskEvent)
        .where(RiskEvent.user_id == request.user_id)
        .order_by(desc(RiskEvent.detected_at))
        .limit(1)
    )
    risk_event = result.scalar_one_or_none()

    if not risk_event:
        raise HTTPException(status_code=404, detail=f"Risk event not found for user {request.user_id}")

    # Get risk factors
    from app.models.database import RiskFactor
    factors_result = await db.execute(
        select(RiskFactor)
        .where(RiskFactor.risk_event_id == risk_event.id)
    )
    factors = [RiskFactorResponse.model_validate(f) for f in factors_result.scalars().all()]

    # Get graph data
    graph_service = GraphAnalysisService(db)
    graph_data = await graph_service.get_user_graph(request.user_id, depth=1)

    # Generate explanation
    llm_service = LLMExplanationService()
    explanation = await llm_service.generate_explanation(
        user_id=request.user_id,
        risk_event=RiskEventResponse.model_validate(risk_event).model_dump(),
        risk_factors=[f.model_dump() for f in factors],
        graph_data=graph_data.model_dump(),
    )

    return ExplanationResponse(**explanation)
