"""
Feature Engineering Service

Transforms raw data into ML features for risk scoring.
Service Layer - Independent of API, can be tested and run standalone.
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal

from app.models.database import (
    User, Device, Trade, Withdrawal, FeatureTable,
)


class FeatureEngineeringService:
    """
    Feature Engineering Service

    Input: Raw database data (users, devices, trades, withdrawals)
    Output: Feature table with engineered features

    Features are organized into categories:
    - Device & Network Features
    - Trading Features
    - Temporal Features
    - Withdrawal Features
    - Cluster Features

    IMPORTANT: This service uses the same feature calculation logic as training
    to ensure training-serving consistency. The reference_time is derived from
    the data itself (max timestamp) rather than datetime.now().
    """

    def __init__(self, db: AsyncSession):
        """Initialize feature engineering service."""
        self.db = db
        self._reference_time = None

    async def _get_reference_time(self) -> datetime:
        """
        Get reference time from database data.

        Uses max timestamp from trades and withdrawals, just like training flow.
        This ensures PSI calculations compare equivalent populations.

        Returns:
            Reference time for feature calculation
        """
        if self._reference_time is not None:
            return self._reference_time

        # Get max timestamp from trades
        max_trade_time = await self.db.scalar(select(func.max(Trade.timestamp)))

        # Get max timestamp from withdrawals
        max_withdrawal_time = await self.db.scalar(select(func.max(Withdrawal.timestamp)))

        # Use the later of the two
        if max_trade_time and max_withdrawal_time:
            self._reference_time = max(max_trade_time, max_withdrawal_time)
        elif max_trade_time:
            self._reference_time = max_trade_time
        elif max_withdrawal_time:
            self._reference_time = max_withdrawal_time
        else:
            # Fallback to current time if no data
            self._reference_time = datetime.now(timezone.utc)

        # Strip timezone for consistency with training flow
        if self._reference_time.tzinfo is not None:
            self._reference_time = self._reference_time.replace(tzinfo=None)

        return self._reference_time

    async def generate_features_for_all_users(self) -> int:
        """
        Generate features for all users in the database.

        Returns:
            Number of users processed
        """
        # Get reference time from data (not datetime.now!)
        reference_time = await self._get_reference_time()

        # Get all users
        result = await self.db.execute(select(User.user_id))
        user_ids = [row[0] for row in result]

        count = 0
        for user_id in user_ids:
            await self.generate_features_for_user(user_id, reference_time)
            count += 1

        return count

    async def generate_features_for_user(
        self,
        user_id: str,
        reference_time: datetime = None
    ) -> FeatureTable:
        """
        Generate features for a single user.

        Args:
            user_id: User ID to generate features for
            reference_time: Reference time for time-based features (optional, uses data max if None)

        Returns:
            FeatureTable record with all features
        """
        # Get user data
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get reference time if not provided
        if reference_time is None:
            reference_time = await self._get_reference_time()
        elif reference_time.tzinfo is not None:
            # Strip timezone for consistency
            reference_time = reference_time.replace(tzinfo=None)

        # Calculate features
        features = await self._calculate_all_features(user_id, reference_time)

        # Create or update feature record
        feature_record = await self.db.get(FeatureTable, user_id)
        if feature_record:
            # Update existing record
            for key, value in features.items():
                setattr(feature_record, key, value)
            feature_record.feature_calculated_at = datetime.now(timezone.utc)
        else:
            # Create new record
            feature_record = FeatureTable(user_id=user_id, **features)
            feature_record.feature_calculated_at = datetime.now(timezone.utc)
            self.db.add(feature_record)

        await self.db.commit()
        await self.db.refresh(feature_record)

        return feature_record

    async def _calculate_all_features(
        self,
        user_id: str,
        reference_time: datetime
    ) -> Dict[str, Any]:
        """
        Calculate all features for a user.

        Args:
            user_id: User ID
            reference_time: Reference time for time-based features

        Returns:
            Dictionary of feature names to values
        """
        # Gather all relevant data
        devices = await self._get_user_devices(user_id)
        trades = await self._get_user_trades(user_id)
        withdrawals = await self._get_user_withdrawals(user_id)
        user = await self.db.get(User, user_id)

        features = {}

        # Device & Network Features (time-independent)
        features.update(await self._device_features(user_id, devices, trades))

        # Trading Features (uses reference_time for windows)
        features.update(await self._trading_features(user_id, trades, reference_time))

        # Temporal Features (uses reference_time for age calculation)
        features.update(await self._temporal_features(user, trades, withdrawals, reference_time))

        # Withdrawal Features (uses reference_time for windows)
        features.update(await self._withdrawal_features(withdrawals, reference_time))

        # Cluster features (placeholder - will be populated by graph analysis)
        features["cluster_size"] = None
        features["cluster_risk_score"] = None

        return features

    async def _device_features(
        self,
        user_id: str,
        devices: List[Device],
        trades: List[Trade]
    ) -> Dict[str, Any]:
        """Calculate device and network features."""
        # Shared device count
        shared_device_count = await self._count_shared_devices(devices)

        # Linked account count (accounts sharing device)
        linked_account_count = await self._count_linked_accounts(user_id, devices)

        # Unique IP count
        unique_ip_count = len(set(d.ip_address for d in devices if d.ip_address))

        return {
            "shared_device_count": shared_device_count,
            "linked_account_count": linked_account_count,
            "unique_ip_count": unique_ip_count,
        }

    async def _trading_features(
        self,
        user_id: str,
        trades: List[Trade],
        reference_time: datetime
    ) -> Dict[str, Any]:
        """
        Calculate trading behavior features.

        Args:
            user_id: User ID
            trades: List of Trade objects
            reference_time: Reference time for time window calculations

        Returns:
            Dict with trading features
        """
        if not trades:
            return {
                "trade_frequency_24h": 0,
                "trade_frequency_7d": 0,
                "opposite_trade_ratio": Decimal("0"),
                "avg_trade_size": Decimal("0"),
                "trade_volume_24h": Decimal("0"),
            }

        # Trade frequency using reference_time
        trades_24h = [
            t for t in trades
            if (reference_time - t.timestamp.replace(tzinfo=None)).total_seconds() <= 86400
        ]
        trades_7d = [
            t for t in trades
            if (reference_time - t.timestamp.replace(tzinfo=None)).total_seconds() <= 604800
        ]

        # Average trade size (all trades, not time-windowed)
        trade_sizes = [float(t.price) * float(t.quantity) for t in trades]
        avg_trade_size = sum(trade_sizes) / len(trade_sizes) if trade_sizes else 0

        # Trade volume 24h
        volume_24h = sum(
            float(t.price) * float(t.quantity)
            for t in trades_24h
        )

        # Opposite trade ratio (simplified - checks for both BUY and SELL)
        sides = [t.side for t in trades]
        if len(sides) >= 2 and "BUY" in sides and "SELL" in sides:
            buy_count = sides.count("BUY")
            sell_count = sides.count("SELL")
            opposite_trade_ratio = Decimal(str(min(buy_count, sell_count) / len(sides)))
        else:
            opposite_trade_ratio = Decimal("0")

        return {
            "trade_frequency_24h": len(trades_24h),
            "trade_frequency_7d": len(trades_7d),
            "opposite_trade_ratio": opposite_trade_ratio,
            "avg_trade_size": Decimal(str(avg_trade_size)),
            "trade_volume_24h": Decimal(str(volume_24h)),
        }

    async def _temporal_features(
        self,
        user: User,
        trades: List[Trade],
        withdrawals: List[Withdrawal],
        reference_time: datetime
    ) -> Dict[str, Any]:
        """
        Calculate temporal features.

        Args:
            user: User object
            trades: List of Trade objects
            withdrawals: List of Withdrawal objects
            reference_time: Reference time for age calculation

        Returns:
            Dict with temporal features
        """
        # Account age using reference_time
        account_age_days = 0
        if user.account_created_time:
            account_age_days = (reference_time - user.account_created_time.replace(tzinfo=None)).days

        # Active days count (time-independent, just counts unique dates)
        active_days = set()
        for t in trades:
            active_days.add(t.timestamp.replace(tzinfo=None).date())
        for w in withdrawals:
            active_days.add(w.timestamp.replace(tzinfo=None).date())

        return {
            "account_age_days": account_age_days,
            "active_days_count": len(active_days),
        }

    async def _withdrawal_features(
        self,
        withdrawals: List[Withdrawal],
        reference_time: datetime
    ) -> Dict[str, Any]:
        """
        Calculate withdrawal behavior features.

        Args:
            withdrawals: List of Withdrawal objects
            reference_time: Reference time for time window calculations

        Returns:
            Dict with withdrawal features
        """
        if not withdrawals:
            return {
                "withdrawal_risk_score": Decimal("0"),
                "withdrawal_frequency_24h": 0,
                "withdrawal_volume_24h": Decimal("0"),
                "first_withdrawal_flag": False,
            }

        # Withdrawal frequency using reference_time
        withdrawals_24h = [
            w for w in withdrawals
            if (reference_time - w.timestamp.replace(tzinfo=None)).total_seconds() <= 86400
        ]

        # First withdrawal flag (is any withdrawal to new address?)
        first_withdrawal_flag = any(w.is_new_address for w in withdrawals if w.is_new_address)

        # Withdrawal risk score (simple heuristic)
        # High if: new addresses + high frequency + large amounts
        new_address_ratio = sum(1 for w in withdrawals if w.is_new_address) / len(withdrawals)
        withdrawal_risk_score = Decimal(str(new_address_ratio))

        # Withdrawal volume in 24h
        volume_24h = sum(float(w.amount) for w in withdrawals_24h)

        return {
            "withdrawal_risk_score": withdrawal_risk_score,
            "withdrawal_frequency_24h": len(withdrawals_24h),
            "withdrawal_volume_24h": Decimal(str(volume_24h)),
            "first_withdrawal_flag": first_withdrawal_flag,
        }

    # Helper methods
    async def _get_user_devices(self, user_id: str) -> List[Device]:
        """Get all devices for a user."""
        result = await self.db.execute(
            select(Device).where(Device.user_id == user_id)
        )
        return list(result.scalars().all())

    async def _get_user_trades(self, user_id: str) -> List[Trade]:
        """Get all trades for a user."""
        result = await self.db.execute(
            select(Trade).where(Trade.user_id == user_id)
        )
        return list(result.scalars().all())

    async def _get_user_withdrawals(self, user_id: str) -> List[Withdrawal]:
        """Get all withdrawals for a user."""
        result = await self.db.execute(
            select(Withdrawal).where(Withdrawal.user_id == user_id)
        )
        return list(result.scalars().all())

    async def _count_shared_devices(self, devices: List[Device]) -> int:
        """Count devices shared with other users."""
        if not devices:
            return 0

        device_ids = [d.device_id for d in devices if d.device_id]
        if not device_ids:
            return 0

        # Count how many of these devices are used by other users
        shared_count = 0
        for device_id in device_ids:
            result = await self.db.execute(
                select(func.count(Device.user_id))
                .where(Device.device_id == device_id)
            )
            user_count = result.scalar() or 0
            if user_count > 1:
                shared_count += 1

        return shared_count

    async def _count_linked_accounts(
        self,
        user_id: str,
        devices: List[Device]
    ) -> int:
        """Count total linked accounts through shared devices."""
        if not devices:
            return 0

        device_ids = [d.device_id for d in devices if d.device_id]
        if not device_ids:
            return 0

        # Get all unique users sharing any device
        result = await self.db.execute(
            select(func.count(func.distinct(Device.user_id)))
            .where(Device.device_id.in_(device_ids))
            .where(Device.user_id != user_id)
        )
        return result.scalar() or 0


class FeatureValidationService:
    """Validates feature data for quality and completeness."""

    @staticmethod
    def validate_features(features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate calculated features.

        Returns:
            Dict with validation results
        """
        issues = []

        # Check for None values in critical features
        critical_features = [
            "shared_device_count",
            "trade_frequency_24h",
            "account_age_days",
        ]

        for feature in critical_features:
            if features.get(feature) is None:
                issues.append(f"{feature} is None")

        # Check for negative values where invalid
        numeric_features = [
            "shared_device_count",
            "linked_account_count",
            "trade_frequency_24h",
            "account_age_days",
        ]

        for feature in numeric_features:
            value = features.get(feature)
            if value is not None and value < 0:
                issues.append(f"{feature} is negative: {value}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }
