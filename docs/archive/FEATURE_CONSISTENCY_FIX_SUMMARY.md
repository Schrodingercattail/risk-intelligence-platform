# Feature Consistency Fix Summary

## Problem
When uploading the same v2_diverse dataset through the pipeline after training:
- **Expected**: Latest PSI Snapshot ≈ 0 (same data as training)
- **Actual**: Latest PSI Snapshot = 3.0758 (significant drift)

## Root Cause
The training and pipeline flows used **different reference times** for time-based feature calculations:

### Training Flow (FeatureCalculator)
```python
reference_time = get_reference_time_from_data(trades_df, withdrawals_df)
# Returns: max(timestamp) in data = 2026-07-20 10:48:04
```

### Pipeline Flow (FeatureEngineeringService - BEFORE FIX)
```python
now = datetime.now(timezone.utc).replace(tzinfo=None)
# Returns: current time = 2026-07-21 07:37:12 (~21 hours later)
```

This caused massive differences in time-window features:
- `trade_frequency_24h`: 17.37 → 0.58 (excluded most trades)
- `trade_volume_24h`: 192,845 → 6,774
- `withdrawal_frequency_24h`: 2.06 → 0.19
- `withdrawal_volume_24h`: 6.69 → 0.60

## Solution
Updated `FeatureEngineeringService` to use **data-based reference time** instead of `datetime.now()`:

### Changes to `backend/app/services/feature_engineering.py`

1. Added `_get_reference_time()` method:
```python
async def _get_reference_time(self) -> datetime:
    # Get max timestamp from trades
    max_trade_time = await self.db.scalar(select(func.max(Trade.timestamp)))
    # Get max timestamp from withdrawals
    max_withdrawal_time = await self.db.scalar(select(func.max(Withdrawal.timestamp)))
    # Use the later of the two
    self._reference_time = max(max_trade_time, max_withdrawal_time)
    return self._reference_time
```

2. Updated all feature calculation methods to use `reference_time` parameter:
   - `_trading_features(user_id, trades, reference_time)`
   - `_temporal_features(user, trades, withdrawals, reference_time)`
   - `_withdrawal_features(withdrawals, reference_time)`

3. Updated `generate_features_for_all_users()` to pass reference_time

## Verification
After the fix, the diagnostic script shows **no significant differences**:

```
COMPARISON (Training - Pipeline)
No significant differences found!
```

All 13 risk features now match between training and pipeline flows.

## MVP Lifecycle Behavior
With this fix:
- **Training**: Uses max(timestamp) from training data
- **Pipeline**: Uses max(timestamp) from uploaded data
- **PSI Calculation**: Compares identical time window logic
- **Expected Result**: PSI ≈ 0 when same data is uploaded through pipeline

## Files Modified
- `backend/app/services/feature_engineering.py` - Added data-based reference time logic
- `debug_feature_consistency.py` - Diagnostic script (can be deleted)

## Testing
To verify the fix:
```bash
python debug_feature_consistency.py
```

Expected output: "No significant differences found!"
