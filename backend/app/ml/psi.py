"""
PSI (Population Stability Index) Calculation Module

PSI measures feature distribution drift between training and production data.
Formula: PSI = Σ(actual_pct - expected_pct) * ln(actual_pct / expected_pct)

Standard thresholds:
- PSI < 0.10: Stable
- 0.10 <= PSI < 0.25: Warning (minor drift)
- PSI >= 0.25: Significant drift (retrain recommended)
"""
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
import json
from pathlib import Path


class PSIAnalyzer:
    """
    PSI Analyzer for model monitoring.

    Calculates Population Stability Index to detect feature distribution drift
    between training baseline and current production data.
    """

    # Features that should use log transformation
    LOG_TRANSFORM_FEATURES = {'avg_trade_size', 'trade_volume_24h', 'withdrawal_volume_24h'}

    # Discrete/count features that need domain-specific fixed bins
    # These features have limited unique values, making quantile binning unstable
    DISCRETE_COUNT_FEATURES = {
        'linked_account_count',
        'shared_device_count',
        'trade_frequency_24h',
        'trade_frequency_7d',
        'active_days_count',
    }

    # Domain-specific bins for discrete count features
    DISCRETE_FEATURE_BINS = {
        'linked_account_count': [-float('inf'), 0, 1, 2, 5, float('inf')],
        'shared_device_count': [-float('inf'), 0, 1, 2, 5, float('inf')],
        'trade_frequency_24h': [-float('inf'), 0, 1, 5, 20, 50, float('inf')],
        'trade_frequency_7d': [-float('inf'), 0, 1, 5, 20, 50, float('inf')],
        'active_days_count': [-float('inf'), 0, 1, 2, 5, 7, float('inf')],
    }

    def __init__(self, n_bins: int = 10, epsilon: float = 1e-10):
        """
        Initialize PSI analyzer.

        Args:
            n_bins: Number of quantile bins for numerical features
            epsilon: Small value to avoid log(0)
        """
        self.n_bins = n_bins
        self.epsilon = epsilon

    def calculate_psi(
        self,
        expected_distribution: List[float],
        actual_distribution: List[float]
    ) -> float:
        """
        Calculate PSI from two distributions with proper smoothing.

        Args:
            expected_distribution: Reference distribution (training data)
            actual_distribution: Current distribution (production data)

        Returns:
            PSI value
        """
        # Convert to numpy arrays
        expected = np.array(expected_distribution, dtype=float)
        actual = np.array(actual_distribution, dtype=float)

        # Normalize to percentages FIRST, then apply smoothing
        expected_sum = expected.sum()
        actual_sum = actual.sum()

        if expected_sum > 0:
            expected_pct = expected / expected_sum
        else:
            expected_pct = np.ones_like(expected) / len(expected)

        if actual_sum > 0:
            actual_pct = actual / actual_sum
        else:
            actual_pct = np.ones_like(actual) / len(actual)

        # Apply smoothing to avoid log(0) - add epsilon to percentages only
        # This ensures we don't inflate PSI with empty bins
        expected_pct = np.maximum(expected_pct, self.epsilon)
        actual_pct = np.maximum(actual_pct, self.epsilon)

        # Calculate PSI
        psi_components = (actual_pct - expected_pct) * np.log(actual_pct / expected_pct)
        psi_value = np.sum(psi_components)

        return float(psi_value)

    def calculate_feature_psi(
        self,
        training_dataframe: pd.DataFrame,
        current_dataframe: pd.DataFrame,
        feature_columns: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate PSI for multiple features.

        Args:
            training_dataframe: Training data DataFrame
            current_dataframe: Current production data DataFrame
            feature_columns: List of feature names to analyze

        Returns:
            Dict mapping feature names to PSI results
        """
        psi_results = {}

        for feature in feature_columns:
            if feature not in training_dataframe.columns:
                continue
            if feature not in current_dataframe.columns:
                continue

            try:
                # Get feature values
                training_values = training_dataframe[feature].dropna()
                current_values = current_dataframe[feature].dropna()

                if len(training_values) == 0 or len(current_values) == 0:
                    continue

                # Apply log transformation for monetary features
                if feature in self.LOG_TRANSFORM_FEATURES:
                    training_values = self._apply_log_transform(training_values)
                    current_values = self._apply_log_transform(current_values)

                # Calculate PSI with appropriate binning
                psi_value = self._calculate_numerical_feature_psi(
                    training_values, current_values, feature
                )

                # Determine status
                status = self._get_psi_status(psi_value)

                psi_results[feature] = {
                    "psi": round(psi_value, 4),
                    "status": status,
                }

            except Exception as e:
                # Skip features that fail to calculate
                psi_results[feature] = {
                    "psi": None,
                    "status": "error",
                    "error": str(e),
                }

        return psi_results

    def _calculate_numerical_feature_psi(
        self,
        training_values: pd.Series,
        current_values: pd.Series,
        feature_name: str = None
    ) -> float:
        """
        Calculate PSI for a numerical feature using binning.

        Args:
            training_values: Training feature values
            current_values: Current feature values
            feature_name: Name of the feature (for domain-specific binning)

        Returns:
            PSI value
        """
        # Use domain-specific bins for discrete count features
        if feature_name in self.DISCRETE_COUNT_FEATURES:
            bin_edges = self.DISCRETE_FEATURE_BINS.get(feature_name, [-float('inf'), 0, 1, 2, 5, float('inf')])
        else:
            # Determine bins from training data (quantiles)
            bins = self._create_quantile_bins(training_values, self.n_bins)
            # Create bin edges (include min/max values)
            bin_edges = [float('-inf')]
            for b in bins:
                bin_edges.append(b)
            bin_edges.append(float('inf'))

        # Count values in each bin
        expected_counts = np.histogram(training_values, bins=bin_edges)[0]
        actual_counts = np.histogram(current_values, bins=bin_edges)[0]

        # Calculate PSI
        psi_value = self.calculate_psi(expected_counts, actual_counts)

        return psi_value

    def _create_quantile_bins(self, values: pd.Series, n_bins: int) -> np.ndarray:
        """
        Create quantile-based bins for numerical feature.

        Removes duplicate bin edges to avoid empty bins in PSI calculation.

        Args:
            values: Feature values
            n_bins: Number of bins

        Returns:
            Array of unique bin edges (quantiles)
        """
        quantiles = np.linspace(0, 1, n_bins + 1)
        bins = []

        for q in quantiles[1:-1]:  # Skip 0 and 1 (min and max)
            bins.append(values.quantile(q))

        # Remove duplicates and sort
        unique_bins = []
        seen = set()
        for b in bins:
            if b not in seen and not pd.isna(b):
                unique_bins.append(b)
                seen.add(b)

        return np.array(unique_bins) if unique_bins else np.array([values.median()])

    def _get_psi_status(self, psi_value: float) -> str:
        """
        Determine PSI status based on value.

        Args:
            psi_value: Calculated PSI value

        Returns:
            Status string: 'stable', 'warning', or 'drift'
        """
        if psi_value < 0.10:
            return "stable"
        elif psi_value < 0.25:
            return "warning"
        else:
            return "drift"

    def _apply_log_transform(self, values: pd.Series) -> pd.Series:
        """
        Apply log1p transformation to monetary features.

        Args:
            values: Feature values

        Returns:
            Log-transformed values
        """
        return np.log1p(values)

    def create_baseline_distribution(
        self,
        dataframe: pd.DataFrame,
        feature_columns: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Create baseline distribution for PSI monitoring.

        This should be saved during model training to serve as the reference.

        Args:
            dataframe: Training data DataFrame
            feature_columns: Feature names to include

        Returns:
            Dict with bin edges and reference distributions
        """
        baseline = {}

        for feature in feature_columns:
            if feature not in dataframe.columns:
                continue

            values = dataframe[feature].dropna()

            if len(values) == 0:
                continue

            # Apply log transformation for monetary features
            if feature in self.LOG_TRANSFORM_FEATURES:
                values = self._apply_log_transform(values)

            # Create bins - use domain-specific bins for discrete features
            if feature in self.DISCRETE_COUNT_FEATURES:
                bin_edges = self.DISCRETE_FEATURE_BINS.get(feature, [-float('inf'), 0, 1, 2, 5, float('inf')])
                n_bins = len(bin_edges) - 1
            else:
                bins = self._create_quantile_bins(values, self.n_bins)
                bin_edges = [float('-inf')]
                for b in bins:
                    bin_edges.append(float(b))
                bin_edges.append(float('inf'))
                n_bins = len(bin_edges) - 1

            # Calculate distribution
            counts, _ = np.histogram(values, bins=bin_edges)
            total = counts.sum()
            distribution = (counts / total).tolist() if total > 0 else []

            baseline[feature] = {
                "bins": [float(b) for b in bin_edges],
                "distribution": distribution,
                "n_bins": n_bins,
                "log_transformed": feature in self.LOG_TRANSFORM_FEATURES,
                "discrete_count_bins": feature in self.DISCRETE_COUNT_FEATURES,
            }

        return baseline

    def save_baseline(
        self,
        baseline: Dict[str, Dict[str, Any]],
        filepath: str
    ):
        """Save baseline distribution to JSON file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(baseline, f, indent=2)

    def load_baseline(self, filepath: str) -> Dict[str, Dict[str, Any]]:
        """Load baseline distribution from JSON file."""
        with open(filepath, 'r') as f:
            return json.load(f)

    def calculate_psi_from_baseline(
        self,
        current_dataframe: pd.DataFrame,
        baseline: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate PSI using pre-saved baseline distribution.

        Args:
            current_dataframe: Current production data
            baseline: Pre-calculated baseline distribution

        Returns:
            PSI results for all features
        """
        psi_results = {}

        for feature, baseline_data in baseline.items():
            if feature not in current_dataframe.columns:
                continue

            try:
                current_values = current_dataframe[feature].dropna()

                if len(current_values) == 0:
                    continue

                # Apply log transformation if baseline was log-transformed
                if baseline_data.get("log_transformed", False):
                    current_values = self._apply_log_transform(current_values)

                # Use baseline bins
                bin_edges = baseline_data["bins"]
                expected_dist = baseline_data["distribution"]

                # Count current values in baseline bins
                actual_counts = np.histogram(current_values, bins=bin_edges)[0]

                # Convert expected distribution to counts (normalized by current sample size)
                total_actual = actual_counts.sum()
                expected_counts = np.array(expected_dist) * total_actual

                # Calculate PSI
                psi_value = self.calculate_psi(expected_counts, actual_counts)

                psi_results[feature] = {
                    "psi": round(psi_value, 4),
                    "status": self._get_psi_status(psi_value),
                }

            except Exception as e:
                psi_results[feature] = {
                    "psi": None,
                    "status": "error",
                    "error": str(e),
                }

        return psi_results

    def get_overall_psi_status(self, psi_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get overall PSI status from all feature results.

        Args:
            psi_results: Individual feature PSI results

        Returns:
            Overall status summary with weighted average PSI
        """
        valid_psi_values = []
        feature_weights = {}

        for feature, result in psi_results.items():
            if result.get("psi") is not None:
                psi_value = result["psi"]
                valid_psi_values.append(psi_value)
                # Weight features by importance (could be customized)
                # For now, equal weight for all features
                feature_weights[feature] = 1.0

        if not valid_psi_values:
            return {
                "overall_status": "unknown",
                "overall_psi": None,
                "max_feature_psi": None,
                "drift_features": [],
            }

        # Calculate weighted average PSI
        total_weight = sum(feature_weights.get(f, 1.0) for f in psi_results.keys())
        weighted_psi = sum(
            psi_results[f]["psi"] * feature_weights.get(f, 1.0)
            for f in psi_results.keys()
            if psi_results[f].get("psi") is not None
        ) / total_weight

        max_psi = max(valid_psi_values)
        max_feature = max(
            (f for f in psi_results.keys() if psi_results[f].get("psi") is not None),
            key=lambda f: psi_results[f]["psi"]
        )

        drift_features = [
            feature for feature, result in psi_results.items()
            if result.get("status") in ["warning", "drift"]
        ]

        # Overall status based on weighted average PSI
        if weighted_psi < 0.10:
            overall_status = "stable"
        elif weighted_psi < 0.25:
            overall_status = "warning"
        else:
            overall_status = "drift"

        return {
            "overall_status": overall_status,
            "overall_psi": round(weighted_psi, 4),
            "max_feature_psi": round(max_psi, 4),
            "max_feature": max_feature,
            "drift_features": drift_features,
        }

    def validate_baseline_consistency(
        self,
        dataframe: pd.DataFrame,
        baseline: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate baseline consistency by comparing baseline with itself.

        PSI calculated on the same data used to create the baseline should be
        approximately 0 (< 0.01). If PSI > 0.05, it indicates a binning issue.

        Args:
            dataframe: The same training data used to create the baseline
            baseline: Pre-calculated baseline distribution

        Returns:
            Validation results with self-PSI and warnings
        """
        psi_results = self.calculate_psi_from_baseline(dataframe, baseline)

        max_psi = 0.0
        inconsistent_features = []

        for feature, result in psi_results.items():
            psi_value = result.get("psi", 0)
            if psi_value is not None:
                max_psi = max(max_psi, psi_value)
                if psi_value > 0.05:
                    inconsistent_features.append({
                        "feature": feature,
                        "psi": psi_value,
                        "status": result.get("status"),
                    })

        return {
            "max_self_psi": round(max_psi, 4),
            "is_consistent": max_psi < 0.01,
            "warning_threshold": 0.05,
            "inconsistent_features": inconsistent_features,
            "message": "Baseline is consistent" if max_psi < 0.01 else
                       f"PSI baseline inconsistency detected: max self-PSI = {max_psi:.4f}" if max_psi < 0.05 else
                       f"WARNING: PSI baseline inconsistency - max self-PSI = {max_psi:.4f} > 0.05 threshold",
        }
