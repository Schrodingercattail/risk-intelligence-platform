"""
Model Monitoring API Routes

Provides model metrics, feature importance, and PSI monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import subprocess
import sys

from app.db.session import get_db
from app.models.database import ModelMetadata, FeatureImportance
from app.models.schemas import ModelMetricsResponse, FeatureImportanceListResponse
from sqlalchemy import select, desc
from app.config import settings
from app.services.model_monitoring_service import ModelMonitoringService

router = APIRouter(prefix="/model", tags=["Model"])


@router.get("/metrics", response_model=ModelMetricsResponse)
async def get_model_metrics(
    db: AsyncSession = Depends(get_db)
):
    """Get current model performance metrics."""
    # Get active model
    result = await db.execute(
        select(ModelMetadata)
        .where(ModelMetadata.is_active == True)
        .order_by(ModelMetadata.deployed_at.desc())
        .limit(1)
    )
    model = result.scalar_one_or_none()

    if model:
        return ModelMetricsResponse(
            model_name=model.model_name,
            version=model.version,
            metrics={
                "auc": float(model.auc_score) if model.auc_score else None,
                "ks": float(model.ks_score) if model.ks_score else None,
                "psi": float(model.psi_score) if model.psi_score else None,
            },
        )
    else:
        # Return null metrics if no model deployed
        return ModelMetricsResponse(
            model_name="LightGBM Risk Model",
            version="v1.0",
            metrics={
                "auc": None,
                "ks": None,
                "psi": None,
            },
        )


@router.get("/feature-importance", response_model=FeatureImportanceListResponse)
async def get_feature_importance(
    db: AsyncSession = Depends(get_db)
):
    """Get feature importance rankings for the active model."""
    # Get active model
    result = await db.execute(
        select(ModelMetadata)
        .where(ModelMetadata.is_active == True)
        .order_by(ModelMetadata.deployed_at.desc())
        .limit(1)
    )
    model = result.scalar_one_or_none()

    features = []

    if model:
        # Get feature importance from database
        result = await db.execute(
            select(FeatureImportance)
            .where(FeatureImportance.model_id == model.model_id)
            .order_by(FeatureImportance.rank)
        )
        features = [
            {
                "name": fi.feature_name,
                "importance": float(fi.importance_score),
                "rank": fi.rank,
            }
            for fi in result.scalars().all()
        ]

    return FeatureImportanceListResponse(features=features)


@router.post("/train")
async def train_model(
    source: str = "database",  # or "csv"
    db: AsyncSession = Depends(get_db)
):
    """
    Train a new LightGBM model on available data.

    This is a long-running operation. In production, this should be
    run as a background task with progress tracking.
    """
    try:
        # Run training script
        project_root = Path(__file__).parent.parent.parent.parent
        script_path = project_root / "ml-models" / "training" / "train_risk_model.py"

        # Run the training script
        result = subprocess.run(
            [sys.executable, "-m", "ml.training.train_risk_model", "--source", source],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Training failed: {result.stderr}"
            )

        return {
            "status": "success",
            "message": "Model training completed successfully",
            "output": result.stdout,
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Training timed out after 5 minutes"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Training error: {str(e)}"
        )


@router.post("/metadata/save")
async def save_model_metadata(
    metadata: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Save model metadata to database after training.

    This should be called automatically by the training script,
    but can also be called manually to update database records.
    """
    try:
        # Create model metadata record
        model = ModelMetadata(
            model_name=metadata.get("model_name", "LightGBM Risk Model"),
            version=metadata.get("version", "v1.0"),
            auc_score=metadata.get("metrics", {}).get("auc"),
            ks_score=metadata.get("metrics", {}).get("ks"),
            psi_score=metadata.get("metrics", {}).get("psi", 0.0),
            is_active=True,
        )
        db.add(model)
        await db.flush()

        # Deactivate previous models
        await db.execute(
            select(ModelMetadata)
            .where(ModelMetadata.model_id != model.model_id)
            .where(ModelMetadata.is_active == True)
        )
        # Mark as inactive
        # (In real implementation, would update those records)

        # Save feature importance
        for i, fi in enumerate(metadata.get("feature_importance", [])[:50], 1):
            feature_importance = FeatureImportance(
                model_id=model.model_id,
                feature_name=fi["feature"],
                importance_score=fi["importance"],
                rank=i,
            )
            db.add(feature_importance)

        await db.commit()

        return {
            "status": "success",
            "model_id": model.model_id,
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save metadata: {str(e)}"
        )


@router.get("/psi")
async def get_psi_monitoring(
    db: AsyncSession = Depends(get_db)
):
    """
    Get PSI (Population Stability Index) monitoring data.

    Returns feature-wise PSI values to detect distribution drift
    between training baseline and current production data.
    """
    service = ModelMonitoringService(db)
    psi_data = await service.calculate_psi()

    return psi_data


@router.get("/monitoring")
async def get_complete_monitoring(
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete model monitoring data including all metrics.

    Returns AUC, KS, PSI, feature importance in a single call.
    """
    service = ModelMonitoringService(db)
    metrics = await service.get_current_model_metrics()

    return metrics


@router.post("/baseline/create")
async def create_baseline(
    db: AsyncSession = Depends(get_db)
):
    """
    Create PSI baseline distribution from current database features.

    Use this to initialize PSI monitoring if baseline doesn't exist.
    """
    service = ModelMonitoringService(db)

    try:
        baseline_path = await service.create_baseline_from_current_data()

        return {
            "status": "success",
            "message": "Baseline distribution created",
            "path": baseline_path,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create baseline: {str(e)}"
        )
