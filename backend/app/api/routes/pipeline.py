"""
Pipeline API Routes

Handles data upload, pipeline status, and pipeline execution.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.pipeline_service import PipelineService, DataValidationService
from app.models.schemas import (
    PipelineStatusResponse,
    PipelineRunRequest,
    DataUploadResponse,
)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    db: AsyncSession = Depends(get_db)
):
    """Get current pipeline status."""
    service = PipelineService(db)
    status = await service.get_pipeline_status()
    return PipelineStatusResponse(**status)


@router.post("/upload", response_model=DataUploadResponse)
async def upload_data(
    users: UploadFile | None = File(None),
    devices: UploadFile | None = File(None),
    trades: UploadFile | None = File(None),
    withdrawals: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload CSV data files.

    All files are optional - upload whatever data you have available.
    """
    files_uploaded = []
    import_counts = {}

    # Save uploaded files temporarily
    import os
    temp_dir = "/tmp/risk_platform_uploads"
    os.makedirs(temp_dir, exist_ok=True)

    users_path = None
    devices_path = None
    trades_path = None
    withdrawals_path = None

    try:
        if users:
            users_path = os.path.join(temp_dir, users.filename)
            with open(users_path, "wb") as f:
                f.write(await users.read())
            files_uploaded.append(users.filename)

        if devices:
            devices_path = os.path.join(temp_dir, devices.filename)
            with open(devices_path, "wb") as f:
                f.write(await devices.read())
            files_uploaded.append(devices.filename)

        if trades:
            trades_path = os.path.join(temp_dir, trades.filename)
            with open(trades_path, "wb") as f:
                f.write(await trades.read())
            files_uploaded.append(trades.filename)

        if withdrawals:
            withdrawals_path = os.path.join(temp_dir, withdrawals.filename)
            with open(withdrawals_path, "wb") as f:
                f.write(await withdrawals.read())
            files_uploaded.append(withdrawals.filename)

        # Import data using pipeline service
        service = PipelineService(db)
        import_counts = await service.import_csv_data(
            users_csv=users_path,
            devices_csv=devices_path,
            trades_csv=trades_path,
            withdrawals_csv=withdrawals_path,
        )

        return DataUploadResponse(
            message=f"Successfully uploaded {len(files_uploaded)} file(s)",
            files_processed=files_uploaded,
            records_imported=import_counts,
        )

    except Exception as e:
        return DataUploadResponse(
            message=f"Upload failed: {str(e)}",
            files_processed=files_uploaded,
            records_imported={},
        )


@router.post("/run")
async def run_pipeline(
    request: PipelineRunRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Run the complete data pipeline.

    Executes: Feature Engineering -> Graph Analysis -> ML Scoring
    """
    service = PipelineService(db)

    result = await service.run_pipeline(
        run_full_pipeline=request.run_full_pipeline,
        generate_risk_events=request.generate_risk_events,
    )

    return result
