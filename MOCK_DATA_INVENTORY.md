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

✅ **COMPLETED** - Now using backend API (`/api/risk/overview`)

Backend fields used:
- risk_level_composition.critical
- risk_level_composition.high
- risk_level_composition.medium
- risk_level_composition.low
- risk_level_composition.total

1.2 Detection Source Analysis

✅ **COMPLETED** - Now using backend API (`/api/risk/overview`)

Backend fields used:
- detection_sources array with method, detected_accounts, detection_rate, color

1.3 Investigation Queue

✅ **COMPLETED** - Now using backend API (`/api/risk/cases`)

Backend fields used:
- items array with case data
- total count for pagination

2. Investigation Page (Investigation.tsx)

2.1 Investigation Cases

✅ **COMPLETED** - Now using backend API (`/api/risk/cases`)

Backend API: GET /api/risk/cases

Fields from backend:
- user_id
- risk_score
- risk_level
- primary_reason
- recommended_action
- detected_at
- ml_score, rule_score, graph_score
- detection_methods (computed from scores)

2.2 Selected Case Detail

✅ **COMPLETED** - Using backend API with full case context

Backend API: GET /api/risk/events/{user_id}

Fields from backend:
- risk_score, risk_level, risk_probability
- primary_reason, recommended_action
- detected_at, event_type
- ml_score, rule_score, graph_score
- detection_methods
- risk_factors (from RiskFactor table)
- cluster (if applicable)
- account_age: Computed from User.account_created_time (days since account creation)
- total_volume: Aggregated from Trade table (SUM of price * quantity)

2.3 Detected Risk Signals

✅ **COMPLETED** - Using backend API

Backend API: GET /api/risk/events/{user_id}

Returns risk_factors array from RiskFactor table

2.4 AI Explanation / Human-readable Recommendation

⏳ **PARTIAL** - Template-based generation in frontend

Backend API exists: POST /api/risk/explain (LLM service)

Current implementation:
- Frontend generates template-based explanation from scores
- Shows ML score, Rule score, Graph score breakdown
- Shows analyst guidance based on recommended_action

Future enhancement:
- Integrate with LLM explanation service for human-readable narratives

3. Data Pipeline Page (DataPipeline.tsx)

3.1 Data Source Cards

⏳ **PENDING** - Still using mock data

Current mock:
- Data source names
- Record counts
- Update timestamps

Future source:
- Pipeline status API
- Dataset metadata API

3.2 Pipeline Processing Steps

⏳ **PENDING** - Still using mock data

Current mock:
- Step names
- Status indicators
- Processing metrics

Future source:
- GET /api/pipeline/status

Expected response:
{
  "data_sources": "PENDING" | "COMPLETED",
  "dataset_validation": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED",
  "feature_engineering": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED",
  "ml_scoring": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED",
  "graph_analysis": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"
}

3.3 Upload Status

⏳ **PARTIAL** - Frontend validation working

Current implementation:
- Frontend validates file selection
- Backend API exists: POST /api/pipeline/upload
- Backend validates all 4 required files

Status:
- Upload validation is implemented
- Pipeline status tracking is pending

4. Model Monitoring Page (ModelMonitoring.tsx)

4.1 Model Metadata

✅ **COMPLETED** - Now using backend API (`/api/model/monitoring`)

Fields from backend:
- model_name: From ModelMetadata table
- version: From ModelMetadata table
- deployed_at: From ModelMetadata table

Fields using defaults:
- algorithm: "LightGBM"
- model_type: "Gradient Boosting"
- feature_count: 128

4.2 Model Performance Metrics

✅ **COMPLETED** - Now using backend API (`/api/model/monitoring`)

Fields from backend:
- auc: From ModelMetadata.auc_score
- ks: From ModelMetadata.ks_score
- psi: From PSI calculation

Behavior:
- No model: Returns null, displays as "No model available"
- Has model: Shows actual evaluation metrics

4.3 AI Risk Drivers (Feature Importance)

✅ **COMPLETED** - Now using backend API (`/api/model/feature-importance`)

Backend API: GET /api/model/feature-importance

Behavior:
- No model: Returns empty array (no fallback)
- Has model: Returns actual feature importance from ModelMetadata

4.4 PSI Monitoring

✅ **COMPLETED** - Now using backend API (`/api/model/monitoring`)

Fields from backend:
- psi: From PSI calculation
- psi_status: "stable" | "warning" | "drift" | "unknown"

Behavior:
- No baseline: Returns "unknown" status
- Has baseline: Shows actual PSI values

4.5 Feature Drift Analysis

✅ **COMPLETED** - Now using backend API (`/api/model/monitoring`)

Fields from backend:
- psi_features: Array of feature PSI values

Behavior:
- No baseline: Returns empty array
- Has baseline: Shows feature-level drift

4.6 Model Training Lifecycle

✅ **COMPLETED** - End-to-end ML lifecycle now functional

Backend API: POST /api/pipeline/train

Training Process:
- Loads features from FeatureTable (database)
- Generates labels from cluster membership
- Trains LightGBM model with 80/20 train-test split
- Calculates AUC, KS, feature importance
- Saves model artifacts to ml-models/artifacts/
- Persists metadata to ModelMetadata table
- Saves feature importance to FeatureImportance table
- Generates PSI baseline distribution

Response includes:
- model_version: Timestamp of training
- metrics: {auc, ks}
- train_size, test_size: Dataset split counts
- positive_ratio: Proportion of risky users
- model_id: Database ID for metadata

Integration:
- After data upload: POST /api/pipeline/upload
- Run pipeline: POST /api/pipeline/run
- Train model: POST /api/pipeline/train
- Monitor: GET /api/model/monitoring

Behavior:
- No features: Returns FAILED status with error
- Success: Returns COMPLETED with full metrics

5. Summary - Mock Data Replacement Status

✅ **FULLY COMPLETED:**
- Risk Overview page (all sections)
- Investigation page (main case data and case detail)
- Model Monitoring page (all sections)

⏳ **PARTIALLY COMPLETED:**
- Investigation page (AI explanation - template based)
- Data Pipeline page (upload validation working)

⏳ **PENDING:**
- Data Pipeline page (data source cards)
- Data Pipeline page (pipeline processing steps)

6. Files Status Summary

Frontend files mock data status:

✅ **COMPLETED:**
- RiskCommandCenter.tsx
- Investigation.tsx
- ModelMonitoring.tsx

⏳ **PARTIAL:**
- DataPipeline.tsx (upload validation)

⏳ **PENDING:**
- DataPipeline.tsx (visualization)
