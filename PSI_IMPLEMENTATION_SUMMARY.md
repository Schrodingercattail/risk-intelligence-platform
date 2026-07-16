# PSI (Population Stability Index) Implementation Summary

## Implementation Status: ✅ COMPLETE

The PSI-based model monitoring system is fully implemented and integrated across the platform.

---

## Architecture Overview

```
Training Pipeline
    ↓
Model Training (LightGBM)
    ↓
Baseline Distribution Created (feature_distribution.json)
    ↓
Model Deployed
    ↓
Current Scoring Features (Database)
    ↓
PSI Calculation (Training vs Current)
    ↓
PSI API Endpoint
    ↓
Frontend Model Monitoring Dashboard
```

---

## Components Implemented

### 1. PSI Calculation Module ✅
**File:** `backend/app/ml/psi.py`

**Class:** `PSIAnalyzer`

**Key Methods:**
- `calculate_psi()` - Core PSI calculation using formula: Σ(actual_pct - expected_pct) * ln(actual_pct / expected_pct)
- `calculate_feature_psi()` - Calculate PSI for multiple features
- `create_baseline_distribution()` - Create baseline from training data using quantile binning (10 bins)
- `calculate_psi_from_baseline()` - Calculate PSI using pre-saved baseline
- `get_overall_psi_status()` - Return overall status and drift features
- `save_baseline()` / `load_baseline()` - Persist baseline distribution to JSON

**PSI Thresholds:**
- `< 0.10`: Stable (green)
- `0.10 - 0.25`: Warning (yellow) - minor drift
- `≥ 0.25`: Significant drift (red) - retrain recommended

---

### 2. Model Monitoring Service ✅
**File:** `backend/app/services/model_monitoring_service.py`

**Class:** `ModelMonitoringService`

**Key Methods:**
- `calculate_psi()` - Load baseline, get current features, calculate PSI
- `get_current_model_metrics()` - Combine AUC, KS, PSI, feature importance
- `_get_current_features()` - Load current features from FeatureTable
- `create_baseline_from_current_data()` - Initialize PSI monitoring from current data

**Integration Points:**
- Uses `PSIAnalyzer` for PSI calculation
- Queries `FeatureTable` database for current features
- Loads baseline from `{MODEL_PATH}/feature_distribution.json`

---

### 3. API Endpoints ✅
**File:** `backend/app/api/routes/model.py`

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/model/psi` | GET | Get PSI monitoring data for all features |
| `/api/model/monitoring` | GET | Get complete monitoring (AUC, KS, PSI, feature importance) |
| `/api/model/baseline/create` | POST | Create PSI baseline from current database features |

**Response Format:**
```json
{
  "model_name": "LightGBM Risk Model",
  "version": "v1.0",
  "metrics": {
    "auc": 0.86,
    "ks": 0.42,
    "psi": 0.08
  },
  "psi_status": "stable",
  "psi_features": [
    {
      "feature": "shared_device_count",
      "psi": 0.03,
      "status": "stable"
    }
  ]
}
```

---

### 4. Frontend API Client ✅
**File:** `frontend/src/services/api.ts`

**Added Methods:**
- `modelApi.getMonitoring()` - Fetch complete monitoring data

**Added Types:**
```typescript
interface PSIFeature {
  feature: string;
  psi: number;
  status: 'stable' | 'warning' | 'drift';
}

interface ModelMonitoringData {
  model_name: string;
  version: string;
  metrics: {
    auc: number;
    ks: number;
    psi: number;
  };
  psi_status: 'stable' | 'warning' | 'drift' | 'unknown';
  psi_features: PSIFeature[];
}
```

---

### 5. Frontend Model Monitoring Page ✅
**File:** `frontend/src/pages/ModelMonitoring.tsx`

**Features:**
- **Model Performance Section:** Display AUC and KS with explanations
- **PSI Monitoring Section:**
  - Overall PSI Status badge (stable/warning/drift)
  - Feature Drift Analysis table with PSI values per feature
  - Color-coded PSI chart (horizontal bar chart)
  - PSI explanation tooltip with thresholds
- **Feature Importance Section:** Global feature importance display

**Status Colors:**
- Stable: `bg-green-100 text-green-800`
- Warning: `bg-yellow-100 text-yellow-800`
- Drift: `bg-red-100 text-red-800`

---

## PSI Calculation Flow

1. **Training Phase:**
   - Model is trained on training data
   - `PSIAnalyzer.create_baseline_distribution()` creates baseline distribution
   - Baseline saved to `{MODEL_PATH}/feature_distribution.json`

2. **Production Phase:**
   - Current features are extracted from `FeatureTable` database
   - `PSIAnalyzer.calculate_psi_from_baseline()` compares current vs baseline
   - PSI calculated per feature using quantile binning (10 bins)
   - Overall status determined by maximum PSI across all features

3. **Monitoring Phase:**
   - Frontend calls `/api/model/monitoring`
   - Service returns complete metrics (AUC, KS, PSI, feature importance)
   - Frontend displays PSI status per feature and overall

---

## Database Schema

**Tables Used:**
- `model_metadata` - Stores model info including `psi_score`
- `feature_importance` - Stores feature rankings
- `feature_table` - Stores current feature values for PSI comparison

**Feature Columns for PSI:**
1. shared_device_count
2. linked_account_count
3. unique_ip_count
4. trade_frequency_24h
5. trade_frequency_7d
6. opposite_trade_ratio
7. avg_trade_size
8. trade_volume_24h
9. account_age_days
10. active_days_count
11. withdrawal_risk_score
12. withdrawal_frequency_24h

---

## Training Pipeline Integration

**File:** `ml-models/training/train_risk_model.py`

**Baseline Creation:**
- Method: `save_baseline_distribution()` (lines 241-268)
- Saves to: `./ml-models/artifacts/feature_distribution.json`
- Called during model training after feature engineering

**Model Artifacts:**
- `risk_model_{timestamp}.pkl` - timestamped model version
- `risk_model_latest.pkl` - latest model for inference
- `feature_distribution.json` - PSI baseline distribution

---

## API Usage Examples

### Get PSI Data Only
```bash
curl http://localhost:8000/api/model/psi
```

### Get Complete Monitoring Data
```bash
curl http://localhost:8000/api/model/monitoring
```

### Create PSI Baseline
```bash
curl -X POST http://localhost:8000/api/model/baseline/create
```

---

## Frontend Display

### PSI Status Badge
- Shows overall PSI status (Stable/Warning/Drift)
- Color-coded based on maximum PSI across all features

### Feature Drift Analysis Table
| Feature | PSI Value | Status |
|---------|-----------|--------|
| shared_device_count | 0.03 | Stable |
| trade_frequency_24h | 0.15 | Warning |
| withdrawal_risk_score | 0.30 | Drift |

### PSI Chart
- Horizontal bar chart showing PSI values per feature
- Color-coded bars (green/yellow/red) based on status

---

## PSI Interpretation Guide

| PSI Value | Status | Meaning | Action |
|-----------|--------|---------|--------|
| < 0.10 | Stable | No significant distribution change | Continue monitoring |
| 0.10 - 0.25 | Warning | Minor distribution shift | Investigate, consider retraining |
| ≥ 0.25 | Drift | Significant distribution change | Retrain model recommended |

---

## Testing Checklist

- [x] PSI module implementation verified
- [x] Model monitoring service implementation verified
- [x] API endpoints defined and documented
- [x] Frontend API client method added
- [x] Frontend model monitoring page displays PSI
- [ ] Baseline distribution file creation (requires model training)
- [ ] End-to-end PSI calculation testing (requires trained model)

---

## Next Steps

1. **Train the model:** Run training script to create model artifacts and baseline
   ```bash
   python ml-models/training/train_risk_model.py
   ```

2. **Create PSI baseline (if not created during training):**
   ```bash
   curl -X POST http://localhost:8000/api/model/baseline/create
   ```

3. **Verify PSI monitoring:**
   - Access Model Monitoring page in frontend
   - Verify PSI values are displayed
   - Check overall PSI status badge

4. **Monitor PSI over time:**
   - Regular PSI checks for model drift
   - Retrain model when PSI indicates drift

---

## Implementation Details

### PSI Formula
```
PSI = Σ(actual_pct - expected_pct) * ln(actual_pct / expected_pct)
```

### Binning Strategy
- Quantile-based binning (10 bins by default)
- Bins determined from training data distribution
- Same bins applied to current data for comparison

### Feature Coverage
- All 12 feature columns monitored
- Individual PSI per feature
- Overall PSI = maximum feature PSI

---

## Files Modified

1. **frontend/src/services/api.ts** - Added `getMonitoring()` method and `ModelMonitoringData` type
2. All other PSI components were already implemented

---

## Conclusion

The PSI-based model monitoring system is **fully implemented** and ready for use. The only remaining step is to train the model to create the baseline distribution file and enable end-to-end PSI monitoring.

Once the model is trained, the system will automatically:
1. Calculate PSI for all features
2. Display PSI values in the Model Monitoring dashboard
3. Alert when distribution drift is detected
4. Recommend retraining when PSI exceeds thresholds
