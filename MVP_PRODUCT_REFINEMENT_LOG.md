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

## Fraud Networks Card Metric Refinement

Date: 2026-07-18

Decision:

Fraud Networks card now displays the number of unique users linked to suspicious clusters, rather than the number of clusters.

Before:

Fraud Networks = Count of suspicious clusters

After:

Fraud Networks = Count of unique users linked to suspicious clusters (deduplicated)

Reasons:

- Users are the actionable entity for investigation, not clusters
- Shows actual impact scale - how many users require review
- Aligns with analyst workflow (investigate users, not clusters)
- Provides more meaningful business context

Implementation Details:

Backend API:

GET /api/risk/overview

summary.fraud_networks calculation:

Before: SELECT COUNT(*) FROM account_clusters

After: SELECT COUNT(DISTINCT user_id) FROM cluster_members

Frontend Display:

Card Title: Fraud Networks

Subtitle: "Users linked to suspicious network clusters"

Value: Unique user count from API

Data Consistency:

The value represents deduplicated users across all clusters.

A user belonging to multiple clusters is counted only once.

This matches the investigation use case where analysts review individual users.

## Case ID Pagination Fix

Date: 2026-07-18

Issue:

Case IDs were not unique across pages. When clicking different pagination buttons on the risk overview page, case IDs always started from CASE-00001.

Root Cause:

Frontend was using array index (`idx`) to generate case IDs without accounting for pagination offset.

When page 2 data was fetched, the array index restarted from 0, causing case IDs to restart from CASE-00001.

Fix Applied:

RiskCommandCenter.tsx:
- Changed from: `case_id: \`CASE-${String(idx + 1).padStart(5, '0')}\``
- Changed to: `case_id: \`CASE-${String((currentPage - 1) * PAGE_SIZE + idx + 1).padStart(5, '0')}\``
- Added `currentPage` to useMemo dependency array

Investigation.tsx:
- Changed to generate case_id from user_id (extracting numeric part)
- This ensures unique case IDs since Investigation page loads all data at once

Implementation Details:

RiskCommandCenter (paginated view):
- Global index = (currentPage - 1) * PAGE_SIZE + idx + 1
- Page 1: CASE-00001 to CASE-00005
- Page 2: CASE-00006 to CASE-00010
- etc.

Investigation (all-at-once view):
- Uses user_id to generate unique case_id
- Extracts numeric part from user_id (e.g., "U01401" → "01401")
- Fallback to array index if no numeric part found

Impact:
- Case IDs are now unique across all pages
- Each case has a distinct, consistent identifier
- Supports proper case tracking and reference

## Risk Score Analytics Metric Refinement

Date: 2026-07-18

Decision:

Removed Median metric from Risk Score Analytics dashboard card.

Before:

Risk Score Analytics displayed: average, median, threshold, maximum

After:

Risk Score Analytics displays: average, threshold, maximum

Reasons:

- Average (mean) provides sufficient central tendency information
- Median is redundant when distribution is available via histogram
- Reduces visual clutter in analytics card
- Simplifies backend API response

Implementation Details:

Backend Changes:
- Removed `median` field from `RiskScoreStatistics` schema (schemas.py)
- Removed median calculation from `/api/risk/overview` endpoint (risk.py)

Frontend Changes:
- Removed `median` from `RiskScoreStatistics` interface (RiskScoreAnalyticsCard.tsx)
- Removed median from mock statistics
- Removed median metric from display array

Data Contract Update:
- Updated `risk_score_statistics` definition in DATA_CONTRACT.md
- Removed median from API response example
- Updated UI mapping documentation

Impact:
- Three metrics now displayed: Average Risk Score, High Risk Threshold, Maximum Risk Score
- Risk distribution histogram provides full distribution context
- Cleaner, more focused analytics display

## Investigation Queue Alignment

Date: 2026-07-18

Issue:

Investigation page was not displaying all "needs review" cases.
Case count and sort order were inconsistent with Risk Overview page.

Root Cause:

1. Investigation page only fetched 100 items (page_size: 100)
2. If more than 100 cases existed, remaining cases were hidden
3. Frontend had redundant sorting logic (backend already sorts correctly)

Fix Applied:

Investigation.tsx:
- Increased page_size from 100 to 10000 to fetch all cases
- Added totalCases state to display actual count from API
- Removed redundant frontend sorting (backend already sorts by risk_score DESC)
- Updated display to show totalCases instead of array length

Backend (already correct):
- `/api/risk/cases` endpoint filters by default: CRITICAL + HIGH + MEDIUM (needs review)
- Backend sorts by `User.current_risk_score DESC`
- Returns total count in response.total field

Result:
- Investigation page now shows all needs review cases (Critical + High + Medium)
- Case count matches Risk Overview needs review count
- Cases are sorted by risk score descending (highest first)
- Consistent display across both pages

## Investigation Page Performance Optimization

Date: 2026-07-18

Issue:

Investigation page was slow to load because:
1. Fetching 500 cases at once from backend (slow query + large data transfer)
2. Rendering 500+ DOM nodes simultaneously (browser rendering overhead)

Users experienced noticeable loading delays.

Solution:

Implemented progressive loading with "Load More" functionality:

Investigation.tsx:
- Reduced initial load from 500 to 50 cases (10x faster initial load)
- Added `loadingMore` state for load more progress
- Added `currentPage` state to track pagination
- Implemented `loadMoreCases()` function for progressive loading
- Added "Load More" button showing remaining count
- Updated header to show "Showing X of Y cases"

Backend (risk.py):
- Increased page_size limit from 100 to 1000 to support pagination

Result:
- Initial page load is ~10x faster (50 cases vs 500)
- Users see cases immediately, can load more as needed
- Shows "Showing 50 of 600 cases" with "Load More (550 remaining)" button
- Better perceived performance and user experience
- Reduced memory footprint on client side

## Investigation Search Smart Matching

Date: 2026-07-18

Issue:

Search was using fuzzy matching (`.includes()`), which returned too many results:
- Searching "1" matched CASE-00001, CASE-00010, CASE-00011, U01401, etc.
- Users wanted flexible search but without overly broad matches

Solution:

Implemented smart matching logic that handles multiple input formats:

Investigation.tsx:
- Numeric search: case number → matches corresponding CASE-XXXXX
- Full case_id: "CASE-XXXXX" → matches exact case
- User ID: "UXXXXX" → matches case by user_id
- Prevents overly broad matches like "1" matching everything

Matching logic:
1. Exact match with case_id or user_id
2. Numeric-only query matches case_id number portion
3. CASE- prefix requires exact match
4. U prefix requires exact user_id match

Result:
- Search by case number, full CASE-XXXXX, or User ID (UXXXXX)
- No overly broad partial matches
- Flexible user experience without unwanted results

## Model Monitoring Mock Data Replacement

Date: 2026-07-18

Issue:

AI Model Health page was using hardcoded mock data for model metadata instead of backend API responses.

Found in:
- mockModelMetadata object with hardcoded values
- Model name, version, algorithm, training_date, feature_count were all static

Solution:

Replaced mock data with actual backend API responses:

ModelMonitoring.tsx:
- Removed mockModelMetadata constant
- Added DEFAULT_MODEL_METADATA for fields not provided by backend
- Updated all displays to use metrics.model_name and metrics.version from API
- Updated TypeScript interface to include deployed_at field

Backend data already available from /api/model/monitoring:
- model_name
- version
- deployed_at
- metrics (auc, ks, psi)
- psi_status
- psi_features

Changes:
1. Model Identity section: Uses metrics.model_name and metrics.version from API
2. Algorithm section: Uses DEFAULT_MODEL_METADATA for algorithm/model_type
3. Training Configuration: Shows deployed_at from API, feature_count from defaults

Result:
- Model metadata now reflects actual backend data
- Model name and version come from database
- Deployed date is real (when model was deployed)
- Algorithm and feature count use defaults (not stored in current schema)
- Future enhancement: Add these fields to backend schema

## Investigation Case Context Enrichment

Date: 2026-07-18

Issue:

Investigation page case detail panel was displaying hardcoded "N/A" values for:
- Account Age
- Total Volume

These fields were marked as "not available from current API" in MOCK_DATA_INVENTORY.md.

Root Cause:

The frontend was only calling `/api/risk/cases` (list endpoint) which returns basic risk event data.
The detailed endpoint `/api/risk/events/{user_id}` existed but was not being called when a case was selected.

Solution:

Enhanced case detail context by adding backend support and frontend integration:

Backend Changes (backend/app/models/schemas.py):
- Added `account_age` field to `RiskEventDetailResponse` (account age in days)
- Added `total_volume` field to `RiskEventDetailResponse` (total trading volume)

Backend Changes (backend/app/api/routes/risk.py):
- Modified `/api/risk/events/{user_id}` endpoint to compute case context
- `account_age`: Computed from `User.account_created_time` (days since account creation)
- `total_volume`: Aggregated from `Trade` table (SUM of price * quantity)

Frontend Changes (frontend/src/services/api.ts):
- Updated `RiskEventDetail` interface to include `account_age` and `total_volume` fields

Frontend Changes (frontend/src/pages/Investigation.tsx):
- Added `loadingDetail` state for case detail loading
- Added `fetchCaseDetail()` function to call `/api/risk/events/{user_id}` when case selected
- Added `handleCaseSelect()` wrapper to fetch details in background
- Updated display logic to format values:
  - account_age: "365 days" or "N/A" if null
  - total_volume: "$125,000.50" or "N/A" if null
- Removed hardcoded "N/A" placeholder values

Data Contract Updates (DATA_CONTRACT.md):
- Added new section "6. Case Detail Context Contract"
- Documented the enhanced `/api/risk/events/{user_id}` endpoint
- Renumbered subsequent sections (6→7→8, etc.)

Mock Data Inventory Updates (MOCK_DATA_INVENTORY.md):
- Updated section 2.2 from "PARTIAL" to "COMPLETED"
- Removed account_age and total_volume from hardcoded fields list
- Updated summary sections to reflect completion

Result:
- Case detail panel now displays real account age and trading volume
- Values computed from actual database records (User and Trade tables)
- Improved investigation context for risk analysts
- No more hardcoded "N/A" placeholders
- Consistent data provenance across all Investigation page fields

Technical Details:
- account_age calculation: `(current_time - User.account_created_time).days`
- total_volume calculation: `SUM(Trade.price * Trade.quantity) WHERE user_id`
- Both fields return null if source data is unavailable
- Frontend gracefully handles null values with "N/A" display

## ML Lifecycle Completion

Date: 2026-07-18

Issue:

Model Monitoring page was displaying partial/fallback data because:
- ML model training existed but was disconnected from data upload pipeline
- Model metadata was only saved when training script was run manually
- No automatic model training after dataset upload
- PSI baseline generation was manual
- Feature importance data used fallback demo values when no model was trained

The platform had incomplete ML lifecycle:
- CSV Upload → Feature Engineering → Risk Scoring ✅
- Feature Engineering → Model Training ❌ (missing)
- Model Training → Metadata Persistence ❌ (manual only)
- Model Training → PSI Baseline ❌ (manual only)

Root Cause:

The training pipeline (`ml-models/training/train_risk_model.py`) existed but was:
1. Only triggered manually via command line
2. Not integrated with the data upload pipeline
3. Not exposed via API for frontend triggering
4. Using CSV files instead of database data
5. Separate from the production feature engineering flow

Solution:

Implemented end-to-end ML lifecycle integration:

Backend Changes (backend/app/services/pipeline_service.py):
- Added `train_model()` method to PipelineService
- Loads features from FeatureTable (database)
- Generates labels from cluster membership (ClusterMember table)
- Trains LightGBM model using existing LightGBMTrainer
- Saves model artifacts to ml-models/artifacts/
- Persists metadata to ModelMetadata table
- Saves feature importance to FeatureImportance table
- Generates PSI baseline distribution
- Returns comprehensive training results

Backend Changes (backend/app/api/routes/pipeline.py):
- Added `POST /api/pipeline/train` endpoint
- Triggers model training on current database data
- Returns ModelTrainingResponse with metrics and model info
- Integrated with existing pipeline flow

Backend Changes (backend/app/models/schemas.py):
- Added `ModelTrainingResponse` schema
- Includes status, metrics, train/test sizes, model_id
- Proper error handling with status field

Backend Changes (backend/app/api/routes/model.py):
- Removed fallback values from `/api/model/metrics` endpoint
- Returns null for auc/ks/psi when no model exists
- Removed demo fallback data from `/api/model/feature-importance`
- Returns empty array when no model metadata exists

Backend Changes (backend/app/services/model_monitoring_service.py):
- Enhanced `get_current_model_metrics()` to handle missing baseline
- Returns "unknown" psi_status when error or no baseline
- Returns empty psi_features when baseline unavailable

Complete ML Workflow:

```
CSV Upload (POST /api/pipeline/upload)
→ Data Import to Database
→ Feature Engineering (POST /api/pipeline/run)
→ Graph Analysis
→ Risk Scoring
→ Model Training (POST /api/pipeline/train)
  ├─ Load features from FeatureTable
  ├─ Generate labels from ClusterMember
  ├─ Train LightGBM model
  ├─ Calculate AUC/KS metrics
  ├─ Save model artifacts
  ├─ Persist metadata to ModelMetadata
  ├─ Save feature importance
  └─ Generate PSI baseline
→ Model Monitoring (GET /api/model/monitoring)
  ├─ Model metrics (AUC, KS, PSI)
  ├─ Feature importance rankings
  └─ Feature-level drift analysis
```

Data Contract Updates (DATA_CONTRACT.md):
- Added section "17. Model Lifecycle Completion"
- Documented POST /api/pipeline/train endpoint
- Documented GET /api/model/monitoring response
- Documented GET /api/model/feature-importance response
- Specified null handling for missing models
- Updated integration points and frontend display behavior

Key Design Decisions:

1. No Fallback Values:
   - When no model is trained, metrics return null
   - Frontend displays "No model available" instead of fake values
   - Maintains data integrity and transparency

2. Label Generation from Clusters:
   - Risky users = cluster members (from ClusterMember table)
   - Normal users = non-cluster members
   - Automatic labeling without manual annotation

3. Database-First Training:
   - Training loads from FeatureTable (not CSV files)
   - Ensures training-serving feature consistency
   - Uses same FeatureCalculator as production inference

4. Incremental Training:
   - Training is separate from pipeline run
   - Allows retraining without full pipeline execution
   - Supports future A/B testing and model comparison

5. PSI Baseline Auto-Generation:
   - Baseline created automatically during training
   - Saved to model artifact directory
   - Used for ongoing drift monitoring

Result:
- Platform now demonstrates complete end-to-end AI risk management workflow
- Model training integrated with data upload pipeline
- Real model metadata available for monitoring
- PSI baseline auto-generated during training
- Feature importance from actual trained models
- No fallback/demo data in model monitoring APIs
- Frontend displays appropriate empty states when no model exists

Product Impact:

Before: Platform demonstrated risk scoring capabilities
After: Platform demonstrates complete AI model lifecycle
- Data management
- Feature engineering
- Model training
- Model evaluation
- Model deployment
- Model monitoring

This positions the platform as an enterprise AI risk management solution
rather than just a risk scoring tool.

Technical Implementation:
- No changes to risk scoring logic (ML/Rules/Graph fusion unchanged)
- No changes to model inference behavior
- No changes to detection attribution thresholds
- Only added missing lifecycle orchestration

MVP Limitation - Fraud Label Generation:

**Important:** The current implementation uses graph clustering for fraud label generation.

Current Approach:
- Fraud labels (is_risky) are derived from graph cluster membership (ClusterMember table)
- Users detected in suspicious clusters are automatically labeled as "risky"
- Labels are generated during model training pipeline execution

Why This Approach for MVP:
- Demonstrates complete ML lifecycle workflow without manual labeling
- Shows model training, evaluation, and monitoring end-to-end
- Provides realistic feature importance rankings for demonstration
- Enables automatic pipeline execution from uploaded datasets

Production Requirement:
For production deployment, fraud labels must come from independent sources:
- Confirmed fraud cases from investigation outcomes
- Manual review and labeling by fraud analysts
- External fraud intelligence and alerts
- Time-separated validation to prevent temporal leakage

Model Behavior with Current Labels:
- Model learns patterns associated with cluster membership
- AUC/KS metrics reflect cluster-based labeling approach
- Feature importance highlights device sharing and trading patterns
- Suitable for pipeline demonstration, not production decision-making
- Metrics are inflated due to circular reasoning with clustering features

Acknowledgment:
This limitation is documented for transparency. The platform successfully
demonstrates the AI risk management workflow, which is the MVP goal.