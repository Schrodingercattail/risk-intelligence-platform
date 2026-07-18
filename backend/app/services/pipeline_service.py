"""
Pipeline Service

Orchestrates the end-to-end data pipeline:
CSV Upload -> Data Validation -> Feature Engineering -> ML Scoring -> Graph Analysis
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.feature_engineering import FeatureEngineeringService
from app.services.graph_service import GraphAnalysisService
from app.services.risk_service import RiskScoringService
from app.models.database import User, Device, Trade, Withdrawal


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

    async def get_pipeline_status(self) -> Dict[str, str]:
        """
        Get current pipeline status.

        Returns:
            Dict mapping step names to their status
        """
        # In a real implementation, this would query a pipeline_runs table
        # For now, return placeholder status
        # Check if we have imported data to determine data_sources status
        from sqlalchemy import select, func
        from app.models.models import User

        user_count = await self.db.scalar(select(func.count()).select_from(User))
        data_sources_status = PipelineStatus.COMPLETED.value if user_count > 0 else PipelineStatus.PENDING.value

        return {
            "data_sources": data_sources_status,
            "dataset_validation": PipelineStatus.PENDING.value,
            "feature_engineering": PipelineStatus.PENDING.value,
            "ml_scoring": PipelineStatus.PENDING.value,
            "graph_analysis": PipelineStatus.PENDING.value,
        }

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
    ) -> Dict[str, Any]:
        """
        Run the complete data pipeline.

        Args:
            run_full_pipeline: Whether to run all steps
            generate_risk_events: Whether to generate risk events

        Returns:
            Dict with pipeline results
        """
        results = {
            "started_at": datetime.now(timezone.utc),
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
                events_created = await risk_service.score_all_users()

                results["steps"]["ml_scoring"].update({
                    "status": PipelineStatus.COMPLETED.value,
                    "completed_at": datetime.now(timezone.utc),
                    "risk_events_created": events_created,
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
                user_id=row["user_id"],
                country=row.get("country"),
                kyc_level=row.get("kyc_level"),
                account_created_time=pd.to_datetime(row.get("account_created_time")).to_pydatetime()
                if row.get("account_created_time") else None,
                vip_level=row.get("vip_level"),
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
                user_id=row["user_id"],
                device_id=row.get("device_id"),
                ip_address=row.get("ip_address"),
                location=row.get("location"),
                browser_fingerprint=row.get("browser_fingerprint"),
                first_seen=pd.to_datetime(row.get("first_seen")).to_pydatetime()
                if row.get("first_seen") else None,
                last_seen=pd.to_datetime(row.get("last_seen")).to_pydatetime()
                if row.get("last_seen") else None,
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
                trade_id=row["trade_id"],
                user_id=row["user_id"],
                symbol=row["symbol"],
                side=row["side"],
                price=row["price"],
                quantity=row["quantity"],
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
            withdrawal = Withdrawal(
                withdraw_id=row["withdraw_id"],
                user_id=row["user_id"],
                asset=row["asset"],
                amount=row["amount"],
                address=row["address"],
                is_new_address=row.get("is_new_address"),
                timestamp=pd.to_datetime(row["timestamp"]).to_pydatetime(),
            )
            self.db.add(withdrawal)
            count += 1
        await self.db.flush()
        return count


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
