"""
Quick utility to switch between drift datasets for PSI testing.

Usage:
    python switch_drift_dataset.py --list              # List available datasets
    python switch_drift_dataset.py --dataset v3_subtle # Switch to subtle drift
    python switch_drift_dataset.py --dataset v3_drift # Switch to high drift
"""
import sys
import argparse
from pathlib import Path

# Available drift datasets
DRIFT_DATASETS = {
    "v3_drift": {
        "name": "High Drift",
        "description": "Significant distribution shifts (max_psi > 0.10)",
        "expected_psi": "> 0.10",
        "users": 2000
    },
    "v3_realistic_drift": {
        "name": "Realistic Drift (Default)",
        "description": "Moderate, realistic production drift (0.25 - 1.0)",
        "expected_psi": "0.25 - 1.0",
        "users": 2000
    },
    "v3_subtle_drift": {
        "name": "Subtle Drift",
        "description": "Minimal population changes (0.25 - 0.80)",
        "expected_psi": "0.25 - 0.80",
        "users": 2000
    }
}

# The update script path
UPDATE_SCRIPT = Path(__file__).parent.parent / "ml-models" / "training" / "update_database_with_drift.py"


def list_datasets():
    """List all available drift datasets."""
    print("\n" + "="*70)
    print("Available Drift Datasets")
    print("="*70)

    for key, info in DRIFT_DATASETS.items():
        print(f"\n[{key}]")
        print(f"  Name: {info['name']}")
        print(f"  Description: {info['description']}")
        print(f"  Expected PSI: {info['expected_psi']}")
        print(f"  Users: {info['users']}")

    print("\n" + "="*70)
    print("Usage: python switch_drift_dataset.py --dataset <key>")
    print("="*70 + "\n")


def verify_dataset(dataset_key: str) -> bool:
    """Verify that a dataset's CSV files exist."""
    dataset_path = Path(__file__).parent / dataset_key

    if not dataset_path.exists():
        print(f"❌ Dataset directory not found: {dataset_path}")
        return False

    required_files = ["users.csv", "devices.csv", "trades.csv", "withdrawals.csv"]
    missing_files = []

    for filename in required_files:
        file_path = dataset_path / filename
        if not file_path.exists():
            missing_files.append(filename)

    if missing_files:
        print(f"❌ Missing required files in {dataset_key}:")
        for f in missing_files:
            print(f"   - {f}")
        return False

    print(f"✓ Dataset verified: {dataset_key}")
    return True


def update_loader_script(dataset_key: str) -> bool:
    """Update the loader script to use the specified dataset."""
    if not UPDATE_SCRIPT.exists():
        print(f"❌ Loader script not found: {UPDATE_SCRIPT}")
        return False

    # Read the script
    content = UPDATE_SCRIPT.read_text()

    # Check if dataset is already configured
    if f'test_data/{dataset_key}"' in content:
        print(f"✓ Loader script already configured for {dataset_key}")
        return True

    # Replace the dataset reference (find any v3_* reference)
    import re
    pattern = r'test_data/v3_[a-z_]+"'
    new_content = re.sub(pattern, f'test_data/{dataset_key}"', content)

    if new_content == content:
        print(f"⚠️  Could not find dataset reference to update")
        return False

    # Write updated script
    UPDATE_SCRIPT.write_text(new_content)
    print(f"✓ Updated loader script to use {dataset_key}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Switch between drift datasets for PSI testing"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available drift datasets"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        choices=list(DRIFT_DATASETS.keys()),
        help="Dataset to switch to"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify dataset, don't update loader script"
    )

    args = parser.parse_args()

    if args.list:
        list_datasets()
        return 0

    if args.dataset:
        dataset_info = DRIFT_DATASETS[args.dataset]

        print(f"\n{'='*70}")
        print(f"Switching to: {dataset_info['name']}")
        print(f"{'='*70}\n")

        # Verify dataset exists and is complete
        if not verify_dataset(args.dataset):
            return 1

        # Update loader script (unless verify-only)
        if not args.verify_only:
            if not update_loader_script(args.dataset):
                return 1

            print(f"\n{'='*70}")
            print("✓ Configuration updated successfully")
            print(f"{'='*70}")
            print(f"\nNext steps:")
            print(f"1. Run: cd ml-models/training && python update_database_with_drift.py")
            print(f"2. Check PSI: curl http://localhost:8000/api/model/psi | jq .")
            print(f"3. Expected PSI: {dataset_info['expected_psi']}")
            print(f"\n")

        return 0

    # No arguments - show list
    list_datasets()
    return 0


if __name__ == "__main__":
    sys.exit(main())
