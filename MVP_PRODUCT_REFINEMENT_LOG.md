# MVP Product Refinement Log

## Project Positioning

AI Risk Command Center is an MVP demonstration platform.

The goal is to demonstrate:

- Risk analytics capability
- ML risk scoring
- Rule-based detection
- Graph-based risk analysis
- Investigation workflow
- Model monitoring concepts

The platform is NOT a production real-time risk monitoring system.

Current data flow:

CSV Upload
↓
Data Processing Pipeline
↓
Feature Engineering
↓
LightGBM Risk Model
↓
Risk Analysis Dashboard


---

# Product Principles

## 1. No Fake Real-time

The platform should NOT claim:

- Real-time monitoring
- Streaming detection
- Automatic refresh
- Live decisioning

Because current MVP does not integrate enterprise systems.

Preferred wording:

- Batch Risk Analysis
- Analysis generated from uploaded datasets
- Manual upload
- Latest processed dataset


---

## 2. Data Transparency

All important metrics should provide provenance information.

Current MVP data source:

Uploaded Risk Dataset

Processing:

Risk Analytics Pipeline

Update method:

Manual upload


Future:

Replace with enterprise data sources after integration.


---

# Dashboard Design Decisions


## Risk Command Center

Removed:

- Environment: Production
- System Operational
- Last Updated: Just now
- Real-time risk intelligence wording


Reason:

These imply production infrastructure.


Kept:

- Executive KPI summary
- Risk composition
- Detection source analysis
- Investigation queue


---

## Risk Recommendations

The system provides:

Risk assessment + recommended actions

NOT:

Automatic business decisions


Use wording:

Recommended Action

Avoid:

Decision
Freeze account automatically
Auto approval/rejection


---

## Historical Data Handling

Historical charts should not display fake trends.

If historical dataset exists:

Show:

Compared with previous analysis


If not:

Show:

No historical baseline available

Upload additional datasets to enable trend analysis


---

# Mock Data Replacement Plan

Current mock data locations:

## Risk Overview

Future API:

GET /api/risk/overview


## Investigation Queue

Future API:

GET /api/investigation/cases


## Model Monitoring

Future API:

GET /api/model/metrics


---

# Model Monitoring Decisions


## AUC

Explanation:

Higher is better


Measures:

Model ranking ability


## PSI

Explanation:

Lower is better


Measures:

Population distribution stability


First MVP:

If no previous dataset:

Display:

Unavailable

Reason:

No baseline dataset exists


Future:

Compare current uploaded dataset against previous analysis datasets.


---

# Case Management Decision

Current MVP:

No independent case management module.

Reason:

Requires:

- assignment workflow
- user ownership
- review status
- backend persistence


Future possibility:

Add after investigation workflow becomes real.


---

# Feature Metadata

Avoid hardcoding misleading values.

Example:

Avoid:

Feature Count: 128

unless model pipeline actually produces 128 features.


Future:

Feature count should come from:

Feature engineering pipeline output.


---

# Current MVP Status

Completed:

- Risk Command Center redesign
- Investigation workspace redesign
- Data pipeline visualization
- Model monitoring page refinement
- Data provenance UI

Remaining:

- Replace mock data with API responses
- Connect CSV upload pipeline
- Generate real feature statistics
- Improve model explainability

## Frontend Design System Alignment

Date:

Changes:
- unified slate color palette
- standardized cards
- aligned spacing
- added design-system.ts

Reason:
Improve enterprise SaaS consistency

Not changed:
- backend
- data flow
- product scope

## Investigation Queue Scope Refinement

Date: 2026-07-18

Decision:

Investigation Queue does not represent all analyzed users.

The queue represents analyst workload, not complete dataset browsing.

Before:

All users displayed in Investigation Queue.

After:

Only Critical / High / Medium risk users requiring review.

Reasons:

- Avoid overwhelming analysts with low-risk users
- Improve investigation efficiency
- Align dashboard behavior with enterprise risk workflow
- Focus on actionable cases

Implementation Details:

Filter Tabs (New):

1. Needs Review (Default) = Critical + High + Medium
2. Critical
3. High
4. Medium

Removed:

- Low filter
- All filter

Default View:

Needs Review selected by default.

Example:

Upload: 2000 users
- Critical: 0
- High: 598
- Medium: 2
- Low: 1400

Investigation Queue displays:
- Needs Review (600)

NOT:
- All (2000)

Pagination:

Backend-controlled, not frontend-only.

API supports:
- page
- page_size
- risk_level filter

Data Consistency:

Investigation Queue numbers match same uploaded dataset shown across platform.

Remove any stale hardcoded values.

## Detection Attribution Architecture Review and Risk Scoring Audit

Date: 2026-07-18

### 1. Problem Background

Risk Detection Coverage (UI dashboard card) initially showed insufficient variety in detection coverage metrics (showing 100% across all methods).

Previous attempts to solve this incorrectly tried to modify risk scoring logic to force chart variety.

The audit identified that scoring logic and detection attribution were incorrectly coupled.

### 2. Audit Findings

#### backend/app/services/risk_service.py

**Changes Made (Should Be Reverted):**
- Added artificial "detection pattern diversity" logic
  - Modified scores based on user hash to force ML/Rule/Graph dominant patterns
  - Applied multipliers (0.4-1.2x) to artificially vary detection methods
  
- Modified `_calculate_ml_score()`
  - Added hash-based probability variation (±0.2)
  - Added score variation (±25 points for high-risk users)
  
- Modified `_calculate_rule_score()`
  - Added variety multiplier (0.5-1.0)
  - Reduced base rule scores (40→30, 35→25, 30→22, 25→18, 20→15)
  - Added ±20 point fine variation
  
- Modified `_calculate_graph_score()`
  - Reduced base contributions (cluster * 0.3 → * 0.25)
  - Reduced cluster size and hub bonuses
  - Added variety multipliers and ±30 point variation

**Impact:**
- ✗ AFFECTS core risk scoring logic
- ✗ AFFECTS final risk score fusion
- ✗ AFFECTS risk level classification

**Recommendation:** REVERT all variety/pattern diversity changes.

#### backend/app/api/routes/risk.py

**Changes Made:**
- Detection source thresholds introduced:
  - ML_THRESHOLD = 70.0
  - RULE_THRESHOLD = 35.0
  - GRAPH_THRESHOLD = 60.0
- Changed from `score > 0` to `score >= threshold`

**Impact:**
- ✓ DOES NOT AFFECT core risk scoring logic
- ⚠️ Threshold values were arbitrarily chosen for chart variety
- This is detection attribution logic, not scoring logic

**Recommendation:** REVERT thresholds to `> 0` (meaningful contribution = any contribution).

#### backend/app/config.py

**Changes Made:**
- Added localhost:3001 to CORS origins

**Impact:** No risk scoring impact. KEEP.

### 3. Root Cause

The current Risk Detection Coverage shows 100% coverage across all methods because:

1. The demo dataset contains fraud clusters where:
   - ML model predicts high probabilities for cluster members
   - Graph analysis assigns high scores to cluster members
   - Rule engine flags suspicious patterns

2. High-risk users (CRITICAL/HIGH) are predominantly cluster members

3. Therefore, all high-risk users have:
   - ML score ≈ 100
   - Rule score ≈ 35-40
   - Graph score ≈ 100

**This is NOT a model bug or scoring logic error.**

This reflects the actual data distribution where:
- Fraud clusters are detected by multiple methods (as designed)
- Multiple detection methods correctly identify the same high-risk users
- The correlation is in the data, not the logic

### 4. Final Architecture Decision

**Separation of Concerns:**

```
Raw Signals:
- LightGBM score (0-100)
- Rule Engine score (0-100)
- Graph Network score (0-100)

        ↓

Risk Fusion:
- Weighted combination (ML=0.5, Rule=0.3, Graph=0.2)
- Final risk score (0-100)

        ↓

Risk Classification:
- Critical (score ≥ 90)
- High (score ≥ 80)
- Medium (score ≥ 50)
- Low (score < 50)

        ↓

Detection Attribution:
- Read-only metadata from RiskEvent table
- Records which detection methods actually triggered
- Stored separately from classification logic

Risk Detection Coverage (read-only from RiskEvent):
- COUNT high-risk users WHERE ml_score >= threshold
- COUNT high-risk users WHERE rule_score >= threshold
- COUNT high-risk users WHERE graph_score >= threshold
- Calculate detection coverage rates independently
```

**Key Principle:**

Detection attribution is **read-only attribution metadata** and must NOT modify model scoring outputs.

The UI displays this as "Risk Detection Coverage" showing percentage of high-risk cases identified by each method.

### 5. Future Implementation Direction

**Risk Scoring Requirements:**
- Keep risk scoring deterministic (same input → same output)
- Do NOT change model outputs to improve visualization variety
- Do NOT add artificial randomness/hash-based variation to scores
- Detection thresholds are for classification, not visualization

**If Demonstration Variety is Needed:**
- Improve mock/test data generation
- Create diverse test scenarios with:
  - ML-only detection cases
  - Rule-only detection cases
  - Graph-only detection cases
  - Multi-method detection cases
- This creates variety through data, not logic changes

**Detection Coverage Calculation:**

```
Detection Coverage Rate for Method X =
(number of high-risk cases where X_score >= threshold) / (total high-risk cases) × 100
```

Where "high-risk cases" = CRITICAL risk level + HIGH risk level (combined)

**Key Characteristics:**
- Multiple methods MAY detect the same case
- Percentages do NOT need to sum to 100%
- This reflects independent detection capability, not mutual exclusion

### 6. Implementation Status

**Pending Actions:**
1. Revert risk_service.py variety/pattern diversity changes
2. Revert risk.py detection source thresholds to `> 0`
3. Keep normalization functions if they add value (currently minimal)
4. Consider improving test data generation for demonstration variety

**Completed:**
- Audit documentation
- Architecture clarification
- Separation of scoring vs attribution concerns
- Reverted artificial detection variety changes from risk scoring pipeline
- Risk Detection Coverage now uses explicit attribution thresholds
- detection_methods API field added for per-case attribution

## Detection Attribution Rules (Post-Cleanup)

Date: 2026-07-18

### Detection Method Attribution Definition

A detection method is considered "triggered" for a case when its component score meets or exceeds the attribution threshold.

**Attribution Rules:**
- **LightGBM triggered**: `ml_score >= 10.0`
- **Rule Engine triggered**: `rule_score >= 15.0`
- **Graph Network triggered**: `graph_score >= 10.0`

**Key Principle:** Detection attribution is read-only metadata derived from actual model outputs. It does not modify or influence risk scoring.

This is returned to the frontend as the `detection_methods` array field.

### Detection Coverage Calculation

```
Detection Coverage Rate for Method X =
(COUNT of high-risk cases WHERE X_score >= threshold) / (Total high-risk cases) × 100
```

Where "high-risk cases" = CRITICAL risk level + HIGH risk level (combined)

**Characteristics:**
- Multiple methods CAN detect the same case
- Percentages do NOT need to sum to 100%
- This reflects independent detection capability
- High correlation in detection coverage reflects actual data distribution

**UI Display:** The "Risk Detection Coverage" dashboard card shows these percentages for each detection method.

**Characteristics:**
- Multiple methods CAN detect the same case
- Percentages do NOT need to sum to 100%
- This reflects independent detection capability
- High correlation in detection coverage reflects actual data distribution, not logic error

### Current Data Distribution (Post-Cleanup)

After implementing threshold-based detection attribution:

- High risk accounts: 598
- Risk Detection Coverage:
  - LightGBM: 598 (100%)
  - Rule Engine: 598 (100%)
  - Graph Network: 598 (100%)

**Interpretation:** All 598 high-risk users have scores meeting or exceeding the attribution thresholds for all three detection methods. This reflects the actual test data where fraud cluster members are detected by multiple methods simultaneously.

### Risk Scoring Pipeline (Deterministic)

**Raw Signal Generation:**
- ML probability from LightGBM model (0-1)
- Rule score from expert rules (accumulated, capped at 100)
- Graph score from cluster analysis (network-based, capped at 100)

**Risk Fusion:**
```
final_score = ml_score × 0.5 + rule_score × 0.3 + graph_score × 0.2
```

**Risk Classification:**
- Critical: final_score ≥ 90
- High: final_score ≥ 80
- Medium: final_score ≥ 50
- Low: final_score < 50

**Key Principle:** Risk scoring remains deterministic and explainable. No artificial variety is added to force chart diversity.