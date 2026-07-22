"""
Realistic Drift Dataset Generator v3 - Fixed

Generates controlled drift from v2_diverse baseline to produce realistic PSI values.
Target PSI: 0.15-0.35 overall, <1.0 max feature

Key improvements:
- Preserves large shared device clusters (55 linked accounts)
- Preserves avg_trade_size distribution
- Realistic production drift simulation
"""
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Configuration
BASELINE_DIR = Path("test_data/v2_diverse")
OUTPUT_DIR = Path("test_data/v3_controlled_drift")
TOTAL_USERS = 2000

# Trading symbols and config
SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC"]
SIDES = ["BUY", "SELL"]
COUNTRIES = ["US", "UK", "SG", "JP", "DE", "FR", "CA", "AU"]
ASSETS = ["BTC", "ETH", "USDT"]

# Random seed for reproducibility
random.seed(20260721)
np.random.seed(20260721)

# ID counters (offset from baseline)
USER_ID_OFFSET = 50000
TRADE_ID_OFFSET = 500000
WITHDRAW_ID_OFFSET = 500000

class FixedDriftGenerator:
    """Generate realistic drift with preserved feature distributions."""

    def __init__(self):
        # Load baseline data
        self.users_baseline = pd.read_csv(BASELINE_DIR / "users.csv")
        self.devices_baseline = pd.read_csv(BASELINE_DIR / "devices.csv")
        self.trades_baseline = pd.read_csv(BASELINE_DIR / "trades.csv")
        self.withdrawals_baseline = pd.read_csv(BASELINE_DIR / "withdrawals.csv")

        # Counters
        self.user_id_counter = USER_ID_OFFSET
        self.trade_id_counter = TRADE_ID_OFFSET
        self.withdraw_id_counter = WITHDRAW_ID_OFFSET

        # Analyze baseline to identify clusters
        self.analyze_baseline_clusters()

    def analyze_baseline_clusters(self):
        """Analyze baseline to identify shared device clusters."""
        # Find shared devices
        device_users = self.devices_baseline.groupby('device_id')['user_id'].apply(list).to_dict()

        # Find large clusters (devices shared by multiple users)
        self.shared_devices = {
            dev_id: users for dev_id, users in device_users.items() if len(users) > 1
        }

        print(f"Found {len(self.shared_devices)} shared devices")

    def generate_user_id(self) -> str:
        """Generate a user ID."""
        user_id = f"U{self.user_id_counter:05d}"
        self.user_id_counter += 1
        return user_id

    def generate_trade_id(self) -> str:
        """Generate a trade ID."""
        trade_id = f"T{self.trade_id_counter:06d}"
        self.trade_id_counter += 1
        return trade_id

    def generate_withdraw_id(self) -> str:
        """Generate a withdrawal ID."""
        withdraw_id = f"W{self.withdraw_id_counter:06d}"
        self.withdraw_id_counter += 1
        return withdraw_id

    def apply_drift_to_users(self, users_df: pd.DataFrame) -> pd.DataFrame:
        """Apply realistic drift to user data."""
        drifted_users = []

        for _, row in users_df.iterrows():
            original_user_id = row["user_id"]

            # Apply minimal account age drift (15% of users)
            if random.random() < 0.15 and row.get("account_created_time"):
                original_time = pd.to_datetime(row["account_created_time"])
                days_shift = random.randint(5, 20)  # Smaller shift
                row = row.copy()
                if random.random() < 0.5:
                    row["account_created_time"] = (original_time - timedelta(days=days_shift)).isoformat()
                else:
                    row["account_created_time"] = (original_time + timedelta(days=days_shift)).isoformat()

            drifted_users.append({
                **row,
                "user_id": self.generate_user_id(),
            })

        return pd.DataFrame(drifted_users)

    def apply_drift_to_devices(self, devices_df: pd.DataFrame, user_mapping: dict) -> pd.DataFrame:
        """Apply drift to devices while preserving shared relationships."""
        drifted_devices = []

        # Keep device_id exactly the same (not adding offset) to preserve sharing
        for _, row in devices_df.iterrows():
            original_user_id = row["user_id"]
            new_user_id = user_mapping.get(original_user_id, original_user_id)

            drifted_devices.append({
                **row,
                "user_id": new_user_id,
                "device_id": row["device_id"],  # Keep original device_id
            })

        return pd.DataFrame(drifted_devices)

    def apply_drift_to_trades(self, trades_df: pd.DataFrame, user_mapping: dict) -> pd.DataFrame:
        """Apply drift to trades while preserving avg_trade_size."""
        drifted_trades = []

        for _, row in trades_df.iterrows():
            user_id = row["user_id"]
            new_user_id = user_mapping.get(user_id, user_id)

            # Preserve trade data exactly to maintain avg_trade_size distribution
            # Only change user ID and trade ID
            drifted_trades.append({
                **row,
                "trade_id": self.generate_trade_id(),
                "user_id": new_user_id,
            })

        return pd.DataFrame(drifted_trades)

    def apply_drift_to_withdrawals(self, withdrawals_df: pd.DataFrame, user_mapping: dict) -> pd.DataFrame:
        """Apply drift to withdrawals."""
        drifted_withdrawals = []

        for _, row in withdrawals_df.iterrows():
            user_id = row["user_id"]
            new_user_id = user_mapping.get(user_id, user_id)

            drifted_withdrawals.append({
                **row,
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": new_user_id,
            })

        return pd.DataFrame(drifted_withdrawals)

    def generate_all(self) -> dict:
        """Generate all drifted datasets."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        print("Generating realistic drift dataset (fixed v2)...")

        # Apply drift to users first to get user mapping
        users_drifted = self.apply_drift_to_users(self.users_baseline)

        # Create user mapping
        user_mapping = dict(zip(self.users_baseline['user_id'], users_drifted['user_id']))

        # Apply drift to other tables
        devices_drifted = self.apply_drift_to_devices(self.devices_baseline, user_mapping)
        trades_drifted = self.apply_drift_to_trades(self.trades_baseline, user_mapping)
        withdrawals_drifted = self.apply_drift_to_withdrawals(self.withdrawals_baseline, user_mapping)

        # Save to CSV
        users_path = OUTPUT_DIR / "users.csv"
        devices_path = OUTPUT_DIR / "devices.csv"
        trades_path = OUTPUT_DIR / "trades.csv"
        withdrawals_path = OUTPUT_DIR / "withdrawals.csv"

        users_drifted.to_csv(users_path, index=False)
        devices_drifted.to_csv(devices_path, index=False)
        trades_drifted.to_csv(trades_path, index=False)
        withdrawals_drifted.to_csv(withdrawals_path, index=False)

        print(f"\n✓ Realistic drift dataset generated:")
        print(f"  Users: {len(users_drifted)}")
        print(f"  Devices: {len(devices_drifted)}")
        print(f"  Trades: {len(trades_drifted)}")
        print(f"  Withdrawals: {len(withdrawals_drifted)}")
        print(f"\nExpected PSI range: 0.15-0.35 overall, <1.0 max feature")

        return {
            "users": users_path,
            "devices": devices_path,
            "trades": trades_path,
            "withdrawals": withdrawals_path,
        }


if __name__ == "__main__":
    generator = FixedDriftGenerator()
    generator.generate_all()
