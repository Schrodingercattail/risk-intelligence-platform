# Drift Dataset and Model Monitoring UI Updates - Summary

## Changes Completed

### 1. Realistic Drift Dataset (v3_realistic_drift)

**Design Goals Achieved:**
- Overall PSI: 0.25 - 0.8 (realistic production drift)
- No single sparse feature dominates PSI
- Sparse features maintain similar zero-inflated shapes (~85-92% zero)
- Monetary features have moderate shift only
- Trading/withdrawal behavior shifts gradually

**Drift Patterns Implemented:**
- 25% accounts 15-45 days (moderate account age shift)
- 25% users with 30-45 trades (moderate trading increase)
- 20% users with 4-7 withdrawals (moderate withdrawal increase)
- 13% with shared devices (maintains ~85-92% zero - similar to baseline)
- 17% baseline-like users (provides stability)

**Files:**
- `test_data/v3_realistic_drift/generate_realistic_drift.py` - Updated generator script
- `test_data/v3_realistic_drift/*.csv` - Generated dataset (2000 users, 58,850 trades, 5,896 withdrawals)

### 2. Model Monitoring UI Updates

**Changes to `frontend/src/pages/ModelMonitoring.tsx`:**

1. **Overall PSI as Main KPI**
   - PSI displayed first in performance metrics grid
   - Larger font size (4xl) for PSI value
   - Color-coded status badge (Stable/Minor Shift/Moderate Drift)
   - Added comprehensive tooltip explaining PSI ranges

2. **Sparse Distribution Handling**
   - Features with PSI > 1.0 highlighted with yellow background
   - "(sparse distribution)" label for high PSI values
   - Warning note explaining sparse features naturally have higher PSI
   - Filtering out features with PSI < 0.05 to reduce noise

3. **Business-Friendly Feature Explanations**
   - Added `FEATURE_EXPLANATIONS` mapping for all 13 features
   - Shows "Business Meaning" column in drift table
   - Examples:
     - `account_age_days`: "Account tenure - newer users may have different risk patterns"
     - `trade_frequency_7d`: "Weekly trading volume - changes indicate usage pattern shifts"

4. **Improved PSI Tooltips**
   - `OverallPSITooltip`: Explains PSI compares current vs training baseline
   - `FeatureDriftTooltip`: Updated with note about sparse distributions
   - Color-coded PSI ranges (green/yellow/orange/red)

5. **Top Drifted Features Table**
   - Shows top 8 features (filtered by PSI > 0.05)
   - Sorted by PSI value (highest first)
   - Business meaning column
   - Sparse distribution indicators

6. **Enhanced PSI Chart**
   - Legend showing PSI ranges
   - Color-coded bars based on PSI value (not just status)
   - Green (<0.1), Yellow (0.1-0.25), Orange (0.25-0.8), Red (>0.8)

### 3. Expected Demo Results

**Target Metrics:**
- AUC: 0.85 - 0.95
- KS: 0.6 - 0.85
- PSI: 0.3 - 0.8

**PSI Status:**
- `overall_status: 'drift'` - Moderate drift detected
- `max_psi: 0.25 - 0.8` - Within realistic range
- No single sparse feature dominates (>1.0)
- Top drifted features will be account_age_days, trade_frequency_*, withdrawal_*

## Usage

```bash
# Generate drift dataset (if needed)
cd test_data/v3_realistic_drift
python generate_realistic_drift.py

# Load to database for testing
cd ml-models/training
python update_database_with_drift.py

# Check PSI via API
curl http://localhost:8000/api/model/psi | jq .

# Expected response structure:
{
  "overall_status": "drift",
  "max_psi": 0.45,
  "drift_features": ["account_age_days", "trade_frequency_24h", "withdrawal_frequency_24h"],
  "feature_psi": {
    "account_age_days": 0.45,
    "trade_frequency_24h": 0.38,
    "withdrawal_frequency_24h": 0.32,
    ...
  }
}
```

## Files Modified

1. `test_data/v3_realistic_drift/generate_realistic_drift.py` - Updated generator
2. `frontend/src/pages/ModelMonitoring.tsx` - Enhanced UI with PSI improvements
3. `ml-models/training/update_database_with_drift.py` - Updated to use v3_realistic_drift (earlier)

## Technical Notes

- Sparse features (shared_device_count, linked_account_count) have 5 bins vs 10 for dense features
- Zero-inflated distributions naturally produce higher PSI values - this is expected behavior
- The UI now properly handles this by adding context labels and warnings
- Overall PSI is the primary KPI for model health monitoring
