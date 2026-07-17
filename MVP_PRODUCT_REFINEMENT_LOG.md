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


## Detection Source

Future API:

GET /api/risk/detection-sources


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