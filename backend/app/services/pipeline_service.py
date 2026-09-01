"""
Pipeline Service

Orchestrates the end-to-end data pipeline:
CSV Upload -> Data Validation -> Feature Engineering -> ML Scoring -> Graph Analysis -> Model Training
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum
import pandas as pd
import numpy as np
import math
import random
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pathlib import Path
import sys
import subprocess

from app.services.feature_engineering import FeatureEngineeringService
from app.services.graph_service import GraphAnalysisService
from app.services.risk_service import RiskScoringService
from app.models.database import User, Device, Trade, Withdrawal, ClusterMember, ModelMetadata


class PipelineStatus(str, Enum):
    """Pipeline step status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineService:
    """
    Pipeline Service

    Orchestrates the data pipeline, ensuring data flows through all layers.
    Service Layer - Independent of API, coordinates multiple services.
    """

    def __init__(self, db: AsyncSession):
        """Initialize pipeline service with database session."""
        self.db = db

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get current pipeline status by inspecting database state.

        Returns:
            Dict with upload info and all pipeline stage statuses
        """
        from sqlalchemy import select, func, update
        from app.models.database import User, Device, Trade, Withdrawal, FeatureTable, RiskEvent, AccountCluster, ClusterMember

        # Get record counts
        user_count = await self.db.scalar(select(func.count()).select_from(User)) or 0
        device_count = await self.db.scalar(select(func.count()).select_from(Device)) or 0
        trade_count = await self.db.scalar(select(func.count()).select_from(Trade)) or 0
        withdrawal_count = await self.db.scalar(select(func.count()).select_from(Withdrawal)) or 0
        feature_count = await self.db.scalar(select(func.count()).select_from(FeatureTable)) or 0
        risk_event_count = await self.db.scalar(select(func.count()).select_from(RiskEvent)) or 0
        cluster_count = await self.db.scalar(select(func.count()).select_from(AccountCluster)) or 0

        # Get distinct risky accounts detected (from graph detection layer)
        risky_accounts_detected = await self.db.scalar(
            select(func.count(func.distinct(ClusterMember.user_id)))
        ) or 0

        # Get max timestamp for upload info - simplified query
        max_timestamp = None
        if user_count > 0:
            # Get the max timestamp from Trade table as a proxy (most recent activity)
            max_trade_time = await self.db.scalar(select(func.max(Trade.timestamp)))
            if max_trade_time:
                max_timestamp = max_trade_time.isoformat()

        # Determine upload status: upload is complete if users.csv was imported successfully
        # Empty datasets (0 records) are still valid uploads, just with warnings
        has_upload = user_count > 0

        upload_status = PipelineStatus.COMPLETED.value if has_upload else PipelineStatus.PENDING.value
        data_sources_status = PipelineStatus.COMPLETED.value if has_upload else PipelineStatus.PENDING.value
        validation_status = PipelineStatus.COMPLETED.value if has_upload else PipelineStatus.PENDING.value
        feature_engineering_status = PipelineStatus.COMPLETED.value if feature_count > 0 else PipelineStatus.PENDING.value

        # Initialize warnings list
        warnings = []

        # Graph analysis status: completed if clusters exist, OR if device data is empty (analysis completed but no findings)
        # When device data is empty, graph analysis should still be marked COMPLETED with a warning
        if cluster_count > 0:
            graph_analysis_status = PipelineStatus.COMPLETED.value
        elif device_count == 0 and has_upload:
            # No device data available - graph analysis completed but found no relationships
            graph_analysis_status = PipelineStatus.COMPLETED.value
            warnings.append("No device relationship data available - graph analysis completed with no findings")
        else:
            graph_analysis_status = PipelineStatus.PENDING.value

        ml_scoring_status = PipelineStatus.COMPLETED.value if risk_event_count > 0 else PipelineStatus.PENDING.value

        # Generate warnings for empty datasets (data quality issues, not upload failures)
        if has_upload:
            if device_count == 0:
                warnings.append("No device records available - device-based analysis disabled")
            if trade_count == 0:
                warnings.append("No transaction history available - trading analysis disabled")
            if withdrawal_count == 0:
                warnings.append("No withdrawal history available - withdrawal analysis disabled")

        # Get pipeline results if completed
        results = None
        if ml_scoring_status == PipelineStatus.COMPLETED.value:
            results = {
                "total_records": user_count + device_count + trade_count + withdrawal_count,
                "users": user_count,
                "risky_accounts_detected": risky_accounts_detected,
                "fraud_networks": cluster_count,
                "feature_vectors_generated": feature_count,
            }

        return {
            "upload_status": upload_status,
            "upload_timestamp": max_timestamp,
            "upload_counts": {
                "users": user_count,
                "devices": device_count,
                "trades": trade_count,
                "withdrawals": withdrawal_count,
            },  # Always return counts, including 0 for empty datasets
            "upload_warnings": warnings if warnings else None,  # New field for empty dataset warnings
            "data_sources": data_sources_status,
            "dataset_validation": validation_status,
            "feature_engineering": feature_engineering_status,
            "graph_analysis": graph_analysis_status,
            "ml_scoring": ml_scoring_status,
            "results": results,
        }

    async def clear_all_data(self) -> Dict[str, int]:
        """
        Clear all existing data from the database.
        WARNING: This also deletes trained models.

        Returns:
            Dict with counts of deleted records per table
        """
        from sqlalchemy import delete, select, func
        from app.models.database import (
            RiskFactor, RiskEvent, ClusterMember, AccountCluster,
            FeatureTable, ModelMetadata, FeatureImportance, Case, Withdrawal, Trade, Device, User,
            CaseExplanation,
        )

        counts = {}

        # Delete in order of dependencies (child tables first)
        # Persisted explanation artifacts reference BOTH users.user_id and
        # risk_events.id — delete them before either parent (see
        # clear_pipeline_data).
        result = await self.db.execute(delete(CaseExplanation))
        counts["case_explanations"] = result.rowcount

        # Risk management
        result = await self.db.execute(delete(RiskFactor))
        counts["risk_factors"] = result.rowcount

        result = await self.db.execute(delete(RiskEvent))
        counts["risk_events"] = result.rowcount

        result = await self.db.execute(delete(Case))
        counts["cases"] = result.rowcount

        # Cluster data
        result = await self.db.execute(delete(ClusterMember))
        counts["cluster_members"] = result.rowcount

        result = await self.db.execute(delete(AccountCluster))
        counts["clusters"] = result.rowcount

        # ML features and models
        result = await self.db.execute(delete(FeatureImportance))
        counts["feature_importance"] = result.rowcount

        result = await self.db.execute(delete(ModelMetadata))
        counts["model_metadata"] = result.rowcount

        result = await self.db.execute(delete(FeatureTable))
        counts["features"] = result.rowcount

        # Transaction data
        result = await self.db.execute(delete(Withdrawal))
        counts["withdrawals"] = result.rowcount

        result = await self.db.execute(delete(Trade))
        counts["trades"] = result.rowcount

        result = await self.db.execute(delete(Device))
        counts["devices"] = result.rowcount

        # Users (last, as other tables depend on them)
        result = await self.db.execute(delete(User))
        counts["users"] = result.rowcount

        await self.db.commit()
        return counts

    async def clear_pipeline_data(self) -> Dict[str, int]:
        """
        Clear only pipeline data (users, devices, trades, withdrawals, risk events).

        This PRESERVES:
        - Model metadata (trained models)
        - Feature importance
        - Model artifacts
        - PSI baseline

        This is used during data upload/reset to maintain model lifecycle
        separate from data lifecycle.

        Returns:
            Dict with counts of deleted records per table
        """
        from sqlalchemy import delete, select, func
        from app.models.database import (
            RiskFactor, RiskEvent, ClusterMember, AccountCluster,
            FeatureTable, Case, Withdrawal, Trade, Device, User,
            CaseExplanation,
        )

        # Log active model count before clearing
        from app.models.database import ModelMetadata
        active_model_count = await self.db.scalar(
            select(func.count()).select_from(ModelMetadata).where(ModelMetadata.is_active == True)
        )

        counts = {
            "active_models_preserved": active_model_count or 0
        }

        # Delete in order of dependencies (child tables first)
        # Persisted explanation artifacts reference BOTH users.user_id and
        # risk_events.id, so they must go before either parent is deleted —
        # otherwise the delete(RiskEvent) below raises a ForeignKeyViolation
        # and the whole reset rolls back.
        result = await self.db.execute(delete(CaseExplanation))
        counts["case_explanations"] = result.rowcount

        # Risk management
        result = await self.db.execute(delete(RiskFactor))
        counts["risk_factors"] = result.rowcount

        result = await self.db.execute(delete(RiskEvent))
        counts["risk_events"] = result.rowcount

        result = await self.db.execute(delete(Case))
        counts["cases"] = result.rowcount

        # Cluster data
        result = await self.db.execute(delete(ClusterMember))
        counts["cluster_members"] = result.rowcount

        result = await self.db.execute(delete(AccountCluster))
        counts["clusters"] = result.rowcount

        # Feature table (regenerated from new data)
        result = await self.db.execute(delete(FeatureTable))
        counts["features"] = result.rowcount

        # Transaction data
        result = await self.db.execute(delete(Withdrawal))
        counts["withdrawals"] = result.rowcount

        result = await self.db.execute(delete(Trade))
        counts["trades"] = result.rowcount

        result = await self.db.execute(delete(Device))
        counts["devices"] = result.rowcount

        # Users (last, as other tables depend on them)
        result = await self.db.execute(delete(User))
        counts["users"] = result.rowcount

        await self.db.commit()

        # Verify model preservation after clearing
        total_model_count = await self.db.scalar(
            select(func.count()).select_from(ModelMetadata)
        )

        counts["total_models_preserved"] = total_model_count or 0

        return counts

    async def import_csv_data(
        self,
        users_csv: Optional[str] = None,
        devices_csv: Optional[str] = None,
        trades_csv: Optional[str] = None,
        withdrawals_csv: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Import CSV data into database.

        Args:
            users_csv: Path to users CSV file
            devices_csv: Path to devices CSV file
            trades_csv: Path to trades CSV file
            withdrawals_csv: Path to withdrawals CSV file

        Returns:
            Dict with counts of imported records
        """
        results = {}

        if users_csv:
            users_df = pd.read_csv(users_csv)
            users_count = await self._import_users(users_df)
            results["users"] = users_count

        if devices_csv:
            devices_df = pd.read_csv(devices_csv)
            devices_count = await self._import_devices(devices_df)
            results["devices"] = devices_count

        if trades_csv:
            trades_df = pd.read_csv(trades_csv)
            trades_count = await self._import_trades(trades_df)
            results["trades"] = trades_count

        if withdrawals_csv:
            withdrawals_df = pd.read_csv(withdrawals_csv)
            withdrawals_count = await self._import_withdrawals(withdrawals_df)
            results["withdrawals"] = withdrawals_count

        await self.db.commit()

        return results

    async def run_pipeline(
        self,
        run_full_pipeline: bool = True,
        generate_risk_events: bool = True,
        train_model: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the complete data pipeline.

        Args:
            run_full_pipeline: Whether to run all steps
            generate_risk_events: Whether to generate risk events
            train_model: Whether to train ML model after feature engineering

        Returns:
            Dict with pipeline results
        """
        # Generate unique pipeline run ID for traceability
        pipeline_run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Get active model version
        model_version = None
        model_result = await self.db.execute(
            select(ModelMetadata.version).where(ModelMetadata.is_active == True)
        )
        active_model = model_result.scalar_one_or_none()
        if active_model:
            model_version = active_model

        results = {
            "started_at": datetime.now(timezone.utc),
            "pipeline_run_id": pipeline_run_id,
            "model_version": model_version,
            "steps": {},
            "final_counts": {},
        }

        try:
            # Step 1: Feature Engineering
            results["steps"]["feature_engineering"] = {
                "status": PipelineStatus.IN_PROGRESS.value,
                "started_at": datetime.now(timezone.utc),
            }

            feature_service = FeatureEngineeringService(self.db)
            users_count = await feature_service.generate_features_for_all_users()

            results["steps"]["feature_engineering"].update({
                "status": PipelineStatus.COMPLETED.value,
                "completed_at": datetime.now(timezone.utc),
                "users_processed": users_count,
            })

            # Step 2: Graph Analysis
            results["steps"]["graph_analysis"] = {
                "status": PipelineStatus.IN_PROGRESS.value,
                "started_at": datetime.now(timezone.utc),
            }

            graph_service = GraphAnalysisService(self.db)
            clusters = await graph_service.detect_all_clusters()

            results["steps"]["graph_analysis"].update({
                "status": PipelineStatus.COMPLETED.value,
                "completed_at": datetime.now(timezone.utc),
                "clusters_detected": len(clusters),
            })

            # Step 3: Risk Scoring
            if generate_risk_events:
                results["steps"]["ml_scoring"] = {
                    "status": PipelineStatus.IN_PROGRESS.value,
                    "started_at": datetime.now(timezone.utc),
                }

                risk_service = RiskScoringService(self.db)
                events_created = await risk_service.score_all_users(
                    pipeline_run_id=pipeline_run_id,
                    model_version=model_version
                )

                results["steps"]["ml_scoring"].update({
                    "status": PipelineStatus.COMPLETED.value,
                    "completed_at": datetime.now(timezone.utc),
                    "risk_events_created": events_created,
                    "pipeline_run_id": pipeline_run_id,
                    "model_version": model_version,
                })

            # Step 4: Model Training (optional)
            if train_model:
                results["steps"]["model_training"] = {
                    "status": PipelineStatus.IN_PROGRESS.value,
                    "started_at": datetime.now(timezone.utc),
                }

                training_result = await self.train_model()

                results["steps"]["model_training"].update({
                    "status": training_result.get("status", PipelineStatus.COMPLETED.value),
                    "completed_at": datetime.now(timezone.utc),
                    **training_result
                })

            results["completed_at"] = datetime.now(timezone.utc)
            results["success"] = True

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            results["failed_at"] = datetime.now(timezone.utc)

        return results

    async def _import_users(self, df: pd.DataFrame) -> int:
        """Import users from DataFrame."""
        count = 0
        for _, row in df.iterrows():
            user = User(
                user_id=str(row["user_id"]),
                country=str(row.get("country")) if pd.notna(row.get("country")) else None,
                kyc_level=str(row.get("kyc_level")) if pd.notna(row.get("kyc_level")) else None,
                account_created_time=pd.to_datetime(row.get("account_created_time")).to_pydatetime()
                if pd.notna(row.get("account_created_time")) else None,
                vip_level=str(row.get("vip_level")) if pd.notna(row.get("vip_level")) else None,
            )
            self.db.add(user)
            count += 1
        await self.db.flush()
        return count

    async def _import_devices(self, df: pd.DataFrame) -> int:
        """Import devices from DataFrame."""
        count = 0
        for _, row in df.iterrows():
            device = Device(
                user_id=str(row["user_id"]),
                device_id=str(row.get("device_id")) if pd.notna(row.get("device_id")) else None,
                ip_address=str(row.get("ip_address")) if pd.notna(row.get("ip_address")) else None,
                location=str(row.get("location")) if pd.notna(row.get("location")) else None,
                browser_fingerprint=str(row.get("browser_fingerprint")) if pd.notna(row.get("browser_fingerprint")) else None,
                first_seen=pd.to_datetime(row.get("first_seen")).to_pydatetime()
                if pd.notna(row.get("first_seen")) else None,
                last_seen=pd.to_datetime(row.get("last_seen")).to_pydatetime()
                if pd.notna(row.get("last_seen")) else None,
            )
            self.db.add(device)
            count += 1
        await self.db.flush()
        return count

    async def _import_trades(self, df: pd.DataFrame) -> int:
        """Import trades from DataFrame."""
        count = 0
        for _, row in df.iterrows():
            trade = Trade(
                trade_id=str(row["trade_id"]),
                user_id=str(row["user_id"]),
                symbol=str(row["symbol"]),
                side=str(row["side"]),
                price=float(row["price"]),
                quantity=float(row["quantity"]),
                timestamp=pd.to_datetime(row["timestamp"]).to_pydatetime(),
            )
            self.db.add(trade)
            count += 1
        await self.db.flush()
        return count

    async def _import_withdrawals(self, df: pd.DataFrame) -> int:
        """Import withdrawals from DataFrame."""
        count = 0
        for _, row in df.iterrows():
            # Handle is_new_address - convert various boolean representations
            is_new = None
            if pd.notna(row.get("is_new_address")):
                val = row.get("is_new_address")
                if isinstance(val, bool):
                    is_new = val
                elif isinstance(val, str):
                    is_new = val.lower() in ('true', '1', 'yes')
                else:
                    is_new = bool(val)

            withdrawal = Withdrawal(
                withdraw_id=str(row["withdraw_id"]),
                user_id=str(row["user_id"]),
                asset=str(row["asset"]),
                amount=float(row["amount"]),
                address=str(row["address"]),
                is_new_address=is_new,
                timestamp=pd.to_datetime(row["timestamp"]).to_pydatetime(),
            )
            self.db.add(withdrawal)
            count += 1
        await self.db.flush()
        return count

    async def train_model(self) -> Dict[str, Any]:
        """
        Train LightGBM model on current database data.

        This method:
        1. Loads features from FeatureTable
        2. Generates labels from behavioral signals (NOT graph features)
        3. Trains LightGBM model
        4. Saves model artifacts and metadata
        5. Creates PSI baseline

        Label Generation (Behavioral-based, no graph leakage):
        - Uses trading patterns, withdrawal patterns, account age
        - Does NOT use shared_device_count, linked_account_count, or cluster membership
        - Labels simulate independent investigator-confirmed risk outcomes

        PSI Handling:
        - During training, we save the feature distribution as baseline
        - We do NOT calculate PSI during training (PSI is not a training metric)
        - PSI (Population Stability Index) is calculated by Model Monitoring service
        - PSI compares current production population against this training baseline
        - Setting psi_score during training would be meaningless

        Returns:
            Dict with training results
        """
        from app.config import settings
        import tempfile
        import os

        try:
            # Check if we have feature data
            from app.models.database import FeatureTable
            feature_count = await self.db.scalar(select(func.count()).select_from(FeatureTable))

            if feature_count == 0:
                return {
                    "status": PipelineStatus.FAILED.value,
                    "error": "No feature data available. Run feature engineering first."
                }

            # Load all features
            features_result = await self.db.execute(select(FeatureTable))
            features_list = features_result.scalars().all()

            # Prepare training data
            # Official 13 risk features (must match frontend RISK_FEATURE_COUNT)
            # These are the predictive model input features used by LightGBM
            feature_cols = [
                # Network features
                'shared_device_count', 'linked_account_count', 'unique_ip_count',
                # Trading features
                'trade_frequency_24h', 'trade_frequency_7d', 'opposite_trade_ratio',
                'avg_trade_size', 'trade_volume_24h',
                # Account features
                'account_age_days', 'active_days_count',
                # Withdrawal features
                'withdrawal_risk_score', 'withdrawal_frequency_24h', 'withdrawal_volume_24h'
            ]

            # Calculate behavioral thresholds from data distribution
            feature_data = []
            labels = []

            # First pass: collect all features to compute thresholds
            all_features = []
            for feature in features_list:
                row = {'user_id': feature.user_id}
                for col in feature_cols:
                    row[col] = getattr(feature, col, 0) or 0
                all_features.append(row)

            temp_df = pd.DataFrame(all_features)

            # Convert all columns except user_id to numeric to handle Decimal types
            numeric_cols = [col for col in temp_df.columns if col != 'user_id']
            for col in numeric_cols:
                temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
            temp_df[numeric_cols] = temp_df[numeric_cols].fillna(0)

            # Calculate thresholds based on data distribution (percentiles)
            trade_freq_threshold = temp_df['trade_frequency_24h'].quantile(0.75)  # Top 25%
            trade_volume_threshold = temp_df['trade_volume_24h'].quantile(0.80)  # Top 20%
            withdrawal_freq_threshold = temp_df['withdrawal_frequency_24h'].quantile(0.75)
            withdrawal_volume_threshold = temp_df['withdrawal_volume_24h'].quantile(0.80)
            account_age_threshold = temp_df['account_age_days'].quantile(0.20)  # Bottom 20% (new accounts)

            # Second pass: generate probabilistic labels based on behavioral signals
            # This simulates investigation outcomes with uncertainty
            import random
            random.seed(42)  # For reproducibility

            for row in all_features:
                risk_score = 0.0

                # Trading patterns (convert to float)
                trade_freq_24h = float(row['trade_frequency_24h'])
                trade_volume_24h = float(row['trade_volume_24h'])
                opposite_trade_ratio = float(row['opposite_trade_ratio'])

                # Add continuous risk contributions (not binary)
                risk_score += min(trade_freq_24h / (trade_freq_threshold + 1), 2.0)  # Cap at 2
                risk_score += min(trade_volume_24h / (trade_volume_threshold + 1000), 1.5)

                # Opposite trading (binary but smaller weight)
                if opposite_trade_ratio > 0:
                    risk_score += 0.5

                # Withdrawal patterns
                withdrawal_freq_24h = float(row['withdrawal_frequency_24h'])
                withdrawal_volume_24h = float(row['withdrawal_volume_24h'])

                risk_score += min(withdrawal_freq_24h / (withdrawal_freq_threshold + 1), 2.0)
                risk_score += min(withdrawal_volume_24h / (withdrawal_volume_threshold + 1000), 1.5)

                if row['first_withdrawal_flag']:
                    risk_score += 0.8

                # Account patterns
                account_age_days = float(row['account_age_days'])

                # New accounts are riskier, but scale logarithmically
                if account_age_days > 0:
                    risk_score += max(0, 1.5 - math.log(account_age_days + 1) * 0.3)
                else:
                    risk_score += 1.5

                # Add probabilistic noise to simulate investigation uncertainty
                # This prevents perfect separation
                noise = random.gauss(0, 0.5)  # Gaussian noise with mean=0, std=0.5
                risk_score += noise

                # Convert to probability using sigmoid
                # Higher risk_score = higher probability of being risky
                risk_probability = 1 / (1 + math.exp(-(risk_score - 2.5) / 0.8))

                # Sample label from probability (Monte Carlo)
                # This introduces uncertainty even with high risk scores
                is_risky = random.random() < risk_probability

                feature_data.append({**row, 'is_risky': 1 if is_risky else 0})
                labels.append(is_risky)

            features_df = pd.DataFrame(feature_data)

            # Normalize dtypes for LightGBM training
            # Convert all feature columns to numeric, excluding user_id
            numeric_cols = [col for col in features_df.columns if col != 'user_id']
            for col in numeric_cols:
                features_df[col] = pd.to_numeric(features_df[col], errors='coerce')

            # Fill missing values with 0
            features_df[numeric_cols] = features_df[numeric_cols].fillna(0)

            # Import trainer - add ml-models to path
            # Path(__file__) = backend/app/services/pipeline_service.py
            # Create model directory if needed
            model_dir = Path(settings.MODEL_PATH)
            model_dir.mkdir(parents=True, exist_ok=True)

            # Train model
            from app.ml.model import LightGBMTrainer
            trainer = LightGBMTrainer(model_path=str(model_dir))
            training_results = trainer.train(features_df)

            # Get version from results
            version = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

            # Save metadata to database
            from app.models.database import ModelMetadata, FeatureImportance

            # Deactivate previous models (do this before creating new one for clarity)
            # Use update statement for efficiency
            await self.db.execute(
                update(ModelMetadata).where(ModelMetadata.is_active == True).values(is_active=False)
            )

            # Create new model metadata
            # IMPORTANT: is_active=False by default for manual activation workflow
            # This allows admin to review metrics before activating the model
            model_metadata = ModelMetadata(
                model_name="LightGBM Risk Model",
                version=version,
                algorithm="LightGBM",
                model_type="Gradient Boosting",
                feature_count=len(training_results['feature_importance']),
                auc_score=training_results['metrics']['auc'],
                ks_score=training_results['metrics']['ks'],
                is_active=False,  # Requires manual activation via POST /api/model/models/{id}/activate
            )
            self.db.add(model_metadata)
            await self.db.flush()

            # Save feature importance
            # Normalize importance scores to relative percentages (sum = 100) to fit in database column
            total_importance = sum(fi['importance'] for fi in training_results['feature_importance'][:50])
            for i, fi in enumerate(training_results['feature_importance'][:50], 1):
                # Normalize to percentage (sum = 100)
                normalized_score = (fi['importance'] / total_importance * 100) if total_importance > 0 else 0
                fi_record = FeatureImportance(
                    model_id=model_metadata.model_id,
                    feature_name=fi['feature'],
                    importance_score=normalized_score,
                    rank=i,
                )
                self.db.add(fi_record)

            # Create PSI baseline only if it doesn't exist
            # This preserves the original training baseline for ongoing drift monitoring
            from app.services.psi_service import PSIService
            psi_service = PSIService(self.db)
            baseline_path = str(Path(settings.MODEL_PATH) / "feature_baseline.json")

            baseline_created = False
            if not Path(baseline_path).exists():
                baseline_path = await psi_service.create_and_save_baseline(features_df, baseline_path)
                baseline_created = True
            else:
                # Keep existing baseline - it represents the original training distribution
                baseline_created = False

            await self.db.commit()

            # Calculate detailed label statistics
            positive_count = sum(labels)
            negative_count = len(labels) - positive_count
            positive_ratio = positive_count / len(labels) if len(labels) > 0 else 0

            # Get top 10 feature importance
            top_10_features = training_results['feature_importance'][:10]

            return {
                "status": PipelineStatus.COMPLETED.value,
                "model_version": version,
                "metrics": training_results['metrics'],
                "train_size": training_results['train_size'],
                "test_size": training_results['test_size'],
                "positive_ratio": training_results['positive_ratio'],
                "feature_importance_count": len(training_results['feature_importance']),
                "baseline_path": str(baseline_path),
                "baseline_created": baseline_created,
                "model_id": model_metadata.model_id,
                # Detailed label statistics
                "positive_label_count": positive_count,
                "negative_label_count": negative_count,
                "positive_ratio_detail": positive_ratio,
                "total_labels": len(labels),
                # Top 10 feature importance
                "top_10_feature_importance": top_10_features
            }

        except Exception as e:
            await self.db.rollback()
            return {
                "status": PipelineStatus.FAILED.value,
                "error": str(e)
            }


class DataValidationService:
    """Validates incoming CSV data."""

    @staticmethod
    def validate_users_csv(df: pd.DataFrame) -> Dict[str, Any]:
        """Validate users CSV structure and data."""
        required_columns = ["user_id"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return {
                "valid": False,
                "error": f"Missing required columns: {missing_columns}",
            }

        # Check for duplicate user_ids
        if df["user_id"].duplicated().any():
            return {
                "valid": False,
                "error": "Duplicate user_ids found",
            }

        return {
            "valid": True,
            "row_count": len(df),
        }

    @staticmethod
    def validate_devices_csv(df: pd.DataFrame) -> Dict[str, Any]:
        """Validate devices CSV structure and data."""
        required_columns = ["user_id"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return {
                "valid": False,
                "error": f"Missing required columns: {missing_columns}",
            }

        return {
            "valid": True,
            "row_count": len(df),
        }

    @staticmethod
    def validate_trades_csv(df: pd.DataFrame) -> Dict[str, Any]:
        """Validate trades CSV structure and data."""
        required_columns = ["trade_id", "user_id", "symbol", "side", "price", "quantity", "timestamp"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return {
                "valid": False,
                "error": f"Missing required columns: {missing_columns}",
            }

        # Validate side values
        valid_sides = {"BUY", "SELL"}
        invalid_sides = set(df["side"].unique()) - valid_sides
        if invalid_sides:
            return {
                "valid": False,
                "error": f"Invalid side values: {invalid_sides}",
            }

        return {
            "valid": True,
            "row_count": len(df),
        }

    @staticmethod
    def validate_withdrawals_csv(df: pd.DataFrame) -> Dict[str, Any]:
        """Validate withdrawals CSV structure and data."""
        required_columns = ["withdraw_id", "user_id", "asset", "amount", "address", "timestamp"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return {
                "valid": False,
                "error": f"Missing required columns: {missing_columns}",
            }

        return {
            "valid": True,
            "row_count": len(df),
        }
