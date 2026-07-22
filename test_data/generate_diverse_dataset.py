"""
Diverse Detection Attribution Dataset Generator v2

Creates a synthetic demo dataset designed to produce diverse detection
attribution patterns for regression testing.

Detection Attribution Thresholds:
- LightGBM: ml_score >= 10.0
- Rule Engine: rule_score >= 15.0
- Graph Network: graph_score >= 10.0

Goal: Create users that trigger different combinations of detection methods.
"""
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import os


class DiverseDatasetGenerator:
    """Generate dataset with diverse detection attribution patterns."""

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
        random.seed(20260720)

        # User ID counter
        self.user_id_counter = 1
        self.trade_id_counter = 1
        self.withdraw_id_counter = 1

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

    def create_ml_only_user(self) -> dict:
        """
        Create ML-only risk user.

        Strategy:
        - Very high trade frequency in 24h window (triggers ML pattern detection)
        - Normal opposite trade ratio (< 0.4 to avoid rule trigger)
        - No shared devices (avoid graph detection)
        - Low withdrawal frequency (< 5 to avoid rule trigger)
        - Moderate account age (avoid new account rules)

        Expected: High ML score (>= 10), low rule score (< 15), low graph score (< 10)
        """
        user_id = self.generate_user_id()

        # User profile - moderate account age (avoid new account rules)
        account_created = datetime.now() - timedelta(days=random.randint(15, 45))

        # Unique device (no sharing)
        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Very high frequency trading in 24h window (ML pattern)
        trades = []
        num_trades = random.randint(60, 100)  # Very high frequency

        # Base time - recent activity to ensure 24h window is populated
        base_time = datetime.now() - timedelta(hours=random.randint(1, 12))

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.1, 2), 4)

            # Distribute trades across last 24 hours
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

        # Very low withdrawal frequency (avoid rule trigger)
        withdrawals = []
        num_withdrawals = random.randint(0, 2)  # Very low frequency

        for i in range(num_withdrawals):
            address = self.generate_address()

            # Older withdrawals to not count in 24h window
            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(0.01, 0.5), 6)),  # Small amounts
                "address": address,
                "is_new_address": False,  # No new addresses
                "timestamp": datetime.now() - timedelta(days=random.randint(5, 20)),
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
            "type": "ml_only",
        }

    def create_rule_only_user(self) -> dict:
        """
        Create rule-only risk user.

        Strategy:
        - New account (< 7 days) + high activity (rule trigger: +40)
        - Normal trade patterns (avoid ML detection)
        - No shared devices (avoid graph detection)

        Expected: Low ML score (< 10), high rule score (>= 15), low graph score (< 10)
        """
        user_id = self.generate_user_id()

        # User profile - very new account (rule trigger)
        account_created = datetime.now() - timedelta(days=random.randint(2, 6))

        # Unique device (no sharing)
        device = {
            "user_id": user_id,
            "device_id": self.generate_device_id(),
            "ip_address": self.generate_ip_address(),
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(hours=random.randint(1, 12)),
        }

        # Normal trading patterns (avoid ML detection)
        trades = []
        num_trades = random.randint(8, 20)  # Normal frequency

        # Distribute across several days (not concentrated in 24h)
        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.5, 5), 4)

            timestamp = datetime.now() - timedelta(
                days=random.randint(0, 6),
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

        # High withdrawal frequency in 24h window (rule trigger: +25)
        withdrawals = []
        num_withdrawals = random.randint(6, 12)  # High frequency

        # Concentrate in recent 24h to trigger rule
        base_time = datetime.now() - timedelta(hours=random.randint(1, 6))

        for i in range(num_withdrawals):
            address = self.generate_address()

            # New address (rule trigger: +20)
            is_new = (i == 0)

            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(1, 5), 6)),  # Moderate amounts
                "address": address,
                "is_new_address": is_new,
                "timestamp": base_time - timedelta(minutes=random.randint(0, 360)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choices(self.kyc_levels, weights=[0.5, 0.3, 0.15, 0.05])[0],
            "account_created_time": account_created,
            "vip_level": "NORMAL",
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "rule_only",
        }

    def create_graph_only_user(self, shared_device: str, shared_ip: str) -> dict:
        """
        Create graph-only risk user.

        Strategy:
        - Shared device with cluster (triggers graph detection)
        - Normal transaction behavior (avoid ML)
        - No rule violations (avoid rule triggers)
        - Part of a cluster with at least 5 members to ensure graph_score >= 10

        Expected: Low ML score (< 10), low rule score (< 15), high graph score (>= 10)
        """
        user_id = self.generate_user_id()

        # User profile - normal account age
        account_created = datetime.now() - timedelta(days=random.randint(30, 180))

        # Shared device and IP (graph trigger - cluster membership)
        device = {
            "user_id": user_id,
            "device_id": shared_device,
            "ip_address": shared_ip,
            "location": random.choice(self.countries),
            "browser_fingerprint": f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}",
            "first_seen": account_created,
            "last_seen": datetime.now() - timedelta(days=random.randint(1, 7)),
        }

        # Normal trading patterns (avoid ML)
        trades = []
        num_trades = random.randint(3, 10)  # Low frequency

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

        # Very low withdrawal frequency (avoid rule triggers)
        withdrawals = []
        num_withdrawals = random.randint(0, 3)  # Very low frequency

        for i in range(num_withdrawals):
            address = self.generate_address()

            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(0.1, 1), 6)),
                "address": address,
                "is_new_address": False,  # No new addresses (avoid rule)
                "timestamp": datetime.now() - timedelta(days=random.randint(10, 30)),
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
            "type": "graph_only",
            "cluster_info": {"device": shared_device, "ip": shared_ip}
        }

    def create_multi_signal_user(self, shared_device: str = None) -> dict:
        """
        Create multi-signal risk user.

        Strategy:
        - High trade frequency (ML trigger)
        - High withdrawal frequency (rule trigger)
        - Shared device if provided (graph trigger)
        - Moderate account age to balance triggers

        Expected: High ML score (>= 10), high rule score (>= 15), high graph score (>= 10) if shared device
        """
        user_id = self.generate_user_id()

        # User profile - moderate account age (not too new, not too old)
        account_created = datetime.now() - timedelta(days=random.randint(10, 30))

        # Device (shared or unique)
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
            "last_seen": datetime.now() - timedelta(days=random.randint(1, 5)),
        }

        # High frequency trading (ML trigger)
        trades = []
        num_trades = random.randint(50, 90)

        # Concentrate in recent 24h
        base_time = datetime.now() - timedelta(hours=random.randint(1, 8))

        for i in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.1, 5), 4)

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

        # High withdrawal frequency (rule trigger)
        withdrawals = []
        num_withdrawals = random.randint(6, 12)

        # Concentrate in recent 24h
        base_withdraw_time = datetime.now() - timedelta(hours=random.randint(1, 6))

        for i in range(num_withdrawals):
            address = self.generate_address()

            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(1, 6), 6)),
                "address": address,
                "is_new_address": (i == 0),  # First to new address
                "timestamp": base_withdraw_time - timedelta(minutes=random.randint(0, 360)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choices(self.kyc_levels, weights=[0.4, 0.3, 0.2, 0.1])[0],
            "account_created_time": account_created,
            "vip_level": "NORMAL",
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "multi_signal",
        }

    def create_normal_user(self) -> dict:
        """Create a normal user with no risk signals."""
        user_id = self.generate_user_id()

        # User profile - established account
        account_created = datetime.now() - timedelta(days=random.randint(60, 365))

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

        # Normal trading
        trades = []
        num_trades = random.randint(2, 10)

        for _ in range(num_trades):
            symbol = random.choice(self.symbols)
            side = random.choice(self.sides)
            price = self._get_symbol_price(symbol)
            quantity = round(random.uniform(0.1, 5), 4)

            timestamp = datetime.now() - timedelta(
                days=random.randint(1, 60),
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
        num_withdrawals = random.randint(0, 3)

        for i in range(num_withdrawals):
            address = self.generate_address()

            withdrawals.append({
                "withdraw_id": self.generate_withdraw_id(),
                "user_id": user_id,
                "asset": random.choice(self.assets),
                "amount": str(round(random.uniform(0.01, 1), 6)),
                "address": address,
                "is_new_address": False,
                "timestamp": datetime.now() - timedelta(days=random.randint(1, 60)),
            })

        user = {
            "user_id": user_id,
            "country": random.choice(self.countries),
            "kyc_level": random.choices(self.kyc_levels, weights=[0.1, 0.2, 0.4, 0.3])[0],
            "account_created_time": account_created,
            "vip_level": random.choices(self.vip_levels, weights=[0.7, 0.2, 0.08, 0.02])[0],
        }

        return {
            "user": user,
            "device": device,
            "trades": trades,
            "withdrawals": withdrawals,
            "type": "normal",
        }

    def generate_all(self) -> dict:
        """
        Generate the complete diverse dataset.

        Updated Distribution (among detected accounts):
        - Normal users: 55% (should not trigger detection)
        - ML-only risk: 11% (of total, ~24% of detected)
        - Rule-only risk: 11% (of total, ~24% of detected)
        - Graph-only risk: 11% (of total, ~24% of detected)
        - Multi-signal risk: 12% (of total, ~26% of detected)
        """
        print(f"Generating diverse dataset with {self.total_users} users...")

        # Calculate counts for balanced detection attribution
        normal_count = int(self.total_users * 0.55)
        ml_only_count = int(self.total_users * 0.11)
        rule_only_count = int(self.total_users * 0.11)
        graph_only_count = int(self.total_users * 0.11)
        multi_signal_count = self.total_users - normal_count - ml_only_count - rule_only_count - graph_only_count

        print(f"\nTarget distribution:")
        print(f"  Normal users (no signal): {normal_count} ({normal_count/self.total_users*100:.1f}%)")
        print(f"  ML-only risk users: {ml_only_count} ({ml_only_count/self.total_users*100:.1f}%)")
        print(f"  Rule-only risk users: {rule_only_count} ({rule_only_count/self.total_users*100:.1f}%)")
        print(f"  Graph-only risk users: {graph_only_count} ({graph_only_count/self.total_users*100:.1f}%)")
        print(f"  Multi-signal risk users: {multi_signal_count} ({multi_signal_count/self.total_users*100:.1f}%)")

        detected_count = ml_only_count + rule_only_count + graph_only_count + multi_signal_count
        print(f"\nExpected detection attribution among {detected_count} detected accounts:")
        print(f"  ML-only: {ml_only_count/detected_count*100:.1f}%")
        print(f"  Rule-only: {rule_only_count/detected_count*100:.1f}%")
        print(f"  Graph-only: {graph_only_count/detected_count*100:.1f}%")
        print(f"  Multi-signal: {multi_signal_count/detected_count*100:.1f}%")

        # Storage for all data
        users = []
        devices = []
        trades = []
        withdrawals = []
        cluster_info = {}  # Track cluster devices for graph users

        # Generate normal users
        print(f"\nGenerating {normal_count} normal users...")
        for _ in range(normal_count):
            user_data = self.create_normal_user()
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        # Generate ML-only users
        print(f"Generating {ml_only_count} ML-only risk users...")
        for _ in range(ml_only_count):
            user_data = self.create_ml_only_user()
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        # Generate rule-only users
        print(f"Generating {rule_only_count} rule-only risk users...")
        for _ in range(rule_only_count):
            user_data = self.create_rule_only_user()
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        # Generate graph-only users (with shared devices for clustering)
        print(f"Generating {graph_only_count} graph-only risk users...")
        # Create larger clusters to ensure graph_score >= 10
        # Need at least 5 members per cluster for meaningful graph detection
        cluster_size = max(5, graph_only_count // 4)  # 4 clusters of ~5-6 users each
        num_graph_clusters = 4

        for cluster_idx in range(num_graph_clusters):
            cluster_users = min(cluster_size, graph_only_count - cluster_idx * cluster_size)
            if cluster_users <= 0:
                break

            # Create shared device and IP for this cluster
            shared_device = self.generate_device_id()
            shared_ip = self.generate_ip_address()

            for i in range(cluster_users):
                user_data = self.create_graph_only_user(shared_device, shared_ip)
                users.append(user_data["user"])
                devices.append(user_data["device"])
                trades.extend(user_data["trades"])
                withdrawals.extend(user_data["withdrawals"])

                # Track cluster info
                current_user_id = user_data["user"]["user_id"]
                if shared_device not in cluster_info:
                    cluster_info[shared_device] = {"users": [], "ip": shared_ip}
                cluster_info[shared_device]["users"].append(current_user_id)

        print(f"  Created {len(cluster_info)} graph clusters with {sum(len(c['users']) for c in cluster_info.values())} users")

        # Generate multi-signal users
        print(f"Generating {multi_signal_count} multi-signal risk users...")
        # Some multi-signal users share devices with graph clusters
        multi_with_graph = min(len(cluster_info), multi_signal_count // 2)

        for i in range(multi_signal_count):
            if i < multi_with_graph and cluster_info:
                # Share with existing cluster for graph signal
                cluster_device = list(cluster_info.keys())[i % len(cluster_info)]
                user_data = self.create_multi_signal_user(cluster_device)
            else:
                user_data = self.create_multi_signal_user(None)
            users.append(user_data["user"])
            devices.append(user_data["device"])
            trades.extend(user_data["trades"])
            withdrawals.extend(user_data["withdrawals"])

        # Create DataFrames
        users_df = pd.DataFrame(users)
        devices_df = pd.DataFrame(devices)
        trades_df = pd.DataFrame(trades)
        withdrawals_df = pd.DataFrame(withdrawals)

        print(f"\nDataset generation complete!")
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

    def save_to_csv(self, output_dir: str = "test_data/v2_diverse"):
        """Save generated datasets to CSV files."""
        data = self.generate_all()

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Save to CSV
        for name, df in data.items():
            filepath = os.path.join(output_dir, f"{name}.csv")
            df.to_csv(filepath, index=False)
            print(f"Saved {filepath}")

        print(f"\nAll CSV files saved to {output_dir}/")

        # Print SQL validation queries
        print("\n" + "="*70)
        print("SQL VALIDATION QUERIES")
        print("="*70)
        print("\nAfter uploading and running pipeline, use these queries to verify:")
        print("\n1. Check detection attribution among detected accounts:")
        print("""
-- Detection Attribution (should show diverse distribution)
WITH detected_accounts AS (
    SELECT DISTINCT u.user_id
    FROM users u
    JOIN risk_events re ON u.user_id = re.user_id
    WHERE re.ml_score >= 10.0
       OR re.rule_score >= 15.0
       OR re.graph_score >= 10.0
)
SELECT
    'ML Only' as category,
    COUNT(*) as count
FROM detected_accounts da
JOIN risk_events re ON da.user_id = re.user_id
WHERE re.ml_score >= 10.0 AND re.rule_score < 15.0 AND re.graph_score < 10.0
UNION ALL
SELECT
    'Rule Only' as category,
    COUNT(*) as count
FROM detected_accounts da
JOIN risk_events re ON da.user_id = re.user_id
WHERE re.ml_score < 10.0 AND re.rule_score >= 15.0 AND re.graph_score < 10.0
UNION ALL
SELECT
    'Graph Only' as category,
    COUNT(*) as count
FROM detected_accounts da
JOIN risk_events re ON da.user_id = re.user_id
WHERE re.ml_score < 10.0 AND re.rule_score < 15.0 AND re.graph_score >= 10.0
UNION ALL
SELECT
    'Multi Signal' as category,
    COUNT(*) as count
FROM detected_accounts da
JOIN risk_events re ON da.user_id = re.user_id
WHERE (re.ml_score >= 10.0 AND re.rule_score >= 15.0)
   OR (re.ml_score >= 10.0 AND re.graph_score >= 10.0)
   OR (re.rule_score >= 15.0 AND re.graph_score >= 10.0);
""")
        print("\n2. Check detection source counts:")
        print("""
-- Detection Source Counts
SELECT
    'ML Model' as method,
    COUNT(DISTINCT CASE WHEN re.ml_score >= 10.0 THEN u.user_id END) as account_count
FROM users u
JOIN risk_events re ON u.user_id = re.user_id
UNION ALL
SELECT
    'Rule Engine' as method,
    COUNT(DISTINCT CASE WHEN re.rule_score >= 15.0 THEN u.user_id END) as account_count
FROM users u
JOIN risk_events re ON u.user_id = re.user_id
UNION ALL
SELECT
    'Graph Network' as method,
    COUNT(DISTINCT CASE WHEN re.graph_score >= 10.0 THEN u.user_id END) as account_count
FROM users u
JOIN risk_events re ON u.user_id = re.user_id;
""")


def main():
    """Main entry point."""
    generator = DiverseDatasetGenerator(total_users=2000)
    generator.save_to_csv()


if __name__ == "__main__":
    main()
