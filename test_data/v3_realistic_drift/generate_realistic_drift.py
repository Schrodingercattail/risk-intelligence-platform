"""
Realistic Drift Dataset Generator v3 for PSI Validation

Creates a synthetic dataset with realistic, gradual production data drift
to validate PSI monitoring with expected PSI values around 0.25-0.8.

Key Design Principles:
1. Sparse features (shared_device_count, linked_account_count) maintain similar zero-inflated shape
2. Monetary features have moderate shift only
3. Trading and withdrawal behavior shift gradually
4. Overall PSI around 0.25-0.8 with no single sparse feature dominating

Expected PSI Result: 0.25 - 0.8 (realistic drift)
"""
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import os


class RealisticDriftDatasetGenerator:
    """Generate dataset with realistic, moderate feature distribution drift."""

    def __init__(self, total_users: int = 2000):
        self.total_users = total_users

        # Trading symbols
        self.symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC"]
        self.sides = ["BUY", "SELL"]
        self.countries = ["US", "UK", "SG", "JP", "DE", "FR", "CA", "AU"]
        self.kyc_levels = ["NONE", "BASIC", "INTERMEDIATE", "FULL"]
        self.vip_levels = ["NORMAL", "SILVER", "GOLD", "PLATINUM"]
        self.assets = ["BTC", "ETH", "USDT"]

        # Random seed for reproducibility
        random.seed(20260724)

        # User ID counter
        self.user_id_counter = 6000
        self.trade_id_counter = 600000
        self.withdraw_id_counter = 600000

        # Shared device clusters (maintain similar ratio to baseline ~11%)
        self.shared_devices = [f"DEVSHARE{i:03d}" for i in range(25)]

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

    def generate_device_id(self) -> str:
        """Generate a device ID."""
        return f"DEV{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}"

    def generate_ip_address(self) -> str:
        """Generate a random IP address."""
        return f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"

    def generate_address(self) -> str:
        """Generate a withdrawal address."""
        return f"0x{''.join(random.choices(string.ascii_lowercase + string.digits, k=40))}"

    def _get_symbol_price(self, symbol: str) -> Decimal:
        """Get a base price for a symbol."""
        prices = {
            "BTC": Decimal("45000.00"),
            "ETH": Decimal("3000.00"),
            "SOL": Decimal("100.00"),
            "BNB": Decimal("300.00"),
            "XRP": Decimal("0.60"),
            "ADA": Decimal("0.50"),
            "DOGE": Decimal("0.08"),
            "MATIC": Decimal("0.90"),
        }
        base = prices.get(symbol, Decimal("100.00"))
        variation = Decimal(str(random.uniform(-0.05, 0.05)))
        return base * (Decimal("1") + variation)

    def create_slight_new_account_drift_user(self) -> dict:
        """
        Create user with slight account age drift.

        Pattern: Accounts 15-45 days (slightly younger than baseline 30-180)
        This creates moderate shift in account_age_days distribution.
        """
        user_id = self.generate_user_id()

        # DRIFT: Slightly younger accounts (15-45 days)
        account_created = datetime.now() - timedelta(days=random.randint(15, 45))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Slightly higher trading activity (20-35 vs baseline 15-35)
        trades = []
        num_trades = random.randint(20, 35)

        base_time = datetime.now() - timedelta(hours=random.randint(1, 12))

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.6, 2.2), 4)

            timestamp = base_time - timedelta(minutes=random.randint(0, 720))

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": timestamp,
            })

        # Normal withdrawal patterns (1-3 withdrawals)
        withdrawals = []
        num_withdrawals = random.randint(1, 3)

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(0.15, 1.2), 6)),
                "address": self.generate_address(),
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(1, 20)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choices(self.kyc_levels, weights=[0.45, 0.35, 0.15, 0.05])[0],
            "account_created_time": account_created,
            "vip_level": random.choices(self.vip_levels, weights=[0.88, 0.10, 0.018, 0.002])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "slight_new_account",
        }

    def create_moderate_activity_user(self) -> dict:
        """
        Create user with moderately increased trading activity.

        Pattern: 30-45 trades (moderate increase from baseline 15-35)
        This creates moderate shift in trade_frequency distributions.
        """
        user_id = self.generate_user_id()

        # Mix of account ages (slightly biased toward newer)
        account_created = datetime.now() - timedelta(days=random.randint(20, 100))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # DRIFT: Moderately increased trading frequency
        trades = []
        num_trades = random.randint(30, 45)

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            # Slightly larger quantities
            quantity = round(random.uniform(0.8, 2.8), 4)

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": datetime.now() - timedelta(days=random.randint(0, 14)),
            })

        # Slightly increased withdrawals (2-4 vs baseline 1-3)
        withdrawals = []
        num_withdrawals = random.randint(2, 4)

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                # Moderate increase in amounts
                "amount": str(round(random.uniform(0.25, 1.8), 6)),
                "address": self.generate_address(),
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(1, 25)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choice(self.kyc_levels),
            "account_created_time": account_created,
            "vip_level": random.choice(self.vip_levels),
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "moderate_activity",
        }

    def create_moderate_withdrawal_user(self) -> dict:
        """
        Create user with moderately increased withdrawal activity.

        Pattern: 4-7 withdrawals (moderate increase from baseline 1-3)
        This creates moderate shift in withdrawal distributions.
        """
        user_id = self.generate_user_id()

        account_created = datetime.now() - timedelta(days=random.randint(25, 120))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Normal to slightly increased trading
        trades = []
        num_trades = random.randint(18, 38)

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.5, 2.5), 4)

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": datetime.now() - timedelta(days=random.randint(0, 12)),
            })

        # DRIFT: Moderately increased withdrawal frequency
        withdrawals = []
        num_withdrawals = random.randint(4, 7)

        base_time = datetime.now() - timedelta(hours=random.randint(1, 12))

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                # Moderate increase in amounts (not extreme)
                "amount": str(round(random.uniform(0.4, 2.5), 6)),
                "address": self.generate_address(),
                "is_new_address": (i == 0),
                "timestamp": base_time - timedelta(minutes=random.randint(0, 360)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choice(self.kyc_levels),
            "account_created_time": account_created,
            "vip_level": random.choice(self.vip_levels),
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "moderate_withdrawal",
        }

    def create_sparse_feature_user(self) -> dict:
        """
        Create user with sparse feature patterns.

        IMPORTANT: Maintains similar zero-inflated shape to baseline.
        Baseline: ~89% zero for shared_device_count and linked_account_count
        Target: ~85-92% zero (similar shape, not extreme drift)
        """
        user_id = self.generate_user_id()

        account_created = datetime.now() - timedelta(days=random.randint(20, 110))

        # Sparse device sharing (~12-15% share, similar to baseline)
        if random.random() < 0.13:
            device_id = self.shared_devices[random.randint(0, len(self.shared_devices) - 1)]
        else:
            device_id = self.generate_device_id()

        device = {
            "user_id": user_id,
            "device_id": device_id,
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Normal trading activity
        trades = []
        num_trades = random.randint(16, 36)

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.5, 2.5), 4)

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": datetime.now() - timedelta(days=random.randint(0, 12)),
            })

        # Normal withdrawal patterns
        withdrawals = []
        num_withdrawals = random.randint(1, 3)

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(0.1, 1.2), 6)),
                "address": self.generate_address(),
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(1, 15)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choice(self.kyc_levels),
            "account_created_time": account_created,
            "vip_level": random.choice(self.vip_levels),
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "sparse_feature",
        }

    def create_baseline_like_user(self) -> dict:
        """Create user similar to baseline patterns."""
        user_id = self.generate_user_id()

        # Baseline-like account age (30-150 days)
        account_created = datetime.now() - timedelta(days=random.randint(30, 150))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Baseline trading activity (15-35 trades)
        trades = []
        num_trades = random.randint(15, 35)

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.5, 2.5), 4)

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": datetime.now() - timedelta(days=random.randint(0, 10)),
            })

        # Baseline withdrawals (1-3 withdrawals)
        withdrawals = []
        num_withdrawals = random.randint(1, 3)

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(0.1, 1), 6)),
                "address": self.generate_address(),
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(1, 15)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choice(self.kyc_levels),
            "account_created_time": account_created,
            "vip_level": random.choices(self.vip_levels, weights=[0.90, 0.08, 0.015, 0.005])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "baseline_like",
        }

    def generate_all(self) -> dict:
        """Generate all data with realistic drift patterns."""
        users = []
        devices = []
        trades = []
        withdrawals = []

        # Distribution designed for realistic, moderate drift (PSI 0.25-0.8)
        # 25% slight new account drift (account_age_days shift)
        # 25% moderate activity (trade_frequency shift)
        # 20% moderate withdrawal (withdrawal_frequency shift)
        # 13% sparse feature patterns (maintains similar zero-inflated shape)
        # 17% baseline-like (provides stability)

        for i in range(self.total_users):
            if i < int(self.total_users * 0.25):
                data = self.create_slight_new_account_drift_user()
            elif i < int(self.total_users * 0.50):
                data = self.create_moderate_activity_user()
            elif i < int(self.total_users * 0.70):
                data = self.create_moderate_withdrawal_user()
            elif i < int(self.total_users * 0.83):
                data = self.create_sparse_feature_user()
            else:
                data = self.create_baseline_like_user()

            users.append(data["user"])
            devices.append(data["device"])
            trades.extend(data["trades"])
            withdrawals.extend(data["withdrawals"])

        return {
            "users": pd.DataFrame(users),
            "devices": pd.DataFrame(devices),
            "trades": pd.DataFrame(trades),
            "withdrawals": pd.DataFrame(withdrawals),
        }


def main():
    """Generate the realistic drifted dataset."""
    print("=" * 70)
    print("GENERATING v3_realistic_drift DATASET")
    print("=" * 70)
    print()
    print("Design Goals:")
    print("  - Overall PSI: 0.25 - 0.8")
    print("  - Sparse features maintain similar zero-inflated shape")
    print("  - Monetary features have moderate shift only")
    print("  - Trading/withdrawal behavior shifts gradually")
    print()

    generator = RealisticDriftDatasetGenerator(total_users=2000)
    data = generator.generate_all()

    # Create output directory (current directory since script is in v3_realistic_drift/)
    output_dir = os.path.dirname(__file__)
    os.makedirs(output_dir, exist_ok=True)

    # Save CSV files
    data["users"].to_csv(os.path.join(output_dir, "users.csv"), index=False)
    data["devices"].to_csv(os.path.join(output_dir, "devices.csv"), index=False)
    data["trades"].to_csv(os.path.join(output_dir, "trades.csv"), index=False)
    data["withdrawals"].to_csv(os.path.join(output_dir, "withdrawals.csv"), index=False)

    print(f"\n{'='*70}")
    print("✓ v3_realistic_drift dataset generated successfully")
    print(f"{'='*70}")
    print()
    print(f"Dataset Statistics:")
    print(f"  Users: {len(data['users'])}")
    print(f"  Devices: {len(data['devices'])}")
    print(f"  Trades: {len(data['trades'])}")
    print(f"  Withdrawals: {len(data['withdrawals'])}")
    print()

    print(f"Realistic Drift Patterns:")
    print(f"  1. Account Age Drift: 25% accounts 15-45 days (moderate shift)")
    print(f"  2. Trading Drift: 25% users with 30-45 trades (moderate increase)")
    print(f"  3. Withdrawal Drift: 20% users with 4-7 withdrawals (moderate increase)")
    print(f"  4. Sparse Features: 13% with shared devices (maintains ~85-92% zero)")
    print(f"  5. Baseline-like: 17% (provides stability)")
    print()

    print(f"Expected PSI Result:")
    print(f"  - overall_status: 'drift'")
    print(f"  - max_psi: 0.25 - 0.8 (realistic drift)")
    print(f"  - No single sparse feature dominates PSI")
    print()

    print(f"Output Location: {output_dir}/")
    print()


if __name__ == "__main__":
    main()
