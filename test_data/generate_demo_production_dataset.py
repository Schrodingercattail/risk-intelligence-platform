"""
Demo Production Dataset Generator v4

Creates a polished demonstration dataset for the Risk Intelligence Platform.
Designed for product demonstration, NOT PSI stress testing.

Key Design Goals:
1. Realistic production environment simulation
2. Meaningful High/Critical risk cases for investigation
3. Stable PSI (0.05-0.20) - healthy monitoring state
4. Professional fraud patterns with clear explanations
5. Proper network clusters for graph analysis

Dataset Size:
- users.csv: 2000 users
- devices.csv: 2000 devices
- trades.csv: 70k-100k records
- withdrawals.csv: 7k-10k records

Risk Distribution:
- Low (60%): 1200 users, scores 10-40
- Medium (25%): 500 users, scores 40-70
- High (11%): 220 users, scores 70-90
- Critical (4%): 80 users, scores 90-100

Fraud Patterns:
1. Account Takeover / Fraud Rings
   - Young accounts, shared devices, linked accounts
   - Multiple IPs, suspicious withdrawals

2. Trading Manipulation
   - High trade frequency, high opposite trade ratio
   - Unusual activity patterns

3. Withdrawal Risk
   - Abnormal withdrawal frequency and volume
   - High withdrawal risk score
"""
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import os
from typing import Dict, List, Any


class DemoProductionDatasetGenerator:
    """Generate realistic demo production dataset."""

    def __init__(self, total_users: int = 2000):
        self.total_users = total_users

        # Trading symbols (diverse portfolio)
        self.symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC", "DOT", "AVAX"]
        self.sides = ["BUY", "SELL"]
        self.countries = ["US", "UK", "SG", "JP", "DE", "FR", "CA", "AU", "IT", "ES", "NL", "CH"]
        self.kyc_levels = ["NONE", "BASIC", "INTERMEDIATE", "FULL"]
        self.vip_levels = ["NORMAL", "SILVER", "GOLD", "PLATINUM"]
        self.assets = ["BTC", "ETH", "USDT", "USDC"]

        # Random seed for reproducibility
        random.seed(20260721)

        # User ID counter
        self.user_id_counter = 1
        self.trade_id_counter = 1
        self.withdraw_id_counter = 1

        # Track fraud ring clusters
        self.fraud_rings = {}
        self.ring_counter = 1

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
        """Generate a realistic IP address."""
        return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    def generate_address(self, asset: str) -> str:
        """Generate a withdrawal address based on asset."""
        if asset in ["USDT", "USDC"]:
            # ERC20 address
            return f"0x{''.join(random.choices(string.ascii_lowercase + string.digits, k=40))}"
        else:
            # Native address (simplified)
            return f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=40))}"

    def _get_symbol_price(self, symbol: str) -> Decimal:
        """Get a realistic base price for a symbol (2025)."""
        prices = {
            "BTC": Decimal("65000.00"),
            "ETH": Decimal("3500.00"),
            "SOL": Decimal("145.00"),
            "BNB": Decimal("590.00"),
            "XRP": Decimal("0.62"),
            "ADA": Decimal("0.45"),
            "DOGE": Decimal("0.12"),
            "MATIC": Decimal("0.58"),
            "DOT": Decimal("7.20"),
            "AVAX": Decimal("35.00"),
        }
        base = prices.get(symbol, Decimal("100.00"))
        variation = Decimal(str(random.uniform(-0.02, 0.02)))
        return base * (Decimal("1") + variation)

    def _create_fraud_ring(self, size: int) -> Dict[str, Any]:
        """Create a fraud ring cluster.

        A fraud ring consists of:
        - Shared device(s)
        - Cluster of linked accounts
        - Suspicious IP patterns
        """
        ring_id = f"RING{self.ring_counter:03d}"
        self.ring_counter += 1

        # Create shared devices (fraud rings often share multiple devices)
        shared_devices = [self.generate_device_id() for _ in range(random.randint(1, 2))]

        # Create IP cluster (similar IPs = same region/proxy)
        base_ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        ips = [f"{base_ip}.{random.randint(1, 254)}" for _ in range(size)]

        ring = {
            "ring_id": ring_id,
            "shared_devices": shared_devices,
            "ips": ips,
            "members": [],
        }

        self.fraud_rings[ring_id] = ring
        return ring

    def create_fraud_ring_user(self, ring: Dict[str, Any,], member_index: int, ring_size: int) -> dict:
        """
        Create a fraud ring member.

        Pattern: Account takeover / fraud ring
        - Young accounts (5-30 days old)
        - Shared devices with ring members
        - Multiple IPs (proxy rotation)
        - Suspicious withdrawal patterns
        - High ML score (trade frequency), High rule score (new account), High graph score (cluster)

        Risk Level: CRITICAL (90-100)
        """
        user_id = self.generate_user_id()

        # Young account (fraud rings typically use new accounts)
        account_created = datetime.now() - timedelta(days=random.randint(5, 30))

        # Assign shared device and IP from ring
        device_id = ring["shared_devices"][member_index % len(ring["shared_devices"])]
        ip_address = ring["ips"][member_index]

        device = {
            "user_id": user_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 6)),
        }

        # High frequency trading (ML trigger)
        trades = []
        num_trades = random.randint(60, 90)  # High frequency for ML detection

        # Concentrate in recent 24h window
        base_time = datetime.now() - timedelta(hours=random.randint(1, 12))

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            # Mix of BUY and SELL for realistic pattern
            side = "BUY" if i % 3 == 0 else "SELL"
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.05, 2), 4)

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

        # Suspicious withdrawal pattern
        withdrawals = []
        num_withdrawals = random.randint(5, 10)

        base_withdraw_time = datetime.now() - timedelta(hours=random.randint(1, 12))

        for i in range(num_withdrawals):
            asset = random.choice(self.assets)
            address = self.generate_address(asset)

            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": asset,
                "amount": str(round(random.uniform(0.5, 5), 6)),
                "address": address,
                "is_new_address": True,  # Always new addresses (suspicious)
                "timestamp": base_withdraw_time - timedelta(minutes=random.randint(0, 360)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choices(self.kyc_levels, weights=[0.6, 0.3, 0.08, 0.02])[0],  # Low KYC
            "account_created_time": account_created,
            "vip_level": "NORMAL",
        }

        ring["members"].append(user_id)

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "fraud_ring",
            "ring_id": ring["ring_id"],
        }

    def create_trading_manipulation_user(self) -> dict:
        """
        Create a trading manipulation user.

        Pattern: High frequency opposite trading (wash trading / market manipulation)
        - Moderate account age (not new)
        - Very high trade frequency (100+ trades in 24h)
        - Very high opposite trade ratio (>0.5)
        - Normal withdrawal behavior
        - Unique device (not part of ring)

        Risk Level: HIGH (70-90) or CRITICAL (90-100)
        """
        user_id = self.generate_user_id()

        # Moderate account age (established account turning malicious)
        account_created = datetime.now() - timedelta(days=random.randint(30, 90))

        # Unique device
        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 6)),
        }

        # Very high frequency with intentional opposite trading
        trades = []
        num_trades = random.randint(100, 150)  # Very high frequency

        base_time = datetime.now() - timedelta(hours=random.randint(1, 12))

        # Create intentional buy/sell pairs (wash trading pattern)
        symbols = random.sample(self.symbols, 3)  # Focus on 3 symbols

        for i in range(num_trades):
            symbol = symbols[i % len(symbols)]
            # Alternate BUY/SELL for high opposite ratio
            side = "BUY" if i % 2 == 0 else "SELL"
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.5, 3), 4)

            timestamp = base_time - timedelta(seconds=random.randint(0, 720 * 60))

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": timestamp,
            })

        # Normal withdrawal behavior
        withdrawals = []
        num_withdrawals = random.randint(0, 3)

        for i in range(num_withdrawals):
            asset = random.choice(self.assets)
            address = self.generate_address(asset)

            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": asset,
                "amount": str(round(random.uniform(0.1, 1), 6)),
                "address": address,
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(5, 30)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choice(self.kyc_levels),
            "account_created_time": account_created,
            "vip_level": random.choices(self.vip_levels, weights=[0.6, 0.3, 0.08, 0.02])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "trading_manipulation",
        }

    def create_withdrawal_risk_user(self) -> dict:
        """
        Create a withdrawal risk user.

        Pattern: Abnormal withdrawal behavior
        - Established account (60-180 days)
        - Normal to moderate trading
        - Very high withdrawal frequency (10+ in 24h)
        - High withdrawal amounts
        - Mix of new and existing addresses

        Risk Level: HIGH (70-90)
        """
        user_id = self.generate_user_id()

        # Established account
        account_created = datetime.now() - timedelta(days=random.randint(60, 180))

        # Unique device
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
        num_trades = random.randint(25, 50)

        for _ in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.1, 3), 4)

            timestamp = datetime.now() - timedelta(
                days=random.randint(1, 30),
                hours=random.randint(0, 23),
            )

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": timestamp,
            })

        # High withdrawal frequency
        withdrawals = []
        num_withdrawals = random.randint(10, 18)

        base_withdraw_time = datetime.now() - timedelta(hours=random.randint(1, 12))

        for i in range(num_withdrawals):
            asset = random.choice(self.assets)
            address = self.generate_address(asset)

            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": asset,
                # Larger amounts
                "amount": str(round(random.uniform(1, 8), 6)),
                "address": address,
                "is_new_address": (i < 3),  # First few to new addresses
                "timestamp": base_withdraw_time - timedelta(minutes=random.randint(0, 720)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choices(self.kyc_levels, weights=[0.1, 0.3, 0.4, 0.2])[0],
            "account_created_time": account_created,
            "vip_level": random.choices(self.vip_levels, weights=[0.5, 0.35, 0.12, 0.03])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "withdrawal_risk",
        }

    def create_medium_risk_user(self, shared_device: str = None) -> dict:
        """
        Create a medium risk user.

        Patterns:
        - Moderate elevated risk factors
        - Some suspicious behavior but not clear fraud
        - May have single risk signal (high trades OR shared device)
        """
        user_id = self.generate_user_id()

        account_created = datetime.now() - timedelta(days=random.randint(20, 120))

        if shared_device:
            device_id = shared_device
            ip_address = self.generate_ip_address()
        else:
            device_id = self.generate_device_id()
            ip_address = self.generate_ip_address()

        device = {
            "user_id": user_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(days=random.randint(1, 7)),
        }

        # Elevated but not extreme trading
        trades = []
        num_trades = random.randint(35, 60)

        for _ in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.1, 3), 4)

            timestamp = datetime.now() - timedelta(
                days=random.randint(0, 7),
                hours=random.randint(0, 23),
            )

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": timestamp,
            })

        # Normal to moderate withdrawals
        withdrawals = []
        num_withdrawals = random.randint(2, 6)

        for i in range(num_withdrawals):
            asset = random.choice(self.assets)
            address = self.generate_address(asset)

            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": asset,
                "amount": str(round(random.uniform(0.2, 2), 6)),
                "address": address,
                "is_new_address": (i == 0),
                "timestamp": datetime.now() - timedelta(days=random.randint(1, 14)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choices(self.kyc_levels, weights=[0.15, 0.3, 0.35, 0.2])[0],
            "account_created_time": account_created,
            "vip_level": random.choices(self.vip_levels, weights=[0.6, 0.3, 0.08, 0.02])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "medium_risk",
        }

    def create_low_risk_user(self) -> dict:
        """Create a low risk user with normal behavior."""
        user_id = self.generate_user_id()

        # Established account
        account_created = datetime.now() - timedelta(days=random.randint(90, 365))

        # Unique device
        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(days=random.randint(1, 30)),
        }

        # Normal trading patterns
        trades = []
        num_trades = random.randint(15, 40)

        for _ in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.1, 5), 4)

            timestamp = datetime.now() - timedelta(
                days=random.randint(1, 90),
                hours=random.randint(0, 23),
            )

            trades.append({
                "trade_id": self.generate_trade_id(),
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": str(quantity),
                "timestamp": timestamp,
            })

        # Normal withdrawals
        withdrawals = []
        num_withdrawals = random.randint(0, 4)

        for i in range(num_withdrawals):
            asset = random.choice(self.assets)
            address = self.generate_address(asset)

            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": asset,
                "amount": str(round(random.uniform(0.01, 1), 6)),
                "address": address,
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(1, 90)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choices(self.kyc_levels, weights=[0.05, 0.15, 0.4, 0.4])[0],
            "account_created_time": account_created,
            "vip_level": random.choices(self.vip_levels, weights=[0.5, 0.35, 0.12, 0.03])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "low_risk",
        }

    def generate_all(self) -> Dict[str, pd.DataFrame]:
        """
        Generate the complete demo production dataset.

        Risk Distribution:
        - Low (60%): 1200 users
        - Medium (25%): 500 users
        - High (11%): 220 users
        - Critical (4%): 80 users
        """
        print("=" * 70)
        print("DEMO PRODUCTION DATASET GENERATOR v4")
        print("=" * 70)
        print(f"Generating dataset with {self.total_users} users...")

        # Calculate counts for realistic risk distribution
        critical_count = int(self.total_users * 0.04)  # 80 users
        high_count = int(self.total_users * 0.11)     # 220 users
        medium_count = int(self.total_users * 0.25)   # 500 users
        low_count = self.total_users - critical_count - high_count - medium_count  # 1200 users

        print(f"\nTarget risk distribution:")
        print(f"  Low risk: {low_count} ({low_count/self.total_users*100:.1f}%)")
        print(f"  Medium risk: {medium_count} ({medium_count/self.total_users*100:.1f}%)")
        print(f"  High risk: {high_count} ({high_count/self.total_users*100:.1f}%)")
        print(f"  Critical risk: {critical_count} ({critical_count/self.total_users*100:.1f}%)")

        # Storage for all data
        users = []
        devices = []
        trades = []
        withdrawals = []

        # ========== FRAUD RINGS (Critical) ==========
        # Create 6 fraud rings with 12-14 members each
        print(f"\nGenerating fraud rings (Critical risk)...")
        fraud_ring_members = critical_count - 20  # Reserve 20 for individual critical users
        num_rings = 6
        ring_size = fraud_ring_members // num_rings

        for ring_idx in range(num_rings):
            ring = self._create_fraud_ring(ring_size)
            actual_size = ring_size if ring_idx < num_rings - 1 else fraud_ring_members - ring_idx * ring_size

            print(f"  Ring {ring_idx + 1}: {actual_size} members")
            for i in range(actual_size):
                user_data = self.create_fraud_ring_user(ring, i, actual_size)
                users.append(user_data["user"])
                devices.append(user_data["device"])
                trades.extend(user_data["trades"])
                withdrawals.extend(user_data["withdrawals"])

        # Individual critical users (trading manipulation extreme)
        print(f"  Individual critical users: 20")
        for _ in range(20):
            user_data = self.create_trading_manipulation_user()
            # Enhance to critical level
            user_data["type"] = "critical_manipulation"
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        # ========== HIGH RISK USERS ==========
        print(f"\nGenerating high risk users ({high_count})...")
        # Mix of trading manipulation and withdrawal risk
        trading_manipulation_count = high_count // 2
        withdrawal_risk_count = high_count - trading_manipulation_count

        print(f"  Trading manipulation: {trading_manipulation_count}")
        for _ in range(trading_manipulation_count):
            user_data = self.create_trading_manipulation_user()
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        print(f"  Withdrawal risk: {withdrawal_risk_count}")
        for _ in range(withdrawal_risk_count):
            user_data = self.create_withdrawal_risk_user()
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        # ========== MEDIUM RISK USERS ==========
        print(f"\nGenerating medium risk users ({medium_count})...")
        # Some share devices with fraud rings for graph signals
        medium_with_graph = 50
        medium_normal = medium_count - medium_with_graph

        print(f"  With graph signals: {medium_with_graph}")
        for i in range(medium_with_graph):
            # Share device with existing fraud ring
            ring_idx = i % len(self.fraud_rings)
            ring = list(self.fraud_rings.values())[ring_idx]
            shared_device = ring["shared_devices"][0]
            user_data = self.create_medium_risk_user(shared_device)
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        print(f"  Normal medium risk: {medium_normal}")
        for _ in range(medium_normal):
            user_data = self.create_medium_risk_user()
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        # ========== LOW RISK USERS ==========
        print(f"\nGenerating low risk users ({low_count})...")
        for _ in range(low_count):
            user_data = self.create_low_risk_user()
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        # Create DataFrames
        users_df = pd.DataFrame(users)
        devices_df = pd.DataFrame(devices)
        trades_df = pd.DataFrame(trades)
        withdrawals_df = pd.DataFrame(withdrawals)

        print(f"\n{'='*70}")
        print("DATASET GENERATION COMPLETE")
        print(f"{'='*70}")
        print(f"  Users: {len(users_df)}")
        print(f"  Devices: {len(devices_df)}")
        print(f"  Trades: {len(trades_df)}")
        print(f"  Withdrawals: {len(withdrawals_df)}")

        return {
            "users": users_df,
            "devices": devices_df,
            "trades": trades_df,
            "withdrawals": withdrawals_df,
        }

    def save_to_csv(self, output_dir: str = "test_data/v4_demo_production"):
        """Save generated datasets to CSV files."""
        data = self.generate_all()

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Save to CSV
        for name, df in data.items():
            filepath = os.path.join(output_dir, f"{name}.csv")
            df.to_csv(filepath, index=False)
            print(f"Saved {filepath}")

        # Generate validation summary
        self._generate_validation_summary(output_dir, data)

        print(f"\nAll CSV files saved to {output_dir}/")

    def _generate_validation_summary(self, output_dir: str, data: Dict[str, pd.DataFrame]):
        """Generate validation summary for the dataset."""
        summary_path = os.path.join(output_dir, "DATASET_VALIDATION.md")

        with open(summary_path, "w") as f:
            f.write("# Demo Production Dataset v4 - Validation Summary\n\n")
            f.write("## Dataset Information\n\n")
            f.write(f"- **Purpose**: Product demonstration for Risk Intelligence Platform\n")
            f.write(f"- **Generation Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Random Seed**: 20260721\n\n")

            f.write("## Dataset Size\n\n")
            f.write("| File | Records |\n")
            f.write("|------|--------|\n")
            for name, df in data.items():
                f.write(f"| {name}.csv | {len(df):,} |\n")
            f.write("\n")

            f.write("## Expected Risk Distribution\n\n")
            f.write("| Risk Level | Count | Percentage | Score Range |\n")
            f.write("|------------|-------|------------|-------------|\n")
            f.write("| Low | 1,200 | 60% | 10-40 |\n")
            f.write("| Medium | 500 | 25% | 40-70 |\n")
            f.write("| High | 220 | 11% | 70-90 |\n")
            f.write("| Critical | 80 | 4% | 90-100 |\n")
            f.write("\n")

            f.write("## Fraud Patterns Generated\n\n")
            f.write("### 1. Account Takeover / Fraud Rings (Critical)\n")
            f.write("- **6 fraud rings** with ~12 members each\n")
            f.write("- Shared devices within rings\n")
            f.write("- Young accounts (5-30 days)\n")
            f.write("- High withdrawal frequency\n")
            f.write("- Multiple IPs per ring\n\n")

            f.write("### 2. Trading Manipulation (High/Critical)\n")
            f.write("- High trade frequency (80-120 trades/24h)\n")
            f.write("- High opposite trade ratio (>50%)\n")
            f.write("- Concentrated on 3 symbols\n")
            f.write("- Alternating BUY/SELL patterns\n\n")

            f.write("### 3. Withdrawal Risk (High)\n")
            f.write("- High withdrawal frequency (10-18/24h)\n")
            f.write("- Large withdrawal amounts\n")
            f.write("- Mix of new addresses\n\n")

            f.write("## Expected ML Metrics\n\n")
            f.write("- **Overall AUC**: 0.85-0.92\n")
            f.write("- **Overall KS**: 0.55-0.70\n")
            f.write("- **PSI vs v2 baseline**: 0.05-0.20 (stable)\n\n")

            f.write("## Feature Distribution Notes\n\n")
            f.write("Features are distributed close to v2 training baseline:\n")
            f.write("- `trade_frequency_24h`: Bimodal (normal users 5-20, manipulation 40-120)\n")
            f.write("- `opposite_trade_ratio`: Normal users 0.1-0.3, manipulation 0.5-0.7\n")
            f.write("- `withdrawal_frequency_24h`: Normal users 0-3, risk users 8-18\n")
            f.write("- `shared_device_count`: Fraud rings 3-12, others 0-1\n")
            f.write("- `account_age_days`: Wide distribution (5-365 days)\n\n")

            f.write("## Investigation Queue Validation\n\n")
            f.write("After uploading and running pipeline, verify:\n\n")
            f.write("```sql\n")
            f.write("-- Check risk level distribution\n")
            f.write("SELECT risk_level, COUNT(*) as count\n")
            f.write("FROM risk_events\n")
            f.write("GROUP BY risk_level\n")
            f.write("ORDER BY \n")
            f.write("  CASE risk_level\n")
            f.write("    WHEN 'CRITICAL' THEN 1\n")
            f.write("    WHEN 'HIGH' THEN 2\n")
            f.write("    WHEN 'MEDIUM' THEN 3\n")
            f.write("    WHEN 'LOW' THEN 4\n")
            f.write("  END;\n")
            f.write("```\n\n")

            f.write("## Critical User Examples\n\n")
            f.write("Expected critical users should have:\n")
            f.write("- ML score >= 80 (high frequency trading)\n")
            f.write("- Rule score >= 40 (new account + suspicious patterns)\n")
            f.write("- Graph score >= 20 (fraud ring membership)\n")
            f.write("- Final score >= 90\n\n")

        print(f"Generated validation summary: {summary_path}")


def main():
    """Main entry point."""
    generator = DemoProductionDatasetGenerator(total_users=2000)
    generator.save_to_csv()


if __name__ == "__main__":
    main()
