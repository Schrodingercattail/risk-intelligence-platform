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
    "median": 48.7,
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

3. Fraud Networks - summary.fraud_networks
   - Definition: Suspicious clusters detected through network analysis
   - Subtitle: "Suspicious clusters detected through network analysis"
   - Note: Number of clusters, NOT users in networks

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
   - Visual stat card with: average, median, threshold, maximum

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
  "cases": [
    {
      "user_id": "U001",
      "risk_score": 87,
      "risk_level": "HIGH",
      "detection_method": ["LightGBM Model", "Rule Engine"],
      "recommended_action": "Review suspicious transaction activity",
      "detected_at": "2026-07-15T10:32:00"
    }
  ],
  "total": 598,
  "page": 1,
  "page_size": 50
}

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

6. Risk Trend Contract

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

7. Detection Attribution Contract

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
    "detected_accounts": 598,
    "detection_rate": 100.0,
    "color": "#8b5cf6"
  },
  {
    "method": "Rule Engine",
    "detected_accounts": 598,
    "detection_rate": 100.0,
    "color": "#3b82f6"
  },
  {
    "method": "Graph Network",
    "detected_accounts": 598,
    "detection_rate": 100.0,
    "color": "#06b6d4"
  }
]

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

8. Model Performance Contract

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

9. Feature Importance Contract

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

10. Feature Drift Contract

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

11. Pipeline Status Contract

API:

GET /api/pipeline/status

Response:

{

"stages":[

{
"name":"Data Validation",

"status":"completed"
},

{
"name":"Feature Engineering",

"status":"completed"
},

{
"name":"Risk Model",

"status":"running"
}

]

}

Frontend:

Pipeline cards.

Rules:

completed:
green

running:
blue

pending:
gray

failed:
red

Do not show completed before backend confirms.

12. Upload Requirement Contract

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

13. Pipeline Status Validation Strategy

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

14. Future Enterprise Integration

Current:

CSV Upload

Future:

Database Connector

Kafka Stream

Data Warehouse

API Gateway

Frontend contract should remain unchanged.

Only backend ingestion layer changes.

14. Current MVP Mock Replacement Plan

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
