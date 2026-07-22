"""
Unit Tests for PSI (Population Stability Index) Calculation

Tests PSI calculation consistency and correctness.
"""
import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.psi import PSIAnalyzer


@pytest.fixture
def psi_analyzer():
    """Create PSI analyzer instance for testing."""
    return PSIAnalyzer(n_bins=10)


@pytest.fixture
def sample_dataframe():
    """Create sample dataframe with known distribution for testing."""
    np.random.seed(42)
    n_samples = 1000

    data = {
        # Discrete count features
        'trade_frequency_24h': np.random.poisson(5, n_samples),
        'trade_frequency_7d': np.random.poisson(20, n_samples),
        'active_days_count': np.random.randint(1, 8, n_samples),
        'linked_account_count': np.random.choice([0, 1, 2], n_samples, p=[0.8, 0.15, 0.05]),
        'shared_device_count': np.random.choice([0, 1], n_samples, p=[0.9, 0.1]),

        # Continuous features
        'trade_volume_24h': np.random.lognormal(7, 1, n_samples),
        'withdrawal_volume_24h': np.random.lognormal(6, 1, n_samples),
        'account_age_days': np.random.randint(1, 365, n_samples),
        'avg_trade_size': np.random.lognormal(8, 1, n_samples),
        'withdrawal_frequency_24h': np.random.poisson(2, n_samples),
        'withdrawal_risk_score': np.random.uniform(0, 1, n_samples),
        'opposite_trade_ratio': np.random.uniform(0, 1, n_samples),
    }

    df = pd.DataFrame(data)
    # Ensure no negative values for features that shouldn't have them
    for col in ['trade_frequency_24h', 'trade_frequency_7d', 'active_days_count',
                'withdrawal_frequency_24h']:
        df[col] = df[col].clip(lower=0)

    return df


class TestPSISelfComparison:
    """
    Test PSI calculation consistency.

    When comparing a distribution with itself, PSI should be approximately 0.
    This validates that the binning strategy is stable.
    """

    def test_psi_self_comparison_zero(self, psi_analyzer, sample_dataframe):
        """
        Test that PSI calculated on a dataset compared with itself is approximately 0.

        This is the key test for PSI calculation consistency.
        If PSI > 0.01 when comparing with itself, there's a binning issue.
        """
        # Create baseline from sample data
        feature_cols = [
            'trade_frequency_24h', 'trade_frequency_7d', 'active_days_count',
            'linked_account_count', 'shared_device_count', 'trade_volume_24h',
            'withdrawal_volume_24h', 'account_age_days', 'avg_trade_size',
            'withdrawal_frequency_24h', 'withdrawal_risk_score', 'opposite_trade_ratio',
        ]

        baseline = psi_analyzer.create_baseline_distribution(sample_dataframe, feature_cols)

        # Calculate PSI using the same data (should be ~0)
        psi_results = psi_analyzer.calculate_psi_from_baseline(sample_dataframe, baseline)

        # Check that all PSI values are very small (< 0.01)
        for feature, result in psi_results.items():
            psi_value = result.get('psi')
            assert psi_value is not None, f"PSI calculation failed for {feature}"
            assert psi_value < 0.01, f"PSI for {feature} is {psi_value:.4f}, expected < 0.01 (self-comparison)"

    def test_baseline_validation_method(self, psi_analyzer, sample_dataframe):
        """
        Test the validate_baseline_consistency method.

        This method should detect when a baseline is inconsistent (high self-PSI).
        """
        feature_cols = [
            'trade_frequency_24h', 'trade_frequency_7d', 'active_days_count',
            'linked_account_count', 'shared_device_count',
        ]

        baseline = psi_analyzer.create_baseline_distribution(sample_dataframe, feature_cols)

        # Validate baseline consistency
        validation = psi_analyzer.validate_baseline_consistency(sample_dataframe, baseline)

        # Should pass validation
        assert validation['is_consistent'], "Baseline should be consistent when compared with itself"
        assert validation['max_self_psi'] < 0.01, f"Max self-PSI should be < 0.01, got {validation['max_self_psi']}"
        assert len(validation['inconsistent_features']) == 0, "No inconsistent features should be detected"

    def test_psi_detects_drift(self, psi_analyzer, sample_dataframe):
        """
        Test that PSI correctly detects distribution drift.

        When we introduce significant drift, PSI should be > 0.25.
        """
        feature_cols = ['trade_frequency_24h']

        # Create baseline from original data
        baseline = psi_analyzer.create_baseline_distribution(sample_dataframe, feature_cols)

        # Create drifted data (shift mean significantly)
        drifted_data = sample_dataframe.copy()
        drifted_data['trade_frequency_24h'] = drifted_data['trade_frequency_24h'] * 10 + 50

        # Calculate PSI (should be high due to drift)
        psi_results = psi_analyzer.calculate_psi_from_baseline(drifted_data, baseline)

        psi_value = psi_results['trade_frequency_24h']['psi']
        assert psi_value > 0.25, f"PSI should detect drift (> 0.25), got {psi_value:.4f}"
        assert psi_results['trade_frequency_24h']['status'] == 'drift'


class TestDiscreteFeatureBinning:
    """Test domain-specific binning for discrete features."""

    def test_discrete_features_use_domain_bins(self, psi_analyzer):
        """Verify discrete features use pre-defined domain bins."""
        assert 'linked_account_count' in psi_analyzer.DISCRETE_COUNT_FEATURES
        assert 'shared_device_count' in psi_analyzer.DISCRETE_COUNT_FEATURES
        assert 'trade_frequency_24h' in psi_analyzer.DISCRETE_COUNT_FEATURES
        assert 'trade_frequency_7d' in psi_analyzer.DISCRETE_COUNT_FEATURES
        assert 'active_days_count' in psi_analyzer.DISCRETE_COUNT_FEATURES

    def test_domain_bins_are_defined(self, psi_analyzer):
        """Verify domain-specific bins are defined for all discrete features."""
        for feature in psi_analyzer.DISCRETE_COUNT_FEATURES:
            assert feature in psi_analyzer.DISCRETE_FEATURE_BINS, f"No bins defined for {feature}"
            bins = psi_analyzer.DISCRETE_FEATURE_BINS[feature]
            assert bins[0] == -float('inf'), f"First bin should be -inf for {feature}"
            assert bins[-1] == float('inf'), f"Last bin should be inf for {feature}"
            assert len(bins) >= 4, f"Domain bins should have at least 4 edges for {feature}"

    def test_discrete_bins_produce_stable_psi(self, psi_analyzer):
        """Test that discrete feature binning produces stable PSI (self-comparison ~0)."""
        # Create data with typical discrete values
        data = pd.DataFrame({
            'linked_account_count': [0] * 800 + [1] * 150 + [2] * 40 + [5] * 10,
            'shared_device_count': [0] * 900 + [1] * 100,
        })

        baseline = psi_analyzer.create_baseline_distribution(
            data, ['linked_account_count', 'shared_device_count']
        )

        # Self-comparison should have PSI < 0.01
        psi_results = psi_analyzer.calculate_psi_from_baseline(data, baseline)

        assert psi_results['linked_account_count']['psi'] < 0.01
        assert psi_results['shared_device_count']['psi'] < 0.01


class TestContinuousFeatureBinning:
    """Test quantile-based binning for continuous features."""

    def test_continuous_features_use_quantile_bins(self, psi_analyzer, sample_dataframe):
        """Test that continuous features use quantile-based bins."""
        continuous_features = ['account_age_days', 'opposite_trade_ratio']

        for feature in continuous_features:
            assert feature not in psi_analyzer.DISCRETE_COUNT_FEATURES, \
                f"{feature} should not use discrete bins"

    def test_quantile_bins_remove_duplicates(self, psi_analyzer, sample_dataframe):
        """Test that quantile binning removes duplicate edges."""
        # Create data with many duplicates (low cardinality)
        # With only 3 unique values, we can't create 10 quantile bins
        data = pd.DataFrame({'low_cardinality': [1] * 500 + [2] * 300 + [3] * 200})

        bins = psi_analyzer._create_quantile_bins(data['low_cardinality'], n_bins=10)

        # Should have fewer bins than requested due to deduplication
        # With only 3 unique values (1, 2, 3), quantile binning will produce fewer bins
        assert len(bins) < 10, f"Deduplication should reduce bin count, got {len(bins)}"
        # Should have the unique values as bins (1, 2, 3 appear in the data)
        unique_values = sorted(data['low_cardinality'].unique())
        # The bins should approximately match the unique values (may have interpolated values)
        assert len(bins) <= len(unique_values) + 2, "Bins should be close to unique value count"

    def test_continuous_bins_produce_stable_psi(self, psi_analyzer, sample_dataframe):
        """Test that continuous feature binning produces stable PSI."""
        continuous_features = ['account_age_days', 'opposite_trade_ratio']

        baseline = psi_analyzer.create_baseline_distribution(sample_dataframe, continuous_features)

        # Self-comparison should have PSI < 0.01
        psi_results = psi_analyzer.calculate_psi_from_baseline(sample_dataframe, baseline)

        for feature in continuous_features:
            psi_value = psi_results[feature]['psi']
            assert psi_value < 0.01, f"PSI for {feature} should be < 0.01, got {psi_value:.4f}"


class TestPSIThresholds:
    """Test PSI status determination."""

    def test_psi_status_stable(self, psi_analyzer):
        """Test PSI < 0.10 returns 'stable' status."""
        assert psi_analyzer._get_psi_status(0.05) == 'stable'
        assert psi_analyzer._get_psi_status(0.09) == 'stable'

    def test_psi_status_warning(self, psi_analyzer):
        """Test 0.10 <= PSI < 0.25 returns 'warning' status."""
        assert psi_analyzer._get_psi_status(0.10) == 'warning'
        assert psi_analyzer._get_psi_status(0.15) == 'warning'
        assert psi_analyzer._get_psi_status(0.24) == 'warning'

    def test_psi_status_drift(self, psi_analyzer):
        """Test PSI >= 0.25 returns 'drift' status."""
        assert psi_analyzer._get_psi_status(0.25) == 'drift'
        assert psi_analyzer._get_psi_status(0.50) == 'drift'
        assert psi_analyzer._get_psi_status(1.0) == 'drift'


class TestBaselinePersistence:
    """Test baseline persistence and loading."""

    def test_baseline_roundtrip(self, psi_analyzer, sample_dataframe, tmp_path):
        """Test that baseline can be saved and loaded correctly."""
        feature_cols = ['trade_frequency_24h', 'linked_account_count']

        # Create baseline
        baseline = psi_analyzer.create_baseline_distribution(sample_dataframe, feature_cols)

        # Save to file
        baseline_path = tmp_path / "test_baseline.json"
        psi_analyzer.save_baseline(baseline, str(baseline_path))

        # Load from file
        loaded_baseline = psi_analyzer.load_baseline(str(baseline_path))

        # Verify features match
        assert set(loaded_baseline.keys()) == set(baseline.keys())

        # Verify bins match
        for feature in feature_cols:
            assert loaded_baseline[feature]['bins'] == baseline[feature]['bins']
            assert loaded_baseline[feature]['distribution'] == baseline[feature]['distribution']

    def test_baseline_bins_are_persisted(self, psi_analyzer, sample_dataframe, tmp_path):
        """Test that final bins are persisted in baseline file."""
        feature_cols = ['trade_frequency_24h']

        baseline = psi_analyzer.create_baseline_distribution(sample_dataframe, feature_cols)

        # Check that bins are included in baseline
        assert 'bins' in baseline['trade_frequency_24h']
        assert 'distribution' in baseline['trade_frequency_24h']
        assert 'n_bins' in baseline['trade_frequency_24h']

        # Verify bin edges are valid
        bins = baseline['trade_frequency_24h']['bins']
        assert bins[0] == -float('inf')
        assert bins[-1] == float('inf')
        assert len(bins) >= 4  # At least: -inf, some bins, inf


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
