CSV Upload → Backend → Frontend Data Contract

Version: MVP v0.7

Purpose:

Define the data exchange contract between:

CSV Upload
→ Backend Processing Pipeline
→ Risk Analytics Engine
→ Frontend Dashboard

The frontend should not depend on data source implementation.

All dashboard metrics should be generated from backend APIs.

1. Overall Data Flow
User uploads CSV files

        |
        v

Backend Upload Service

        |
        v

Data Validation

        |
        v

Feature Engineering

        |
        v

Risk Engine

(LightGBM Model)
+
(Rule Engine)
+
(Graph Analysis)

        |
        v

Risk Analytics APIs

        |
        v

Frontend Dashboard
2. Dataset Metadata Contract

API:

GET /api/dataset/latest

Purpose:

Provide current uploaded dataset information.

Response:

{
  "dataset_id": "dataset_20260715_001",

  "upload_time": "2026-07-15T14:32:00",

  "files": [
    {
      "name": "users.csv",
      "records": 10000,
      "status": "processed"
    },
    {
      "name": "transactions.csv",
      "records": 50000,
      "status": "processed"
    }
  ],

  "total_records": 60000,

  "date_range": {
    "start": "2026-07-01",
    "end": "2026-07-15"
  },

  "processing_status": "completed"
}

Frontend usage:

Used by:

Dataset Info
Data Provenance Tooltip
Generated Timestamp
Date Range Display
3. Risk Overview Homepage Contract

API:

GET /api/risk/overview

Purpose:

Homepage dashboard metrics and visualizations.

Response:

{
  "summary": {
    "analyzed_users": 10000,
    "high_risk_accounts": 208,
    "fraud_networks": 25,
    "risk_recommendations": 156
  },
  "risk_score_distribution": [
    { "range": "0-20", "count": 1600, "percentage": 16.0 },
    { "range": "20-40", "count": 2400, "percentage": 24.0 },
    { "range": "40-60", "count": 2800, "percentage": 28.0 },
    { "range": "60-80", "count": 1900, "percentage": 19.0 },
    { "range": "80-100", "count": 1300, "percentage": 13.0 }
  ],
  "risk_score_statistics": {
    "average": 52.3,
    "threshold": 80.0,
    "maximum": 98.2
  },
  "risk_level_composition": {
    "critical": 32,
    "high": 176,
    "medium": 390,
    "low": 845,
    "total": 1443
  },
  "detection_sources": [
    { "name": "Rule Engine", "percentage": 30.0, "color": "#3b82f6" },
    { "name": "LightGBM Model", "percentage": 55.0, "color": "#8b5cf6" },
    { "name": "Graph Network", "percentage": 15.0, "color": "#06b6d4" }
  ]
}

Frontend mapping:

Section 1 - Executive Risk Summary KPI Cards (in order):
1. Analyzed Users - summary.analyzed_users
   - Definition: Total unique users analyzed from uploaded dataset
   - Subtitle: "Unique users analyzed from uploaded dataset"

2. High Risk Accounts - summary.high_risk_accounts
   - Definition: Users with Critical or High risk scores
   - Subtitle: "Users with Critical or High risk scores"
   - Note: Count of unique users, NOT alerts/events

3. Network-linked Accounts - summary.fraud_networks
   - Definition: Unique users linked to suspicious clusters detected through network analysis
   - Subtitle: "Accounts in suspicious network clusters"
   - Note: Count of unique users in fraud clusters (deduplicated), NOT cluster count

4. Risk Recommendations - summary.risk_recommendations
   - Definition: Users with AI-generated risk actions
   - Subtitle: "Users with AI-generated risk actions"
   - Note: Unique users with recommendations, NOT recommendation text count

Section 2 - Risk Intelligence Overview:

Row 1:
1. Risk Score Distribution - risk_score_distribution
   - Histogram chart with buckets (0-20, 20-40, 40-60, 60-80, 80-100)
   - Shows high risk threshold marker

2. Risk Score Analytics - risk_score_statistics
   - Visual stat card with: average, threshold, maximum

Row 2:
3. Risk Level Composition - risk_level_composition
   - Segmented horizontal bar with counts per level

4. Risk Detection Coverage - detection_sources
   - Bar chart showing detection method percentages
   - UI label: "Risk Detection Coverage"

Important Design Rules:
- All KPI values come from backend API
- Do NOT hardcode business values in UI
- Mock data only as temporary fallback if API unavailable
- No real-time wording (upload-based analysis)
- No automated decision wording (recommendations only)
4. Risk Recommendation Contract

API:

GET /api/risk/recommendations

Purpose:

Generate human-readable risk suggestions.

Important:

This is NOT automated decision making.

System provides:

Risk assessment + recommended action.

Response:

[
 {
  "case_id":"CASE001",

  "user_id":"U01401",

  "risk_score":99.5,

  "risk_level":"CRITICAL",


  "recommended_action":
  "Review withdrawal activity",


  "risk_signals":[
    "Large withdrawal",
    "Unusual device",
    "Graph connection anomaly"
  ],


  "detection_methods":[

    "LightGBM",

    "Rule Engine",

    "Graph Analysis"

  ],


  "generated_time":
  "2026-07-15T14:32:00"

 }
]

Frontend:

Risk Investigation Queue.

5. Investigation Queue Contract

API:

GET /api/risk/cases

Purpose:

Returns users requiring risk investigation or review.

Investigation Queue represents analyst workload,
not the complete analyzed dataset.

Request Parameters:

page: Page number (default: 1)
page_size: Items per page (default: 20, max: 100)
risk_level: Filter by risk level - CRITICAL, HIGH, MEDIUM (optional)

Example Request:

GET /api/risk/cases?page=1&page_size=50&risk_level=high

Response:

{
  "items": [
    {
      "user_id": "U001",
      "risk_score": 87,
      "risk_level": "HIGH",
      "detection_methods": ["LightGBM Model", "Rule Engine"],
      "primary_reason": "Suspicious trading pattern",
      "recommended_action": "Review suspicious transaction activity",
      "detected_at": "2026-07-15T10:32:00"
    }
  ],
  "total": 598,
  "page": 1,
  "page_size": 50
}

Table Columns (Frontend Display):
- Case ID
- User ID
- Risk Score
- Risk Level
- Detection (detection_methods badge)
- Recommended Action

Note: "Risk Signals" column removed - risk signals are now displayed in Investigation page case detail panel via Risk Evidence section.

Risk Filtering Rules:

Needs Review (default):
Critical + High + Medium risk users

Formula:
Needs Review = Critical + High + Medium

Critical:
Only Critical risk cases

High:
Only High risk cases

Medium:
Only Medium risk cases

Low Risk Users:

NOT included in Investigation Queue.

Reason:

Low-risk users do not require analyst investigation.

They are represented in:
- Risk Level Composition chart
- Overall risk distribution

Default View:

When opening Investigation Queue:

Default selected tab: Needs Review

Example Upload:

2000 users uploaded

Risk distribution:
- Critical: 0
- High: 598
- Medium: 2
- Low: 1400

Investigation Queue displays:
Needs Review (600)

NOT:
All (2000)

No fields:

status
assigned_to
resolved_time

Reason:

MVP does not include case workflow management.

Pagination:

Backend-controlled, not frontend-only.

API returns:
- filtered cases for current page
- total count matching filter
- pagination metadata

Frontend displays:
- current page cases
- total matching count
- pagination controls

6. Case Detail Context Contract

API:

GET /api/risk/events/{user_id}

Purpose:

Returns detailed case context including account age and trading volume.

This endpoint provides enriched case context for investigation detail view.

Response:

{
  "user_id": "U001",
  "risk_score": 87,
  "risk_level": "HIGH",
  "risk_probability": 0.87,
  "primary_reason": "Unusual trading activity",
  "recommended_action": "Review account",
  "detected_at": "2026-07-15T10:32:00",
  "event_type": "trading_anomaly",
  "ml_score": 45.0,
  "rule_score": 25.0,
  "graph_score": 0.0,
  "detection_methods": ["LightGBM", "Rule Engine"],
  "risk_factors": [
    {
      "id": 1,
      "factor_name": "high_frequency_trading",
      "factor_value": 0.85,
      "factor_description": "Trading frequency exceeds normal patterns"
    }
  ],
  "cluster": {
    "cluster_id": 42,
    "member_count": 5,
    "risk_score": 92.5
  },
  "account_age": 365,
  "total_volume": 125000.50
}

Field Definitions:

- account_age: Account age in days (computed from User.account_created_time)
  - Returns null if account_created_time is not available
  - Calculated as: (current_time - account_created_time) in days

- total_volume: Total trading volume (sum of price * quantity from all trades)
  - Returns null if user has no trading history
  - Calculated as: SUM(Trade.price * Trade.quantity) WHERE user_id

Frontend:

Investigation page - Case Detail panel.

Display format:
- account_age: "{N} days" or "N/A" if null
- total_volume: "${X,XXX.XX}" or "N/A" if null

7. Risk Trend Contract

API:

GET /api/risk/trend

Important:

Only display trend when historical datasets exist.

Response:

{
 "available":true,


 "periods":[
   {
    "date":"2026-07-10",
    "risk_events":120
   },

   {
    "date":"2026-07-11",
    "risk_events":150
   }
 ]
}

If no historical data:

{
 "available":false,

 "message":
 "Upload additional datasets to enable trend analysis"
}

Frontend:

Do NOT display fake line chart.

8. Detection Attribution Contract

API:

GET /api/risk/overview

Purpose:

Returns detection attribution metadata as part of risk overview.

Detection attribution is READ-ONLY metadata computed from RiskEvent scores.

It does NOT modify or influence risk scoring logic.

Risk Detection Coverage (UI Display):

Shows what percentage of high-risk cases were identified by each detection method.

Detection Coverage Rate = (High-risk accounts detected by method / Total high-risk accounts) × 100

Where:
- "High-risk accounts" = CRITICAL risk level + HIGH risk level (combined)
- A detection method identifies an account if its score meets or exceeds the attribution threshold

This is the dashboard card labeled "Risk Detection Coverage" in the UI.

Key Characteristics:

- Multiple methods CAN detect the same account
- Percentages do NOT need to sum to 100%
- This reflects independent detection capability
- High correlation in detection coverage reflects actual data distribution

Response (detection_sources field):

[
  {
    "method": "LightGBM Model",
    "account_count": 598,
    "percentage": 100.0,
    "color": "#8b5cf6"
  },
  {
    "method": "Rule Engine",
    "account_count": 598,
    "percentage": 100.0,
    "color": "#3b82f6"
  },
  {
    "method": "Graph Network",
    "account_count": 598,
    "percentage": 100.0,
    "color": "#06b6d4"
  }
]

Field Definitions:
- method: Detection method name
- account_count: Number of HIGH/CRITICAL accounts detected by this method
- percentage: Detection coverage rate = (account_count / total_high_risk) × 100
- color: Hex color for UI visualization

Detection Attribution Rules:

A detection method is considered "triggered" when its component score meets or exceeds the attribution threshold.

| Method | Attribution Rule | Threshold | Source |
|--------|------------------|-----------|--------|
| LightGBM | ml_score >= DETECTION_ML_THRESHOLD | 10.0 | ML model probability × 100 |
| Rule Engine | rule_score >= DETECTION_RULE_THRESHOLD | 15.0 | Accumulated rule score (0-100) |
| Graph Network | graph_score >= DETECTION_GRAPH_THRESHOLD | 10.0 | Cluster-based score (0-100) |

**Note:** Detection coverage is calculated over CRITICAL + HIGH risk level cases combined.

Per-Case Detection Methods Field:

API: GET /api/risk/cases

Each case response includes detection_methods field:

{
  "user_id": "user_123",
  "risk_score": 87,
  "risk_level": "HIGH",
  "ml_score": 45.0,
  "rule_score": 25.0,
  "graph_score": 0.0,
  "detection_methods": ["LightGBM", "Rule Engine"]
}

detection_methods represents:
"Risk detection methods that contributed meaningful risk signals for this case."

This field is computed on backend using the attribution thresholds above.
It is NOT derived in frontend.

Separation of Concerns:

Risk Scoring Pipeline (deterministic):

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

Detection Attribution (read-only):
- COUNT high-risk users WHERE ml_score >= threshold
- COUNT high-risk users WHERE rule_score >= threshold
- COUNT high-risk users WHERE graph_score >= threshold
- Calculate detection coverage rates independently
- Generate detection_methods array for each case

Key Principle:

Detection attribution is derived from actual model outputs using explicit attribution thresholds.

It does NOT introduce artificial variety or modify scoring logic.

Detection coverage percentages may exceed 100% total because one case can have multiple detection methods.

If all high-risk accounts have non-zero scores from all methods (as in current demo data),

then all methods show 100% detection rate - this reflects the data, not a bug.

Frontend:

Bar chart (horizontal).

X axis: percentage (%)

Y axis: method name

Color: each method has distinct color

Tooltip: shows detection rate percentage

Signal Combination Breakdown (UI Display):

Shows the overlap between detection methods - how high-risk accounts are detected by different signal combinations.

Response (signal_combination_breakdown field):

{
  "ml_only": 45,
  "rule_only": 30,
  "graph_only": 15,
  "ml_rule": 80,
  "ml_graph": 25,
  "rule_graph": 20,
  "multi_signal": 100
}

Field Definitions:
- ml_only: Accounts detected only by LightGBM (ML score >= threshold, but Rule and Graph scores below threshold)
- rule_only: Accounts detected only by Rule Engine (Rule score >= threshold, but ML and Graph scores below threshold)
- graph_only: Accounts detected only by Graph Network (Graph score >= threshold, but ML and Rule scores below threshold)
- ml_rule: Accounts detected by both LightGBM and Rule Engine (both scores >= threshold, Graph score below threshold)
- ml_graph: Accounts detected by both LightGBM and Graph Network (both scores >= threshold, Rule score below threshold)
- rule_graph: Accounts detected by both Rule Engine and Graph Network (both scores >= threshold, ML score below threshold)
- multi_signal: Accounts detected by all three methods (all scores >= threshold)

Calculation Logic:
For each HIGH/CRITICAL risk account, the backend checks each signal against its attribution threshold:
- Has ML Signal: ml_score >= DETECTION_ML_THRESHOLD (10.0)
- Has Rule Signal: rule_score >= DETECTION_RULE_THRESHOLD (15.0)
- Has Graph Signal: graph_score >= DETECTION_GRAPH_THRESHOLD (10.0)

Based on which signals are triggered, each account is counted in exactly one of the seven categories above.

Key Characteristics:
- Shows true detection overlap, not forced diversity
- Multi-signal accounts indicate stronger consensus for risk
- Single-signal accounts may warrant special investigation
- Sum of all categories equals total HIGH/CRITICAL accounts

Frontend:
Horizontal bar chart showing account counts for each combination.
Sorted by: single signals (ML, Rule, Graph), then pairs (ML+Rule, ML+Graph, Rule+Graph), then multi-signal.
Color-coded: distinct colors for each combination to differentiate overlap patterns.
Tooltip: shows account count and percentage of total HIGH/CRITICAL accounts.

UI Location:
Risk Intelligence Overview section (Row 3)
Card title: "Signal Combination Breakdown"

9. Model Performance Contract

API:

GET /api/model/performance

Response:

{

"model_name":
"LightGBM Risk Model",


"metrics":{

 "auc":0.86,

 "ks":0.42,

 "psi":0.12

}

}

Frontend explanation:

AUC:

Higher is better

KS:

Higher is better

PSI:

Lower is better

10. Feature Importance Contract

API:

GET /api/model/features

Response:

[
{
"name":"withdrawal_frequency",

"importance":0.18
},

{
"name":"device_count",

"importance":0.12
}
]

Frontend:

AI Risk Drivers chart.

11. Feature Drift Contract

API:

GET /api/model/drift

Response:

[
{
"feature":
"withdrawal_amount",

"psi":0.08,

"status":
"stable"
},

{
"feature":
"device_count",

"psi":0.25,

"status":
"drift_detected"
}
]

Frontend:

Feature-Level Drift Analysis.

12. Pipeline Status Contract

API:

GET /api/pipeline/status

Purpose:

Get comprehensive pipeline status including upload state, stage completion, and results.

Backend derives all status by inspecting database state (no manual status tracking).

Response:

{
  "upload_status": "COMPLETED" | "PENDING" | "FAILED",
  "upload_timestamp": "2026-07-19T08:49:37.086772+00:00" | null,
  "upload_counts": {
    "users": 2000,
    "devices": 2000,
    "trades": 38482,
    "withdrawals": 6475
  } | null,
  "data_sources": "PENDING" | "COMPLETED",
  "dataset_validation": "PENDING" | "COMPLETED",
  "feature_engineering": "PENDING" | "COMPLETED",
  "ml_scoring": "PENDING" | "COMPLETED",
  "graph_analysis": "PENDING" | "COMPLETED",
  "results": {
    "total_records": 48957,
    "users": 2000,
    "high_risk_accounts": 2000,
    "fraud_networks": 40,
    "features_generated": 2000
  } | null
}

Field Definitions:

- upload_status: Status of CSV file upload (PENDING/COMPLETED/FAILED)
  - COMPLETED when all 4 required datasets uploaded successfully
  - PENDING when no data or incomplete upload
  - FAILED when upload attempt failed

- upload_timestamp: ISO timestamp of most recent upload
  - Derived from max(Trade.timestamp) where trades exist
  - null when no data uploaded

- upload_counts: Record counts per uploaded dataset
  - users: Count of users in users table
  - devices: Count of devices in devices table
  - trades: Count of trades in trades table
  - withdrawals: Count of withdrawals in withdrawals table
  - null when no data uploaded

- data_sources: Status of data upload stage
  - COMPLETED when all 4 datasets exist in database
  - PENDING otherwise

- dataset_validation: Status of data validation stage
  - COMPLETED when data exists (validation passed during upload)
  - PENDING otherwise

- feature_engineering: Status of feature engineering stage
  - COMPLETED when FeatureTable has records
  - PENDING otherwise

- graph_analysis: Status of graph analysis stage
  - COMPLETED when AccountCluster has records
  - PENDING otherwise

- ml_scoring: Status of ML risk scoring stage
  - COMPLETED when RiskEvent has records
  - PENDING otherwise

- results: Pipeline results (available when ml_scoring = COMPLETED)
  - total_records: Sum of all uploaded records
  - users: Total users analyzed
  - risky_accounts_detected: Number of unique risky accounts detected via graph analysis (cluster_members distinct user_ids)
  - fraud_networks: Number of detected suspicious account clusters (account_clusters count)
    - UI Label: "Suspicious Clusters Detected"
  - feature_vectors_generated: Number of user feature vectors generated (feature_table count)
    - UI Label: "Users Processed"
  - null when pipeline not completed

Backend Status Determination:

```python
# Check if all required datasets exist
has_data = (user_count > 0 and device_count > 0 and 
           trade_count > 0 and withdrawal_count > 0)

upload_status = COMPLETED if has_data else PENDING
data_sources_status = COMPLETED if has_data else PENDING

# Check individual pipeline stages
feature_engineering_status = COMPLETED if feature_count > 0 else PENDING
graph_analysis_status = COMPLETED if cluster_count > 0 else PENDING
ml_scoring_status = COMPLETED if risk_event_count > 0 else PENDING
```

Frontend Usage:

DataPipeline page - Pipeline State:
- Fetch status on component mount
- Derive all UI state from backend response
- No manual status construction
- Reload status after operations complete

Display Rules:

Pipeline stage cards:
- completed: green border + "✓ COMPLETED" badge
- running: blue border + "⏳ RUNNING" badge
- pending: gray border + "PENDING" badge
- failed: red border + "✗ FAILED" badge

Upload status:
- COMPLETED: Show green checkmarks, display record counts and timestamp
- PENDING: Show file input fields
- FAILED: Show error message

Loading states:
- uploading: true during upload API call
- runningPipeline: true during pipeline execution
- Both independent, not mutually exclusive

Reset API:

POST /api/pipeline/reset

Purpose:

Clear all data and return pipeline to initial state.

Response:

{
  "message": "Pipeline reset successfully",
  "deleted_counts": {
    "users": 2000,
    "devices": 2000,
    "trades": 38482,
    "withdrawals": 6475,
    ...
  },
  "total_deleted": 56295,
  "status": {
    "upload_status": "PENDING",
    "upload_timestamp": null,
    "upload_counts": null,
    "data_sources": "PENDING",
    "dataset_validation": "PENDING",
    "feature_engineering": "PENDING",
    "ml_scoring": "PENDING",
    "graph_analysis": "PENDING",
    "results": null
  }
}

Frontend behavior:
- Clear local file selection state
- Reload pipeline status from backend
- Return UI to initial upload state

State Management Principles:

✅ Backend is single source of truth
✅ All state derived from database inspection
✅ No manual status tracking in application
✅ Frontend only displays backend state
✅ State survives page refresh
✅ Reset capability for starting fresh

13. Upload Requirement Contract

Required files:

users.csv

transactions.csv

devices.csv

withdrawals.csv

Upload API:

POST /api/upload

Validation:

All required CSV files must exist.

Before:

Upload Files button disabled

After:

All required files validated

Button enabled.

14. Pipeline Status Validation Strategy

IMPORTANT: Two-Layer Validation Strategy

Data Ingestion and Processing Pipeline status must follow strict validation rules.

Frontend Layer Validation:
- The "Upload Datasets" button in Data Ingestion MUST remain disabled unless all 4 required CSV datasets are selected
- Required datasets: User Data, Device Data, Transaction Data, Withdrawal Data
- Validate file extensions (.csv only) before enabling upload button
- Provide clear visual feedback for missing/invalid files
- Show progress indicator: "Selected X/4 required datasets"

Backend Layer Validation:
- Upload API MUST validate that all 4 required datasets are provided
- Reject incomplete uploads with meaningful error response
- Return detailed error message specifying which datasets are missing
- Only process upload when all required datasets are present and valid

Pipeline Status Rules:

CRITICAL: Do not mark pipeline stages as COMPLETED based on assumptions.

Data Sources Stage:
- Status: PENDING (default)
- Status: COMPLETED (only after all 4 required datasets successfully uploaded AND backend confirms ingestion)
- NEVER mark as COMPLETED just because any single file exists
- Frontend must consume backend pipeline status, not use hardcoded values

Data Validation Stage:
- Status: PENDING (default)
- Status: RUNNING (during validation)
- Status: COMPLETED (only after backend confirms validation passed)
- Status: FAILED (if backend validation fails)

Feature Engineering Stage:
- Status: PENDING (default)
- Status: RUNNING (during feature extraction)
- Status: COMPLETED (only after backend confirms completion)
- Status: FAILED (if backend processing fails)

ML Risk Scoring Stage:
- Status: PENDING (default)
- Status: RUNNING (during model execution)
- Status: COMPLETED (only after backend confirms scoring complete)
- Status: FAILED (if model execution fails)

Graph Analysis Stage:
- Status: PENDING (default)
- Status: RUNNING (during network analysis)
- Status: COMPLETED (only after backend confirms analysis complete)
- Status: FAILED (if graph processing fails)

Risk Decision Engine Stage:
- Status: PENDING (default)
- Status: COMPLETED (only after ML Risk Scoring completes)
- Depends on ML Risk Scoring stage completion

Frontend Implementation Requirements:
1. Always fetch pipeline status from backend API: GET /api/pipeline/status
2. Never hardcode stage status values
3. Map backend status directly to UI display states
4. Handle all possible states: PENDING, RUNNING, COMPLETED, FAILED
5. Update UI in real-time as backend status changes

Backend Implementation Requirements:
1. Provide accurate, real-time pipeline status
2. Status must reflect actual processing state, not assumptions
3. Include detailed error information for failed stages
4. Support status polling for long-running operations
5. Return meaningful error messages for validation failures

API Contract:

GET /api/pipeline/status
Response:
{
  "data_sources": "PENDING" | "COMPLETED",
  "dataset_validation": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED",
  "feature_engineering": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED",
  "ml_scoring": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED",
  "graph_analysis": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"
}

POST /api/pipeline/upload
Request: FormData with all 4 required CSV files
Success Response:
{
  "message": "Successfully uploaded 4 file(s)",
  "files_processed": ["users.csv", "devices.csv", "trades.csv", "withdrawals.csv"],
  "records_imported": {
    "users": 10000,
    "devices": 8500,
    "trades": 50000,
    "withdrawals": 2500
  }
}

Error Response (Missing Files):
{
  "detail": "Upload failed: Missing required datasets. Please provide all 4 files: users.csv, devices.csv, trades.csv, withdrawals.csv"
}

Error Response (Invalid File Type):
{
  "detail": "Upload failed: Invalid file format. All files must be CSV format."
}

Error Response (Processing Failed):
{
  "detail": "Upload failed: Data validation error - users.csv contains invalid records."
}

15. Future Enterprise Integration

Current:

CSV Upload

Future:

Database Connector

Kafka Stream

Data Warehouse

API Gateway

Frontend contract should remain unchanged.

Only backend ingestion layer changes.

16. Current MVP Mock Replacement Plan

Remove frontend mocks from:

RiskCommandCenter.tsx

Investigation.tsx

DataPipeline.tsx

ModelMonitoring.tsx

Replace with:

api.ts
 ↓
backend endpoints
 ↓
real processed dataset
Design Principle

The platform should present:

"AI Risk Analysis Platform"

not:

"fake real-time monitoring system"

All metrics must be:

traceable
dataset based
reproducible
explainable
Implementation Priority

Phase 1:
Dataset Metadata API

Phase 2:
Risk Summary API

Phase 3:
Investigation API

Phase 4:
Pipeline Status API

Phase 5:
Model Monitoring API

17. Model Lifecycle Completion

Overview:

The platform now demonstrates an end-to-end AI risk management workflow:

CSV Upload
→ Data Import
→ Feature Engineering
→ Graph Analysis
→ Model Training
→ Model Evaluation
→ Metadata Persistence
→ PSI Baseline Generation
→ Risk Scoring
→ Model Monitoring

Model Training API:

POST /api/pipeline/train

Purpose:

Train LightGBM model on current database data and persist model metadata.

Requirements:
- Features must be calculated (FeatureEngineeringService.run())
- Clusters must be detected (GraphAnalysisService.detect_all_clusters())
- Labels generated from cluster membership

Training Process:
1. Load features from FeatureTable
2. Generate labels: risky = cluster members, normal = non-members
3. Train/test split (80/20, stratified)
4. Train LightGBM model
5. Evaluate (AUC, KS, feature importance)
6. Save model artifact to ml-models/artifacts/
7. Save metadata to ModelMetadata table
8. Save feature importance to FeatureImportance table
9. Generate PSI baseline distribution

Response:
{
  "status": "COMPLETED",
  "model_version": "20260718_143022",
  "metrics": {
    "auc": 0.8567,
    "ks": 0.4234
  },
  "train_size": 8000,
  "test_size": 2000,
  "positive_ratio": 0.15,
  "feature_importance_count": 12,
  "baseline_saved": "/path/to/feature_distribution.json",
  "model_id": 42
}

Error Response:
{
  "status": "FAILED",
  "error": "No feature data available. Run feature engineering first."
}

Model Monitoring API:

GET /api/model/monitoring

Purpose:

Get complete model health metrics including AUC, KS, PSI, and feature drift.

Response (with trained model):
{
  "model_name": "LightGBM Risk Model",
  "version": "20260718_143022",
  "algorithm": "LightGBM",
  "model_type": "Gradient Boosting",
  "feature_count": 14,
  "deployed_at": "2026-07-18T14:30:22Z",
  "metrics": {
    "auc": 0.8567,
    "ks": 0.4234,
    "psi": 0.08
  },
  "psi_status": "stable",
  "psi_features": [
    {"feature": "shared_device_count", "psi": 0.05, "status": "stable"},
    {"feature": "trade_frequency_24h", "psi": 0.12, "status": "warning"}
  ]
}

Response (no model trained):
{
  "model_name": "LightGBM Risk Model",
  "version": "v1.0",
  "algorithm": null,
  "model_type": null,
  "feature_count": null,
  "deployed_at": null,
  "metrics": {
    "auc": null,
    "ks": null,
    "psi": null
  },
  "psi_status": "unknown",
  "psi_features": []
}

Key Behaviors:
- No fallback values when model not available
- Returns null for missing metrics
- psi_status: "stable" | "warning" | "drift" | "unknown"
- Frontend displays "No model available" when all metrics are null

Feature Importance API:

GET /api/model/feature-importance

Response (with trained model):
{
  "features": [
    {"name": "shared_device_count", "importance": 0.35, "rank": 1},
    {"name": "opposite_trade_ratio", "importance": 0.28, "rank": 2},
    {"name": "withdrawal_risk_score", "importance": 0.18, "rank": 3}
  ]
}

Response (no model trained):
{
  "features": []
}

Key Behaviors:
- No fallback demo data when model not available
- Returns empty array when no model metadata exists
- Frontend displays "No feature importance available"

Integration Points:

1. After Data Upload:
   POST /api/pipeline/upload
   → Import CSV files to database
   → Return record counts

2. Run Pipeline:
   POST /api/pipeline/run
   → Feature Engineering
   → Graph Analysis
   → Risk Scoring
   → Return pipeline status

3. Train Model:
   POST /api/pipeline/train
   → Load features from database
   → Generate labels from clusters
   → Train LightGBM model
   → Save metadata and baseline
   → Return training results

4. Monitor Model:
   GET /api/model/monitoring
   → Return model metrics and PSI data

Frontend Display:

Model Health Card:
- Shows model name, version, deployed_at
- Displays AUC, KS, PSI metrics
- Shows "No model available" when metrics are null

Feature Drift Chart:
- Shows PSI values per feature
- Shows "No drift analysis available" when psi_features is empty
- Color-coded by status (green=stable, yellow=warning, red=drift)

Feature Importance Chart:
- Shows top features by importance score
- Shows "No feature importance available" when features array is empty
- Displays actual trained model importance or empty state

MVP Limitation - Fraud Label Generation:

**Important:** The current implementation uses graph clustering for fraud label generation.

Label Source:
- Fraud labels (is_risky) are derived from graph cluster membership
- Users detected in suspicious clusters are labeled as "risky"
- This is done automatically during training pipeline execution

Why This Approach for MVP:
- Demonstrates complete ML lifecycle workflow
- Shows model training, evaluation, and monitoring
- Provides realistic feature importance rankings
- Works end-to-end without manual labeling

Production Requirement:
For production deployment, fraud labels must come from:
- Independent fraud investigation confirmation
- Manual review by fraud analysts
- External fraud intelligence sources
- Time-separated validation to prevent overfitting

Model Behavior with Current Labels:
- Model learns patterns associated with cluster membership
- AUC/KS metrics reflect cluster-based labeling
- Feature importance highlights device/trading patterns in clusters
- Suitable for pipeline demonstration, not production decision-making

18. Risk Evidence Explainability API

API:

GET /api/risk/cases/{user_id}/evidence

Purpose:

Returns explainable evidence behind a risk case for investigation workflow.

This is a READ-ONLY explanation generated from existing backend data.
Does NOT modify risk scores, ML predictions, or perform new detection.

Response:

{
  "user_id": "U01406",
  "risk_summary": {
    "risk_level": "HIGH",
    "risk_score": 80.27,
    "primary_reason": "Graph Network Analysis",
    "recommended_action": "Manual Review",
    "detection_methods": ["LightGBM", "Rule Engine", "Graph Network"],
    "detected_at": "2026-07-18T09:19:42Z",
    "ml_score": 99.54,
    "rule_score": 35.0,
    "graph_score": 100.0
  },
  "transaction_evidence": [
    {
      "transaction_id": "T024565",
      "symbol": "BTC",
      "side": "SELL",
      "price": 46854.26,
      "quantity": 8.2299,
      "value": 385605.90,
      "timestamp": "2026-06-23T02:27:47Z",
      "risk_reason": "Large transaction amount"
    }
  ],
  "withdrawal_evidence": [
    {
      "withdrawal_id": "W005755",
      "asset": "ETH",
      "amount": 19.42,
      "address": "0xau87cm453kf486i3ce8zna8nzxc45bnccu3fg00z",
      "is_new_address": false,
      "timestamp": "2026-06-23T01:05:47Z",
      "risk_reason": "Large withdrawal amount"
    }
  ],
  "network_evidence": {
    "cluster_id": 6,
    "cluster_name": "Cluster_device_sharing_6",
    "detection_type": "device_sharing",
    "member_count": 24,
    "cluster_risk_score": 92.77,
    "role_in_cluster": "spoke",
    "related_accounts_count": 23,
    "related_accounts": ["U01407", "U01408", "U01409"],
    "shared_devices": ["DEVICE001", "DEVICE002"]
  },
  "risk_factor_evidence": [
    {
      "factor_id": 67234,
      "factor_name": "Shared Device Relationships",
      "factor_value": 1.0,
      "factor_description": "1 linked accounts through shared devices",
      "severity": "medium"
    }
  ],
  "feature_evidence": {
    "shared_device_count": 1,
    "linked_account_count": 23,
    "unique_ip_count": 1,
    "trade_frequency_24h": 0,
    "trade_frequency_7d": 2,
    "opposite_trade_ratio": 0.15,
    "avg_trade_size": 45000.50,
    "trade_volume_24h": 0,
    "account_age_days": 86,
    "active_days_count": 45,
    "withdrawal_risk_score": 0.5,
    "withdrawal_frequency_24h": 0,
    "withdrawal_volume_24h": 0
  },
  "rule_evidence": [
    {
      "rule_name": "Large linked account network",
      "severity": "MEDIUM",
      "description": "User connected to 23 other accounts"
    }
  ]
}

Evidence Definitions:

1. Transaction Evidence
- Shows top 3-5 suspicious trades by value
- Displays transaction ID, symbol, side, price, quantity, calculated value
- Includes risk reason classification (e.g., "Large transaction amount")
- Source: trades table

2. Withdrawal Evidence
- Shows top 3-5 withdrawals by amount
- Displays asset, amount, destination address
- Highlights withdrawals to new addresses
- Source: withdrawals table

3. Network Evidence
- Shows cluster membership and relationships
- Displays cluster ID, type, member count, cluster risk score
- Lists related accounts and shared devices
- Source: cluster_members, account_clusters tables

4. Risk Factor Evidence
- Shows detailed risk factors from latest risk event
- Displays factor name, value, description, severity
- Source: risk_factors table

5. Feature Evidence
- Shows ML feature values that contributed to risk score
- Displays all 12 engineered features (shared_device_count, trade_frequency_24h, etc.)
- Source: feature_table

6. Rule Evidence
- Shows triggered rules derived from feature values
- Displays rule name, severity, description
- Source: Derived from feature values using same logic as RiskScoringService

Frontend Usage:

Investigation page - Case Detail panel:
- Transaction Signals section
- Withdrawal Signals section
- Network Signals section
- Rule Signals section
- Risk Drivers section

Design Requirements:
- Match existing UI style
- Use cards/components consistent with current application
- Avoid overwhelming the user
- This is an investigator workflow, not a data dump

Architecture Compliance:

✅ READ-ONLY - Does NOT modify risk scores
✅ READ-ONLY - Does NOT modify ML predictions
✅ READ-ONLY - Does NOT modify risk level thresholds
✅ NO artificial demo logic - All data from actual database
✅ Aggregates existing evidence - No new detection or scoring

19. Network Signals Explainability

API:

GET /api/risk/cases/{user_id}/network-signals?limit=5

Purpose:

Returns entity-level network relationship evidence for investigation workflow.

This is a READ-ONLY explanation generated from existing backend data.
Does NOT modify risk scores, ML predictions, or perform new detection.

Purpose:

Move from "network detected risk" to "here are the specific network relationships that explain the risk."

Response:

{
  "connected_account_count": 6,
  "connected_accounts": [
    {
      "user_id": "U10234",
      "relationship_type": ["shared_device"],
      "device_fingerprints": ["DEVICE_88921"],
      "shared_ips": [],
      "risk_level": "HIGH",
      "risk_score": 82
    },
    {
      "user_id": "U10987",
      "relationship_type": ["shared_ip"],
      "device_fingerprints": [],
      "shared_ips": ["192.168.1.100"],
      "risk_level": "MEDIUM",
      "risk_score": 65
    }
  ]
}

Field Definitions:

- connected_account_count: Total number of accounts connected to this user through network relationships

- connected_accounts: List of related accounts with relationship details
  - user_id: Related account identifier
  - relationship_type: Array of relationship types connecting the accounts
    - "shared_device": Both accounts used the same device
    - "shared_ip": Both accounts accessed from the same IP address
  - device_fingerprints: Device IDs that both accounts share (if relationship_type includes "shared_device")
  - shared_ips: IP addresses that both accounts share (if relationship_type includes "shared_ip")
  - risk_level: Related account's current risk level (LOW/MEDIUM/HIGH/CRITICAL/UNKNOWN)
  - risk_score: Related account's current risk score (0-100)

Request Parameters:

- limit: Maximum number of connected accounts to return (default: 5, max: 50)

Data Sources:

- Cluster membership from cluster_members table
- Device relationships from devices table (device_id, ip_address)
- Risk scores from risk_events table

Supported Relationship Types (MVP):

1. Shared Device Fingerprint
   - Multiple accounts using the same device
   - Evidence: device_id from devices table

2. Shared IP Address
   - Multiple accounts accessing from the same IP
   - Evidence: ip_address from devices table

NOT Implemented (out of MVP scope):
- Email similarity
- Address similarity
- Behavioral similarity
- Graph embedding similarity

Frontend Usage:

Investigation page - Case Detail panel - Network Signals section:

Display structure:
1. Cluster summary (from network_evidence)
   - Cluster name, type, member count, cluster risk score

2. Connected accounts (from network_signals)
   - Expandable list of related accounts
   - Default display: top 3 riskiest connections (sorted by risk_score descending)
   - Load More button: Shows 3 more accounts each click
   - Each account shows:
     - Account ID
     - Relationship type(s)
     - Evidence entity (device ID, IP address)
     - Risk level
     - Risk score

3. Empty state
   - "No suspicious network relationships detected."
   - Only shown when connected_account_count = 0

Load More Behavior:
- Initial display: top 3 accounts (highest risk_score)
- "Load More" button appears when connected_account_count > displayed count
- Each click increases display by 3 accounts
- Button shows remaining count: "Load More (X more accounts)"

Transaction Evidence Load More:
- Initial display: top 3 transactions (highest value)
- "Load More" button appears when transaction_evidence.length > 3
- Each click increases display by 3 transactions
- Button shows remaining count: "Load More (X more transactions)"

UI Example:

▼ U10234
  Shared Device Fingerprint
  DEVICE_88921
  HIGH Risk (82/100)

▼ U10987
  Shared IP Address
  192.168.1.100
  MEDIUM Risk (65/100)

Sorted by:
- Risk score (highest first) for investigation priority

Load More:
If connected_account_count exceeds limit, show remaining count

Data Flow:

1. User selects case in Investigation Queue
2. Frontend calls GET /api/risk/cases/{user_id}/network-signals
3. EvidenceService.get_network_signals() queries:
   - cluster_members table for related accounts
   - devices table for shared devices and IPs
   - risk_events table for related account risk scores
4. Returns evidence package with relationship-level detail
5. Frontend displays expandable account relationships

Compliance:

✅ READ-ONLY - Does NOT modify risk scoring logic
✅ READ-ONLY - Does NOT modify ML model inference
✅ READ-ONLY - Does NOT modify graph detection algorithm
✅ READ-ONLY - Does NOT modify clustering logic
✅ NO artificial data - All relationships from actual database
✅ READ-ONLY explanation from existing cluster and device data

---

20. Dataset Information Display

API:

GET /api/pipeline/status

Purpose:

Provide dataset provenance information for the bottom-left Dataset Information panel.

Used Fields:

- upload_timestamp: ISO timestamp of most recent data upload
- results.total_records: Total number of records processed across all datasets

Frontend Usage:

Layout.tsx - Dataset Information panel:
- Fetches pipeline status on component mount
- Displays formatted timestamp (e.g., "Jul 19, 2026 08:49")
- Displays total records count (e.g., "48,957")

Display Format:

```
Dataset Information
- Source: Uploaded Dataset
- Processing: Risk Analytics Pipeline  
- Update: Manual Upload
- Generated: [Dynamic timestamp from backend]
- Records: [Dynamic total records count]
```

Fallback Behavior:

- If no data uploaded: "No data uploaded"
- If records unavailable: "N/A"

Technical Implementation:

```typescript
useEffect(() => {
  const fetchDatasetInfo = async () => {
    const status = await pipelineApi.getStatus()
    if (status.upload_timestamp) {
      const date = new Date(status.upload_timestamp)
      setDatasetInfo({
        generated: date.toLocaleString('en-US', {
          month: 'short',
          day: 'numeric', 
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        }),
        totalRecords: status.results?.total_records || 0
      })
    }
  }
  fetchDatasetInfo()
}, [])
```

Data Source Consistency:

- Same timestamp as shown in Data Pipeline page
- Same record count as Pipeline Results total_records
- Automatically updates when new data is uploaded

No hardcoded values - all data from backend API responses.

---

21. Explanation Narrative Contract (LLM / Fallback)

This section defines the data contract for the Policy-backed Narrative APIs:
ordinary explanation reads, explicit regeneration, the persisted canonical
explanation artifact, and the canonical evidence structure that feeds them.
Architecture rationale lives in
[docs/architecture/llm-optional-design.md](architecture/llm-optional-design.md).

Endpoint Summary:

| Endpoint | Purpose | Generation behavior | Response |
|----------|---------|---------------------|----------|
| POST /api/risk/explain | Ordinary explanation read | May be served from the in-memory cache, the persisted canonical artifact, or (only when no valid artifact exists) a fresh generation | ExplanationResponse |
| POST /api/risk/explain/regenerate | Explicit generation request | Always bypasses read tiers and generates a new explanation; persists it as the new canonical artifact | ExplanationResponse |

An ordinary `/explain` request is a READ, not a generation request.

---

21.1 POST /api/risk/explain

Request body (ExplanationRequest):

{
  "user_id": "U00233"        // string, required
}

Query parameters:

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| audience  | string | investigator | investigator (full detail) or business (reduced sensitive detail) |
| bypass_cache | bool | false | Skips the in-memory cache tier ONLY. Does NOT force regeneration — the persisted canonical artifact can still serve the request |

Response: ExplanationResponse (see 21.3).

Serving behavior (contract-level):

"Response may be served from in-memory cache, persisted canonical artifact,
or a fresh generation path depending on the current case version."

- Cache hit: stored artifact returned; no generation.
- Cache miss/expiry: falls through to the persisted artifact; no generation
  merely because the cache expired.
- Persisted artifact absent or stale (version_fingerprint mismatch): fresh
  generation (LLM default when configured, otherwise deterministic fallback),
  then persisted as the new canonical artifact.

This endpoint does not modify RiskEvent fields.

---

21.2 POST /api/risk/explain/regenerate

Explicit regeneration request — creates a new explanation artifact.

Request body (ExplanationRequest): same as /explain.

Query parameters:

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| audience  | string | investigator | Same audience semantics as /explain |

Response: ExplanationResponse (see 21.3).

Behavior:

- Bypasses both read tiers (cache and persisted artifact)
- Generates a new narrative (LLM default when configured, otherwise
  deterministic fallback)
- Runs citation/evidence/narrative assembly
- Persists the result as the new canonical artifact for (user_id, audience)
- Returns the new ExplanationResponse

This endpoint does NOT:

- Modify any RiskEvent score fields
- Recalculate ML score
- Recalculate Rule score
- Recalculate Graph score
- Recalculate the final risk score
- Change risk level

Regeneration is an explanation-level operation; RiskEvent data remains
unchanged.

---

21.3 ExplanationResponse Schema

Source of truth: backend/app/models/schemas.py (ExplanationResponse).

{
  "summary": string,                      // required
  "key_findings": List[string],           // default []
  "recommended_action": string,           // required
  "citations": List[PolicyCitation],      // default []
  "explanation_source": string,           // "LLM" | "MODEL_FALLBACK" (default "MODEL_FALLBACK")
  "llm_error": string | null,             // optional; short provider error message
  "missing_info": List[string]            // default []; evidence gaps from actual case data
}

Field semantics:

- explanation_source: the generator of the artifact. Values defined by the
  code: "LLM" (successful LLM generation) or "MODEL_FALLBACK" (deterministic
  model-based explanation — LLM disabled/unavailable, timed out, or failed).
- llm_error: null on success; on fallback carries a short reason
  (e.g. "LLM provider timeout"). It is metadata, not narrative content.
- key_findings: array of strings. The backend owns numbering and grouping;
  each element is one conceptual finding (typically "N. Title\nsupporting
  evidence" as assembled by the narrative contract). Citation markers [n]
  may appear inline within finding/action strings — they are text, not
  response fields.
- missing_info: List[string]; evidence-completeness gaps derived from actual
  case data (e.g. unavailable device history). An empty list is valid and
  means no gaps detected.

Citation markers are NOT separate response fields: [n] inside
key_findings/recommended_action text refers to the nth entry of the
citations array.

---

21.4 PolicyCitation Schema (citations array items)

Source of truth: backend/app/models/schemas.py (PolicyCitation).

{
  "id": int,          // citation number referenced by [n] markers in text
  "doc": string,      // policy document filename
  "section": string,  // policy section path
  "quote": string,    // policy quote (audience-redacted for business mode)
  "chunk_id": string  // retrieval chunk identifier
}

Data-contract semantics:

- A finding MAY exist without a citation. Not every finding has a citation,
  and not every finding is required to have one.
- "No citation is better than a wrong citation": citations are attached only
  when the policy quote supports the finding's exact claim.
- Uncited findings simply carry no [n] marker; they are not dropped.

---

21.5 CaseExplanation Persistence Contract

Source of truth: backend/app/models/database.py (CaseExplanation, table
case_explanations). This is NOT a cache table — it stores the current
canonical explanation artifact for a (user_id, audience) pair together with
its version context.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | Integer PK | no | autoincrement |
| user_id | String(50), FK users.user_id | no | |
| audience | String(20) | no | "investigator" or "business" |
| risk_event_id | Integer, FK risk_events.id | yes | case version context |
| pipeline_run_id | String(50) | yes | case version context |
| model_version | String(20) | yes | case version context |
| policy_version | String(50) | yes | case version context |
| version_fingerprint | String(64) | no | sha256 — see 21.6 |
| explanation_payload | Text | no | full ExplanationResponse JSON |
| explanation_source | String(20) | no | "LLM" or "MODEL_FALLBACK" |
| model_provider | String(50) | yes | e.g. ANTHROPIC_MODEL, or "replay" |
| generated_at | DateTime(tz), server_default now() | no (default) | artifact generation time |

Constraints:

- UNIQUE (user_id, audience) — one current canonical artifact per
  user/audience pair; regeneration replaces the row
- INDEX idx_case_explanations_user (user_id)

explanation_payload is the JSON serialization of the ExplanationResponse
served to clients; ordinary reads deserialize and return it.

---

21.6 version_fingerprint Contract

Computed by backend/app/services/explanation_store_service.py:

version_fingerprint = sha256(
    audience | risk_event_id | pipeline_run_id | model_version | policy_version
)

Data-contract meaning:

- Identifies the case/version context for which the persisted explanation
  is valid
- Determines whether a persisted artifact corresponds to the CURRENT case
  context: a fingerprint mismatch marks the artifact stale, and the next
  ordinary read regenerates

This is a hash of the listed context VALUES (the policy_version value that
participates in the fingerprint), not a hash of policy file contents and not
an automatic invalidation on any policy file change.

---

21.7 Canonical Evidence Structure

Source of truth: backend/app/services/evidence_service.py
(EvidenceService.get_canonical_evidence()). This structure is the data
contract consumed by the explanation pipeline (LLM prompt, citation
retrieval, investigation flows); it is an internal service structure, not a
public API response.

{
  "ml": {
    "score": float,              // 0-100 system signal (not a calibrated probability)
    "probability": float|null,   // raw model output
    "primary_driver": string|null
  },
  "rules": {
    "score": float,              // sum of triggered contributions, capped at 100
    "triggered": [
      {
        "rule_name": string,
        "severity": string,
        "description": string,
        "trigger": { "<feature>": value },   // observed values
        "threshold": string,                 // e.g. "account_age_days < 7 AND trade_frequency_24h > 50"
        "contribution": int                  // score points
      }
    ],
    "note": string,
    "consistent": bool|null       // derived rule evidence reconciles with rule score
  },
  "graph": {
    "score": float,
    "has_evidence": bool,
    "connected_accounts": int     // present when has_evidence
    // OR "note": string           // explicit no-signal note when score = 0
  },
  "contextual": {
    "account_age_days": int,      // present when available
    "account_age_note": string
  },
  "findings": [
    {
      "name": string,
      "evidence": string,
      "detection_sources": List[string],   // e.g. ["Rule"], ["Graph","Feature"], ["ML"]
      "evidence_type": string,             // "detector_signal" | "rule" | "graph" | "feature"
      "observed_value": object|null,
      "threshold": string|null,
      "contribution": int|null,
      "description": string|null,
      "supporting_feature": string|null
    }
  ]
}

Contract semantics:

- detection_sources is INTERNAL provenance metadata (which detection methods
  produced the finding). It is not a user-facing narrative field.
- Structured data contract ≠ presentation contract: fields such as
  contribution, threshold, and detection_sources are retained in Canonical
  Evidence even though the default user-facing narrative does not display
  them.

---

21.8 RiskFactor Contract (data semantics)

Source of truth: backend/app/models/database.py (RiskFactor, table
risk_factors).

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | Integer PK | no | autoincrement |
| risk_event_id | Integer, FK risk_events.id | no | owning risk event |
| factor_name | String(100) | no | e.g. "High Trading Frequency", "Account Age" |
| factor_value | Numeric(10, 4) | yes | observed feature value |
| factor_description | Text | yes | human-readable description |

Data semantics:

RiskFactor rows are persisted feature-level / contextual descriptive
evidence associated with a risk event. A RiskFactor is NOT:

- an ML finding
- a Rule trigger
- a Graph finding

"A feature is used by the ML model" does not imply "ML independently
detected that finding". Attribution of findings to detection sources is
carried by Canonical Evidence findings[].detection_sources, not by
RiskFactor rows.

---

21.9 Backward Compatibility

The persisted explanation architecture changes the GENERATION LIFECYCLE,
not the public ExplanationResponse contract:

- ExplanationResponse fields are unchanged (summary, key_findings,
  recommended_action, citations, explanation_source, llm_error, missing_info)
- /api/risk/explain keeps its request shape and response schema
- /api/risk/explain/regenerate is an ADDITIONAL endpoint
- bypass_cache remains a query parameter (its semantics narrowed to
  "skip in-memory cache tier only", which is behaviorally compatible for
  readers and stricter for anyone who relied on it forcing regeneration —
  such callers must use the regenerate endpoint)

No public response schema breaking change was introduced.
