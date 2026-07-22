"""
Update Database with Realistic Drift Data

This script clears existing data and loads v3_realistic_drift data
to demonstrate realistic PSI monitoring with moderate drift patterns.

Expected PSI: 0.25 - 1.0 (realistic production drift)
"""
import sys
import asyncio
from pathlib import Path
import pandas as pd

# Add backend to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine
from app.models.database import Base
from app.config import settings


def clear_database():
    """Clear all existing data from database."""
    from sqlalchemy import text

    engine = create_engine(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))

    print("Clearing existing data...")
    with engine.begin() as conn:
        # Delete all data (in correct order due to foreign keys)
        conn.execute(text("DELETE FROM feature_table"))
        conn.execute(text("DELETE FROM cluster_members"))
        conn.execute(text("DELETE FROM account_clusters"))
        conn.execute(text("DELETE FROM risk_events"))
        conn.execute(text("DELETE FROM withdrawals"))
        conn.execute(text("DELETE FROM trades"))
        conn.execute(text("DELETE FROM devices"))
        conn.execute(text("DELETE FROM users"))

        print("✓ Database cleared")


def load_drift_data(csv_dir: str = "test_data/v3_realistic_drift"):
    """Load drift data from CSV files."""
    csv_path = project_root / csv_dir

    print(f"\nLoading drift data from {csv_path}...")

    # Load CSV files
    users_df = pd.read_csv(csv_path / "users.csv")
    devices_df = pd.read_csv(csv_path / "devices.csv")
    trades_df = pd.read_csv(csv_path / "trades.csv")
    withdrawals_df = pd.read_csv(csv_path / "withdrawals.csv")

    # Remove columns that don't exist in database schema
    # account_age_days is a derived feature, not stored in users table
    if "account_age_days" in users_df.columns:
        users_df = users_df.drop(columns=["account_age_days"])

    print(f"✓ Loaded data:")
    print(f"  - Users: {len(users_df)}")
    print(f"  - Devices: {len(devices_df)}")
    print(f"  - Trades: {len(trades_df)}")
    print(f"  - Withdrawals: {len(withdrawals_df)}")

    # Load to database
    engine = create_engine(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))

    with engine.begin() as conn:
        # Insert users
        users_df.to_sql("users", conn, if_exists="append", index=False)
        print("✓ Users loaded")

        # Insert devices
        devices_df.to_sql("devices", conn, if_exists="append", index=False)
        print("✓ Devices loaded")

        # Insert trades
        trades_df.to_sql("trades", conn, if_exists="append", index=False)
        print("✓ Trades loaded")

        # Insert withdrawals
        withdrawals_df.to_sql("withdrawals", conn, if_exists="append", index=False)
        print("✓ Withdrawals loaded")


def regenerate_features():
    """Regenerate features after loading drift data."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    from app.services.feature_engineering import FeatureEngineeringService

    print("\nRegenerating features...")

    # Use synchronous engine with psycopg2
    engine = create_engine(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))

    # Create a session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Create a wrapper that makes the sync session look like async
        class SyncSessionWrapper:
            def __init__(self, sync_session):
                self._sync_session = sync_session

            async def get(self, model, key):
                return self._sync_session.get(model, key)

            async def execute(self, stmt):
                result = self._sync_session.execute(stmt)
                return result

            async def commit(self):
                self._sync_session.commit()

            async def refresh(self, obj):
                self._sync_session.refresh(obj)

            async def add(self, obj):
                self._sync_session.add(obj)

            def __getattr__(self, name):
                return getattr(self._sync_session, name)

        # Use synchronous approach directly
        from app.models.database import User, FeatureTable
        import pandas as pd
        from datetime import datetime, timezone

        # Get all users
        users = session.query(User.user_id).all()

        # Simple feature calculation (mirroring the feature engineering logic)
        from sqlalchemy import func, text

        count = 0
        for (user_id,) in users:
            # Calculate features using more comprehensive SQL
            result = session.execute(text("""
                WITH user_trades AS (
                    SELECT side, price, quantity, timestamp FROM trades WHERE user_id = :uid
                ),
                user_withdrawals AS (
                    SELECT amount, is_new_address, timestamp FROM withdrawals WHERE user_id = :uid
                ),
                trade_days AS (
                    SELECT DISTINCT DATE(timestamp) as trade_day FROM user_trades
                ),
                withdrawal_days AS (
                    SELECT DISTINCT DATE(timestamp) as withdraw_day FROM user_withdrawals
                ),
                trade_counts AS (
                    SELECT
                        COUNT(*) FILTER (WHERE side = 'BUY') as buy_count,
                        COUNT(*) FILTER (WHERE side = 'SELL') as sell_count,
                        COUNT(*) as total_count
                    FROM user_trades
                )
                SELECT
                    (SELECT COUNT(*) FROM user_trades WHERE timestamp >= NOW() - INTERVAL '1 day')::int as tf24h,
                    (SELECT COUNT(*) FROM user_trades WHERE timestamp >= NOW() - INTERVAL '7 days')::int as tf7d,
                    (SELECT COALESCE(SUM(price * quantity), 0) FROM user_trades WHERE timestamp >= NOW() - INTERVAL '1 day')::decimal as tv24h,
                    (SELECT COUNT(DISTINCT d.device_id) FROM devices d JOIN devices d2 ON d.device_id = d2.device_id AND d2.user_id = :uid WHERE d.user_id != :uid) as sdc,
                    (SELECT COUNT(DISTINCT d.user_id) FROM devices d JOIN devices d2 ON d.device_id = d2.device_id WHERE d.user_id = :uid AND d2.user_id != :uid) as lac,
                    (SELECT COUNT(DISTINCT ip_address) FROM devices WHERE user_id = :uid) as uic,
                    (SELECT COUNT(*) FROM user_withdrawals WHERE timestamp >= NOW() - INTERVAL '1 day')::int as wf24h,
                    (SELECT COALESCE(SUM(amount), 0) FROM user_withdrawals WHERE timestamp >= NOW() - INTERVAL '1 day')::decimal as wv24h,
                    (SELECT EXTRACT(DAY FROM (NOW() - (SELECT account_created_time FROM users WHERE user_id = :uid))))::int as aad,
                    (SELECT COUNT(*) FROM trade_days) + (SELECT COUNT(*) FROM withdrawal_days) as adc,
                    (SELECT CASE
                        WHEN total_count = 0 THEN 0
                        ELSE LEAST(buy_count, sell_count)::float / total_count
                    END FROM trade_counts) as otr,
                    (SELECT CASE WHEN (SELECT COUNT(*) FROM user_withdrawals) > 0 THEN
                        (SELECT COUNT(*) FROM user_withdrawals WHERE is_new_address = true)::float / (SELECT COUNT(*) FROM user_withdrawals)
                        ELSE 0 END) as wrs
            """), {"uid": user_id}).fetchone()

            if result:
                # Create or update feature record
                feature = session.query(FeatureTable).filter_by(user_id=user_id).first()
                if not feature:
                    feature = FeatureTable(user_id=user_id)
                    session.add(feature)

                feature.trade_frequency_24h = result[0] or 0
                feature.trade_frequency_7d = result[1] or 0
                feature.trade_volume_24h = float(result[2] or 0)
                feature.shared_device_count = result[3] or 0
                feature.linked_account_count = result[4] or 0
                feature.unique_ip_count = result[5] or 0
                feature.withdrawal_frequency_24h = result[6] or 0
                feature.withdrawal_volume_24h = float(result[7] or 0)
                feature.account_age_days = result[8] or 0
                feature.active_days_count = result[9] or 1
                # Set opposite_trade_ratio: minority trade ratio (0-0.5)
                # This represents how mixed the user's trading is (0 = single side, 0.5 = balanced)
                feature.opposite_trade_ratio = float(result[10] or 0.0)
                feature.withdrawal_risk_score = float(result[11] or 0)

                # Calculate average trade size
                tf24h = result[0] or 1
                tv24h = float(result[2] or 0)
                feature.avg_trade_size = tv24h / max(tf24h, 1)

                feature.feature_calculated_at = datetime.now(timezone.utc)

                count += 1

        session.commit()
        print(f"✓ Features regenerated for {count} users")

    finally:
        session.close()


if __name__ == "__main__":
    print("="*60)
    print("UPDATE DATABASE WITH REALISTIC DRIFT DATA")
    print("="*60)

    # Clear existing data
    clear_database()

    # Load drift data
    load_drift_data("test_data/v3_realistic_drift")

    # Regenerate features
    regenerate_features()

    print("\n" + "="*60)
    print("Database updated successfully!")
    print("="*60)
    print("\nExpected PSI range: 0.25 - 1.0 (realistic drift)")
    print("Drift dataset: v3_realistic_drift")
    print("Check PSI at: http://localhost:8000/api/model/psi")
