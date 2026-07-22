# Drift Dataset Generation System

## Overview

This system provides multiple drift datasets for PSI (Population Stability Index) monitoring validation. PSI detects feature distribution drift between the training baseline and current production data.

## Dataset Directory Structure

```
test_data/
├── v2_diverse/                    # Training baseline (no drift)
├── v3_drift/                      # High drift (max_psi > 0.10)
├── v3_realistic_drift/            # Moderate drift (0.25 - 1.0)
├── v3_subtle_drift/               # Subtle drift (0.25 - 0.80)
└── v3_controlled_drift/           # CSV files only
```

## Dataset Characteristics

### v2_diverse (Baseline)
- **Purpose**: Training data and PSI baseline reference
- **Users**: 2000
- **Characteristics**: Mixed account ages, normal trading patterns, baseline withdrawal activity
- **Expected PSI**: N/A (this is the reference)

### v3_drift (High Drift)
- **Purpose**: Validate PSI detects significant drift
- **Users**: 2000
- **Drift Patterns**:
  - 40% accounts < 7 days old (high account age drift)
  - 25% high-frequency traders (80-150 trades)
  - 20% high-volume withdrawers (8-20 withdrawals)
  - 10% shared device users
- **Expected PSI**: > 0.10 (warning or drift status)
- **Use Case**: Validate PSI detects extreme distribution changes

### v3_realistic_drift (Moderate Drift)
- **Purpose**: Simulate realistic production data drift
- **Users**: 2000
- **Drift Patterns**:
  - 30% moderate new accounts (7-30 days old)
  - 25% moderate activity traders (40-65 trades)
  - 20% moderate withdrawal users (4-8 withdrawals)
  - 25% normal users
- **Expected PSI**: 0.25 - 1.0 (drift but not extreme)
- **Use Case**: Most common for testing - realistic gradual shift

### v3_subtle_drift (Subtle Drift)
- **Purpose**: Test PSI sensitivity to minimal changes
- **Users**: 2000
- **Drift Patterns**:
  - 90% baseline-like users
  - 10% subtle drift users (minimal changes)
- **Expected PSI**: 0.25 - 0.80 (barely detectable drift)
- **Use Case**: Validate PSI catches subtle population shifts

## PSI Baseline Creation

The PSI baseline is created from v2_diverse training data:

```bash
cd ml-models/training
python create_baseline_from_training.py
```

This generates `ml-models/artifacts/feature_baseline.json` with:
- Bin boundaries for each feature
- Reference distribution percentages
- Feature metadata (log_transformed, sparse_count_bins)

## Loading Drift Data to Database

To simulate production data drift:

```bash
cd ml-models/training
python update_database_with_drift.py
```

This script:
1. Clears existing database data
2. Loads v3_realistic_drift CSV files
3. Regenerates features
4. Makes current data available for PSI comparison

**Note**: Default dataset is now `v3_realistic_drift` (moderate, realistic drift)

## PSI Validation Workflow

### 1. Start with Baseline (v2_diverse)
```bash
# Upload v2_diverse data
curl -X POST http://localhost:8000/api/pipeline/upload \
  -F "users=@test_data/v2_diverse/users.csv" \
  -F "devices=@test_data/v2_diverse/devices.csv" \
  -F "trades=@test_data/v2_diverse/trades.csv" \
  -F "withdrawals=@test_data/v2_diverse/withdrawals.csv"

# Run pipeline to create baseline
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"run_full_pipeline": true, "generate_risk_events": true, "train_model": true}'
```

### 2. Upload Drift Dataset
```bash
# Upload drift dataset (e.g., v3_realistic_drift)
curl -X POST http://localhost:8000/api/pipeline/upload \
  -F "users=@test_data/v3_realistic_drift/users.csv" \
  -F "devices=@test_data/v3_realistic_drift/devices.csv" \
  -F "trades=@test_data/v3_realistic_drift/trades.csv" \
  -F "withdrawals=@test_data/v3_realistic_drift/withdrawals.csv"

# Run pipeline (DO NOT retrain - keeps baseline intact)
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"run_full_pipeline": true, "generate_risk_events": true, "train_model": false}'
```

### 3. Check PSI
```bash
curl http://localhost:8000/api/model/psi | jq .
```

Expected response for v3_realistic_drift:
```json
{
  "overall_status": "drift",
  "max_psi": 0.35,
  "drift_features": [
    "account_age_days",
    "trade_frequency_24h",
    "withdrawal_frequency_24h"
  ],
  "feature_psi": {
    "account_age_days": 0.45,
    "trade_frequency_24h": 0.35,
    "withdrawal_frequency_24h": 0.30
  }
}
```

## PSI Interpretation

- **PSI < 0.10**: No significant drift (stable)
- **PSI 0.10 - 0.25**: Minor drift (warning)
- **PSI > 0.25**: Significant drift (drift detected)

## Regenerating Drift Datasets

Each drift dataset has a generator script:

```bash
# Generate v3_drift
cd test_data/v3_drift
python generate_drift_dataset.py

# Generate v3_realistic_drift
cd test_data/v3_realistic_drift
python generate_realistic_drift.py

# Generate v3_subtle_drift
cd test_data/v3_subtle_drift
python generate_subtle_drift.py
```

## Files Modified

- `ml-models/training/update_database_with_drift.py` - Updated to use v3_realistic_drift
- `ml-models/artifacts/feature_baseline.json` - PSI baseline from v2_diverse

## Next Steps

1. Verify PSI baseline exists and is valid
2. Test drift detection with v3_realistic_drift
3. Validate PSI endpoint returns expected values
4. Test PSI monitoring in Risk Command Center UI
