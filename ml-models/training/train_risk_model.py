"""
Model Training Script

Standalone script to train LightGBM model on demo data.

Usage:
    # Train from CSV files
    python -m ml.training.train_risk_model --source csv --csv-dir data/generated

    # Train from database
    python -m ml.training.train_risk_model --source database
"""
import sys
import os
from pathlib import Path
import argparse
import json

# Add backend to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio
from datetime import datetime

from app.ml.model import LightGBMTrainer
from app.config import settings
from app.models.database import ModelMetadata, FeatureImportance, Base
from sqlalchemy.orm import Session


async def save_metadata_to_db(
    auc: float,
    ks: float,
    feature_importance: list,
    version: str,
    psi_score: float = None
):
    """
    Save model metadata to database after training.

    PSI Handling:
    - psi_score parameter should remain None during training
    - PSI is NOT a training metric - it's calculated by Model Monitoring service
    - PSI compares current production population against training baseline
    - Setting psi_score here would be misleading as it represents production drift, not training quality
    - Model Monitoring service will calculate PSI when comparing current data against this model's baseline
    """
    # Use synchronous engine for metadata saving
    engine = create_engine(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))

    with Session(engine) as session:
        # Create model metadata record
        model = ModelMetadata(
            model_name="LightGBM Risk Model",
            version=version,
            algorithm="LightGBM",
            model_type="Gradient Boosting",
            feature_count=len(feature_importance),
            auc_score=float(auc),
            ks_score=float(ks),
            psi_score=psi_score,  # PSI calculated from baseline comparison (None during training)
            psi_status=None if psi_score is None else "stable" if psi_score < 0.1 else "warning" if psi_score < 0.25 else "drift",
            is_active=True,
        )

        # Deactivate previous models
        session.execute(
            text("UPDATE model_metadata SET is_active = FALSE WHERE is_active = TRUE")
        )

        session.add(model)
        session.flush()

        # Save feature importance
        for fi_data in feature_importance[:50]:
            feature_importance_record = FeatureImportance(
                model_id=model.model_id,
                feature_name=fi_data["feature"],
                importance_score=fi_data["importance"],
                rank=fi_data.get("rank", 0),
            )
            session.add(feature_importance_record)

        session.commit()

        print(f"\n✓ Model metadata saved to database (model_id: {model.model_id})")


def train_from_csv(csv_dir: str = "data/generated"):
    """Train model using CSV files."""
    print(f"Loading data from {csv_dir}...")

    csv_path = project_root / csv_dir

    # Load CSV files
    try:
        users_df = pd.read_csv(csv_path / "users.csv")
        devices_df = pd.read_csv(csv_path / "devices.csv")
        trades_df = pd.read_csv(csv_path / "trades.csv")
        withdrawals_df = pd.read_csv(csv_path / "withdrawals.csv")
        labels_df = pd.read_csv(csv_path / "risk_labels.csv")
    except FileNotFoundError as e:
        print(f"Error: CSV file not found: {e}")
        print("\nGenerating demo data first...")
        from backend.app.utils.data_generation import DemoDataGenerator

        generator = DemoDataGenerator()
        data = generator.generate_all()

        # Save to CSV
        output_dir = project_root / "data" / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)

        for key, df in data.items():
            if key != "cluster_info" and isinstance(df, pd.DataFrame):
                filepath = output_dir / f"{key}.csv"
                df.to_csv(filepath, index=False)
                print(f"✓ Saved {filepath.name}")

        # Reload
        users_df = data["users"]
        devices_df = data["devices"]
        trades_df = data["trades"]
        withdrawals_df = data["withdrawals"]
        labels_df = data["risk_labels"]

    print(f"\n✓ Loaded data:")
    print(f"  - Users: {len(users_df)}")
    print(f"  - Devices: {len(devices_df)}")
    print(f"  - Trades: {len(trades_df)}")
    print(f"  - Withdrawals: {len(withdrawals_df)}")
    print(f"  - Labels: {len(labels_df)}")

    positive_count = labels_df['is_risky'].sum()
    print(f"  - Risky users: {positive_count} ({positive_count/len(labels_df)*100:.1f}%)")
    print(f"  - Normal users: {len(labels_df) - positive_count}")

    # Prepare features
    print("\nPreparing features for training...")
    trainer = LightGBMTrainer()

    features_df = trainer.prepare_features(
        users_df, devices_df, trades_df, withdrawals_df, labels_df
    )

    print(f"✓ Prepared {len(features_df)} feature vectors")

    # Train model
    print(f"\n{'='*50}")
    print("Training LightGBM Model")
    print(f"{'='*50}")

    results = trainer.train(features_df)

    print(f"\n{'='*50}")
    print("Training Complete!")
    print(f"{'='*50}")
    print(f"\nModel Metrics:")
    print(f"  ✓ AUC: {results['metrics']['auc']:.4f}")
    print(f"  ✓ KS: {results['metrics']['ks']:.4f}")

    print(f"\nData Split:")
    print(f"  - Train: {results['train_size']} ({results['train_size']/(results['train_size']+results['test_size'])*100:.1f}%)")
    print(f"  - Test: {results['test_size']} ({results['test_size']/(results['train_size']+results['test_size'])*100:.1f}%)")
    print(f"  - Positive Ratio: {results['positive_ratio']:.2%}")

    print(f"\n{'='*50}")
    print("Top 10 Feature Importance")
    print(f"{'='*50}")
    for i, fi in enumerate(results['feature_importance'][:10], 1):
        print(f"  {i:2d}. {fi['feature']:30s} : {fi['importance']:8.2f}")

    # Get version from model info
    version = results.get('version', datetime.now().strftime('%Y%m%d_%H%M%S'))

    # Save metadata to database
    try:
        asyncio.run(save_metadata_to_db(
            auc=results['metrics']['auc'],
            ks=results['metrics']['ks'],
            feature_importance=results['feature_importance'],
            version=version
        ))
    except Exception as e:
        print(f"\n⚠ Warning: Could not save metadata to database: {e}")
        print("Model was trained but metadata not stored. Update database manually if needed.")

    # Save PSI baseline distribution for monitoring
    print(f"\n{'='*50}")
    print("Creating PSI Baseline Distribution")
    print(f"{'='*50}")

    baseline_path = trainer.save_baseline_distribution(features_df)
    print(f"✓ PSI baseline saved to: {baseline_path}")
    print(f"  - This baseline will be used for model monitoring")
    print(f"  - PSI calculations compare current data vs this baseline")

    # Validate baseline consistency (PSI should be ~0 when compared with itself)
    print(f"\n{'='*50}")
    print("Validating PSI Baseline Consistency")
    print(f"{'='*50}")

    from app.ml.psi import PSIAnalyzer
    psi_analyzer = PSIAnalyzer(n_bins=10)
    baseline = psi_analyzer.load_baseline(baseline_path)
    validation = psi_analyzer.validate_baseline_consistency(features_df, baseline)

    print(f"  - Max self-PSI: {validation['max_self_psi']}")
    print(f"  - Consistent: {validation['is_consistent']}")
    if validation['inconsistent_features']:
        print(f"  ⚠ WARNING: {len(validation['inconsistent_features'])} features have PSI > 0.05:")
        for feat in validation['inconsistent_features']:
            print(f"    - {feat['feature']}: PSI = {feat['psi']}")
    print(f"  - {validation['message']}")

    print(f"\n{'='*50}")
    print("Model Saved Successfully!")
    print(f"{'='*50}")
    print(f"\nArtifacts:")
    model_dir = project_root / "ml-models" / "artifacts"
    print(f"  - Model: {model_dir / 'risk_model_latest.pkl'}")
    print(f"  - PSI Baseline: {baseline_path}")
    print(f"\nThe RiskScoringService will now use this trained model for inference.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train LightGBM risk model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train from CSV files (generates demo data if not found)
  python -m ml.training.train_risk_model --source csv

  # Train from database (requires data to be loaded)
  python -m ml.training.train_risk_model --source database
        """
    )

    parser.add_argument(
        "--source",
        choices=["csv", "database"],
        default="csv",
        help="Data source for training (default: csv)"
    )

    parser.add_argument(
        "--csv-dir",
        default="data/generated",
        help="Directory containing CSV files (default: data/generated)"
    )

    args = parser.parse_args()

    if args.source == "csv":
        train_from_csv(args.csv_dir)
    else:
        print("Database training not yet implemented. Use --source csv")
        print("The pipeline will load data from database for training in production.")
