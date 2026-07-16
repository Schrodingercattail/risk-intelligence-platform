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
        Calculate PSI from two distributions.

        Args:
            expected_distribution: Reference distribution (training data)
            actual_distribution: Current distribution (production data)

        Returns:
            PSI value
        """
        # Convert to numpy arrays
        expected = np.array(expected_distribution, dtype=float)
        actual = np.array(actual_distribution, dtype=float)

        # Add epsilon to avoid log(0)
        expected = np.maximum(expected, self.epsilon)
        actual = np.maximum(actual, self.epsilon)

        # Normalize to percentages
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

                # Calculate PSI
                psi_value = self._calculate_numerical_feature_psi(
                    training_values, current_values
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
        current_values: pd.Series
    ) -> float:
        """
        Calculate PSI for a numerical feature using binning.

        Args:
            training_values: Training feature values
            current_values: Current feature values

        Returns:
            PSI value
        """
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

        Args:
            values: Feature values
            n_bins: Number of bins

        Returns:
            Array of bin edges (quantiles)
        """
        quantiles = np.linspace(0, 1, n_bins + 1)
        bins = []

        for q in quantiles[1:-1]:  # Skip 0 and 1 (min and max)
            bins.append(values.quantile(q))

        return np.array(bins)

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

            # Create bins
            bins = self._create_quantile_bins(values, self.n_bins)

            # Create bin edges
            bin_edges = [float('-inf')]
            for b in bins:
                bin_edges.append(float(b))
            bin_edges.append(float('inf'))

            # Calculate distribution
            counts, _ = np.histogram(values, bins=bin_edges)
            total = counts.sum()
            distribution = (counts / total).tolist() if total > 0 else []

            baseline[feature] = {
                "bins": bin_edges,
                "distribution": distribution,
                "n_bins": self.n_bins,
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
            Overall status summary
        """
        valid_psi_values = [
            r["psi"] for r in psi_results.values()
            if r.get("psi") is not None
        ]

        if not valid_psi_values:
            return {
                "overall_status": "unknown",
                "max_psi": None,
                "drift_features": [],
            }

        max_psi = max(valid_psi_values)
        drift_features = [
            feature for feature, result in psi_results.items()
            if result.get("status") in ["warning", "drift"]
        ]

        # Overall status based on worst PSI
        if max_psi < 0.10:
            overall_status = "stable"
        elif max_psi < 0.25:
            overall_status = "warning"
        else:
            overall_status = "drift"

        return {
            "overall_status": overall_status,
            "max_psi": round(max_psi, 4),
            "drift_features": drift_features,
        }
