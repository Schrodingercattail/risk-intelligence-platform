"""
PSI Service for Model Monitoring

Calculates Population Stability Index to detect feature distribution drift
between training baseline and current production data.

This service integrates PSI calculations with the database and provides
real-time model monitoring capabilities.
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.ml.psi import PSIAnalyzer
from app.models.database import FeatureTable, ModelMetadata
from app.config import settings


class PSIService:
    """
    PSI Service for model monitoring.

    Provides PSI calculation between training baseline and current feature data
    to detect distribution drift in model features.
    """

    def __init__(self, db: AsyncSession):
        """Initialize PSI service with database session."""
        self.db = db
        self.analyzer = PSIAnalyzer(n_bins=10)

    async def calculate_current_psi(
        self,
        model_id: Optional[int] = None,
        baseline_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate PSI between training baseline and current feature population.

        Args:
            model_id: Optional model ID to get baseline from
            baseline_path: Optional path to baseline JSON file

        Returns:
            PSI results with overall status and per-feature breakdown
        """
        # Load baseline distribution
        baseline = self._load_baseline(model_id, baseline_path)

        if baseline is None:
            return {
                "overall_psi": None,
                "overall_status": "no_baseline",
                "max_psi": None,
                "drift_features": [],
                "feature_psi": {},
                "message": "No baseline distribution available. PSI cannot be calculated."
            }

        # Get current feature data
        current_features = await self._get_current_features()

        if current_features.empty:
            return {
                "overall_psi": None,
                "overall_status": "no_data",
                "max_psi": None,
                "drift_features": [],
                "feature_psi": {},
                "message": "No current feature data available."
            }

        # Calculate PSI for all features
        feature_psi = self.analyzer.calculate_psi_from_baseline(
            current_features, baseline
        )

        # Get overall status
        overall_status = self.analyzer.get_overall_psi_status(feature_psi)

        return {
            "overall_psi": overall_status.get("max_psi"),
            "overall_status": overall_status.get("overall_status"),
            "max_psi": overall_status.get("max_psi"),
            "drift_features": overall_status.get("drift_features", []),
            "feature_psi": feature_psi,
            "calculated_at": datetime.now().isoformat(),
        }

    async def create_and_save_baseline(
        self,
        features_df: pd.DataFrame,
        baseline_path: Optional[str] = None
    ) -> str:
        """
        Create and save baseline distribution from training data.

        Args:
            features_df: Training features DataFrame
            baseline_path: Optional path to save baseline

        Returns:
            Path to saved baseline file
        """
        if baseline_path is None:
            baseline_path = str(Path(settings.MODEL_PATH) / "feature_baseline.json")

        feature_cols = [
            'trade_frequency_7d', 'trade_frequency_24h', 'trade_volume_24h',
            'withdrawal_volume_24h', 'account_age_days', 'avg_trade_size',
            'shared_device_count', 'linked_account_count', 'unique_ip_count',
            'withdrawal_frequency_24h', 'withdrawal_risk_score',
            'opposite_trade_ratio', 'active_days_count'
        ]

        baseline = self.analyzer.create_baseline_distribution(
            features_df, feature_cols
        )

        self.analyzer.save_baseline(baseline, baseline_path)

        return baseline_path

    async def update_model_psi_score(
        self,
        model_id: int,
        baseline_path: Optional[str] = None
    ) -> Optional[float]:
        """
        Update model metadata with current PSI score.

        Args:
            model_id: Model ID to update
            baseline_path: Optional path to baseline file

        Returns:
            Calculated PSI score or None if calculation failed
        """
        psi_results = await self.calculate_current_psi(model_id, baseline_path)

        overall_psi = psi_results.get("overall_psi")

        if overall_psi is not None:
            # Update model metadata
            model = await self.db.get(ModelMetadata, model_id)
            if model:
                model.psi_score = overall_psi
                model.psi_status = psi_results.get("overall_status")
                model.psi_calculated_at = datetime.now()
                await self.db.commit()

        return overall_psi

    def _load_baseline(
        self,
        model_id: Optional[int] = None,
        baseline_path: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Load baseline distribution from file.

        Args:
            model_id: Optional model ID (for future model-specific baselines)
            baseline_path: Path to baseline JSON file

        Returns:
            Baseline distribution dict or None if not found
        """
        if baseline_path is None:
            baseline_path = str(Path(settings.MODEL_PATH) / "feature_baseline.json")

        try:
            return self.analyzer.load_baseline(baseline_path)
        except FileNotFoundError:
            return None
        except Exception:
            return None

    async def _get_current_features(self) -> pd.DataFrame:
        """
        Get current feature data from database.

        Returns:
            DataFrame with current feature values
        """
        # Get all features from database
        result = await self.db.execute(select(FeatureTable))
        features_list = result.scalars().all()

        if not features_list:
            return pd.DataFrame()

        # Build DataFrame
        feature_cols = [
            'trade_frequency_7d', 'trade_frequency_24h', 'trade_volume_24h',
            'withdrawal_volume_24h', 'account_age_days', 'avg_trade_size',
            'shared_device_count', 'linked_account_count', 'unique_ip_count',
            'withdrawal_frequency_24h', 'withdrawal_risk_score',
            'opposite_trade_ratio', 'active_days_count'
        ]

        feature_data = []
        for feature in features_list:
            row = {}
            for col in feature_cols:
                value = getattr(feature, col, None)
                row[col] = float(value) if value is not None else 0.0
            feature_data.append(row)

        return pd.DataFrame(feature_data)


class PSICalculationResult:
    """PSI calculation result for API responses."""

    def __init__(
        self,
        overall_psi: Optional[float],
        overall_status: str,
        max_psi: Optional[float],
        drift_features: List[str],
        feature_psi: Dict[str, Dict[str, Any]],
        calculated_at: str,
        message: Optional[str] = None
    ):
        self.overall_psi = overall_psi
        self.overall_status = overall_status
        self.max_psi = max_psi
        self.drift_features = drift_features
        self.feature_psi = feature_psi
        self.calculated_at = calculated_at
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall_psi": self.overall_psi,
            "overall_status": self.overall_status,
            "max_psi": self.max_psi,
            "drift_features": self.drift_features,
            "feature_psi": self.feature_psi,
            "calculated_at": self.calculated_at,
            "message": self.message
        }


# PSI tooltip for UI
PSI_TOOLTIP = (
    "PSI measures feature distribution stability between the training baseline "
    "and current population. Lower values indicate more stable behavior. "
    "PSI < 0.1: Stable, 0.1-0.25: Minor drift, > 0.25: Significant drift."
)
