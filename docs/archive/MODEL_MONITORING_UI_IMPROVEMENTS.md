# Model Monitoring UI Improvements Summary

## Overview
Improved the Model Monitoring page to make PSI monitoring more understandable for business users (risk managers and risk analysts) while maintaining all existing functionality.

---

## Modified Files

### 1. `frontend/src/pages/ModelMonitoring.tsx`

---

## UI Changes Implemented

### 1. Improved Model Stability Section

**Before:**
```tsx
<h3>Model Stability (PSI Monitoring)</h3>
<p>PSI measures whether current user behavior distribution has shifted from training data.</p>
<div class="card">
  <h4>Overall PSI Status</h4>
  <p>Max PSI across all features: 0.08</p>
  <badge>Stable</badge>
</div>
```

**After:**
```tsx
<h3>
  Model Stability
  <ModelStabilityExplanation />  <!-- Info icon with tooltip -->
</h3>
<div class="card">
  <h4>Overall PSI</h4>
  <p>0.08</p>
  <badge>Stable</badge>
  <p>Current user behavior distribution is consistent with training baseline.</p>
</div>
```

**Improvements:**
- Removed "(PSI Monitoring)" from heading - cleaner title
- Added info icon with tooltip explaining "Overall PSI" concept
- Changed "Overall PSI Status" to "Overall PSI" - simpler
- Moved PSI value directly under label (no "Max PSI across all features" text)
- Added contextual message explaining the current status in business-friendly language
- Tooltip content: "Provides a high-level model stability indicator. Measures whether the current user population distribution has shifted from the training baseline."

---

### 2. Renamed Feature Drift Section

**Before:**
```tsx
<h4>Feature Drift Analysis</h4>
```

**After:**
```tsx
<h4>
  Feature Distribution Drift
  <FeatureDriftExplanation />  <!-- Info icon with tooltip -->
</h4>
```

**Improvements:**
- Renamed to "Feature Distribution Drift" - more descriptive
- Added info icon with tooltip explaining feature-level PSI
- Tooltip content: "Feature-level PSI identifies which input variables contribute most to population distribution changes. Use this analysis to investigate changes in user behavior patterns."

---

### 3. Improved Feature Drift Table

**Before:**
- PSI values displayed as percentages (multiplied by 100)
- Confusing format: "18.00%"

**After:**
- PSI values displayed in raw format: "0.1800"
- Clear decimal precision (4 decimal places)
- Status badges: Stable, Warning, Drift

**Table Structure:**
| Feature | PSI Value | Status |
|---------|-----------|--------|
| shared_device_count | 0.1800 | Warning |
| opposite_trade_ratio | 0.1200 | Warning |
| trade_frequency_24h | 0.0500 | Stable |

---

### 4. Added PSI Interpretation Information Card

**New Feature:**
```tsx
<div class="card">
  <h4>How to Interpret PSI</h4>
  <button>Show/Hide</button>
  {showPSIGuide && (
    <div class="guide">
      <div class="stable">
        <span class="indicator green"></span>
        <p>Stable: PSI < 0.10</p>
        <p>No significant user behavior distribution change.</p>
      </div>
      <div class="warning">
        <span class="indicator yellow"></span>
        <p>Warning: PSI 0.10 - 0.25</p>
        <p>Monitor potential changes in user behavior patterns.</p>
      </div>
      <div class="drift">
        <span class="indicator red"></span>
        <p>Drift: PSI ≥ 0.25</p>
        <p>Investigate potential impact on model performance.</p>
      </div>
    </div>
  )}
</div>
```

**Improvements:**
- Collapsible guide (Show/Hide button)
- Color-coded indicators (green/yellow/red circles)
- Business-friendly explanations
- Clear action recommendations for each status level

---

### 5. Business-Friendly Wording

**Status Messages:**

| Status | Technical | Business-Friendly |
|--------|-----------|------------------|
| Stable | "No distribution shift" | "Current user behavior distribution is consistent with training baseline." |
| Warning | "Minor distribution shift" | "User behavior patterns are beginning to shift from training baseline." |
| Drift | "Significant distribution shift" | "User behavior patterns have significantly changed from training baseline." |
| Unknown | "Unable to determine" | "Unable to determine stability status." |

**Interpretation Guide:**
- Stable: "No significant user behavior distribution change."
- Warning: "Monitor potential changes in user behavior patterns."
- Drift: "Investigate potential impact on model performance."

---

### 6. Fixed Data Separation

**Bug Fix:**
- Separated PSI features from feature importance data
- PSI features → Feature Distribution Drift table and chart
- Feature importance → Feature Importance chart

**Before:**
- Both sections used same data (incorrectly showing PSI values as feature importance)

**After:**
- PSI features fetched from `/api/model/monitoring`
- Feature importance fetched from `/api/model/feature-importance`
- Each chart displays correct data

---

### 7. Updated PSI Chart

**Improvements:**
- Fixed tooltip to show raw PSI values (not percentages)
- Correct data source (psiFeatures instead of generic features)
- Color-coded bars based on status (green/yellow/red)

---

## Page Layout (Final)

```
┌─────────────────────────────────────────┐
│ Model Information                        │
│ LightGBM Risk Model v1.0  [Refresh]      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Model Performance                       │
│ ┌──────────┐  ┌──────────┐              │
│ │   AUC    │  │    KS    │              │
│ │  0.910   │  │  0.720   │              │
│ └──────────┘  └──────────┘              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Model Stability ℹ                       │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Overall PSI          [Stable]       │ │
│ │ 0.0800                              │ │
│ │ ─────────────────────────────────  │ │
│ │ Current user behavior distribution │ │
│ │ is consistent with training        │ │
│ │ baseline.                          │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Feature Distribution Drift ℹ             │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Feature     │ PSI Value │ Status    │ │
│ │─────────────│───────────│───────────│ │
│ │ shared_device  │ 0.1800  │ Warning   │ │
│ │ opposite_trade │ 0.1200  │ Warning   │ │
│ │ trade_freq_24h │ 0.0500  │ Stable    │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [PSI Chart]                             │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ How to Interpret PSI            [Show]  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Feature Importance (Global)              │
│                                         │
│ [Feature Importance Chart]              │
└─────────────────────────────────────────┘
```

---

## Overall PSI vs Feature-Level PSI Differentiation

### Overall PSI (High-Level Indicator)
- **Location:** Model Stability section
- **Purpose:** Quick health check of overall model stability
- **Display:** Single value with status badge
- **Interpretation:**
  - Stable: Model operating normally
  - Warning: Monitor model performance
  - Drift: Consider retraining

### Feature-Level PSI (Detailed Analysis)
- **Location:** Feature Distribution Drift section
- **Purpose:** Identify which features are causing distribution changes
- **Display:** Table with all features and their PSI values
- **Usage:** Investigate specific user behavior patterns that have changed

**Visual Hierarchy:**
```
Overall PSI (0.08 - Stable)
    ↓
    │ What's causing the drift?
    ↓
Feature-Level PSI (shared_device_count: 0.18 - Warning)
    ↓
    │ Action: Investigate shared device patterns
    ↓
Investigate user behavior changes
```

---

## Tooltips Added

1. **Model Stability** (Overall PSI)
   - "Provides a high-level model stability indicator. Measures whether the current user population distribution has shifted from the training baseline. Higher PSI indicates potential model degradation risk."

2. **Feature Distribution Drift**
   - "Feature-level PSI identifies which input variables contribute most to population distribution changes. Use this analysis to investigate changes in user behavior patterns."

---

## Technical Details

### New State Variables
```typescript
const [psiFeatures, setPsiFeatures] = useState<FeatureImportance[]>([]);
const [featureImportance, setFeatureImportance] = useState<FeatureImportance[]>([]);
const [showPSIGuide, setShowPSIGuide] = useState(false);
```

### New Components
- `ModelStabilityExplanation()` - Tooltip for Overall PSI
- `FeatureDriftExplanation()` - Tooltip for Feature Distribution Drift

### Data Fetching
```typescript
// PSI features from monitoring endpoint
const data = await modelApi.getMonitoring();
setPsiFeatures(data.psi_features);

// Feature importance from separate endpoint
const importanceData = await modelApi.getFeatureImportance();
setFeatureImportance(importanceData.features);
```

---

## Testing Checklist

- [x] Model Stability section displays Overall PSI with info icon
- [x] Feature Distribution Drift section shows table with PSI values
- [x] PSI Interpretation Guide is collapsible
- [x] Business-friendly status messages display correctly
- [x] PSI chart uses correct data (psiFeatures)
- [x] Feature Importance chart uses correct data (featureImportance)
- [x] Tooltips display on hover/click
- [x] Status badges color-coded correctly
- [x] Responsive layout maintained

---

## Implementation Notes

1. **No Backend Changes:** All improvements are frontend-only
2. **No New Dependencies:** Uses existing components and libraries
3. **Consistent Design:** Maintains existing UI patterns and styling
4. **Backward Compatible:** No breaking changes to API or data structures
5. **Accessibility:** Tooltips use existing Tooltip component

---

## Summary

The Model Monitoring page now clearly communicates:
1. **Overall PSI** as a high-level model stability indicator
2. **Feature-level PSI** for detailed drift analysis
3. **Business-friendly interpretation** of PSI values
4. **Actionable guidance** for each status level

Risk managers can now quickly assess model health and investigate specific user behavior changes without requiring ML expertise.
