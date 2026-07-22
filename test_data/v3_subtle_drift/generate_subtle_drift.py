"""
Subtle Drift Dataset Generator v3 for PSI Validation

Creates a synthetic dataset with **very subtle, realistic production data drift**
to validate PSI monitoring with expected PSI values in the range of 0.25-1.0.

This dataset is designed to be 85-90% similar to baseline with only minor shifts.
"""
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import os


class SubtleDriftDatasetGenerator:
    """Generate dataset with very subtle, realistic feature distribution drift."""

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
        random.seed(20260723)

        # User ID counter
        self.user_id_counter = 5000
        self.trade_id_counter = 500000
        self.withdraw_id_counter = 500000

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

    def create_baseline_like_user(self) -> dict:
        """
        Create user that matches baseline distribution (90% of users).

        Very similar to v2_diverse baseline patterns.
        """
        user_id = self.generate_user_id()

        # Account age similar to baseline (30-120 days)
        account_created = datetime.now() - timedelta(days=random.randint(30, 120))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Baseline-like trading (15-35 trades)
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

        # Baseline-like withdrawals (1-3 withdrawals)
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
            "vip_level": random.choices(self.vip_levels, weights=[0.9, 0.08, 0.015, 0.005])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "baseline_like",
        }

    def create_subtle_drift_user(self) -> dict:
        """
        Create user with very subtle drift (10% of users).

        Minimal changes: slightly higher activity, slightly newer accounts.
        """
        user_id = self.generate_user_id()

        # DRIFT: Slightly newer accounts (20-50 days vs 30-120)
        account_created = datetime.now() - timedelta(days=random.randint(20, 50))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # DRIFT: Slightly higher trading (20-40 vs 15-35)
        trades = []
        num_trades = random.randint(20, 40)

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            # DRIFT: Slightly larger quantities (0.8-3 vs 0.5-2.5)
            quantity = round(random.uniform(0.8, 3), 4)

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": datetime.now() - timedelta(days=random.randint(0, 10)),
            })

        # DRIFT: Slightly more withdrawals (2-4 vs 1-3)
        withdrawals = []
        num_withdrawals = random.randint(2, 4)

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                # DRIFT: Slightly higher amounts (0.2-1.5 vs 0.1-1)
                "amount": str(round(random.uniform(0.2, 1.5), 6)),
                "address": self.generate_address(),
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(1, 15)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choice(self.kyc_levels),
            "account_created_time": account_created,
            "vip_level": random.choices(self.vip_levels, weights=[0.92, 0.07, 0.008, 0.002])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "subtle_drift",
        }

    def generate_all(self) -> dict:
        """Generate all data with very subtle drift patterns."""
        users = []
        devices = []
        trades = []
        withdrawals = []

        # 90% baseline-like, 10% subtle drift
        # This should produce PSI in the 0.25-1.0 range
        for i in range(self.total_users):
            if i < int(self.total_users * 0.90):
                data = self.create_baseline_like_user()
            else:
                data = self.create_subtle_drift_user()

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
    """Generate the subtle drift dataset."""
    print("Generating v3_subtle_drift dataset for PSI validation...")

    generator = SubtleDriftDatasetGenerator(total_users=2000)
    data = generator.generate_all()

    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), "v3_subtle_drift")
    os.makedirs(output_dir, exist_ok=True)

    # Save CSV files
    data["users"].to_csv(os.path.join(output_dir, "users.csv"), index=False)
    data["devices"].to_csv(os.path.join(output_dir, "devices.csv"), index=False)
    data["trades"].to_csv(os.path.join(output_dir, "trades.csv"), index=False)
    data["withdrawals"].to_csv(os.path.join(output_dir, "withdrawals.csv"), index=False)

    print(f"\n✓ v3_subtle_drift dataset generated successfully")
    print(f"\nDataset Statistics:")
    print(f"  Users: {len(data['users'])}")
    print(f"  Devices: {len(data['devices'])}")
    print(f"  Trades: {len(data['trades'])}")
    print(f"  Withdrawals: {len(data['withdrawals'])}")

    print(f"\nSubtle Drift Patterns:")
    print(f"  90% baseline-like users (similar to v2_diverse)")
    print(f"  10% subtle drift users (minimal changes)")

    print(f"\nExpected PSI Result:")
    print(f"  - max_psi: 0.25 - 0.80 (realistic drift)")

    print(f"\nOutput Location: {output_dir}/")


if __name__ == "__main__":
    main()
