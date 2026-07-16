"""
Common Feature Engineering Module

This module provides shared feature calculation logic for both:
- Training (LightGBMTrainer)
- Online Inference (FeatureEngineeringService)

This ensures training-serving feature consistency and prevents feature drift.
"""
from typing import Dict, Any, List, Union, Set
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from decimal import Decimal


class FeatureCalculator:
    """
    Common feature calculation logic shared by training and serving.

    Time-based features use a reference_time:
    - Training: reference_time = max(timestamp) in training data
    - Serving: reference_time = datetime.now(timezone.utc)
    """

    def __init__(self, reference_time: datetime):
        """
        Initialize with reference time for time-based feature calculations.

        Args:
            reference_time: The reference time for calculating time windows
                          - Training: max timestamp in data
                          - Serving: current time (datetime.now(timezone.utc))
        """
        self.reference_time = reference_time

    def calculate_trading_features(
        self,
        trades: Union[pd.DataFrame, List[Any]]
    ) -> Dict[str, Any]:
        """
        Calculate trading behavior features.

        Args:
            trades: List of Trade objects (serving) or DataFrame (training)

        Returns:
            Dict with trading features
        """
        if trades is None or (isinstance(trades, pd.DataFrame) and trades.empty) or (isinstance(trades, list) and len(trades) == 0):
            return {
                "trade_frequency_24h": 0,
                "trade_frequency_7d": 0,
                "opposite_trade_ratio": 0.0,
                "avg_trade_size": 0.0,
                "trade_volume_24h": 0.0,
            }

        # Handle both DataFrame (training) and list of objects (serving)
        if isinstance(trades, pd.DataFrame):
            timestamps = pd.to_datetime(trades['timestamp'])
            # Ensure UTC timezone-aware
            if timestamps.dt.tz is None:
                timestamps = timestamps.dt.tz_localize('UTC')
            else:
                timestamps = timestamps.dt.tz_convert('UTC')
            prices = pd.to_numeric(trades['price'])
            quantities = pd.to_numeric(trades['quantity'])
            sides = trades['side'].tolist()
        else:
            # List of Trade objects from database
            timestamps = pd.to_datetime([t.timestamp for t in trades])
            prices = pd.to_numeric([t.price for t in trades])
            quantities = pd.to_numeric([t.quantity for t in trades])
            sides = [t.side for t in trades]

        # Calculate time deltas
        time_deltas = (self.reference_time - timestamps).dt.total_seconds()

        # Trade frequency in time windows
        trades_24h_mask = time_deltas <= 86400  # 24 hours
        trades_7d_mask = time_deltas <= 604800   # 7 days

        trade_frequency_24h = trades_24h_mask.sum()
        trade_frequency_7d = trades_7d_mask.sum()

        # Average trade size (all trades)
        trade_sizes = prices * quantities
        avg_trade_size = trade_sizes.mean() if len(trade_sizes) > 0 else 0

        # Trade volume in 24h
        volume_24h = trade_sizes[trades_24h_mask].sum() if trade_frequency_24h > 0 else 0

        # Opposite trade ratio (both BUY and SELL present)
        if len(sides) >= 2 and "BUY" in sides and "SELL" in sides:
            buy_count = sides.count("BUY")
            sell_count = sides.count("SELL")
            opposite_trade_ratio = min(buy_count, sell_count) / len(sides)
        else:
            opposite_trade_ratio = 0.0

        return {
            "trade_frequency_24h": int(trade_frequency_24h),
            "trade_frequency_7d": int(trade_frequency_7d),
            "opposite_trade_ratio": float(opposite_trade_ratio),
            "avg_trade_size": float(avg_trade_size),
            "trade_volume_24h": float(volume_24h),
        }

    def calculate_withdrawal_features(
        self,
        withdrawals: Union[pd.DataFrame, List[Any]]
    ) -> Dict[str, Any]:
        """
        Calculate withdrawal behavior features.

        Args:
            withdrawals: List of Withdrawal objects (serving) or DataFrame (training)

        Returns:
            Dict with withdrawal features
        """
        if withdrawals is None or (isinstance(withdrawals, pd.DataFrame) and withdrawals.empty) or (isinstance(withdrawals, list) and len(withdrawals) == 0):
            return {
                "withdrawal_risk_score": 0.0,
                "withdrawal_frequency_24h": 0,
                "withdrawal_volume_24h": 0.0,
                "first_withdrawal_flag": False,
            }

        # Handle both DataFrame (training) and list of objects (serving)
        if isinstance(withdrawals, pd.DataFrame):
            timestamps = pd.to_datetime(withdrawals['timestamp'])
            # Ensure UTC timezone-aware
            if timestamps.dt.tz is None:
                timestamps = timestamps.dt.tz_localize('UTC')
            else:
                timestamps = timestamps.dt.tz_convert('UTC')
            amounts = pd.to_numeric(withdrawals['amount'])
            is_new_address = withdrawals['is_new_address'].fillna(False).tolist()
        else:
            # List of Withdrawal objects from database
            timestamps = pd.to_datetime([w.timestamp for w in withdrawals])
            amounts = pd.to_numeric([w.amount for w in withdrawals])
            is_new_address = [w.is_new_address for w in withdrawals]

        # Calculate time deltas
        time_deltas = (self.reference_time - timestamps).dt.total_seconds()

        # Withdrawal frequency in 24h
        withdrawals_24h_mask = time_deltas <= 86400  # 24 hours
        withdrawal_frequency_24h = withdrawals_24h_mask.sum()

        # Withdrawal volume in 24h
        withdrawal_volume_24h = amounts[withdrawals_24h_mask].sum() if withdrawal_frequency_24h > 0 else 0

        # First withdrawal flag (any withdrawal to new address)
        first_withdrawal_flag = any(is_new_address) if is_new_address else False

        # Withdrawal risk score (ratio of withdrawals to new addresses)
        if len(is_new_address) > 0:
            new_address_ratio = sum(1 for x in is_new_address if x) / len(is_new_address)
            withdrawal_risk_score = float(new_address_ratio)
        else:
            withdrawal_risk_score = 0.0

        return {
            "withdrawal_risk_score": float(withdrawal_risk_score),
            "withdrawal_frequency_24h": int(withdrawal_frequency_24h),
            "withdrawal_volume_24h": float(withdrawal_volume_24h),
            "first_withdrawal_flag": first_withdrawal_flag,
        }

    def calculate_temporal_features(
        self,
        user: Union[pd.Series, Any],
        trades: Union[pd.DataFrame, List[Any]],
        withdrawals: Union[pd.DataFrame, List[Any]]
    ) -> Dict[str, Any]:
        """
        Calculate temporal features.

        Args:
            user: User data (Series for training, User object for serving)
            trades: Trade data
            withdrawals: Withdrawal data

        Returns:
            Dict with temporal features
        """
        # Account age in days
        account_age_days = 0
        if user is not None:
            if isinstance(user, pd.Series):
                created_time = user.get('account_created_time')
            else:
                created_time = user.account_created_time

            if created_time is not None and pd.notna(created_time):
                created_dt = pd.to_datetime(created_time)
                # Ensure UTC timezone-aware for comparison
                if hasattr(created_dt, 'tz') and created_dt.tz is None:
                    created_dt = created_dt.tz_localize('UTC')
                elif hasattr(created_dt, 'tz_convert'):
                    created_dt = created_dt.tz_convert('UTC')
                age_delta = self.reference_time - created_dt
                account_age_days = age_delta.days

        # Active days count
        active_days = set()

        if trades is not None and (isinstance(trades, pd.DataFrame) and not trades.empty or isinstance(trades, list) and len(trades) > 0):
            if isinstance(trades, pd.DataFrame):
                trade_dates = pd.to_datetime(trades['timestamp']).dt.date.unique()
            else:
                trade_dates = set(pd.to_datetime([t.timestamp for t in trades]).date)
            active_days.update(trade_dates)

        if withdrawals is not None and (isinstance(withdrawals, pd.DataFrame) and not withdrawals.empty or isinstance(withdrawals, list) and len(withdrawals) > 0):
            if isinstance(withdrawals, pd.DataFrame):
                withdrawal_dates = pd.to_datetime(withdrawals['timestamp']).dt.date.unique()
            else:
                withdrawal_dates = set(pd.to_datetime([w.timestamp for w in withdrawals]).date)
            active_days.update(withdrawal_dates)

        return {
            "account_age_days": account_age_days,
            "active_days_count": len(active_days),
        }

    def calculate_device_features(
        self,
        user_devices: Union[pd.DataFrame, List[Any]],
        all_devices: Union[pd.DataFrame, List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate device-based features.

        Args:
            user_devices: Devices for the specific user
            all_devices: All devices (needed for shared device calculation)

        Returns:
            Dict with device features
        """
        if user_devices is None or (isinstance(user_devices, pd.DataFrame) and user_devices.empty) or (isinstance(user_devices, list) and len(user_devices) == 0):
            return {
                "shared_device_count": 0,
                "linked_account_count": 0,
                "unique_ip_count": 0,
            }

        # Handle both DataFrame (training) and list of objects (serving)
        if isinstance(user_devices, pd.DataFrame):
            device_ids = user_devices['device_id'].tolist()
            ip_addresses = user_devices['ip_address'].tolist()
            user_id = user_devices.iloc[0]['user_id'] if len(user_devices) > 0 else None
        else:
            device_ids = [d.device_id for d in user_devices if d.device_id]
            ip_addresses = [d.ip_address for d in user_devices if d.ip_address]
            user_id = user_devices[0].user_id if len(user_devices) > 0 else None

        # Unique IP count
        unique_ip_count = len(set(ip_addresses)) if ip_addresses else 0

        # Shared device count
        shared_device_count = 0
        if all_devices is not None and len(all_devices) > 0 and device_ids:
            if isinstance(all_devices, pd.DataFrame):
                device_counts = all_devices['device_id'].value_counts()
                shared_device_count = sum(1 for dev_id in device_ids if device_counts.get(dev_id, 0) > 1)
            else:
                # Count devices used by multiple users
                from collections import Counter
                all_device_ids = [d.device_id for d in all_devices if d.device_id]
                device_counts = Counter(all_device_ids)
                shared_device_count = sum(1 for dev_id in device_ids if device_counts.get(dev_id, 0) > 1)

        # Linked account count (unique users sharing devices with this user)
        linked_account_count = 0
        if all_devices is not None and len(all_devices) > 0 and device_ids and user_id:
            # Collect unique other users who share any device with this user
            linked_users: Set[str] = set()

            if isinstance(all_devices, pd.DataFrame):
                # Build device-to-users mapping
                from collections import defaultdict
                device_to_users = defaultdict(set)
                for _, row in all_devices.iterrows():
                    if row['device_id'] and row['user_id']:
                        device_to_users[row['device_id']].add(row['user_id'])

                # Find users sharing devices with this user
                for dev_id in device_ids:
                    if dev_id in device_to_users:
                        other_users = device_to_users[dev_id] - {user_id}
                        linked_users.update(other_users)

                linked_account_count = len(linked_users)
            else:
                # For list of objects
                from collections import defaultdict
                device_to_users = defaultdict(set)
                for d in all_devices:
                    if d.device_id and d.user_id:
                        device_to_users[d.device_id].add(d.user_id)

                # Find users sharing devices with this user
                for dev_id in device_ids:
                    if dev_id in device_to_users:
                        other_users = device_to_users[dev_id] - {user_id}
                        linked_users.update(other_users)

                linked_account_count = len(linked_users)

        return {
            "shared_device_count": shared_device_count,
            "linked_account_count": linked_account_count,
            "unique_ip_count": unique_ip_count,
        }


def get_reference_time_from_data(
    trades_df: pd.DataFrame = None,
    withdrawals_df: pd.DataFrame = None
) -> datetime:
    """
    Calculate reference time from training data (max timestamp).

    For training, use max timestamp in data as reference time.
    For serving, use datetime.now(timezone.utc).

    Args:
        trades_df: Trading data DataFrame
        withdrawals_df: Withdrawal data DataFrame

    Returns:
        Reference time for feature calculation
    """
    max_timestamp = None

    if trades_df is not None and len(trades_df) > 0:
        trade_max = pd.to_datetime(trades_df['timestamp']).max()
        # Ensure timezone-aware UTC
        if trade_max.tzinfo is None:
            trade_max = trade_max.tz_localize('UTC')
        else:
            trade_max = trade_max.tz_convert('UTC')
        max_timestamp = trade_max if max_timestamp is None else max(max_timestamp, trade_max)

    if withdrawals_df is not None and len(withdrawals_df) > 0:
        withdrawal_max = pd.to_datetime(withdrawals_df['timestamp']).max()
        # Ensure timezone-aware UTC
        if withdrawal_max.tzinfo is None:
            withdrawal_max = withdrawal_max.tz_localize('UTC')
        else:
            withdrawal_max = withdrawal_max.tz_convert('UTC')
        max_timestamp = withdrawal_max if max_timestamp is None else max(max_timestamp, withdrawal_max)

    if max_timestamp is None:
        # Fallback to current time in UTC
        max_timestamp = datetime.now(timezone.utc)

    return max_timestamp
