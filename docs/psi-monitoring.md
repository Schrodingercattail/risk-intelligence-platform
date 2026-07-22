# PSI Monitoring & Model Drift Detection

## Overview

Population Stability Index (PSI) monitoring is implemented to detect model drift by comparing current production feature distributions against the training baseline.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 PSI MONITORING LIFECYCLE                     │
└─────────────────────────────────────────────────────────────┘

Training Phase:
    Dataset → PSI Analyzer → Create Baseline → Save JSON

Production Monitoring:
    Current Data → PSI Analyzer → Load Baseline → Calculate PSI
                                                           │
                                                           ▼
                                             PSI Score + Status
                                                           │
                              ┌──────────────────────────┴────────┐
                              │                                   │
                              ▼                                   ▼
                         PSI < 0.1                            PSI >= 0.1
                      "Stable"                            "Drift Detected"
```

## PSI Interpretation

| PSI Range | Status | Meaning | Action |
|-----------|--------|---------|--------|
| < 0.1 | Stable | No significant drift | Continue monitoring |
| 0.1 - 0.25 | Warning | Minor population shift | Review features, consider retraining |
| > 0.25 | Drift | Significant population change | Retrain model recommended |

## Implementation Components

### PSI Analyzer (`backend/app/ml/psi.py`)

- `create_baseline_distribution()`: Analyzes training data to establish reference distribution
- `calculate_psi()`: Compares current data against baseline
- `get_psi_status()`: Returns status classification (stable/warning/drift)

### Monitoring Service (`backend/app/services/model_monitoring_service.py`)

- Loads baseline from training artifacts
- Compares current feature table against baseline
- Returns PSI metrics per feature
- Provides overall drift assessment

## Baseline Validation PSI

A special PSI calculation performed during training to validate baseline correctness:

- Compares baseline distribution against training dataframe
- Should yield PSI ≈ 0 (or < 0.01) when baseline is correctly created
- Serves as self-consistency check for baseline generation

## Data Flow

### During Training

1. Training dataframe passed to PSI analyzer
2. Feature distributions analyzed (categorical: value counts, numerical: quantiles)
3. Baseline saved as JSON artifact
4. Validation PSI calculated (baseline vs training data)
5. `baseline_validation_psi` stored in ModelMetadata

### During Monitoring

1. Current feature table queried
2. Baseline loaded from training artifacts
3. PSI calculated for each feature
4. Overall PSI status determined
5. Results returned via monitoring API

## API Endpoints

```
GET /api/model/monitoring/status
Returns:
- Overall PSI status
- Per-feature PSI scores
- Feature counts compared
- Recommendation (stable/monitor/retrain)
```

## Test Datasets for PSI Validation

| Dataset | Purpose | Expected PSI |
|---------|---------|--------------|
| v2_diverse | Training baseline | N/A (used for baseline) |
| v3_subtle_drift | Stable monitoring | < 0.1 (Stable) |
| v3_realistic_drift | Warning drift demo | 0.1 - 0.25 (Warning) |
| v3_drift | Severe drift demo | > 0.25 (Drift) |
| v4_demo_production | Production validation | Per-feature analysis |
