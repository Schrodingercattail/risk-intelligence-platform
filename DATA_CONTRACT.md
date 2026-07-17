CSV Upload → Backend → Frontend Data Contract

Version: MVP v0.6

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
3. Risk Summary Contract

API:

GET /api/risk/summary

Purpose:

Homepage KPI cards.

Response:

{
  "total_accounts": 10000,

  "risk_distribution": {

    "critical": 32,

    "high": 176,

    "medium": 390,

    "low": 845

  },


  "high_risk_accounts": 208,


  "suspicious_networks": 25,


  "recommendations_count": 2990,


  "generated_time": "2026-07-15T14:32:00"
}

Frontend mapping:

Frontend Card	Backend Field
High Risk Accounts	high_risk_accounts
Risk Score Distribution	risk_distribution
Suspicious Networks	suspicious_networks
Risk Recommendations	recommendations_count
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

GET /api/investigation/cases

Response:

[
{
 "case_id":"CASE001",

 "user_id":"U01401",

 "risk_score":99.5,

 "risk_level":"HIGH",

 "recommended_action":
 "Review account activity",

 "risk_factors":[
   "Device sharing",
   "Abnormal transaction"
 ],

 "detection_method":[
   "ML",
   "Rule",
   "Graph"
 ],

 "created_time":
 "2026-07-15T10:32:00"

}
]

No fields:

status
assigned_to
resolved_time

Reason:

MVP does not include case workflow management.

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

7. Detection Source Contract

API:

GET /api/risk/detection-source

Response:

[
{
 "method":"LightGBM",

 "percentage":55
},

{
 "method":"Rule Engine",

 "percentage":30
},

{
 "method":"Graph Analysis",

 "percentage":15
}
]

Frontend:

Bar chart.

X axis:

percentage (%)

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

13. Future Enterprise Integration

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
