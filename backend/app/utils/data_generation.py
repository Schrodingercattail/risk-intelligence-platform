"""
Demo Data Generator

Generates realistic demo data for the risk platform including:
- Normal users (70%)
- Suspicious clusters (30%) with coordinated trading patterns
"""
import random
import string
from datetime import datetime, timedelta
from typing import List, Tuple
import pandas as pd
from decimal import Decimal

from app.config import settings


class DemoDataGenerator:
    """Generate demo data for risk platform testing."""

    def __init__(
        self,
        user_count: int = None,
        trade_count: int = None,
        cluster_count: int = None,
        normal_ratio: float = None,
    ):
        """Initialize generator with configuration."""
        self.user_count = user_count or settings.DEMO_USER_COUNT
        self.trade_count = trade_count or settings.DEMO_TRADE_COUNT
        self.cluster_count = cluster_count or settings.DEMO_CLUSTER_COUNT
        self.normal_ratio = normal_ratio or settings.DEMO_NORMAL_RATIO

        # Calculate counts
        self.normal_user_count = int(self.user_count * self.normal_ratio)
        self.suspicious_user_count = self.user_count - self.normal_user_count

        # Configuration for cluster types
        self.cluster_types = ["device_sharing", "coordinated_trading", "withdrawal_abuse"]
        self.cluster_type_distribution = [0.4, 0.4, 0.2]  # 40%, 40%, 20%

        # Trading symbols
        self.symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC"]
        self.sides = ["BUY", "SELL"]

        # Countries
        self.countries = ["US", "UK", "SG", "JP", "DE", "FR", "CA", "AU"]

        # KYC levels
        self.kyc_levels = ["NONE", "BASIC", "INTERMEDIATE", "FULL"]

        # VIP levels
        self.vip_levels = ["NORMAL", "SILVER", "GOLD", "PLATINUM"]

        # Random seed for reproducibility
        random.seed(42)

    def generate_user_id(self, index: int) -> str:
        """Generate a user ID."""
        return f"U{index:05d}"

    def generate_device_id(self) -> str:
        """Generate a device ID."""
        return f"DEV{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}"

    def generate_ip_address(self) -> str:
        """Generate a random IP address."""
        return f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"

    def generate_users(self) -> pd.DataFrame:
        """Generate users data including both normal and suspicious users."""
        users = []

        # Normal users
        for i in range(self.normal_user_count):
            user_id = self.generate_user_id(i + 1)
            account_created = datetime.now() - timedelta(days=random.randint(30, 365))

            users.append({
                "user_id": user_id,
                "country": random.choice(self.countries),
                "kyc_level": random.choice(self.kyc_levels),
                "account_created_time": account_created,
                "vip_level": random.choices(
                    self.vip_levels, weights=[0.8, 0.1, 0.08, 0.02]
                )[0],
            })

        # Suspicious users (will be assigned to risk clusters)
        for i in range(self.suspicious_user_count):
            user_id = self.generate_user_id(self.normal_user_count + i + 1)
            # Suspicious users tend to have newer accounts
            account_created = datetime.now() - timedelta(days=random.randint(7, 90))

            users.append({
                "user_id": user_id,
                "country": random.choice(self.countries),
                "kyc_level": random.choices(self.kyc_levels, weights=[0.4, 0.3, 0.2, 0.1])[0],  # Lower KYC levels
                "account_created_time": account_created,
                "vip_level": random.choices(
                    self.vip_levels, weights=[0.95, 0.03, 0.015, 0.005]
                )[0],  # Mostly normal VIP level
            })

        return pd.DataFrame(users)

    def generate_devices(self, users_df: pd.DataFrame, cluster_info: dict = None) -> pd.DataFrame:
        """Generate device data with shared devices for suspicious clusters."""
        devices = []

        # Build a mapping of user_id to shared device_id from cluster_info
        user_to_shared_device = {}
        if cluster_info and cluster_info.get("shared_devices"):
            for device_id, user_list in cluster_info["shared_devices"].items():
                for user_id in user_list:
                    user_to_shared_device[user_id] = device_id

        for _, user in users_df.iterrows():
            user_id = user["user_id"]

            # Check if this user should have a shared device
            if user_id in user_to_shared_device:
                device_id = user_to_shared_device[user_id]
                # Suspicious users on shared devices might share IPs too
                ip_address = self.generate_ip_address()
                # Multiple users on same device might have similar fingerprints
                browser_fingerprint = f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}"
            else:
                # Normal users get unique devices
                device_id = self.generate_device_id()
                ip_address = self.generate_ip_address()
                browser_fingerprint = f"FP{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}"

            devices.append({
                "user_id": user_id,
                "device_id": device_id,
                "ip_address": ip_address,
                "location": random.choice(self.countries),
                "browser_fingerprint": browser_fingerprint,
                "first_seen": user["account_created_time"],
                "last_seen": datetime.now() - timedelta(days=random.randint(1, 7)),
            })

        return pd.DataFrame(devices)

    def generate_trades(
        self,
        users_df: pd.DataFrame,
        coordinated_pairs: List[Tuple[str, str]] = None
    ) -> pd.DataFrame:
        """Generate trading data with coordinated trading patterns for suspicious pairs."""
        trades = []
        trade_id = 1

        # Build set of users in coordinated pairs for quick lookup
        coordinated_users = set()
        if coordinated_pairs:
            for user1, user2 in coordinated_pairs:
                coordinated_users.add(user1)
                coordinated_users.add(user2)

        # Generate coordinated trades first (for suspicious pairs)
        coordinated_trades = []
        if coordinated_pairs:
            for user1, user2 in coordinated_pairs:
                # Generate 20-50 coordinated trades per pair
                num_coordinated = random.randint(20, 50)
                base_time = datetime.now() - timedelta(days=random.randint(1, 30))

                for _ in range(num_coordinated):
                    # Same symbol for both
                    symbol = random.choice(self.symbols)
                    price = self._get_symbol_price(symbol)

                    # Same timestamp (within seconds)
                    trade_time = base_time + timedelta(
                        minutes=random.randint(0, 60),
                        seconds=random.randint(0, 59)
                    )

                    # Opposite sides (coordinated trading pattern)
                    quantity1 = round(random.uniform(0.5, 5), 4)
                    quantity2 = round(random.uniform(0.5, 5), 4)

                    # User1 buys, User2 sells (or vice versa)
                    if random.random() < 0.5:
                        coordinated_trades.append({
                            "user_id": user1,
                            "symbol": symbol,
                            "side": "BUY",
                            "price": str(price),
                            "quantity": str(quantity1),
                            "timestamp": trade_time,
                        })
                        coordinated_trades.append({
                            "user_id": user2,
                            "symbol": symbol,
                            "side": "SELL",
                            "price": str(price),
                            "quantity": str(quantity2),
                            "timestamp": trade_time,
                        })
                    else:
                        coordinated_trades.append({
                            "user_id": user1,
                            "symbol": symbol,
                            "side": "SELL",
                            "price": str(price),
                            "quantity": str(quantity1),
                            "timestamp": trade_time,
                        })
                        coordinated_trades.append({
                            "user_id": user2,
                            "symbol": symbol,
                            "side": "BUY",
                            "price": str(price),
                            "quantity": str(quantity2),
                            "timestamp": trade_time,
                        })

        # Generate regular trades for all users
        user_trade_counts = {}  # Track trades per user

        for _, user in users_df.iterrows():
            user_id = user["user_id"]

            # Determine number of regular trades for this user
            # Normal users: 5-30 trades
            # Suspicious users: more frequent trading
            if user_id in coordinated_users:
                num_regular_trades = random.randint(30, 80)
            else:
                num_regular_trades = random.randint(5, 30)

            for _ in range(num_regular_trades):
                symbol = random.choice(self.symbols)
                side = random.choice(self.sides)
                price = self._get_symbol_price(symbol)
                quantity = round(random.uniform(0.1, 10), 4)

                # Random timestamp within last 30 days
                timestamp = datetime.now() - timedelta(
                    days=random.randint(1, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )

                trades.append({
                    "trade_id": f"T{trade_id:06d}",
                    "user_id": user_id,
                    "symbol": symbol,
                    "side": side,
                    "price": str(price),
                    "quantity": str(quantity),
                    "timestamp": timestamp,
                })
                trade_id += 1

            # Initialize trade count for this user
            user_trade_counts[user_id] = num_regular_trades

        # Add coordinated trades with trade IDs
        for trade in coordinated_trades:
            user_id = trade["user_id"]
            user_trade_counts[user_id] = user_trade_counts.get(user_id, 0) + 1

            trades.append({
                "trade_id": f"T{trade_id:06d}",
                **trade,
            })
            trade_id += 1

        return pd.DataFrame(trades)

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
        # Add some random variation (-5% to +5%)
        variation = Decimal(str(random.uniform(-0.05, 0.05)))
        return base * (Decimal("1") + variation)

    def generate_withdrawals(
        self,
        users_df: pd.DataFrame,
        shared_addresses: List[str] = None
    ) -> pd.DataFrame:
        """Generate withdrawal data with abuse patterns for suspicious users."""
        withdrawals = []
        withdraw_id = 1

        # Build set of users who should use shared addresses
        shared_address_users = set()
        if shared_addresses:
            # Randomly assign some suspicious users to use shared addresses
            # Get suspicious users (those with higher index)
            suspicious_indices = list(range(self.normal_user_count, len(users_df)))
            # About 60% of suspicious users use shared addresses
            num_shared_users = int(len(suspicious_indices) * 0.6)
            shared_address_users = set(users_df.iloc[suspicious_indices[:num_shared_users]]["user_id"].tolist())

        for _, user in users_df.iterrows():
            user_id = user["user_id"]

            # Determine withdrawal behavior
            # Extract user index from user_id (e.g., "U00523" -> 523)
            user_index = int(user_id[1:]) - 1  # Convert to 0-based index

            if user_id in shared_address_users and shared_addresses:
                # Suspicious users: more frequent withdrawals to shared addresses
                num_withdrawals = random.randint(10, 30)
                use_shared_address = True
            elif user_index >= self.normal_user_count:  # Other suspicious users
                # Still higher withdrawal frequency but to unique addresses
                num_withdrawals = random.randint(5, 15)
                use_shared_address = False
            else:  # Normal users
                # Normal users: occasional withdrawals
                num_withdrawals = random.randint(0, 8)
                use_shared_address = False

            for i in range(num_withdrawals):
                if use_shared_address and shared_addresses and random.random() < 0.7:  # 70% to shared addresses
                    address = random.choice(shared_addresses)
                    is_new = False
                else:
                    address = f"0x{''.join(random.choices(string.ascii_lowercase + string.digits, k=40))}"
                    is_new = (i == 0)  # First withdrawal is usually to new address

                asset = random.choice(["BTC", "ETH", "USDT"])
                # Suspicious users tend to withdraw larger amounts
                if user_id in shared_address_users:
                    amount = round(random.uniform(0.5, 20), 6)
                else:
                    amount = round(random.uniform(0.01, 5), 6)

                timestamp = datetime.now() - timedelta(
                    days=random.randint(1, 30),
                    hours=random.randint(0, 23),
                )

                withdrawals.append({
                    "withdraw_id": f"W{withdraw_id:06d}",
                    "user_id": user_id,
                    "asset": asset,
                    "amount": str(amount),
                    "address": address,
                    "is_new_address": is_new,
                    "timestamp": timestamp,
                })
                withdraw_id += 1

        return pd.DataFrame(withdrawals)

    def generate_suspicious_clusters(self, users_df: pd.DataFrame) -> dict:
        """
        Generate suspicious cluster information with realistic patterns.

        Returns:
            dict with:
            - coordinated_pairs: List of (user1, user2) tuples for coordinated trading
            - shared_devices: Dict mapping device_id to list of user_ids
            - shared_addresses: List of addresses shared across accounts
        """
        # Get suspicious users (those not in normal range)
        suspicious_users = users_df.iloc[self.normal_user_count:]["user_id"].tolist()

        if len(suspicious_users) == 0:
            # No suspicious users to cluster
            return {
                "coordinated_pairs": [],
                "shared_devices": {},
                "shared_addresses": [],
            }

        coordinated_pairs = []
        shared_devices = {}
        shared_addresses = []

        # Create clusters with at least 3 members per cluster for better ML signals
        cluster_size = max(3, len(suspicious_users) // max(1, self.cluster_count))

        # Shuffle suspicious users for random assignment
        random.shuffle(suspicious_users)

        for i in range(0, len(suspicious_users), cluster_size):
            cluster_users = suspicious_users[i:i + cluster_size]
            if len(cluster_users) < 2:
                continue  # Skip clusters with only 1 member

            # Assign cluster type with weighted distribution
            cluster_type = random.choices(
                self.cluster_types,
                weights=self.cluster_type_distribution
            )[0]

            # Shared device for all cluster members
            shared_device_id = self.generate_device_id()
            shared_devices[shared_device_id] = cluster_users

            # For coordinated trading clusters, create trading pairs
            if cluster_type == "coordinated_trading":
                # Create multiple coordinated pairs within cluster
                for j in range(len(cluster_users)):
                    for k in range(j + 1, min(j + 3, len(cluster_users))):
                        # Each pair trades together
                        coordinated_pairs.append((cluster_users[j], cluster_users[k]))

            # For device sharing and withdrawal abuse, create shared addresses
            if cluster_type in ["device_sharing", "withdrawal_abuse"]:
                # Create 2-3 shared addresses per cluster
                num_addresses = random.randint(2, 3)
                for _ in range(num_addresses):
                    shared_addr = f"0x{''.join(random.choices(string.ascii_lowercase + string.digits, k=40))}"
                    shared_addresses.append(shared_addr)

        # Ensure we have some coordinated pairs even if clusters didn't create many
        while len(coordinated_pairs) < min(20, len(suspicious_users) // 2):
            # Create additional coordinated pairs
            user1 = random.choice(suspicious_users)
            user2 = random.choice([u for u in suspicious_users if u != user1])
            if (user1, user2) not in coordinated_pairs and (user2, user1) not in coordinated_pairs:
                coordinated_pairs.append((user1, user2))

        # Ensure we have some shared addresses
        while len(shared_addresses) < 10:
            shared_addr = f"0x{''.join(random.choices(string.ascii_lowercase + string.digits, k=40))}"
            shared_addresses.append(shared_addr)

        return {
            "coordinated_pairs": coordinated_pairs,
            "shared_devices": shared_devices,
            "shared_addresses": shared_addresses,
        }

    def generate_risk_labels(self, users_df: pd.DataFrame, cluster_info: dict) -> pd.DataFrame:
        """
        Generate risk labels for supervised learning.

        Returns:
            DataFrame with user_id and is_risky columns
        """
        labels = []

        # Get suspicious users from cluster info
        risky_users = set()
        for pair in cluster_info["coordinated_pairs"]:
            risky_users.update(pair)
        for device_users in cluster_info["shared_devices"].values():
            risky_users.update(device_users)

        for _, user in users_df.iterrows():
            labels.append({
                "user_id": user["user_id"],
                "is_risky": user["user_id"] in risky_users,
            })

        return pd.DataFrame(labels)

    def generate_all(self) -> dict:
        """
        Generate all demo datasets.

        Returns:
            dict with DataFrames for users, devices, trades, withdrawals, labels
        """
        print(f"Generating demo data with {self.user_count} users...")

        # Generate users
        users_df = self.generate_users()
        print(f"Generated {len(users_df)} users")

        # Generate cluster information
        cluster_info = self.generate_suspicious_clusters(users_df)
        print(f"Generated {len(cluster_info['coordinated_pairs'])} coordinated trading pairs")
        print(f"Generated {len(cluster_info['shared_devices'])} shared device clusters")
        print(f"Generated {len(cluster_info['shared_addresses'])} shared withdrawal addresses")

        # Generate devices with cluster info applied
        devices_df = self.generate_devices(users_df, cluster_info)
        print(f"Generated {len(devices_df)} device records")

        # Generate trades with coordinated pairs
        trades_df = self.generate_trades(users_df, cluster_info["coordinated_pairs"])
        print(f"Generated {len(trades_df)} trade records")

        # Generate withdrawals with shared addresses
        withdrawals_df = self.generate_withdrawals(users_df, cluster_info["shared_addresses"])
        print(f"Generated {len(withdrawals_df)} withdrawal records")

        # Generate risk labels
        labels_df = self.generate_risk_labels(users_df, cluster_info)
        print(f"Generated {len(labels_df)} risk labels")
        print(f"  - Risky users: {labels_df['is_risky'].sum()}")
        print(f"  - Normal users: {(~labels_df['is_risky']).sum()}")

        return {
            "users": users_df,
            "devices": devices_df,
            "trades": trades_df,
            "withdrawals": withdrawals_df,
            "risk_labels": labels_df,
            "cluster_info": cluster_info,
        }


# Standalone execution for testing
if __name__ == "__main__":
    generator = DemoDataGenerator()
    data = generator.generate_all()

    # Save to CSV
    import os
    output_dir = "data/generated"
    os.makedirs(output_dir, exist_ok=True)

    for key, df in data.items():
        if key != "cluster_info" and isinstance(df, pd.DataFrame):
            filepath = os.path.join(output_dir, f"{key}.csv")
            df.to_csv(filepath, index=False)
            print(f"Saved {filepath}")
