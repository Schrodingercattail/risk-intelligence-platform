"""
Create PSI Baseline from Training Data

This script creates a proper PSI baseline from the v2_diverse training data.
The baseline represents the "production" feature distribution that PSI monitoring
will compare against.
"""
import sys
from pathlib import Path
import pandas as pd
import json

# Add backend to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.ml.psi import PSIAnalyzer

def create_baseline_from_csv(csv_dir: str = "test_data/v2_diverse"):
    """Create baseline distribution from training CSV data."""
    csv_path = project_root / csv_dir

    print(f"Loading training data from {csv_path}...")

    # Load CSV files
    users_df = pd.read_csv(csv_path / "users.csv")
    devices_df = pd.read_csv(csv_path / "devices.csv")
    trades_df = pd.read_csv(csv_path / "trades.csv")
    withdrawals_df = pd.read_csv(csv_path / "withdrawals.csv")

    print(f"✓ Loaded data:")
    print(f"  - Users: {len(users_df)}")
    print(f"  - Devices: {len(devices_df)}")
    print(f"  - Trades: {len(trades_df)}")
    print(f"  - Withdrawals: {len(withdrawals_df)}")

    # Calculate features using the training approach
    from app.ml.model import LightGBMTrainer
    trainer = LightGBMTrainer()

    # Combine with labels (create dummy labels for feature preparation)
    labels_df = pd.DataFrame({
        "user_id": users_df["user_id"],
        "is_risky": [0] * len(users_df)  # Dummy labels, not used for baseline
    })

    features_df = trainer.prepare_features(
        users_df, devices_df, trades_df, withdrawals_df, labels_df
    )

    print(f"\n✓ Prepared {len(features_df)} feature vectors")

    # Create PSI baseline
    analyzer = PSIAnalyzer(n_bins=10)

    feature_cols = [
        'trade_frequency_7d', 'trade_frequency_24h', 'trade_volume_24h',
        'withdrawal_volume_24h', 'account_age_days', 'avg_trade_size',
        'shared_device_count', 'linked_account_count', 'unique_ip_count',
        'withdrawal_frequency_24h', 'withdrawal_risk_score',
        'opposite_trade_ratio', 'active_days_count'
    ]

    baseline = analyzer.create_baseline_distribution(features_df, feature_cols)

    # Save baseline
    output_path = project_root / "ml-models" / "artifacts" / "feature_baseline.json"
    analyzer.save_baseline(baseline, str(output_path))

    print(f"\n✓ Baseline saved to {output_path}")
    print(f"\nBaseline summary:")
    for feature, data in baseline.items():
        dist = data["distribution"]
        non_zero = sum(1 for d in dist if d > 0.01)
        print(f"  - {feature}: {non_zero} non-zero bins")

    return str(output_path)


if __name__ == "__main__":
    create_baseline_from_csv("test_data/v2_diverse")
