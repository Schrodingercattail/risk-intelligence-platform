"""
Model Monitoring Service

Provides model stability monitoring through PSI calculation.
Monitors feature distribution drift between training and production data.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd

from app.models.database import FeatureTable, ModelMetadata
from app.config import settings
from app.ml.psi import PSIAnalyzer


class ModelMonitoringService:
    """
    Model Monitoring Service

    Tracks model health by calculating PSI (Population Stability Index)
    between training baseline and current feature distributions.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
        self.psi_analyzer = PSIAnalyzer(n_bins=10)

    async def calculate_psi(
        self,
        baseline_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate PSI for all features using current database data.

        Args:
            baseline_path: Path to baseline distribution JSON
                          (defaults to model artifact directory)

        Returns:
            PSI monitoring results
        """
        # Load baseline distribution
        if baseline_path is None:
            baseline_path = f"{settings.MODEL_PATH}/feature_distribution.json"

        try:
            baseline = self.psi_analyzer.load_baseline(baseline_path)
        except FileNotFoundError:
            return {
                "error": "Baseline distribution not found. Train model first.",
                "overall_status": "unknown",
                "features": [],
            }

        # Get current feature data from database
        current_features = await self._get_current_features()

        if current_features.empty:
            return {
                "error": "No current features found in database",
                "overall_status": "unknown",
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
            "max_psi": overall_status["max_psi"],
            "drift_features": overall_status["drift_features"],
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
                "metrics": {
                    "auc": float(model.auc_score) if model.auc_score else None,
                    "ks": float(model.ks_score) if model.ks_score else None,
                    "psi": psi_data.get("max_psi"),
                },
                "psi_status": psi_data.get("overall_status") if not psi_data.get("error") else "unknown",
                "psi_features": psi_data.get("features", []) if not psi_data.get("error") else [],
            }
        else:
            metrics = {
                "model_name": "LightGBM Risk Model",
                "version": "v1.0",
                "algorithm": None,
                "model_type": None,
                "feature_count": None,
                "deployed_at": None,
                "metrics": {
                    "auc": None,
                    "ks": None,
                    "psi": psi_data.get("max_psi"),
                },
                "psi_status": psi_data.get("overall_status") if not psi_data.get("error") else "unknown",
                "psi_features": psi_data.get("features", []) if not psi_data.get("error") else [],
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
            'shared_device_count', 'linked_account_count', 'unique_ip_count',
            'trade_frequency_24h', 'trade_frequency_7d', 'opposite_trade_ratio',
            'avg_trade_size', 'trade_volume_24h', 'account_age_days',
            'active_days_count', 'withdrawal_risk_score', 'withdrawal_frequency_24h',
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
            output_path = f"{settings.MODEL_PATH}/feature_distribution.json"

        feature_cols = [
            'shared_device_count', 'linked_account_count', 'unique_ip_count',
            'trade_frequency_24h', 'trade_frequency_7d', 'opposite_trade_ratio',
            'avg_trade_size', 'trade_volume_24h', 'account_age_days',
            'active_days_count', 'withdrawal_risk_score', 'withdrawal_frequency_24h',
        ]

        baseline = self.psi_analyzer.create_baseline_distribution(
            current_features, feature_cols
        )

        self.psi_analyzer.save_baseline(baseline, output_path)

        return output_path
