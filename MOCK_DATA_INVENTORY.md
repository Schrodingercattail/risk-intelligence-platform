Mock Data Inventory
Purpose

This document tracks all currently hardcoded or mock data used in the MVP version of AI Risk Command Center.

The purpose is to:

identify temporary mock values
track future backend/API replacement points
prevent mock data from being treated as production data
guide future integration work
1. Risk Overview Page (RiskCommandCenter.tsx)
1.1 Risk Score Distribution
Current mock location
frontend/src/pages/RiskCommandCenter.tsx

MOCK_DATA.riskDistribution
Current mock data
{
  critical: 32,
  high: 208,
  medium: 390,
  low: 845,
  total: 1475
}
Used for
Risk Score Distribution card
Risk Level Distribution visualization
Risk severity summary
Current status

Mock

Future source

Backend risk summary API

Expected fields:

{
  "critical": number,
  "high": number,
  "medium": number,
  "low": number,
  "total": number
}
1.2 Detection Source Analysis
Current mock location
frontend/src/components/Charts/DetectionSourceChart.tsx
Current mock data

Example:

[
  {
    name: "Rule Engine",
    value: 45
  },
  {
    name: "LightGBM Model",
    value: 32
  },
  {
    name: "Graph Analysis",
    value: 18
  }
]
Used for

Detection source percentage bar chart

Current status

Mock

Future source

Backend detection aggregation API

Expected:

[
  {
    "source": "Rule Engine",
    "percentage": number
  },
  {
    "source": "ML Model",
    "percentage": number
  },
  {
    "source": "Graph Analysis",
    "percentage": number
  }
]
1.3 Investigation Queue
Current mock location
frontend/src/pages/RiskCommandCenter.tsx
Current mock cases

Example:

[
 {
   caseId:"CASE-10291",
   userId:"user_1248",
   riskScore:94,
   riskLevel:"CRITICAL"
 },
 {
   caseId:"CASE-10290",
   userId:"user_0847",
   riskScore:87,
   riskLevel:"CRITICAL"
 }
]
Used for
Investigation Queue table
Case selection
Current status

Mock

Future source

Backend case detection API

2. Investigation Page (Investigation.tsx)
2.1 Investigation Cases
Current mock location
frontend/src/pages/Investigation.tsx
Current mock fields
{
 caseId,
 userId,
 riskScore,
 riskLevel,
 detectedSignals,
 recommendedAction
}
Used for

Left investigation queue

Current status

Mock

Future source

Backend:

GET /api/cases
2.2 Selected Case Detail
Current mock data

Example:

{
 accountAge:"47 days",
 totalVolume:"$124,830",
 created:"2025/1/15"
}
Used for

Account Information card

Future source

Case detail API

Example:

GET /api/cases/{case_id}
2.3 Detected Risk Signals
Current mock

Example:

[
"Shared Device with 3 high-risk users",
"Abnormal Location Login",
"Rapid Withdrawal Pattern"
]
Used for

Risk signal display

Future source

ML feature explanation service

2.4 AI Explanation / Human-readable Recommendation
Planned feature

Not implemented yet.

Purpose:

Convert model output into analyst-friendly explanation.

Example:

Instead of:

Feature:
device_shared_count = 5

Show:

This account shares the same device with multiple high-risk users,
which significantly increases fraud probability.

Future source:

LLM explanation service

Backend:

/api/cases/{id}/explanation
3. Data Pipeline Page (DataPipeline.tsx)
3.1 Data Source Cards
Current mock

Example:

[
 {
   name:"User Behavior Data",
   records:12483,
   updated:"2 min ago"
 },
 {
   name:"Transaction Data",
   records:48291,
   updated:"Just now"
 }
]
Used for

Data Sources cards

Current status

Mock

Future source

Uploaded CSV metadata

Backend should provide:

{
 "fileName":"",
 "recordCount":number,
 "uploadedAt":"datetime"
}
3.2 Pipeline Processing Steps
Current mock

Pipeline steps:

Data Sources

Data Validation

Feature Engineering

ML Risk Scoring

Graph Analysis

Risk Decision Engine

Current values:

{
 sources:4,
 records:71920,
 features:128,
 clusters:225,
 actions:2990
}
Used for

Processing Pipeline visualization

Current status

Mock

Future source

Pipeline execution status API

Expected:

{
 step:"",
 status:"completed|running|pending|failed",
 metrics:{}
}
3.3 Upload Status
Current behavior

Upload requires:

user.csv
device.csv
trades.csv
withdrawals.csv

All files required before pipeline execution.

Validation rules

Upload button enabled only when:

all required files uploaded
file type = CSV

Future backend validation:

POST /api/pipeline/upload
4. Model Monitoring Page (ModelMonitoring.tsx)
4.1 Model Metadata
Current mock fields
{
 modelName:"LightGBM Risk Engine",
 version:"v1.0",
 featureCount:128,
 algorithm:"LightGBM",
 trainingDate:"2026-07-01"
}
Classification

Some fields belong to model artifact, not uploaded data.

Model-owned fields

Can come from saved model:

model name
version
algorithm
feature count
training date

Example:

risk_model.pkl metadata
Dataset-owned fields

Should come from uploaded data:

record count
upload time
data range
4.2 Model Performance Metrics
Current mock
{
 auc:0.000,
 ks:0.000,
 psi:0.000
}
Used for

Model performance cards

Future source

Model evaluation API

Expected:

{
 "auc":number,
 "ks":number,
 "psi":number
}
4.3 AI Risk Drivers
Current mock

Example:

[
 {
  feature:"Shared Device Risk",
  importance:35
 },
 {
  feature:"Coordinated Transaction",
  importance:30
 }
]
Used for

Feature importance chart

Future source

LightGBM feature importance output

Possible source:

model.feature_importances_
4.4 PSI Monitoring
Current mock
{
 psi:0,
 status:"Unknown"
}
Current limitation

First upload has no comparison baseline.

Expected behavior:

First dataset:

PSI unavailable
Reason:
No previous dataset available

Second dataset onwards:

Compare:

previous dataset
vs
current dataset
4.5 Feature Drift Analysis
Current status

UI implemented.

Backend definition needed.

Expected backend response:

[
 {
  "feature":"transaction_amount",
  "psi":0.12,
  "status":"stable"
 },
 {
  "feature":"device_count",
  "psi":0.35,
  "status":"drift"
 }
]
5. Files Containing Mock Data
Frontend
frontend/src/pages/RiskCommandCenter.tsx

frontend/src/pages/Investigation.tsx

frontend/src/pages/DataPipeline.tsx

frontend/src/pages/ModelMonitoring.tsx

frontend/src/components/Charts/*.tsx

frontend/src/types/index.ts
6. Mock Data Replacement Priority
High priority

Replace first:

Risk Overview metrics
Investigation cases
Uploaded dataset metadata
Pipeline execution status
Medium priority
Detection source analysis
AI risk drivers
Feature drift analysis
Low priority
Static model metadata
7. Principle

All mock data should eventually be replaced by:

uploaded CSV metadata
backend database records
ML model outputs
pipeline execution status
model monitoring service

No production UI value should permanently depend on frontend hardcoded values.