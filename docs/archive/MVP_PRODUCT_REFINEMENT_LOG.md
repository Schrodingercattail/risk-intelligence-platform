# MVP Product Refinement Log

## Dataset Information Dynamic Display

Date: 2026-07-19

Issue:

The Dataset Information in the bottom left corner showed hardcoded values:
- Generated: "Jul 15, 2026 14:32" (static, outdated)
- No record count displayed

This did not reflect the actual uploaded dataset or processing timestamp.

Decision:

Make Dataset Information display actual data from backend pipeline status.

Implementation:

**Layout.tsx Changes:**

1. Added state management:
```typescript
const [datasetInfo, setDatasetInfo] = useState<{
  generated: string | null
  totalRecords: number
}>({ generated: null, totalRecords: 0 })
```

2. Added API call to fetch pipeline status:
```typescript
useEffect(() => {
  const fetchDatasetInfo = async () => {
    const status = await pipelineApi.getStatus()
    // Format timestamp and extract record count
  }
  fetchDatasetInfo()
}, [])
```

3. Updated display fields:
- Generated: Shows actual upload timestamp from pipeline (e.g., "Jul 19, 2026 08:49")
- Records: Added new field showing total records processed (e.g., "48,957")

**API Endpoint Used:**
GET /api/pipeline/status
- Uses upload_timestamp field for Generated display
- Uses results.total_records for Records display

**Behavior:**
- Shows "No data uploaded" when no pipeline data exists
- Shows "N/A" for records when not available
- Automatically updates when new data is uploaded via Data Pipeline

**Fields:**
- Source: "Uploaded Dataset" (static)
- Processing: "Risk Analytics Pipeline" (static)
- Update: "Manual Upload" (static)
- Generated: Dynamic timestamp from backend ✅
- Records: Dynamic count from backend ✅

Product Impact:

Before: Static, outdated timestamp that didn't reflect actual data
After: Real-time dataset information that updates with each pipeline run

Users can now see:
- When the current dataset was actually uploaded
- How many total records are being analyzed
- Consistent data provenance across the application

No changes to:
- Backend API structure
- Data Pipeline functionality
- Upload mechanism

---

## Network Risk Metrics Terminology Refinement

Date: 2026-07-19

Issue:

The product had inconsistent naming for "Fraud Networks" across different pages:

**Data Pipeline page:**
- "Fraud Networks: 80"
- This number represents detected suspicious network clusters (account_clusters count)
- Cluster-level metric

**Risk Overview page:**
- "Fraud Networks: 240"
- This number represents users involved in suspicious network clusters (cluster_members distinct count)
- Account-level metric

The label "Fraud Networks" was ambiguous and misleading because the same term represented two different entities.

Decision:

Refine terminology to clearly distinguish between cluster-level and account-level network metrics.

Implementation:

**1. Data Pipeline Page Changes:**

Label Change:
- Before: "Fraud Networks: 80"
- After: "Suspicious Clusters Detected: 80"

Meaning:
- Number of suspicious graph clusters identified by network analysis
- Source: account_clusters table (COUNT of clusters)
- Cluster-level metric

Tooltip Added:
"Suspicious Clusters Detected: Number of suspicious account clusters detected through graph network analysis based on shared devices, IP addresses, or other network relationships."

**2. Risk Overview Page Changes:**

Label Change:
- Before: "Fraud Networks: 240"
- After: "Network-linked Accounts: 240"

Meaning:
- Number of user accounts involved in suspicious network clusters
- Source: cluster_members table (COUNT DISTINCT user_id)
- Account-level metric

Tooltip Added:
"Network-linked Accounts: Number of accounts connected to suspicious networks through shared devices, IP addresses, or other graph relationships."

Subtitle Updated:
- Before: "Users linked to suspicious network clusters"
- After: "Accounts in suspicious network clusters"

**3. Investigation / Risk Evidence Pages:**

Reviewed for "Fraud Networks" terminology - no changes needed as these pages use:
- "Network Signals" (relationship evidence)
- "Network Evidence" (cluster information)
- These terms are already specific and clear

**4. Metric Hierarchy Clarification:**

Graph analysis pipeline hierarchy now clearly reflected in UI:

```
Raw relationships (device/IP/fingerprint sharing)
        ↓
Graph clustering
        ↓
Suspicious Clusters Detected (cluster-level)
        ↓
Cluster members
        ↓
Network-linked Accounts (account-level)
```

**5. Regression Verification:**

After implementation verified:

Data Pipeline:
- Suspicious Clusters Detected = account_clusters count
- Example: 80 clusters

Risk Overview:
- Network-linked Accounts = distinct users in cluster_members
- Example: 240 accounts

Both metrics can coexist with different values (80 ≠ 240) which is expected and correct.

Frontend Changes:

1. DataPipeline.tsx:
   - Added SimpleMetricTooltip import
   - Updated "Fraud Networks" → "Suspicious Clusters Detected"
   - Added tooltip with cluster-level definition
   - API field name unchanged (fraud_networks)

2. RiskCommandCenter.tsx:
   - Updated "Fraud Networks" → "Network-linked Accounts"
   - Added tooltip with account-level definition
   - Updated subtitle text
   - API field name unchanged (fraud_networks)

Backend Changes:
- None (API structure, field names, and calculation logic unchanged)

Documentation Updates:

1. DATA_CONTRACT.md:
   - Updated Risk Overview section (Network-linked Accounts definition)
   - Updated Pipeline Status section (Suspicious Clusters Detected definition)
   - Added UI label mappings for clarity

2. MVP_PRODUCT_REFINEMENT_LOG.md (this entry):
   - Documented the terminology refinement
   - Explained cluster-level vs account-level distinction

Product Impact:

Before: Ambiguous "Fraud Networks" label represented different concepts on different pages
After: Clear, specific terminology that indicates whether metric is cluster-level or account-level

This aligns the platform with enterprise fraud/risk management platforms where analysts understand whether a metric represents:
- Entities (accounts/users)
- Clusters (groups of connected entities)
- Relationships (connections between entities)

No changes to:
- Backend calculation logic
- Database schema
- Graph detection algorithm
- Risk scoring logic
- API response structure
- Existing thresholds

The refinement only improves display semantics and user understanding.

---

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


---

# Risk Evidence Explainability Decision

Date: 2026-07-19

Problem:

Investigation workflow only shows model outputs (risk scores, detection methods)
but does not explain WHY an account is risky.

Current Investigation page displays:
- Risk score (0-100)
- Risk level (LOW/MEDIUM/HIGH/CRITICAL)
- Detection methods (LightGBM, Rule Engine, Graph Network)
- Component scores (ML, Rule, Graph)
- Recommended action

Missing:
- What transactions triggered the risk?
- What network connections exist?
- What rules were triggered?
- What features contributed to the score?

Analyst feedback:
"I see the risk score is 85, but I don't know WHY.
What transactions did this user make?
Who are they connected to?
What rules did they violate?"

Decision:

Add Risk Evidence Explainability API to support investigation workflow.

This is a READ-ONLY evidence aggregation feature.
Does NOT modify risk scoring logic.
Does NOT perform new detection.
Only aggregates existing database evidence for explainability.

Implementation:

New API Endpoint:
GET /api/risk/cases/{user_id}/evidence

Evidence Categories:

1. Transaction Evidence
- Top 3-5 suspicious trades by value
- Shows: transaction ID, symbol, side, amount, risk reason
- Source: trades table

2. Withdrawal Evidence
- Top 3-5 withdrawals by amount
- Shows: withdrawal ID, asset, amount, destination address
- Highlights: New addresses (higher risk)
- Source: withdrawals table

3. Network Evidence
- Cluster membership information
- Shows: cluster ID, member count, cluster risk score
- Shows: Related accounts, shared devices
- Source: cluster_members, account_clusters tables

4. Risk Factor Evidence
- Detailed factors from latest risk event
- Shows: factor name, value, description, severity
- Source: risk_factors table

5. Feature Evidence
- ML feature values that contributed to score
- Shows: shared_device_count, trade_frequency_24h, etc.
- Source: feature_table

6. Rule Evidence
- Triggered rules derived from feature values
- Shows: rule name, severity, description
- Source: Derived using same logic as RiskScoringService

Frontend Integration:

Investigation page - Case Detail panel:
New "Risk Evidence" section displaying:
- Transaction Signals
- Withdrawal Signals
- Network Signals
- Rule Signals
- Risk Drivers

Design Principles:
- Match existing UI style
- Investigator-focused, not data dump
- Clear visual hierarchy
- Contextual explanations

Architecture Compliance:

✅ DOES NOT modify existing risk scoring logic
✅ DOES NOT modify LightGBM model prediction
✅ DOES NOT modify risk level thresholds
✅ DOES NOT introduce artificial demo logic
✅ READ-ONLY explanation from existing risk events
✅ Follows existing API contract design principles

Product Impact:

Before: Investigation workflow showed "what" (risk score)
After: Investigation workflow shows "why" (evidence behind the score)

This completes the investigation narrative:
1. See risk score in queue
2. Select case for investigation
3. See evidence explaining WHY the account is risky
4. Take appropriate action

Use Case Example:

Before:
"I see user U01406 has risk score 80.27 (HIGH).
I should investigate this case."

After:
"I see user U01406 has risk score 80.27 (HIGH).
They are part of a 24-member fraud cluster (Cluster_device_sharing_6).
They made a $385,605 BTC sell transaction.
They are connected to 23 other accounts through shared devices.
Multiple rules were triggered: large linked account network.
I should investigate this case immediately."

Technical Implementation Summary:

Files Modified:
1. backend/app/services/evidence_service.py (NEW)
2. backend/app/models/schemas.py (added RiskEvidenceResponse)
3. backend/app/api/routes/risk.py (added evidence endpoint)
4. frontend/src/services/api.ts (added getCaseEvidence method)
5. frontend/src/pages/Investigation.tsx (added Risk Evidence section)
6. DATA_CONTRACT.md (added section 18)
7. MVP_PRODUCT_REFINEMENT_LOG.md (this entry)

Data Flow:
1. User selects case in Investigation Queue
2. Frontend calls GET /api/risk/cases/{user_id}/evidence
3. EvidenceService aggregates data from existing tables
4. Returns evidence package (transactions, network, rules, features)
5. Frontend displays evidence in Case Detail panel

No changes to:
- Risk scoring logic (RiskScoringService)
- ML model inference (MLInferenceService)
- Graph analysis (GraphAnalysisService)
- Feature engineering (FeatureEngineeringService)
- Rule thresholds or detection logic

Validation:

Evidence data is 100% derived from existing database:
- Transaction evidence from trades table
- Withdrawal evidence from withdrawals table
- Network evidence from cluster_members, account_clusters
- Risk factor evidence from risk_factors table
- Feature evidence from feature_table
- Rule evidence derived from feature values

No artificial or mock data generated.

Future Enhancements (Out of MVP Scope):

- Evidence timeline visualization
- Related account investigation workflow
- Evidence export for case reporting
- Custom evidence rules configuration
- Evidence-based case routing
- Historical evidence comparison

---

# Network Signals Explainability Enhancement

Date: 2026-07-19

Problem:

Current Investigation workflow Network Signals only showed aggregated information:

- "Suspicious network relationship detected"
- Connected Accounts: 6
- Shared device count

This was insufficient for fraud investigators because they could not understand:
- Which accounts are connected?
- Why are they connected?
- What entity created the relationship?
- Which relationship is the strongest evidence?

Decision:

Enhance Network Signals from summary-level to actionable investigation evidence.

This is a READ-ONLY explainability enhancement - does NOT modify:
- Risk scoring logic
- ML model inference
- Graph detection algorithm
- Clustering logic
- Any existing detection behavior

Implementation:

Backend Changes:

1. evidence_service.py - Added new method:
   - `get_network_signals(user_id, limit)` - Returns entity-level relationship evidence
   - For each related account, provides:
     - Relationship type (shared_device, shared_ip)
     - Evidence entities (device_fingerprints, shared_ips)
     - Related account's risk level and score
   - Sorts by risk score (highest first) for investigation priority

2. risk.py - Added new API endpoint:
   - `GET /api/risk/cases/{user_id}/network-signals?limit=5`
   - Returns NetworkSignalsResponse with connected account details

3. schemas.py - Added new schemas:
   - `ConnectedAccountSignal` - Single connected account with relationship details
   - `NetworkSignalsResponse` - Container for connected accounts list

Frontend Changes:

1. api.ts - Updated types and API:
   - Added `ConnectedAccountSignal` interface
   - Added `NetworkSignals` interface
   - Added `getNetworkSignals(userId, limit)` method

2. Investigation.tsx - Enhanced Network Signals display:
   - Added state for network_signals and loadingNetworkSignals
   - Added expandable account relationships UI
   - Each account shows:
     - User ID
     - Relationship type (Shared Device Fingerprint, Shared IP Address)
     - Evidence entity (Device ID, IP Address)
     - Risk level badge
     - Risk score
   - Sorted by risk score (highest first)
   - Empty state: "No suspicious network relationships detected."

Supported Relationship Types (MVP):

1. Shared Device Fingerprint
   - Multiple accounts using the same device
   - Evidence: device_id from devices table

2. Shared IP Address
   - Multiple accounts accessing from the same IP address
   - Evidence: ip_address from devices table

NOT Implemented (out of MVP scope):
- Email similarity
- Address similarity
- Behavioral similarity
- Graph embedding similarity

Data Sources (all existing, no new data):
- cluster_members table - Related accounts in same cluster
- devices table - Shared devices and IPs
- risk_events table - Related account risk scores

UI Example:

Before:
```
Connected Accounts: 6
```

After:
```
▼ U10234  |  HIGH Risk  |  82/100
  Shared Device Fingerprint
  DEVICE_88921

▼ U10987  |  MEDIUM Risk  |  65/100
  Shared IP Address
  192.168.1.100
```

Documentation Updates:

1. DATA_CONTRACT.md
   - Added section "19. Network Signals Explainability"
   - Documented API contract, field definitions, data sources
   - Documented supported relationship types
   - Documented frontend usage and UI structure

2. MOCK_DATA_INVENTORY.md
   - Marked Network Signals as backend-generated
   - No frontend hardcoded values

Validation Checklist:

✅ Risk scoring unchanged
✅ Graph clustering unchanged
✅ Existing detection_methods API unchanged
✅ Investigation Queue still works
✅ Case Detail displays detailed Network Signals
✅ API response contains explainable network relationship data

Product Impact:

Before: Analyst sees "network detected risk" but doesn't know why
After: Analyst sees specific relationships explaining the risk

This completes the investigation narrative:
1. See risk score in queue
2. Select case for investigation
3. See evidence explaining WHY the account is risky (including network relationships)
4. Take appropriate action

Use Case Example:

Before:
"I see user U01406 is part of a 24-member fraud cluster.
I should investigate this case."

After:
"I see user U01406 is connected to U10234 through shared device DEVICE_88921.
U10234 has HIGH risk (82/100).
They are also connected to U10987 through IP 192.168.1.100.
These are strong indicators of account takeover or fraud ring.
I should investigate this case immediately."

Technical Implementation Summary:

Files Modified:
1. backend/app/services/evidence_service.py (added get_network_signals method)
2. backend/app/api/routes/risk.py (added network-signals endpoint)
3. backend/app/models/schemas.py (added ConnectedAccountSignal, NetworkSignalsResponse)
4. frontend/src/services/api.ts (added types and getNetworkSignals method)
5. frontend/src/pages/Investigation.tsx (enhanced Network Signals display)
6. DATA_CONTRACT.md (added section 19)
7. MVP_PRODUCT_REFINEMENT_LOG.md (this entry)

No changes to:
- Risk scoring logic (RiskScoringService)
- ML model inference (MLInferenceService)
- Graph analysis (GraphAnalysisService)
- Feature engineering (FeatureEngineeringService)
- Rule thresholds or detection logic
- Any database schema

Data Flow:
1. User selects case in Investigation Queue
2. Frontend calls GET /api/risk/cases/{user_id}/network-signals
3. EvidenceService aggregates relationship data from existing tables
4. Returns network signals with account-level detail
5. Frontend displays expandable account relationships

All data is 100% derived from existing database tables.
No artificial or mock data generated.

---

# Evidence Load More Functionality

Date: 2026-07-19

Decision:

Add Load More functionality for Transaction Signals and Network Signals to:
- Improve page performance by reducing initial render load
- Prioritize high-risk evidence (top 3) for quick investigation
- Allow analysts to load additional evidence as needed

Implementation:

Frontend Changes (Investigation.tsx):

1. New state variables:
   - `displayedTransactionCount`: Controls how many transactions to display (default: 3)
   - `displayedNetworkCount`: Controls how many network accounts to display (default: 3)

2. Load more functions:
   - `loadMoreTransactions()`: Increases displayedTransactionCount by 3
   - `loadMoreNetworkSignals()`: Increases displayedNetworkCount by 3, up to total available

3. Display logic:
   - Transaction Signals: `.slice(0, displayedTransactionCount)`
   - Network Signals: `.slice(0, displayedNetworkCount)`

4. Reset on case change:
   - `handleCaseSelect()` resets both counts to 3 when selecting a new case

Backend Behavior:

Transaction Evidence:
- Already returns all suspicious transactions sorted by value (highest first)
- Frontend displays top 3 by default

Network Signals:
- Backend already sorts by risk_score descending (highest risk first)
- Frontend displays top 3 by default

UI Behavior:

Transaction Signals:
- Default: Shows top 3 transactions
- If more than 3: Shows "Load More (X more transactions)" button
- Each click loads 3 more transactions
- Shows "Showing top X" in header

Network Signals:
- Default: Shows top 3 riskiest connections
- If more than 3: Shows "Load More (X more accounts)" button
- Each click loads 3 more accounts
- Shows "Showing top 3 riskiest connections" in header

Files Modified:
1. frontend/src/pages/Investigation.tsx (added Load More state and functions)
2. DATA_CONTRACT.md (updated Network Signals section with Load More behavior)
3. MOCK_DATA_INVENTORY.md (updated Risk Evidence section status)
4. MVP_PRODUCT_REFINEMENT_LOG.md (this entry)

No backend changes required - sorting already implemented correctly.

Product Impact:

Before: All evidence loaded at once (potential performance issue with large datasets)
After: Progressive loading prioritizes highest-risk evidence, improves performance

Analysts can:
- Quickly see top 3 riskiest transactions
- Quickly see top 3 riskiest network connections
- Load more evidence as needed for deeper investigation

No changes to:
- Risk scoring logic (RiskScoringService)
- ML model inference (MLInferenceService)
- Graph analysis (GraphAnalysisService)
- Feature engineering (FeatureEngineeringService)
- Rule thresholds or detection logic
- Any database schema

Data Flow:
1. User selects case in Investigation Queue
2. Frontend calls GET /api/risk/cases/{user_id}/network-signals
3. EvidenceService aggregates relationship data from existing tables
4. Returns network signals with account-level detail
5. Frontend displays expandable account relationships

All data is 100% derived from existing database tables.
No artificial or mock data generated.

---

# Risk Signals Display Refinement

Date: 2026-07-19

Issue:

"Risk Signals" information was displayed in multiple locations, creating redundancy and visual clutter:

1. Risk Command Center - Risk Investigation Queue table had a "Risk Signals" column showing factor text
2. Investigation page - Case Detail panel had a standalone "Risk Signals" section

This created inconsistent display patterns and duplicated information now better served by the Risk Evidence section.

Decision:

Remove "Risk Signals" from both locations to:

1. Reduce visual clutter in Investigation Queue table
2. Streamline Investigation page case detail panel
3. Avoid redundancy with new Risk Evidence explainability feature
4. Maintain consistent information architecture

Changes Made:

Risk Command Center (RiskCommandCenter.tsx):
- Removed "Risk Signals" column from Investigation Queue table
- Removed `risk_factors` from tableColumns array
- Removed risk_factors data mapping from tableData
- Cleaned up unused risk_factors property from transformedCases

Investigation page (Investigation.tsx):
- Removed "Risk Signals" section from Case Detail panel
- This was a standalone card showing risk factors with severity badges

Result:

Risk Investigation Queue table now displays:
- Case ID
- User ID
- Risk Score
- Risk Level
- Detection (detection methods badge)
- Recommended Action

Investigation page Case Detail panel now displays:
- Case Header (case info, risk score)
- Risk Profile (account age, volume, detection methods)
- Recommended Action
- AI Risk Explanation
- Risk Evidence (transaction, network, rule, feature evidence)

Risk signals information is now available through:
1. Detection Methods badge (shows ML/Rule/Graph attribution)
2. Risk Evidence section (detailed transaction, network, rule evidence)
3. AI Risk Explanation (summary and contributing factors)

Data Contract Updates (DATA_CONTRACT.md):
- Updated Investigation Queue Contract to reflect removed column
- Added note about Risk Evidence section as alternative source
- Updated response example to use "items" instead of "cases"
- Removed risk_factors from table columns documentation

Product Impact:

Before: Multiple locations showed overlapping risk signal information
After: Consolidated, streamlined display with clear information hierarchy

The Risk Evidence section provides more detailed and actionable evidence than the previous "Risk Signals" display, making this a net improvement for investigation workflow efficiency.
---

# Model Metadata Refinement

Date: 2026-07-19

Issue:

Model Monitoring page Model Metadata section was displaying hardcoded values for algorithm, model_type, and feature_dimension instead of using actual model metadata from the backend API.

Found in:
- DEFAULT_MODEL_METADATA constant with hardcoded values (algorithm: 'LightGBM', model_type: 'Gradient Boosting', feature_dimension: 14)
- Frontend displaying these defaults regardless of actual trained model metadata
- No backend storage of these values

Root Cause:

The ModelMetadata database table only stored model_name, version, and performance metrics (auc, ks, psi) but not algorithm, model_type, or feature_count.
The frontend used DEFAULT_MODEL_METADATA as a fallback for these missing fields.

Solution:

Implemented end-to-end model metadata storage and retrieval:

Backend Changes:
1. database.py - Added new columns to ModelMetadata table:
   - algorithm: String(50) - e.g., "LightGBM"
   - model_type: String(50) - e.g., "Gradient Boosting"
   - feature_count: Integer - Number of features used in training

2. train_risk_model.py - Updated to save new metadata fields:
   - Set algorithm="LightGBM"
   - Set model_type="Gradient Boosting"
   - Set feature_count=len(feature_importance)

3. pipeline_service.py - Updated train_model() method:
   - Save algorithm, model_type, feature_count when creating ModelMetadata record

4. model_monitoring_service.py - Updated get_current_model_metrics():
   - Return algorithm, model_type, feature_count in API response
   - Handle backward compatibility with hasattr checks for existing models

5. Created migration script (migrations/add_model_metadata_fields.py):
   - Add new columns to existing databases
   - Supports upgrade and downgrade operations

Frontend Changes:
1. api.ts - Updated ModelMonitoringData interface:
   - Added algorithm?: string | null
   - Added model_type?: string | null
   - Added feature_count?: number | null

2. ModelMonitoring.tsx - Removed hardcoded defaults:
   - Removed DEFAULT_MODEL_METADATA constant entirely
   - Updated all displays to use metrics.algorithm, metrics.model_type, metrics.feature_count
   - Shows "N/A" when fields are null (no model trained)

Data Contract Updates (DATA_CONTRACT.md):
- Updated Model Monitoring API response examples
- Added algorithm, model_type, feature_count to response documentation
- Updated null handling documentation

Result:
- Model metadata now reflects actual trained model information
- Algorithm name comes from database (e.g., "LightGBM")
- Model type comes from database (e.g., "Gradient Boosting")
- Feature count is the actual number of features used in training
- Displays "N/A" when no model is available (instead of fake values)
- Future models with different algorithms will display correctly

Product Impact:

Before: Platform displayed hardcoded model metadata that didn't reflect actual trained models
After: Platform displays real model metadata from database, enabling accurate model tracking

Technical Implementation Summary:

Files Modified:
1. backend/app/models/database.py (added algorithm, model_type, feature_count columns)
2. backend/app/migrations/add_model_metadata_fields.py (NEW - migration script)
3. ml-models/training/train_risk_model.py (save new fields during training)
4. backend/app/services/pipeline_service.py (save new fields during pipeline training)
5. backend/app/services/model_monitoring_service.py (return new fields in API)
6. frontend/src/services/api.ts (updated interface)
7. frontend/src/pages/ModelMonitoring.tsx (removed DEFAULT_MODEL_METADATA)
8. DATA_CONTRACT.md (updated API contract documentation)
9. MVP_PRODUCT_REFINEMENT_LOG.md (this entry)

No changes to:
- Risk scoring logic (RiskScoringService)
- ML model inference (MLInferenceService)
- Graph analysis (GraphAnalysisService)
- Feature engineering (FeatureEngineeringService)
- Any existing detection behavior

Validation:
- New models trained will save algorithm, model_type, feature_count
- API returns these fields in monitoring endpoint
- Frontend displays real metadata instead of hardcoded values
- Backward compatible with existing models (returns null for missing fields)

Future Enhancements:
- Add more model metadata fields (training_data_size, hyperparameters, etc.)
- Support multiple algorithms (XGBoost, Random Forest, etc.)
- Model comparison feature (compare metrics across versions)

---

# Pipeline Results Metrics Alignment

Date: 2026-07-19

Issue:

Pipeline Results was mixing different risk concepts:

1. Detection Layer (graph analysis):
   - account_clusters table = detected fraud networks
   - cluster_members table = users belonging to those networks

2. Scoring Layer (ML/Rule/Graph):
   - Generates risk scores for users

3. Case Management Layer:
   - risk_events/cases = investigation cases created after scoring

Current Problem:
- "High Risk Accounts: 135" came from risk_events/cases table
- Should be "Risky Accounts Detected: 240" from cluster_members distinct user_ids
- "Features Generated: 2000" was misleading (users, not features)

Decision:

Fix Pipeline Results to show DETECTION output, not investigation cases.

Implementation:

Backend Changes (backend/app/services/pipeline_service.py):

1. Add ClusterMember import
2. Query distinct risky accounts from detection layer:
   ```python
   risky_accounts_detected = await self.db.scalar(
       select(func.count(func.distinct(ClusterMember.user_id)))
   ) or 0
   ```

3. Update results dictionary:
   - Rename "high_risk_accounts" → "risky_accounts_detected"
   - Use cluster_members distinct count instead of risk_event_count
   - Rename "features_generated" → "feature_vectors_generated"
   - Keep fraud_networks as cluster_count (already correct)

Frontend Changes (frontend/src/services/api.ts):

1. Update PipelineStatus interface:
   - high_risk_accounts → risky_accounts_detected
   - features_generated → feature_vectors_generated

Frontend Changes (frontend/src/pages/DataPipeline.tsx):

1. Update Pipeline Results card labels:
   - "High Risk Accounts" → "Risky Accounts Detected"
   - "Features Generated" → "Users Processed"
   - Update field references to use new names

Data Contract Updates (DATA_CONTRACT.md):

1. Update results field definitions:
   - Document that risky_accounts_detected comes from cluster_members distinct user_ids
   - Document that fraud_networks is account_clusters count
   - Document that feature_vectors_generated is feature_table count

Result:

Before:
- High Risk Accounts: 135 (from risk_events table - wrong concept)
- Features Generated: 2000 (misleading - these are users, not features)

After:
- Risky Accounts Detected: 240 (from cluster_members - correct detection metric)
- Users Processed: 2000 (clear what this represents)

Product Impact:

Pipeline Results now correctly answers:
"What did the pipeline detect?"

NOT:
"How many investigation cases were created?"

This aligns the platform with enterprise fraud platform terminology:
- Detection Layer: Graph-based network detection
- Scoring Layer: ML/Rule/Graph risk scores
- Case Management: Investigation workflow (separate concern)

No changes to:
- ML scoring logic
- Rule engine thresholds
- Graph detection algorithm
- risk_events generation logic

Technical Implementation Summary:

Files Modified:
1. backend/app/services/pipeline_service.py (added ClusterMember import, updated metrics)
2. frontend/src/services/api.ts (updated PipelineStatus interface)
3. frontend/src/pages/DataPipeline.tsx (updated labels and field names)
4. DATA_CONTRACT.md (updated results field documentation)
5. MVP_PRODUCT_REFINEMENT_LOG.md (this entry)

Database verification:
- account_clusters = 40 (Fraud Networks)
- cluster_members distinct users = 240 (Risky Accounts Detected)
- feature_table rows = 2000 (Users Processed)

---

# DataPipeline State Management Refactor

Date: 2026-07-19

Problem:

The DataPipeline page had inconsistent state management with multiple issues:

1. **Frontend-driven state with no backend persistence**
   - Upload status tracked in React state only
   - Lost on page refresh
   - No way to see if data was previously uploaded

2. **Single loading state for all operations**
   - One `loading` boolean for both upload and pipeline execution
   - Can't distinguish which operation is running
   - Poor UX during long-running operations

3. **Manual stage status updates**
   - Frontend manually constructed stage status after pipeline run
   - Not derived from backend state
   - Status mapping was lossy and inconsistent

4. **No reset capability**
   - No way to clear pipeline state and start fresh
   - Had to manually clear database
   - Poor user experience for starting over

5. **Backend returned hardcoded status**
   - `get_pipeline_status()` returned PENDING for most stages
   - Only `data_sources` was dynamic
   - No way to know actual pipeline state

Decision:

Implement backend-driven state management where:
- Backend is the single source of truth for all pipeline state
- Frontend derives all state from backend API
- No manual state construction in frontend
- Proper loading states for each operation
- Reset functionality for starting fresh

Implementation:

Backend Changes (backend/app/services/pipeline_service.py):

1. Enhanced `get_pipeline_status()` method:
   - Added `upload_status`, `upload_timestamp`, `upload_counts` fields
   - All stage statuses derived from database inspection
   - Returns `results` when pipeline completed

2. Database-based status determination:
   ```python
   # Determine statuses based on data presence
   has_data = user_count > 0 and device_count > 0 and trade_count > 0 and withdrawal_count > 0
   
   upload_status = COMPLETED if has_data else PENDING
   feature_engineering_status = COMPLETED if feature_count > 0 else PENDING
   graph_analysis_status = COMPLETED if cluster_count > 0 else PENDING
   ml_scoring_status = COMPLETED if risk_event_count > 0 else PENDING
   ```

3. New `POST /api/pipeline/reset` endpoint:
   - Clears all data via `clear_all_data()`
   - Returns fresh status after reset
   - Simplifies frontend reset workflow

Backend Changes (backend/app/models/schemas.py):

1. Enhanced `PipelineStatusResponse` schema:
   - Added `upload_status: str` (PENDING/COMPLETED/FAILED)
   - Added `upload_timestamp: Optional[str]`
   - Added `upload_counts: Optional[Dict[str, int]]`
   - Added `results: Optional[Dict[str, Any]]`

2. Added `Any` to imports (fix for NameError)

Frontend Changes (frontend/src/pages/DataPipeline.tsx):

1. Split loading states:
   ```typescript
   const [uploadStatus, setUploadStatus] = useState<UploadStatus>('INITIAL');
   const [uploading, setUploading] = useState(false);
   const [runningPipeline, setRunningPipeline] = useState(false);
   const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
   const [files, setFiles] = useState<Record<string, File>>({});
   ```

2. Upload button states:
   - INITIAL → UPLOADING → UPLOADED / FAILED
   - Disabled when UPLOADING or UPLOADED
   - Shows correct text for each state

3. Run Pipeline button:
   - Disabled until `upload_status === 'COMPLETED'`
   - Only shows loading during `runningPipeline`

4. Removed manual state updates:
   - No more `setUploadedDatasets()` calls
   - No more manual stage construction
   - All state derived from backend

5. Added Reset Pipeline button:
   - Only shows when `upload_status === 'COMPLETED'`
   - Calls `/api/pipeline/reset` endpoint
   - Clears local file selection state
   - Reloads backend status

6. File selection UI improvements:
   - Shows selected files with blue border before upload
   - Shows uploaded files with green border
   - Remove button for selected files
   - Clear visual feedback for each state

Frontend Changes (frontend/src/services/api.ts):

1. Updated `PipelineStatus` interface:
   ```typescript
   export interface PipelineStatus {
     upload_status: string;
     upload_timestamp?: string;
     upload_counts?: { users, devices, trades, withdrawals };
     data_sources: string;
     dataset_validation: string;
     feature_engineering: string;
     ml_scoring: string;
     graph_analysis: string;
     results?: { total_records, users, high_risk_accounts, fraud_networks, features_generated };
   }
   ```

2. Added `resetPipeline()` method:
   ```typescript
   resetPipeline: () => api.post<{
     message: string;
     deleted_counts: Record<string, number>;
     total_deleted: number;
     status: PipelineStatus;
   }>('/api/pipeline/reset')
   ```

Data Contract Updates (DATA_CONTRACT.md):

1. Updated Pipeline Status Contract section:
   - Enhanced API response documentation
   - Added upload status fields
   - Added results fields
   - Updated frontend mapping documentation

Result:

**Before:**
- State lost on page refresh
- Can't tell if data was uploaded
- Single loading state for all operations
- Manual stage status construction
- No way to reset pipeline

**After:**
- Backend is single source of truth
- All state persists and survives refresh
- Separate loading states for upload and pipeline execution
- All stage statuses from backend
- Reset button for starting fresh
- Clear visual feedback for file selection

Product Impact:

Before: Users couldn't tell if data was already uploaded, had no way to start over, and couldn't see which operation was running.

After: Users can:
- See upload status at a glance
- Know if pipeline has been run
- See which operation is in progress
- Reset pipeline to start fresh
- Understand current pipeline state

Technical Implementation Summary:

Files Modified:
1. backend/app/services/pipeline_service.py (enhanced status logic)
2. backend/app/api/routes/pipeline.py (added reset endpoint)
3. backend/app/models/schemas.py (enhanced schemas, added Any import)
4. frontend/src/pages/DataPipeline.tsx (refactored state management)
5. frontend/src/services/api.ts (updated types, added reset method)
6. DATA_CONTRACT.md (updated Pipeline Status Contract)
7. MVP_PRODUCT_REFINEMENT_LOG.md (this entry)

No changes to:
- Risk scoring logic (RiskScoringService)
- ML model inference (MLInferenceService)
- Graph analysis (GraphAnalysisService)
- Feature engineering (FeatureEngineeringService)
- Any existing detection behavior
- Database schema (using existing tables)

Data Flow:

1. Page load: Frontend calls `GET /api/pipeline/status`
2. Backend inspects database and returns current state
3. Frontend derives all UI state from backend response
4. User selects files: Local state updates immediately (blue border)
5. User clicks upload: `uploading = true`, calls API
6. Upload completes: Reload status, `upload_status = COMPLETED`
7. User clicks run pipeline: `runningPipeline = true`, calls API
8. Pipeline completes: Reload status, stages show COMPLETED
9. User clicks reset: Clear data, reload status, back to INITIAL

State Management Principles:

✅ Backend is single source of truth
✅ Frontend derives all state from backend
✅ No manual state construction
✅ Clear visual feedback for each state
✅ Operations can run independently
✅ Reset capability for starting fresh
