"""
Model Monitoring API Routes

Provides model metrics, feature importance, and PSI monitoring.
Also handles model training and activation for the ML lifecycle.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.session import get_db
from app.models.database import ModelMetadata, FeatureImportance
from app.models.schemas import ModelMetricsResponse, FeatureImportanceListResponse
from sqlalchemy import select, desc, update
from app.services.model_monitoring_service import ModelMonitoringService

router = APIRouter(prefix="/model", tags=["Model"])


@router.get("/metrics", response_model=ModelMetricsResponse)
async def get_model_metrics(
    db: AsyncSession = Depends(get_db)
):
    """Get current model performance metrics. Returns null if no trained model available."""
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
                "psi": None,  # PSI is calculated dynamically, not stored
            },
        )
    else:
        # Return null metrics if no model deployed (not misleading 0 values)
        return ModelMetricsResponse(
            model_name="LightGBM Risk Model",
            version=None,
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
    dataset: str = "historical",  # "historical" or "current"
    db: AsyncSession = Depends(get_db)
):
    """
    Train a new LightGBM model on available data.

    This creates a new model entry in the registry without activating it.
    The admin can review metrics before activating the model.

    Training Dataset Options:
    - historical (default): Uses test_data/v2_diverse CSV files (official baseline)
    - current: Uses current database FeatureTable data

    Training Flow:
    1. Load training dataset (CSV files or database features)
    2. Generate labels using behavioral signals (simulates investigation outcomes)
    3. Train LightGBM model
    4. Evaluate performance (AUC, KS)
    5. Save model artifacts (.pkl)
    6. Create PSI baseline distribution (only for historical dataset)
    7. Save metadata to database (is_active=False by default)

    Returns:
        Training result with model version and metrics

    Error Cases:
        - No feature data available for current dataset: Run pipeline first
        - Training failure: Check logs for details
    """
    try:
        if dataset == "historical":
            # Use historical CSV training dataset (v2_diverse)
            from app.services.historical_training_service import HistoricalTrainingService

            training_service = HistoricalTrainingService(db)
            training_result = await training_service.train_from_historical_dataset()
        else:
            # Use current database dataset
            from app.services.pipeline_service import PipelineService

            pipeline_service = PipelineService(db)
            training_result = await pipeline_service.train_model()

        if training_result.get("status") == "failed":
            error_msg = training_result.get("error", "Training failed")
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )

        # Get the newly created model from database
        new_model = await db.execute(
            select(ModelMetadata)
            .order_by(ModelMetadata.model_id.desc())
            .limit(1)
        )
        new_model = new_model.scalar_one_or_none()

        if not new_model:
            raise HTTPException(
                status_code=500,
                detail="Training completed but failed to save model metadata"
            )

        return {
            "status": "completed",
            "model_id": new_model.model_id,
            "model_version": new_model.version,
            "algorithm": new_model.algorithm or "LightGBM",
            "model_type": new_model.model_type or "Gradient Boosting",
            "metrics": {
                "auc": float(new_model.auc_score) if new_model.auc_score else None,
                "ks": float(new_model.ks_score) if new_model.ks_score else None,
            },
            "feature_count": new_model.feature_count,
            "deployment_status": "pending",
            "message": "Model training completed successfully. Review metrics before activation."
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()  # Log the full traceback for debugging
        import sys
        print(f"ERROR: {str(e)}", file=sys.stderr)
        print(f"ERROR TYPE: {type(e).__name__}", file=sys.stderr)
        traceback.print_exc()
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

    PSI is calculated dynamically by comparing current feature population
    against the original training baseline. Training data comparison is not
    used as it will always produce PSI=0.

    Thresholds:
    - PSI < 0.1: Stable (no significant drift)
    - PSI 0.1-0.25: Warning (minor drift, monitor closely)
    - PSI > 0.25: Significant drift (retrain recommended)
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


@router.post("/models/{model_id}/activate")
async def activate_model(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Activate a specific model as the production model.

    This endpoint:
    1. Sets the selected model to is_active=True
    2. Deactivates all other models (is_active=False)
    3. Updates the production model reference

    Flow:
    - Admin reviews newly trained model metrics
    - Admin clicks "Activate Model" for the selected model
    - System switches production model to new version
    - Monitoring continues with new model

    Important:
    - PSI monitoring continues using the NEW model's training baseline
    - Old models remain in registry for rollback capability
    """
    try:
        # Verify the model exists
        result = await db.execute(
            select(ModelMetadata).where(ModelMetadata.model_id == model_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            raise HTTPException(
                status_code=404,
                detail=f"Model with ID {model_id} not found"
            )

        # Deactivate all models
        await db.execute(
            update(ModelMetadata)
            .where(ModelMetadata.is_active == True)
            .values(is_active=False)
        )

        # Activate the selected model
        await db.execute(
            update(ModelMetadata)
            .where(ModelMetadata.model_id == model_id)
            .values(is_active=True)
        )

        await db.commit()

        return {
            "status": "success",
            "message": f"Model {model.version} activated successfully",
            "model_id": model_id,
            "model_version": model.version,
            "previous_models_deactivated": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate model: {str(e)}"
        )
