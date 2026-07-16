"""
Case Management API Routes

Handles investigation case lifecycle.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.risk_service import CaseManagementService
from app.models.database import Case, CaseStatus
from app.models.schemas import CaseCreate, CaseUpdate, CaseResponse
from sqlalchemy import select

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("/{user_id}", response_model=dict)
async def create_case(
    user_id: str,
    risk_event_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Create a new investigation case for a user."""
    service = CaseManagementService(db)
    case = await service.create_case(user_id, risk_event_id)
    return case


@router.get("/{user_id}", response_model=CaseResponse)
async def get_user_case(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the latest case for a user."""
    result = await db.execute(
        select(Case)
        .where(Case.user_id == user_id)
        .order_by(Case.created_at.desc())
        .limit(1)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found for user {user_id}")

    return CaseResponse.model_validate(case)


@router.post("/{case_id}/decision", response_model=dict)
async def submit_case_decision(
    case_id: str,
    status: str,
    decision: str | None = None,
    notes: str | None = None,
    assigned_analyst: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Submit a decision for a case."""
    service = CaseManagementService(db)

    update_data = {"status": status}
    if decision is not None:
        update_data["decision"] = decision
    if notes is not None:
        update_data["notes"] = notes
    if assigned_analyst is not None:
        update_data["assigned_analyst"] = assigned_analyst

    result = await service.update_case(case_id, **update_data)
    return result
