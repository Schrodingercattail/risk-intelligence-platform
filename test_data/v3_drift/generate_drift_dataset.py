"""
Drift Dataset Generator v3 for PSI Validation

Creates a synthetic dataset with realistic production data drift patterns
to validate PSI (Population Stability Index) monitoring.

Purpose: PSI compares current population feature distribution against
the original training baseline to detect drift over time.

Drift Patterns Introduced:
1. Account population drift - More newly created accounts
2. Transaction behavior drift - Higher frequency and volume
3. Withdrawal behavior drift - More frequent withdrawals
4. Device/network drift - Slightly more shared devices

Expected PSI Result: warning or drift (max_psi > 0.10)
"""
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import os


class DriftDatasetGenerator:
    """Generate dataset with realistic feature distribution drift."""

    def __init__(self, total_users: int = 2000):
        self.total_users = total_users

        # Trading symbols
        self.symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC"]
        self.sides = ["BUY", "SELL"]
        self.countries = ["US", "UK", "SG", "JP", "DE", "FR", "CA", "AU"]
        self.kyc_levels = ["NONE", "BASIC", "INTERMEDIATE", "FULL"]
        self.vip_levels = ["NORMAL", "SILVER", "GOLD", "PLATINUM"]
        self.assets = ["BTC", "ETH", "USDT"]

        # Random seed for reproducibility (different from v2)
        random.seed(20260721)

        # User ID counter (start after v2 to avoid conflicts)
        self.user_id_counter = 3000
        self.trade_id_counter = 300000
        self.withdraw_id_counter = 300000

        # Shared devices for drift (create some clusters)
        self.shared_devices = [f"DEVSHARE{i:03d}" for i in range(20)]
        self.shared_ips = [f"10.20.{i}.1" for i in range(20)]

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

    def create_new_account_drift_user(self) -> dict:
        """
        Create user with account age drift.

        Pattern: Very new account (< 7 days) - simulates influx of new users
        This will shift the account_age_days distribution significantly.
        """
        user_id = self.generate_user_id()

        # DRIFT: Very new accounts (majority < 7 days)
        account_created = datetime.now() - timedelta(days=random.randint(1, 6))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choices(self.kyc_levels, weights=[0.6, 0.3, 0.08, 0.02])[0],
            "account_created_time": account_created,
            "vip_level": "NORMAL",
        }

        return {
            "user": user,
            "device": device,
            "trades": [],
            "withdrawals": [],
            "type": "new_account_drift",
        }

    def create_high_frequency_trader(self) -> dict:
        """
        Create user with high trading frequency drift.

        Pattern: Increased trade frequency and volume in 24h/7d windows
        This will shift trade_frequency_24h and trade_frequency_7d distributions.
        """
        user_id = self.generate_user_id()

        # Mix of account ages (but biased toward newer)
        account_created = datetime.now() - timedelta(days=random.randint(5, 30))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # DRIFT: Very high trading frequency
        trades = []
        num_trades = random.randint(80, 150)  # Much higher than baseline

        base_time = datetime.now() - timedelta(hours=random.randint(1, 6))

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            # DRIFT: Larger trade sizes
            quantity = round(random.uniform(1, 8), 4)

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

        # Normal withdrawal patterns
        withdrawals = []
        num_withdrawals = random.randint(0, 3)

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(0.1, 1), 6)),
                "address": self.generate_address(),
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(5, 15)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choice(self.kyc_levels),
            "account_created_time": account_created,
            "vip_level": random.choices(self.vip_levels, weights=[0.85, 0.12, 0.025, 0.005])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "high_frequency_trader",
        }

    def create_high_volume_withdrawer(self) -> dict:
        """
        Create user with high withdrawal volume drift.

        Pattern: Increased withdrawal frequency and volume in 24h window
        This will shift withdrawal_frequency_24h and withdrawal_volume_24h distributions.
        """
        user_id = self.generate_user_id()

        account_created = datetime.now() - timedelta(days=random.randint(10, 60))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Normal trading
        trades = []
        num_trades = random.randint(10, 30)

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.5, 3), 4)

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": datetime.now() - timedelta(days=random.randint(0, 10)),
            })

        # DRIFT: High withdrawal frequency and volume
        withdrawals = []
        num_withdrawals = random.randint(8, 20)  # Higher frequency

        base_time = datetime.now() - timedelta(hours=random.randint(1, 6))

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                # DRIFT: Higher withdrawal amounts
                "amount": str(round(random.uniform(2, 10), 6)),
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
            "type": "high_volume_withdrawer",
        }

    def create_shared_device_user(self, cluster_index: int) -> dict:
        """
        Create user with shared device drift.

        Pattern: Slightly increased shared devices and linked accounts
        This will shift shared_device_count and linked_account_count distributions.
        """
        user_id = self.generate_user_id()

        account_created = datetime.now() - timedelta(days=random.randint(15, 90))

        # DRIFT: Shared device (increases graph-related features)
        device = {
            "user_id": user_id,
            "device_id": self.shared_devices[cluster_index % len(self.shared_devices)],
            "ip_address": self.shared_ips[cluster_index % len(self.shared_ips)],
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Normal trading and withdrawal patterns
        trades = []
        num_trades = random.randint(15, 35)

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.3, 2), 4)

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": datetime.now() - timedelta(days=random.randint(0, 14)),
            })

        withdrawals = []
        num_withdrawals = random.randint(2, 6)

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(0.5, 3), 6)),
                "address": self.generate_address(),
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(1, 20)),
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
            "type": "shared_device_drift",
        }

    def create_normal_user(self) -> dict:
        """Create normal user with moderate activity (baseline-like)."""
        user_id = self.generate_user_id()

        # Slightly biased toward newer accounts (drift pattern)
        account_created = datetime.now() - timedelta(days=random.randint(7, 120))

        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Moderate trading activity
        trades = []
        num_trades = random.randint(20, 50)  # Slightly higher than baseline

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.5, 3), 4)

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": datetime.now() - timedelta(days=random.randint(0, 10)),
            })

        withdrawals = []
        num_withdrawals = random.randint(2, 5)

        for i in range(num_withdrawals):
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(0.3, 2), 6)),
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
            "type": "normal",
        }

    def generate_all(self) -> dict:
        """Generate all data with drift patterns."""
        users = []
        devices = []
        trades = []
        withdrawals = []

        # Distribution designed to create feature distribution drift
        # 40% new accounts (drift: account_age_days)
        # 25% high frequency traders (drift: trade_frequency_24h, trade_frequency_7d, trade_volume_24h)
        # 20% high volume withdrawers (drift: withdrawal_frequency_24h, withdrawal_volume_24h)
        # 10% shared device users (drift: shared_device_count, linked_account_count)
        # 5% normal users

        for i in range(self.total_users):
            if i < int(self.total_users * 0.40):
                data = self.create_new_account_drift_user()
            elif i < int(self.total_users * 0.65):
                data = self.create_high_frequency_trader()
            elif i < int(self.total_users * 0.85):
                data = self.create_high_volume_withdrawer()
            elif i < int(self.total_users * 0.95):
                cluster_idx = i // 5  # 5 users per cluster
                data = self.create_shared_device_user(cluster_idx)
            else:
                data = self.create_normal_user()

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
    """Generate the drifted dataset."""
    print("Generating v3_drift dataset for PSI validation...")

    generator = DriftDatasetGenerator(total_users=2000)
    data = generator.generate_all()

    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), "v3_drift")
    os.makedirs(output_dir, exist_ok=True)

    # Save CSV files
    data["users"].to_csv(os.path.join(output_dir, "users.csv"), index=False)
    data["devices"].to_csv(os.path.join(output_dir, "devices.csv"), index=False)
    data["trades"].to_csv(os.path.join(output_dir, "trades.csv"), index=False)
    data["withdrawals"].to_csv(os.path.join(output_dir, "withdrawals.csv"), index=False)

    print(f"\n✓ v3_drift dataset generated successfully")
    print(f"\nDataset Statistics:")
    print(f"  Users: {len(data['users'])}")
    print(f"  Devices: {len(data['devices'])}")
    print(f"  Trades: {len(data['trades'])}")
    print(f"  Withdrawals: {len(data['withdrawals'])}")

    print(f"\nDrift Patterns Introduced:")
    print(f"  1. Account Age Drift: 40% accounts < 7 days old (vs baseline mixed distribution)")
    print(f"  2. Trading Drift: 25% high-frequency traders (80-150 trades)")
    print(f"  3. Withdrawal Drift: 20% high-volume withdrawers (8-20 withdrawals)")
    print(f"  4. Device Drift: 10% shared device users (increased graph features)")

    print(f"\nExpected PSI Result:")
    print(f"  - overall_status: 'warning' or 'drift'")
    print(f"  - max_psi: > 0.10")
    print(f"  - drift_features: account_age_days, trade_frequency_24h, withdrawal_frequency_24h, etc.")

    print(f"\nOutput Location: {output_dir}/")


if __name__ == "__main__":
    main()
