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
    ModelTrainingResponse,
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
    clear_existing: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload CSV data files.

    All 4 required datasets must be provided:
    - users.csv
    - devices.csv
    - trades.csv
    - withdrawals.csv

    Args:
        clear_existing: If True, clears all existing data before import

    Rejects incomplete uploads with meaningful error response.
    """
    # Debug logging
    print(f"[UPLOAD] Received request - users: {users.filename if users else None}, devices: {devices.filename if devices else None}, trades: {trades.filename if trades else None}, withdrawals: {withdrawals.filename if withdrawals else None}, clear_existing: {clear_existing}")

    # Validate that all required files are provided
    required_files = {
        'users': users,
        'devices': devices,
        'trades': trades,
        'withdrawals': withdrawals
    }

    missing_files = [name for name, file in required_files.items() if file is None]

    if missing_files:
        return DataUploadResponse(
            message=f"Upload failed: Missing required datasets. Please provide all 4 files: users.csv, devices.csv, trades.csv, withdrawals.csv. Missing: {', '.join(missing_files)}",
            files_processed=[],
            records_imported={}
        )

    # Validate file extensions
    invalid_files = []
    for name, file in required_files.items():
        if file and not file.filename.lower().endswith('.csv'):
            invalid_files.append(f"{name}.{file.filename}")

    if invalid_files:
        return DataUploadResponse(
            message=f"Upload failed: Invalid file format. All files must be CSV format. Invalid files: {', '.join(invalid_files)}",
            files_processed=[],
            records_imported={}
        )

    files_uploaded = []
    import_counts = {}
    cleared_counts = {}

    # Save uploaded files temporarily
    import os
    temp_dir = "/tmp/risk_platform_uploads"
    os.makedirs(temp_dir, exist_ok=True)

    users_path = None
    devices_path = None
    trades_path = None
    withdrawals_path = None

    try:
        # Clear existing pipeline data if requested
        # This preserves trained models and only resets data lifecycle
        if clear_existing:
            service = PipelineService(db)
            cleared_counts = await service.clear_pipeline_data()

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

        message_parts = []
        if cleared_counts:
            message_parts.append(f"cleared {sum(cleared_counts.values())} existing records")
        message_parts.append(f"imported {sum(import_counts.values())} new records")

        return DataUploadResponse(
            message=f"Successfully {' and '.join(message_parts)}",
            files_processed=files_uploaded,
            records_imported=import_counts,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()  # Log full traceback to console
        return DataUploadResponse(
            message=f"Upload failed: {str(e)}",
            files_processed=files_uploaded,
            records_imported={},
        )


@router.post("/clear-data")
async def clear_data(
    db: AsyncSession = Depends(get_db)
):
    """
    Clear all existing data from the database.

    Returns counts of deleted records per table.
    """
    service = PipelineService(db)
    counts = await service.clear_all_data()
    return {
        "message": "Successfully cleared all data",
        "deleted_counts": counts,
        "total_deleted": sum(counts.values())
    }


@router.post("/reset")
async def reset_pipeline(
    clear_models: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset pipeline to initial state.

    Clears pipeline data and returns the pipeline to a clean state.
    This is the recommended way to start fresh with new data.

    Args:
        clear_models: If True, also deletes trained models (default: False)
                     When False, preserves model metadata and artifacts

    The default behavior preserves trained models so Model Monitoring
    continues to show AUC/KS from the latest trained model.
    """
    service = PipelineService(db)

    if clear_models:
        # Full reset including models (destructive)
        counts = await service.clear_all_data()
    else:
        # Data-only reset (preserves models)
        counts = await service.clear_pipeline_data()

    # Return fresh status after reset
    status = await service.get_pipeline_status()

    return {
        "message": "Pipeline reset successfully",
        "deleted_counts": counts,
        "total_deleted": sum(counts.values()),
        "models_preserved": counts.get("total_models_preserved", 0),
        "status": status
    }


@router.post("/run")
async def run_pipeline(
    request: PipelineRunRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Run the complete data pipeline.

    Executes: Feature Engineering -> Graph Analysis -> ML Scoring -> Model Training (optional)
    """
    service = PipelineService(db)

    result = await service.run_pipeline(
        run_full_pipeline=request.run_full_pipeline,
        generate_risk_events=request.generate_risk_events,
        train_model=False,  # Training is separate endpoint
    )

    return result


@router.post("/train", response_model=ModelTrainingResponse)
async def train_model(
    db: AsyncSession = Depends(get_db)
):
    """
    Train LightGBM model on current database data.

    This endpoint:
    1. Loads features from FeatureTable
    2. Generates labels from cluster membership
    3. Trains LightGBM model
    4. Saves model artifacts and metadata
    5. Creates PSI baseline

    Returns:
        Training results with metrics and model info
    """
    service = PipelineService(db)

    result = await service.train_model()

    return ModelTrainingResponse(**result)


@router.get("/dataset-info")
async def get_dataset_info(
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about currently uploaded datasets.

    Returns metadata about the source, processing method, and record counts.
    """
    from sqlalchemy import select, func
    from app.models.models import User, Device, Trade, WithdrawalRequest

    # Get record counts for each table
    user_count = await db.scalar(select(func.count()).select_from(User))
    device_count = await db.scalar(select(func.count()).select_from(Device))
    trade_count = await db.scalar(select(func.count()).select_from(Trade))
    withdrawal_count = await db.scalar(select(func.count()).select_from(WithdrawalRequest))

    # Get the most recent data import timestamp if available
    # This would typically come from a data_import_log table
    # For now, we'll return null if no data exists
    generated_at = None
    if user_count > 0 or device_count > 0 or trade_count > 0 or withdrawal_count > 0:
        # Get most recent created_at from any table as proxy
        from sqlalchemy import or_
        most_recent = await db.execute(
            select(
                func.greatest(
                    func.coalesce(func.max(User.created_at), None),
                    func.coalesce(func.max(Device.created_at), None),
                    func.coalesce(func.max(Trade.timestamp), None),
                    func.coalesce(func.max(WithdrawalRequest.created_at), None)
                )
            ).where(
                or_(
                    User.id.isnot(None),
                    Device.id.isnot(None),
                    Trade.id.isnot(None),
                    WithdrawalRequest.id.isnot(None)
                )
            )
        )
        generated_at = most_recent.scalar_one()

    return {
        "source": "Uploaded Dataset",
        "processing_method": "Risk Analytics Pipeline",
        "update_method": "Manual Upload",
        "generated_at": generated_at.isoformat() if generated_at else None,
        "records_count": {
            "users": user_count or 0,
            "devices": device_count or 0,
            "trades": trade_count or 0,
            "withdrawals": withdrawal_count or 0,
        }
    }
