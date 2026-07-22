# Model Monitoring & Performance Tracking

## Overview

Model Monitoring provides comprehensive visibility into model performance, feature distribution stability, and overall system health.

## Monitoring Dashboard Components

### 1. Model Overview Panel

Displays:
- Current model version and deployment timestamp
- Training metrics (AUC, KS)
- PSI status (current population stability)
- Feature count

### 2. Feature Distribution Panel

Per-feature visualization:
- Training baseline distribution
- Current production distribution
- PSI score for each feature
- Status indicator (stable/warning/drift)

### 3. Performance Metrics

Tracked metrics:
- **AUC** (Area Under ROC): Overall discrimination ability (target: >0.75)
- **KS** (Kolmogorov-Smirnov): Maximum separation between distributions (target: >0.30)
- **PSI** (Population Stability Index): Model drift detection (target: <0.10)

### 4. Baseline Validation

Validation performed during training:
- Compares baseline against training dataframe
- Expected PSI ≈ 0 (baseline consistency check)
- Ensures baseline was correctly created

## Monitoring Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│              MODEL MONITORING LIFECYCLE                      │
└─────────────────────────────────────────────────────────────┘

Training:
    Train Model → Create PSI Baseline → Validate Baseline → Deploy

Production Monitoring:
    Load Current Data → Load Baseline → Calculate PSI → Display Status

Continuous Tracking:
    Per-Feature PSI → Overall Status → Retrain Recommendation
```

## API Integration

### Monitoring Status Endpoint

```
GET /api/model/monitoring/status
```

Response includes:
- Model metadata
- PSI scores per feature
- Baseline information
- Overall monitoring status
- Retrain recommendations

### Model Metadata Query

```
GET /api/model/metadata
```

Returns all model versions with:
- Training metrics
- PSI validation results
- Deployment status

## Operational Considerations

### Monitoring Frequency

- **Real-time**: Feature distribution updates on each pipeline run
- **Batch**: PSI calculations triggered on monitoring API calls
- **Historical**: PSI snapshots stored in ModelMetadata table

### Alert Thresholds

| Condition | Alert Type | Action Required |
|-----------|------------|-----------------|
| PSI > 0.25 (any feature) | Severe Drift | Immediate retraining recommended |
| PSI 0.1-0.25 (any feature) | Warning | Monitor closely, plan retraining |
| Overall PSI < 0.1 | Stable | Continue normal operations |

### Data Requirements

For accurate PSI monitoring:
- Baseline must exist in training artifacts
- Current feature table must be populated
- Feature schema must match training

## UI Features

### Feature Distribution Charts

- Side-by-side comparison (baseline vs current)
- Color-coded by PSI status
- Interactive tooltips for detailed values

### Model Selection

- View active model metrics
- Compare historical model versions
- Track performance over time

### Export Capability

- Download monitoring reports
- Export PSI analysis results
- Model performance comparison
