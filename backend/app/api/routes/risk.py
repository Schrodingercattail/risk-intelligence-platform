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
from app.models.database import RiskEvent, User, RiskLevel
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

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get("/overview", response_model=RiskOverviewResponse)
async def get_risk_overview(
    db: AsyncSession = Depends(get_db)
):
    """Get risk overview dashboard metrics."""
    # High risk accounts
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

    # Suspicious clusters
    cluster_result = await db.execute(
        select(func.count())
        .select_from(text("account_clusters"))
    )
    suspicious_clusters = cluster_result.scalar() or 0

    # Pending review cases
    from app.models.database import Case, CaseStatus
    cases_result = await db.execute(
        select(func.count(Case.case_id))
        .where(Case.status.in_([
            CaseStatus.NEW.value,
            CaseStatus.INVESTIGATING.value,
        ]))
    )
    pending_review_cases = cases_result.scalar() or 0

    # Withdrawal freeze recommendations (HIGH risk with withdrawal factors)
    withdrawal_result = await db.execute(
        select(func.count(RiskEvent.id))
        .join(User, RiskEvent.user_id == User.user_id)
        .where(User.risk_level.in_([RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]))
    )
    withdrawal_freeze_recommendations = withdrawal_result.scalar() or 0

    return RiskOverviewResponse(
        high_risk_accounts=high_risk_accounts,
        suspicious_clusters=suspicious_clusters,
        pending_review_cases=pending_review_cases,
        withdrawal_freeze_recommendations=withdrawal_freeze_recommendations,
    )


@router.get("/events", response_model=RiskEventListResponse)
async def get_risk_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
    """Get detailed risk information for a specific user."""
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

    return RiskEventDetailResponse(
        **RiskEventResponse.model_validate(risk_event).model_dump(),
        risk_factors=[RiskFactorResponse.model_validate(f) for f in factors],
        cluster=cluster_info,
    )


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
