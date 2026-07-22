# Model Monitoring and PSI Product Design - Final Implementation

## Overview

Comprehensive updates to Model Monitoring UI and PSI interpretation based on enterprise risk monitoring best practices.

---

## Changes Implemented

### 1. PSI Interpretation and Product Definition

**Before:** PSI > 0.25 implied model failure/mandatory retraining.

**After:**
- PSI measures population distribution change between current uploaded data and training baseline
- Status meanings clearly defined:
  - `< 0.10`: Stable
  - `0.10 - 0.25`: Minor drift
  - `> 0.25`: Significant drift detected
- **Recommendation:** "Review feature distribution changes before deciding whether model retraining is required"
- Does NOT automatically imply retraining is mandatory

### 2. PSI Score Definition

**Clarified semantics:**
- `psi_score` represents "latest calculated PSI snapshot"
- NOT a training PSI or model quality metric
- NOT a static value saved during training

**UI Updates:**
- Section renamed: "Latest PSI Snapshot"
- Shows "Calculated at: {timestamp}" when available
- Clear separation from model performance metrics

### 3. Sparse Distribution Classification Fix

**Before:** All features with PSI > 1.0 were marked as "sparse distribution"

**After:**
- **Explicit SPARSE_FEATURES configuration:**
  ```typescript
  const SPARSE_FEATURES = [
    'shared_device_count',
    'linked_account_count',
    'unique_ip_count',
  ] as const;
  ```

- **Only these features** show "(sparse distribution)" annotation
- High PSI alone does NOT mean sparse distribution
- Example: `avg_trade_size` PSI > 1.0 = real behavioral change (NOT sparse)

### 4. Feature Types and Enhanced Explanations

**Added Feature Types:**
- **Behavioral:** trading_frequency_*, trade_volume_*, avg_trade_size, opposite_trade_ratio, active_days_count
- **Account:** account_age_days
- **Network:** shared_device_count, linked_account_count, unique_ip_count
- **Withdrawal:** withdrawal_frequency_24h, withdrawal_volume_24h, withdrawal_risk_score

**Enhanced Business Meanings:**
- `avg_trade_size`: "Average transaction amount. Large changes indicate changes in position sizing behavior."
- `linked_account_count`: "Account linkages. Sparse distribution naturally creates larger PSI movement."
- Each feature has clear, business-friendly explanations

### 5. Model Feature Count Consistency

**Investigation Results:**
- **Model Input Features:** 14 (all features used by LightGBM)
  - Includes: `first_withdrawal_flag` (binary flag, excluded from PSI)
- **Monitored Drift Features:** 13 (features tracked for population changes)
  - Excludes: `first_withdrawal_flag` (PSI less meaningful for binary features)

**Product Definition:**
```typescript
const MODEL_INPUT_FEATURES = 14;
const MONITORED_FEATURES = 13;
```

**UI Display:**
- Feature count tooltip explains the difference
- Shows both numbers explicitly
- Clear about why binary flags are excluded from drift monitoring

### 6. PSI Drift Detection - No Artificial Reduction

**Maintained realistic drift detection:**
- Sparse features: domain-specific interpretation (zero-inflated distributions)
- Continuous behavioral features: large PSI = actual distribution change
- No artificial PSI reduction to make numbers look good

### 7. Dashboard Presentation Reorganization

**Before:** Mixed presentation of performance and drift metrics.

**After:** Clear separation:

```
┌─────────────────────────────────────────┐
│ Model Overview Card                     │
│ - Model name, version, algorithm       │
│ - Feature count (with tooltip)          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Model Performance                       │
│ - AUC Score                             │
│ - KS Statistic                          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Model Drift Monitoring                  │
│ - Latest PSI Snapshot (main KPI)        │
│ - Drift Status                          │
│ - Feature Distribution Changes Table    │
│   - Feature, Type, Business Meaning     │
│   - PSI Value, Status                   │
│   - Sparse annotation (explicit only)    │
│ - PSI Distribution Chart                │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ AI Risk Drivers                         │
│ - Feature Importance Chart              │
└─────────────────────────────────────────┘
```

---

## Feature Breakdown Table

| Feature | Type | Sparse? | Business Meaning |
|---------|------|---------|------------------|
| trade_frequency_7d | Behavioral | No | Weekly trading volume. Changes indicate usage pattern shifts |
| trade_frequency_24h | Behavioral | No | Daily trading activity. Changes may signal anomalous behavior |
| trade_volume_24h | Behavioral | No | Daily trade amounts. Changes in transaction scale patterns |
| avg_trade_size | Behavioral | No | Average transaction amount. Large changes indicate behavioral changes |
| opposite_trade_ratio | Behavioral | No | Trading balance (buy vs sell mix). Changes indicate strategy shifts |
| active_days_count | Behavioral | No | Platform engagement level. Changes in activity patterns |
| account_age_days | Account | No | Account tenure. Newer cohorts may have different risk characteristics |
| shared_device_count | Network | **Yes** | Device sharing. Sparse distribution naturally creates larger PSI |
| linked_account_count | Network | **Yes** | Account linkages. Sparse distribution naturally creates larger PSI |
| unique_ip_count | Network | **Yes** | IP connection diversity. Sparse distribution naturally creates larger PSI |
| withdrawal_frequency_24h | Withdrawal | No | Cash-out frequency. Changes indicate withdrawal pattern evolution |
| withdrawal_volume_24h | Withdrawal | No | Withdrawal amounts. Changes in risk transfer patterns |
| withdrawal_risk_score | Withdrawal | No | Withdrawal risk indicators. Changes in cash-out risk behavior |

---

## Expected Demo Results

**Target Metrics:**
- AUC: 0.85 - 0.95
- KS: 0.6 - 0.85
- PSI: 0.3 - 0.8

**Expected PSI Status:**
- `overall_status: 'drift'` - "Significant drift detected"
- Top drifted features: account_age_days, trade_frequency_*, withdrawal_*
- Sparse features may show higher PSI but properly annotated

---

## Files Modified

1. **frontend/src/pages/ModelMonitoring.tsx**
   - Complete rewrite with product-aligned design
   - Added SPARSE_FEATURES configuration
   - Added feature types and enhanced explanations
   - Reorganized into clear sections
   - Updated all PSI interpretation wording

---

## Technical Implementation Details

**Sparse Feature Check:**
```typescript
const isSparseFeature = (featureName: string): boolean => {
  return SPARSE_FEATURES.includes(featureName as any);
};
```

**Feature Type Colors:**
- Behavioral: Blue (bg-blue-100 text-blue-800)
- Account: Purple (bg-purple-100 text-purple-800)
- Network: Amber (bg-amber-100 text-amber-800)
- Withdrawal: Emerald (bg-emerald-100 text-emerald-800)

**PSI Status Colors:**
- Stable: Green
- Warning: Yellow
- Drift: Orange (not red - to avoid implying failure)

---

## Product Principles Applied

1. **Transparency:** Clear about what PSI measures and what it doesn't
2. **No False Alarms:** PSI drift doesn't imply model failure
3. **Contextual Information:** Sparse features properly annotated
4. **Actionable Recommendations:** "Review before deciding" vs "Must retrain"
5. **Consistent Terminology:** "Latest PSI Snapshot" vs "Training PSI"
6. **Enterprise Presentation:** Clear section separation and professional layout
