"""
Model Monitoring Service

Provides model stability monitoring through PSI calculation.
Monitors feature distribution drift between training and production data.

PSI Lifecycle:
1. During Training: Feature distribution is saved as baseline (no PSI calculated)
2. During Monitoring: Current population is compared against baseline to calculate PSI
3. PSI Meaning: Production population drift compared to training baseline
4. NOT Training Metric: PSI is not calculated during training (would be meaningless)

Important: PSI in model_metadata.psi_score represents the LAST CALCULATED PSI snapshot
from Model Monitoring, not a training metric. It's updated when the monitoring
service runs and compares current data against the model's training baseline.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd
from pathlib import Path

from app.models.database import FeatureTable, ModelMetadata
from app.config import settings
from app.ml.psi import PSIAnalyzer
from app.services.psi_service import PSIService, PSI_TOOLTIP


class ModelMonitoringService:
    """
    Model Monitoring Service

    Tracks model health by calculating PSI (Population Stability Index)
    between training baseline and current feature distributions.

    PSI compares the current population feature distribution against the
    original training baseline. Training data comparison should NOT be used
    as PSI because it will always produce PSI=0.

    PSI Lifecycle:
    - Training: Save feature distribution as baseline (psi_score = None/0)
    - Monitoring: Calculate PSI by comparing current data vs baseline
    - Storage: Store latest PSI in model_metadata.psi_score for dashboard display
    - Interpretation: PSI < 0.1 (stable), 0.1-0.25 (warning), > 0.25 (drift)
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
        self.psi_analyzer = PSIAnalyzer(n_bins=10)
        self.psi_service = PSIService(db)

    async def calculate_psi(
        self,
        baseline_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate PSI for all features using current database data.

        PSI compares the current population feature distribution against the
        original training baseline. This allows detection of feature drift over
        time as the production data distribution changes.

        Args:
            baseline_path: Path to baseline distribution JSON
                          (defaults to model artifact directory)

        Returns:
            PSI monitoring results with real-time calculation
        """
        # Load baseline distribution
        if baseline_path is None:
            baseline_path = str(Path(settings.MODEL_PATH) / "feature_baseline.json")

        try:
            baseline = self.psi_analyzer.load_baseline(baseline_path)
        except FileNotFoundError:
            return {
                "error": "Baseline distribution not found. Train model first.",
                "overall_status": "no_baseline",
                "tooltip": PSI_TOOLTIP,
                "explanation": "PSI compares the current population feature distribution against the original training baseline. Training data comparison is not used as it will always produce PSI=0.",
                "features": [],
            }

        # Get current feature data from database
        current_features = await self._get_current_features()

        if current_features.empty:
            return {
                "error": "No current features found in database",
                "overall_status": "no_data",
                "tooltip": PSI_TOOLTIP,
                "explanation": "PSI compares the current population feature distribution against the original training baseline. Training data comparison is not used as it will always produce PSI=0.",
                "features": [],
            }

        # Calculate PSI
        feature_columns = list(baseline.keys())
        psi_results = self.psi_analyzer.calculate_psi_from_baseline(
            current_features, baseline
        )

        # Get overall status
        overall_status = self.psi_analyzer.get_overall_psi_status(psi_results)

        return {
            "model": "risk_model_latest",
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status["overall_status"],
            "overall_psi": overall_status["overall_psi"],
            "max_feature_psi": overall_status["max_feature_psi"],
            "max_feature": overall_status["max_feature"],
            "drift_features": overall_status["drift_features"],
            "tooltip": PSI_TOOLTIP,
            "explanation": "PSI compares the current population feature distribution against the original training baseline. Training data comparison is not used as it will always produce PSI=0.",
            "features": [
                {
                    "feature": feature,
                    "psi": result["psi"],
                    "status": result["status"],
                }
                for feature, result in psi_results.items()
            ],
        }

    async def get_current_model_metrics(
        self
    ) -> Dict[str, Any]:
        """
        Get complete model metrics including PSI.

        Returns:
            Combined metrics: AUC, KS, PSI, feature importance
            Returns "No trained model available" if no model exists
        """
        # Get existing model metadata
        result = await self.db.execute(
            select(ModelMetadata)
            .where(ModelMetadata.is_active == True)
            .order_by(ModelMetadata.deployed_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()

        # Get PSI
        psi_data = await self.calculate_psi()

        if model:
            metrics = {
                "model_name": model.model_name,
                "version": model.version,
                "algorithm": model.algorithm if hasattr(model, 'algorithm') else "LightGBM",
                "model_type": model.model_type if hasattr(model, 'model_type') else "Gradient Boosting",
                "feature_count": model.feature_count if hasattr(model, 'feature_count') else None,
                "deployed_at": model.deployed_at.isoformat() if model.deployed_at else None,
                # Baseline validation (from training)
                "baseline_validation_psi": float(model.baseline_validation_psi) if model.baseline_validation_psi is not None else None,
                "baseline_validation_status": model.baseline_validation_status,
                "baseline_validated_at": model.baseline_validated_at.isoformat() if model.baseline_validated_at else None,
                # Production metrics
                "metrics": {
                    "auc": float(model.auc_score) if model.auc_score else None,
                    "ks": float(model.ks_score) if model.ks_score else None,
                    "psi": psi_data.get("overall_psi"),  # Latest production PSI snapshot
                },
                "psi_status": psi_data.get("overall_status") if not psi_data.get("error") else "unknown",
                "psi_calculated_at": model.psi_calculated_at.isoformat() if model.psi_calculated_at else None,
                "max_feature_psi": psi_data.get("max_feature_psi"),
                "max_feature": psi_data.get("max_feature"),
                "drift_features": psi_data.get("drift_features", []),
                "psi_features": psi_data.get("features", []) if not psi_data.get("error") else [],
                "psi_tooltip": psi_data.get("tooltip"),
                "psi_explanation": psi_data.get("explanation"),
                "model_available": True,
            }
        else:
            metrics = {
                "model_name": "LightGBM Risk Model",
                "version": None,
                "algorithm": None,
                "model_type": None,
                "feature_count": None,
                "deployed_at": None,
                # Baseline validation (not available without model)
                "baseline_validation_psi": None,
                "baseline_validation_status": None,
                "baseline_validated_at": None,
                # Production metrics
                "metrics": {
                    "auc": None,
                    "ks": None,
                    "psi": psi_data.get("overall_psi"),
                },
                "psi_status": psi_data.get("overall_status") if not psi_data.get("error") else "unknown",
                "psi_calculated_at": None,
                "max_feature_psi": psi_data.get("max_feature_psi"),
                "max_feature": psi_data.get("max_feature"),
                "drift_features": psi_data.get("drift_features", []),
                "psi_features": psi_data.get("features", []) if not psi_data.get("error") else [],
                "psi_tooltip": psi_data.get("tooltip"),
                "psi_explanation": psi_data.get("explanation"),
                "model_available": False,
                "message": "No trained model available. Train a model to see AUC and KS metrics.",
            }

        return metrics

    async def _get_current_features(self) -> pd.DataFrame:
        """
        Load current features from database.

        Returns:
            DataFrame with current feature values
        """
        result = await self.db.execute(select(FeatureTable))
        features = result.scalars().all()

        if not features:
            return pd.DataFrame()

        # Convert to DataFrame
        feature_data = []
        feature_cols = [
            'trade_frequency_7d', 'trade_frequency_24h', 'trade_volume_24h',
            'withdrawal_volume_24h', 'account_age_days', 'avg_trade_size',
            'shared_device_count', 'linked_account_count', 'unique_ip_count',
            'withdrawal_frequency_24h', 'withdrawal_risk_score',
            'opposite_trade_ratio', 'active_days_count'
        ]

        for feature in features:
            row = {col: getattr(feature, col) for col in feature_cols}
            row['user_id'] = feature.user_id
            feature_data.append(row)

        df = pd.DataFrame(feature_data)

        # Convert to numeric, handle NaN
        for col in df.columns:
            if col != 'user_id':
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    async def create_baseline_from_current_data(
        self,
        output_path: Optional[str] = None
    ) -> str:
        """
        Create baseline distribution from current database features.

        Useful for initializing PSI monitoring before model training.

        Args:
            output_path: Where to save baseline JSON

        Returns:
            Path to saved baseline file
        """
        current_features = await self._get_current_features()

        if current_features.empty:
            raise ValueError("No features found in database")

        if output_path is None:
            output_path = str(Path(settings.MODEL_PATH) / "feature_baseline.json")

        feature_cols = [
            'trade_frequency_7d', 'trade_frequency_24h', 'trade_volume_24h',
            'withdrawal_volume_24h', 'account_age_days', 'avg_trade_size',
            'shared_device_count', 'linked_account_count', 'unique_ip_count',
            'withdrawal_frequency_24h', 'withdrawal_risk_score',
            'opposite_trade_ratio', 'active_days_count'
        ]

        baseline = self.psi_analyzer.create_baseline_distribution(
            current_features, feature_cols
        )

        self.psi_analyzer.save_baseline(baseline, output_path)

        return output_path
