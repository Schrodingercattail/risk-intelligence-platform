"""
Migration: Add pipeline_run_id and model_version to risk_events table

This migration adds pipeline tracking fields to RiskEvent for:
- Tracking which pipeline run created each risk event
- Recording which model version was used for scoring
- Supporting history queries by pipeline run

Run this script to add new columns to an existing database:
    python -m app.migrations.add_riskevent_lifecycle_fields
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import engine


async def upgrade():
    """Add pipeline_run_id and model_version columns to risk_events table."""
    async with engine.begin() as conn:
        # Check if columns already exist
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'risk_events' AND column_name IN ('pipeline_run_id', 'model_version')
        """))
        existing_columns = [row[0] for row in result]

        # Add pipeline_run_id column if it doesn't exist
        if 'pipeline_run_id' not in existing_columns:
            await conn.execute(text("""
                ALTER TABLE risk_events ADD COLUMN pipeline_run_id VARCHAR(50)
            """))
            print("✓ Added pipeline_run_id column")
        else:
            print("- pipeline_run_id column already exists")

        # Add model_version column if it doesn't exist
        if 'model_version' not in existing_columns:
            await conn.execute(text("""
                ALTER TABLE risk_events ADD COLUMN model_version VARCHAR(20)
            """))
            print("✓ Added model_version column")
        else:
            print("- model_version column already exists")

        # Add index for pipeline_run_id to support efficient queries
        result = await conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'risk_events' AND indexname = 'idx_risk_events_pipeline_run'
        """))
        if not result.scalar():
            await conn.execute(text("""
                CREATE INDEX idx_risk_events_pipeline_run ON risk_events(pipeline_run_id, detected_at)
            """))
            print("✓ Added idx_risk_events_pipeline_run index")
        else:
            print("- idx_risk_events_pipeline_run index already exists")

    print("\nMigration completed successfully!")


async def downgrade():
    """Remove pipeline_run_id and model_version columns from risk_events table."""
    async with engine.begin() as conn:
        # Drop index first
        result = await conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'risk_events' AND indexname = 'idx_risk_events_pipeline_run'
        """))
        if result.scalar():
            await conn.execute(text("""
                DROP INDEX IF EXISTS idx_risk_events_pipeline_run
            """))
            print("✓ Dropped idx_risk_events_pipeline_run index")

        # Drop columns
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'risk_events' AND column_name IN ('pipeline_run_id', 'model_version')
        """))
        existing_columns = [row[0] for row in result]

        if 'pipeline_run_id' in existing_columns:
            await conn.execute(text("""
                ALTER TABLE risk_events DROP COLUMN IF EXISTS pipeline_run_id
            """))
            print("✓ Dropped pipeline_run_id column")

        if 'model_version' in existing_columns:
            await conn.execute(text("""
                ALTER TABLE risk_events DROP COLUMN IF EXISTS model_version
            """))
            print("✓ Dropped model_version column")

    print("\nDowngrade completed successfully!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migration for RiskEvent lifecycle fields")
    parser.add_argument("--downgrade", action="store_true", help="Reverse the migration")
    args = parser.parse_args()

    if args.downgrade:
        print("Running downgrade...")
        asyncio.run(downgrade())
    else:
        print("Running upgrade...")
        asyncio.run(upgrade())
