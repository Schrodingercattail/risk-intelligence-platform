"""
Migration: Add algorithm, model_type, feature_count to model_metadata table

Run this script to add new columns to an existing database:
    python -m app.migrations.add_model_metadata_fields
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
    """Add new columns to model_metadata table."""
    async with engine.begin() as conn:
        # Check if columns already exist
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'model_metadata' AND column_name IN ('algorithm', 'model_type', 'feature_count')
        """))
        existing_columns = [row[0] for row in result]

        # Add algorithm column if it doesn't exist
        if 'algorithm' not in existing_columns:
            await conn.execute(text("""
                ALTER TABLE model_metadata ADD COLUMN algorithm VARCHAR(50)
            """))
            print("✓ Added algorithm column")
        else:
            print("- algorithm column already exists")

        # Add model_type column if it doesn't exist
        if 'model_type' not in existing_columns:
            await conn.execute(text("""
                ALTER TABLE model_metadata ADD COLUMN model_type VARCHAR(50)
            """))
            print("✓ Added model_type column")
        else:
            print("- model_type column already exists")

        # Add feature_count column if it doesn't exist
        if 'feature_count' not in existing_columns:
            await conn.execute(text("""
                ALTER TABLE model_metadata ADD COLUMN feature_count INTEGER
            """))
            print("✓ Added feature_count column")
        else:
            print("- feature_count column already exists")

        print("\nMigration complete!")


async def downgrade():
    """Remove new columns from model_metadata table (if needed)."""
    async with engine.begin() as conn:
        # Drop columns
        await conn.execute(text("ALTER TABLE model_metadata DROP COLUMN IF EXISTS algorithm"))
        await conn.execute(text("ALTER TABLE model_metadata DROP COLUMN IF EXISTS model_type"))
        await conn.execute(text("ALTER TABLE model_metadata DROP COLUMN IF EXISTS feature_count"))
        print("✓ Removed algorithm, model_type, feature_count columns")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate model_metadata table")
    parser.add_argument("--downgrade", action="store_true", help="Reverse the migration")
    args = parser.parse_args()

    if args.downgrade:
        asyncio.run(downgrade())
    else:
        asyncio.run(upgrade())
