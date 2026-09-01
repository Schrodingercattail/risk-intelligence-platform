"""
Historical Training Service

Handles model training using the historical v2_diverse CSV dataset.
This is the official baseline training dataset for the MVP.
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
import sys
import pandas as pd
import numpy as np
import math
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

# Add project root to path
# __file__ is backend/app/services/historical_training_service.py
# Parent directories: services -> app -> backend -> project_root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.ml.model import LightGBMTrainer
from app.models.database import ModelMetadata, FeatureImportance
from app.config import settings


class HistoricalTrainingService:
    """
    Service for training models using historical v2_diverse dataset.

    v2_diverse is the official baseline training dataset for the MVP.
    It contains diverse fraud scenarios for comprehensive detection coverage.
    """

    def __init__(self, db: AsyncSession):
        """Initialize training service with database session."""
        self.db = db
        self.historical_data_path = project_root / "test_data" / "v2_diverse"

    async def train_from_historical_dataset(self) -> Dict[str, Any]:
        """
        Train a new LightGBM model using the historical v2_diverse CSV dataset.

        This is the official baseline training method for the MVP.
        v2_diverse contains diverse fraud scenarios for detection coverage.

        Labels are generated from behavioral signals during training.

        After training, this also loads v2_diverse data into the database FeatureTable
        so that PSI calculations compare matching distributions (PSI ≈ 0).

        Returns:
            Training result with model version and metrics
        """
        try:
            # Load historical CSV data
            csv_path = self.historical_data_path

            users_df = pd.read_csv(csv_path / "users.csv")
            devices_df = pd.read_csv(csv_path / "devices.csv")
            trades_df = pd.read_csv(csv_path / "trades.csv")
            withdrawals_df = pd.read_csv(csv_path / "withdrawals.csv")

            # Generate labels from behavioral signals (simulates investigation outcomes)
            labels_df = self._generate_behavioral_labels(users_df, trades_df, withdrawals_df)

            # Prepare features using shared trainer
            trainer = LightGBMTrainer(model_path=settings.MODEL_PATH)
            features_df = trainer.prepare_features(
                users_df, devices_df, trades_df, withdrawals_df, labels_df
            )

            # Load v2_diverse data into database for PSI consistency
            await self._load_v2diverse_to_database(users_df, devices_df, trades_df, withdrawals_df)

            # Train model
            results = trainer.train(features_df)

            # Get version from results or generate timestamp
            version = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

            # Save model metadata to database
            await self._save_model_metadata(
                version=version,
                training_results=results,
                dataset_name="v2_diverse"
            )

            # Create PSI baseline (only for historical training)
            baseline_path, baseline_validation = await self._create_psi_baseline(trainer, features_df)

            # Save model metadata with baseline validation results
            await self._save_model_metadata(
                version=version,
                training_results=results,
                dataset_name="v2_diverse",
                baseline_validation=baseline_validation
            )

            return {
                "status": "completed",
                "model_version": version,
                "dataset": "v2_diverse",
                "metrics": results['metrics'],
                "feature_count": len(results['feature_importance']),
                "train_size": results['train_size'],
                "test_size": results['test_size'],
                "positive_ratio": results['positive_ratio'],
                "baseline_path": str(baseline_path),
                "baseline_validation": {
                    "psi": baseline_validation['max_self_psi'],
                    "status": "passed" if baseline_validation['is_consistent'] else "failed",
                    "message": baseline_validation['message'],
                },
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"HISTORICAL TRAINING ERROR: {str(e)}", file=sys.stderr)
            print(f"ERROR TYPE: {type(e).__name__}", file=sys.stderr)
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _save_model_metadata(
        self,
        version: str,
        training_results: Dict[str, Any],
        dataset_name: str,
        baseline_validation: Optional[Dict[str, Any]] = None
    ):
        """
        Save model metadata to database.

        Args:
            version: Model version string
            training_results: Training metrics and feature importance
            dataset_name: Name of training dataset
            baseline_validation: Optional baseline validation results from training
        """
        # Deactivate previous models
        await self.db.execute(
            update(ModelMetadata).where(ModelMetadata.is_active == True).values(is_active=False)
        )

        # Determine baseline validation status
        baseline_validation_psi = None
        baseline_validation_status = "not_validated"
        baseline_validated_at = None

        if baseline_validation:
            baseline_validation_psi = baseline_validation.get('max_self_psi')
            baseline_validation_status = "passed" if baseline_validation.get('is_consistent') else "failed"
            baseline_validated_at = datetime.now(timezone.utc)

        # Create new model metadata
        # IMPORTANT: is_active=False by default for manual activation workflow
        # NOTE: psi_score is NOT set during training - it's updated only by monitoring service
        model_metadata = ModelMetadata(
            model_name="LightGBM Risk Model",
            version=version,
            algorithm="LightGBM",
            model_type="Gradient Boosting",
            feature_count=len(training_results['feature_importance']),
            auc_score=training_results['metrics']['auc'],
            ks_score=training_results['metrics']['ks'],
            # Baseline validation fields (set during training)
            baseline_validation_psi=baseline_validation_psi,
            baseline_validation_status=baseline_validation_status,
            baseline_validated_at=baseline_validated_at,
            # psi_score remains None - will be updated by monitoring service
            psi_score=None,
            psi_status=None,
            psi_calculated_at=None,
            is_active=False,  # Requires manual activation
        )
        self.db.add(model_metadata)
        await self.db.flush()

        # Save feature importance
        # Normalize importance scores to relative percentages (sum = 100)
        total_importance = sum(fi['importance'] for fi in training_results['feature_importance'][:50])
        for i, fi in enumerate(training_results['feature_importance'][:50], 1):
            normalized_score = (fi['importance'] / total_importance * 100) if total_importance > 0 else 0
            fi_record = FeatureImportance(
                model_id=model_metadata.model_id,
                feature_name=fi['feature'],
                importance_score=normalized_score,
                rank=i,
            )
            self.db.add(fi_record)

        await self.db.commit()

        return model_metadata.model_id

    async def _create_psi_baseline(
        self,
        trainer: LightGBMTrainer,
        features_df: pd.DataFrame
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create PSI baseline distribution for monitoring.

        For historical training (v2_diverse), we ALWAYS overwrite the baseline
        to ensure PSI calculations compare against the correct training baseline.

        Returns:
            Tuple of (baseline_path, validation_results)
        """
        baseline_path = Path(settings.MODEL_PATH) / "feature_baseline.json"

        # Log training dataset info
        print(f"\n{'='*50}")
        print("PSI Baseline Creation")
        print(f"{'='*50}")
        print(f"Training dataset rows: {len(features_df)}")
        print(f"Training features: {len(features_df.columns)}")

        # Always create baseline from historical training data
        # This ensures PSI calculations are comparing against v2_diverse baseline
        trainer.save_baseline_distribution(features_df, str(baseline_path))

        # Validate baseline consistency (PSI should be ~0 when compared with itself)
        from app.ml.psi import PSIAnalyzer
        psi_analyzer = PSIAnalyzer(n_bins=10)
        baseline = psi_analyzer.load_baseline(str(baseline_path))
        validation = psi_analyzer.validate_baseline_consistency(features_df, baseline)

        print(f"\nBaseline Validation Results:")
        print(f"  Baseline rows: {sum(len(data.get('distribution', [])) for data in baseline.values())}")
        print(f"  Baseline validation PSI: {validation['max_self_psi']}")
        print(f"  Validation status: {validation['message']}")
        if validation['inconsistent_features']:
            print(f"  ⚠ WARNING: {len(validation['inconsistent_features'])} features have PSI > 0.05:")
            for feat in validation['inconsistent_features']:
                print(f"    - {feat['feature']}: PSI = {feat['psi']}")

        return str(baseline_path), validation

    def _generate_behavioral_labels(
        self,
        users_df: pd.DataFrame,
        trades_df: pd.DataFrame,
        withdrawals_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Generate labels from behavioral signals.

        This simulates investigation-confirmed risk outcomes based on user behavior patterns.
        Uses the same logic as pipeline_service for consistency.
        """
        import random
        random.seed(42)  # For reproducibility

        # Get reference time for calculations
        reference_time = pd.to_datetime(trades_df['timestamp']).max()
        if pd.isna(reference_time) or len(trades_df) == 0:
            reference_time = pd.to_datetime(withdrawals_df['timestamp']).max()

        # Calculate behavioral features for each user
        user_labels = []

        for user_id in users_df['user_id'].unique():
            user_trades = trades_df[trades_df['user_id'] == user_id]
            user_withdrawals = withdrawals_df[withdrawals_df['user_id'] == user_id]
            user = users_df[users_df['user_id'] == user_id].iloc[0]

            # Calculate risk score based on behavioral signals
            risk_score = 0.0

            # Trading patterns
            trade_freq_24h = len(user_trades)  # Simplified
            trade_volume_24h = user_trades['price'].multiply(user_trades['quantity']).sum()

            # Opposite trading detection
            buy_trades = user_trades[user_trades['side'] == 'BUY']
            sell_trades = user_trades[user_trades['side'] == 'SELL']
            opposite_trade_ratio = 0
            if len(buy_trades) > 0 and len(sell_trades) > 0:
                opposite_trade_ratio = min(len(buy_trades), len(sell_trades)) / len(user_trades)

            # Withdrawal patterns
            withdrawal_freq_24h = len(user_withdrawals)
            withdrawal_volume_24h = user_withdrawals['amount'].sum()

            # Account age
            account_created = pd.to_datetime(user['account_created_time'])
            account_age_days = (reference_time - account_created).days

            # Calculate risk contributions
            risk_score += min(trade_freq_24h / 10, 2.0)
            risk_score += min(trade_volume_24h / 10000, 1.5)
            if opposite_trade_ratio > 0:
                risk_score += 0.5
            risk_score += min(withdrawal_freq_24h / 5, 2.0)
            risk_score += min(withdrawal_volume_24h / 5000, 1.5)
            if account_age_days < 30:
                risk_score += 1.5

            # Add probabilistic noise
            noise = random.gauss(0, 0.5)
            risk_score += noise

            # Convert to probability using sigmoid
            risk_probability = 1 / (1 + math.exp(-(risk_score - 2.5) / 0.8))

            # Sample label from probability
            is_risky = random.random() < risk_probability

            user_labels.append({
                'user_id': user_id,
                'is_risky': 1 if is_risky else 0
            })

        return pd.DataFrame(user_labels)

    async def _load_v2diverse_to_database(
        self,
        users_df: pd.DataFrame,
        devices_df: pd.DataFrame,
        trades_df: pd.DataFrame,
        withdrawals_df: pd.DataFrame
    ):
        """
        Load v2_diverse data into database tables.

        This ensures PSI calculations compare matching distributions:
        - Baseline: Created from v2_diverse
        - Current: Database FeatureTable populated with v2_diverse
        - Result: PSI ≈ 0 immediately after training

        Note: This clears existing data and loads fresh v2_diverse data.
        """
        from app.models.database import (
            User, Device, Trade, Withdrawal, FeatureTable,
            RiskFactor, RiskEvent, ClusterMember, AccountCluster,
            CaseExplanation
        )
        from sqlalchemy import delete
        from datetime import datetime

        # Clear existing data (respecting foreign key dependencies).
        # Persisted explanation artifacts reference BOTH users.user_id and
        # risk_events.id, so they must be deleted before either parent —
        # otherwise delete(RiskEvent) raises a ForeignKeyViolation once any
        # explanation has been persisted (same constraint the pipeline reset
        # paths honor).
        await self.db.execute(delete(CaseExplanation))
        await self.db.execute(delete(RiskFactor))
        await self.db.execute(delete(RiskEvent))
        await self.db.execute(delete(ClusterMember))
        await self.db.execute(delete(AccountCluster))
        await self.db.execute(delete(FeatureTable))
        await self.db.execute(delete(Withdrawal))
        await self.db.execute(delete(Trade))
        await self.db.execute(delete(Device))
        await self.db.execute(delete(User))

        # Load users
        for _, row in users_df.iterrows():
            account_time = row.get('account_created_time')
            user = User(
                user_id=row['user_id'],
                country=row.get('country'),
                kyc_level=row.get('kyc_level'),
                account_created_time=pd.to_datetime(account_time).to_pydatetime().replace(tzinfo=None)
                if account_time else None,
                vip_level=row.get('vip_level'),
            )
            self.db.add(user)

        # Load devices
        for _, row in devices_df.iterrows():
            first = row.get('first_seen')
            last = row.get('last_seen')
            device = Device(
                user_id=row['user_id'],
                device_id=row.get('device_id'),
                ip_address=row.get('ip_address'),
                location=row.get('location'),
                browser_fingerprint=row.get('browser_fingerprint'),
                first_seen=pd.to_datetime(first).to_pydatetime().replace(tzinfo=None)
                if first else None,
                last_seen=pd.to_datetime(last).to_pydatetime().replace(tzinfo=None)
                if last else None,
            )
            self.db.add(device)

        # Load trades
        for _, row in trades_df.iterrows():
            trade = Trade(
                trade_id=row['trade_id'],
                user_id=row['user_id'],
                symbol=row['symbol'],
                side=row['side'],
                price=row['price'],
                quantity=row['quantity'],
                timestamp=pd.to_datetime(row['timestamp']).to_pydatetime().replace(tzinfo=None),
            )
            self.db.add(trade)

        # Load withdrawals
        for _, row in withdrawals_df.iterrows():
            withdrawal = Withdrawal(
                withdraw_id=row['withdraw_id'],
                user_id=row['user_id'],
                asset=row['asset'],
                amount=row['amount'],
                address=row['address'],
                is_new_address=row.get('is_new_address'),
                timestamp=pd.to_datetime(row['timestamp']).to_pydatetime().replace(tzinfo=None),
            )
            self.db.add(withdrawal)

        await self.db.commit()

        # Generate features using FeatureEngineeringService
        from app.services.feature_engineering import FeatureEngineeringService
        feature_service = FeatureEngineeringService(self.db)
        await feature_service.generate_features_for_all_users()
