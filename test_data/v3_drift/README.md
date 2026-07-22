# v3_drift Dataset - PSI Validation

## Purpose

This dataset simulates **production data drift** to validate PSI (Population Stability Index) monitoring.

PSI compares the **current population feature distribution** against the **original training baseline** to detect drift over time.

## Difference from v2_diverse Baseline

| Feature | v2_diverse (Baseline) | v3_drift (Current) | Drift Magnitude |
|---------|----------------------|-------------------|-----------------|
| **account_age_days** | Mixed distribution (30-180 days avg) | 40% accounts < 7 days | **HIGH** |
| **trade_frequency_24h** | Normal distribution (8-30 trades) | 25% users with 80-150 trades | **HIGH** |
| **trade_frequency_7d** | Moderate activity | Significantly increased | **HIGH** |
| **trade_volume_24h** | Normal range | Increased (larger positions) | **MEDIUM** |
| **withdrawal_frequency_24h** | Low (2-6 withdrawals) | 20% users with 8-20 withdrawals | **HIGH** |
| **withdrawal_volume_24h** | Normal amounts | Increased (2-10x larger) | **HIGH** |
| **shared_device_count** | Mostly unique | 10% shared device users | **LOW-MEDIUM** |
| **linked_account_count** | Mostly 0 | Slightly increased | **LOW** |

## Drift Patterns Introduced

### 1. Account Population Drift
- **40% of accounts are newly created** (< 7 days old)
- Simulates influx of new users after marketing campaign
- Expected to significantly shift `account_age_days` distribution

### 2. Transaction Behavior Drift
- **25% of users are high-frequency traders** (80-150 trades in 24h)
- Increased trade volume (larger position sizes)
- Expected to shift `trade_frequency_24h`, `trade_frequency_7d`, `trade_volume_24h`

### 3. Withdrawal Behavior Drift
- **20% of users have high withdrawal activity** (8-20 withdrawals in 24h)
- Increased withdrawal amounts (2-10x baseline)
- Expected to shift `withdrawal_frequency_24h`, `withdrawal_volume_24h`

### 4. Device/Network Drift
- **10% of users share devices** (organized into clusters)
- Slightly increased graph-related features
- Expected to shift `shared_device_count`, `linked_account_count`

## Expected PSI Behavior

After uploading v3_drift and running the pipeline:

### Before Upload (Baseline vs Current)
```bash
GET /api/model/psi
# Returns PSI comparing baseline (v2_diverse) vs current empty data
# May show "no_data" status if no current features exist
```

### After Upload and Pipeline Run
```bash
GET /api/model/psi
# Returns PSI comparing baseline (v2_diverse) vs v3_drift current data
```

**Expected Response:**
```json
{
  "overall_status": "warning" or "drift",
  "max_psi": 0.15 - 0.40,
  "drift_features": [
    "account_age_days",
    "trade_frequency_24h",
    "trade_frequency_7d",
    "withdrawal_frequency_24h",
    "withdrawal_volume_24h"
  ]
}
```

## Upload Steps

### 1. Clear Existing Data (Optional)
```bash
curl -X POST http://localhost:8000/api/pipeline/clear-data
```

### 2. Upload v3_drift Dataset
```bash
curl -X POST http://localhost:8000/api/pipeline/upload \
  -F "users=@test_data/v3_drift/users.csv" \
  -F "devices=@test_data/v3_drift/devices.csv" \
  -F "trades=@test_data/v3_drift/trades.csv" \
  -F "withdrawals=@test_data/v3_drift/withdrawals.csv" \
  -F "clear_existing=false"
```

### 3. Run Pipeline
```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "run_full_pipeline": true,
    "generate_risk_events": true,
    "train_model": false
  }'
```

### 4. Check PSI
```bash
curl http://localhost:8000/api/model/psi | jq .
```

## File Information

| File | Rows | Size |
|------|------|------|
| users.csv | 2,000 | 101 KB |
| devices.csv | 2,000 | 223 KB |
| trades.csv | 74,335 | 6.1 MB |
| withdrawals.csv | 7,483 | 780 KB |

## Schema Compatibility

✅ **Compatible** with existing pipeline upload API
✅ **Same columns** as v2_diverse dataset
✅ **Same data types** and relationships
✅ **No breaking changes** to ingestion logic

## SQL Queries for Feature Distribution Verification

### Before Upload (Baseline Distribution)
```sql
-- Run on v2_diverse data before clearing/uploading v3_drift

SELECT 
    COUNT(*) as total_users,
    AVG(account_age_days) as avg_account_age,
    AVG(trade_frequency_24h) as avg_trade_freq_24h,
    AVG(trade_frequency_7d) as avg_trade_freq_7d,
    AVG(withdrawal_frequency_24h) as avg_withdraw_freq_24h,
    AVG(shared_device_count) as avg_shared_devices
FROM feature_table;
```

### After Upload (Current Distribution)
```sql
-- Run on v3_drift data after pipeline run

SELECT 
    COUNT(*) as total_users,
    AVG(account_age_days) as avg_account_age,
    AVG(trade_frequency_24h) as avg_trade_freq_24h,
    AVG(trade_frequency_7d) as avg_trade_freq_7d,
    AVG(withdrawal_frequency_24h) as avg_withdraw_freq_24h,
    AVG(shared_device_count) as avg_shared_devices
FROM feature_table;
```

### Account Age Distribution Comparison
```sql
-- New accounts (< 7 days) percentage
SELECT 
    CASE 
        WHEN account_age_days < 7 THEN 'new'
        WHEN account_age_days < 30 THEN 'recent'
        ELSE 'established'
    END as age_category,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM feature_table
GROUP BY age_category
ORDER BY age_category;
```

## Important Notes

- **This is NOT a fraud-only dataset** - it simulates population drift
- **Goal is PSI validation**, not increased fraud detection
- **Training should NOT be rerun** - baseline remains v2_diverse
- **PSI should calculate dynamically** comparing current vs baseline
- **Expected max_psi > 0.10** to validate drift detection

## Validation Checklist

After uploading v3_drift:

- [ ] Pipeline runs successfully
- [ ] Feature engineering completes
- [ ] PSI endpoint returns data
- [ ] `max_psi > 0.10`
- [ ] `overall_status` is "warning" or "drift"
- [ ] `drift_features` includes at least 2 drifted features
- [ ] Tooltip and explanation present in PSI response
