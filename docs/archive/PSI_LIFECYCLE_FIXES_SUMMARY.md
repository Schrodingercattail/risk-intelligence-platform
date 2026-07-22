# PSI Lifecycle Fixes Summary

## Date: 2026-07-21

## Issue Description

The PSI (Population Stability Index) calculation lifecycle had several integration issues:
1. Training script didn't create baseline distribution during model training
2. Baseline filename inconsistency across services (`feature_baseline.json` vs `feature_distribution.json`)
3. Old baseline files contained incorrect features

## Root Causes

1. **Missing Integration**: `train_risk_model.py` never called `save_baseline_distribution()`
2. **Filename Inconsistency**: Different services used different default filenames:
   - `model.py` saved to `feature_distribution.json`
   - PSI services looked for `feature_baseline.json`
3. **Stale Baselines**: Old baseline files had extra features like `first_withdrawal_flag`

## Fixes Applied

### 1. Training Script Integration (`ml-models/training/train_risk_model.py`)

**Before:**
```python
print(f"\n{'='*50}")
print("Model Saved Successfully!")
```

**After:**
```python
# Save PSI baseline distribution for monitoring
print(f"\n{'='*50}")
print("Creating PSI Baseline Distribution")
print(f"{'='*50}")

baseline_path = trainer.save_baseline_distribution(features_df)
print(f"✓ PSI baseline saved to: {baseline_path}")
```

**Impact**: Training now automatically creates the PSI baseline as part of the model training workflow.

### 2. Standardized Baseline Filename (`backend/app/ml/model.py`)

**Before:**
```python
if output_path is None:
    output_path = f"{self.model_path}/feature_distribution.json"
```

**After:**
```python
if output_path is None:
    output_path = str(Path(self.model_path) / "feature_baseline.json")
```

**Impact**: All services now use `feature_baseline.json` consistently.

### 3. Fixed Method Bug (`backend/app/services/psi_service.py`)

The `create_and_save_baseline()` method had unreachable code due to early return.

**Before:**
```python
if baseline_path is None:
    baseline_path = str(Path(settings.MODEL_PATH) / "feature_baseline.json")

self.analyzer.save_baseline(baseline, baseline_path)  # 'baseline' undefined!

return baseline_path

# Unreachable code below
feature_cols = [...]
baseline = self.analyzer.create_baseline_distribution(...)
```

**After:**
```python
if baseline_path is None:
    baseline_path = str(Path(settings.MODEL_PATH) / "feature_baseline.json")

feature_cols = [...]
baseline = self.analyzer.create_baseline_distribution(features_df, feature_cols)
self.analyzer.save_baseline(baseline, baseline_path)

return baseline_path
```

**Impact**: Method now works correctly.

### 4. Clean Baseline Regeneration

- Removed stale `feature_distribution.json`
- Removed old `feature_baseline.json` with extra features
- Ran training to create clean baseline with exactly 13 official features

## Verification

### Baseline File Structure
The new `feature_baseline.json` contains exactly 13 official risk features:

1. trade_frequency_7d
2. trade_frequency_24h
3. trade_volume_24h
4. withdrawal_volume_24h
5. account_age_days
6. avg_trade_size
7. shared_device_count
8. linked_account_count
9. unique_ip_count
10. withdrawal_frequency_24h
11. withdrawal_risk_score
12. opposite_trade_ratio
13. active_days_count

### PSI Calculation Working
```bash
curl http://localhost:8000/api/model/monitoring
```

Returns proper PSI values with per-feature breakdown.

## PSI Lifecycle Now Working Correctly

1. **Training Phase**: `train_risk_model.py` creates baseline distribution
2. **Baseline Saved**: `ml-models/artifacts/feature_baseline.json`
3. **Monitoring Phase**: `model_monitoring_service.py` loads baseline and calculates PSI
4. **Consistency**: All services use same filename and 13 features

## Files Modified

- `ml-models/training/train_risk_model.py` - Added baseline creation
- `backend/app/ml/model.py` - Standardized filename to `feature_baseline.json`
- `backend/app/services/psi_service.py` - Fixed method bug

## Testing Checklist

- [x] Training creates baseline automatically
- [x] Baseline filename consistent across all services
- [x] Baseline contains exactly 13 official features
- [x] PSI calculation endpoint returns valid results
- [x] No extra features in baseline file
