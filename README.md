# Risk Intelligence Platform

**Machine Learning–Driven Detection, Monitoring & Investigation**

A machine learning-driven risk detection and monitoring platform designed to identify suspicious behaviors, combine multiple risk signals, and support investigation workflows across risk-sensitive industries.

---

## Project Overview

This is an **extensible risk intelligence platform** that demonstrates how modern risk systems can combine data pipelines, machine learning models, rule engines, graph-based signals, monitoring systems, and investigation workflows into a unified architecture.

The platform implements a complete risk detection pipeline from data ingestion through scoring, monitoring, and alerting. While demonstrated with trading-inspired datasets, the underlying architecture is **industry-agnostic** and transferable to multiple domains.

## Design Evolution

The platform evolved from an initial dashboard wireframe exploration.

Original UI concept:

https://github.com/Schrodingercattail/risk-overview-wireframe

### Core Capabilities

**Risk Detection**
- ML Risk Scoring — LightGBM-powered pattern recognition (AUC: 0.85, KS: 0.43)
- Rule Engine — Expert-defined risk signals for known fraud patterns
- Graph Detection — Network analysis for coordinated behavior rings
- Multi-Signal Fusion — Weighted combination with business override logic

**Risk Monitoring**
- PSI Drift Detection — Population Stability Index for model drift monitoring
- Model Performance Tracking — AUC, KS, feature distribution monitoring
- Baseline Validation — Automated comparison against training distributions

**Investigation Support**
- Risk Event Lifecycle — Complete audit trail with pipeline traceability
- Signal Attribution — Which detection methods contributed to each risk score
- Evidence Factors — Detailed feature-level explanations for risk decisions
- Investigation Queue — Filterable workflow for analyst review

### Design Philosophy

This platform is an **investigation support system**, not an auto-ban system. The final enforcement decision remains with human operators. The goal is to surface risks, explain them, and enable efficient investigation.

---

## Project Motivation

Risk management systems across industries share similar technical challenges:

- Identifying abnormal user behavior patterns
- Combining multiple risk signals into coherent decisions
- Explaining risk decisions to investigators and regulators
- Monitoring model performance over time
- Detecting when production data drifts from training conditions
- Supporting end-to-end investigation workflows

This project abstracts these common challenges into a **reusable Risk Intelligence Platform architecture**. The goal is not to build a single-industry solution, but to demonstrate how modern risk systems can integrate:

- Data pipelines and feature engineering
- Machine learning models with monitoring
- Rule-based expert systems
- Graph-based relationship analysis
- Investigation workflow support

---

## Business Background

This project is inspired by risk management scenarios from both **consumer finance** and **digital asset platforms**, but the architecture is designed to be **industry-agnostic**.

**From Consumer Finance:**
- Fraud detection and behavioral risk scoring
- Machine learning-based risk models
- Model monitoring and governance requirements
- Account lifecycle risk assessment

**From Digital Asset Trading:**
- Abnormal transaction behavior detection
- Coordinated account activity analysis
- Suspicious trading pattern identification
- Account relationship network analysis

**Applicable Domains:**
- Fintech & Consumer Finance
- Fraud Prevention & Account Security
- Digital Asset Platforms & Exchanges
- E-Commerce Risk Control
- Marketplace Integrity
- Any risk-sensitive domain requiring behavior analysis

Although the demonstration datasets use synthetic trading scenarios, the underlying architecture transfers to multiple risk-sensitive industries. The platform demonstrates **general risk intelligence patterns** rather than industry-specific implementations.

---

## Architecture Overview

### Current Prototype Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  DATASET INGESTION LAYER                     │
├─────────────────────────────────────────────────────────────┤
│  CSV Upload → Data Validation → Quality Checks             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               FEATURE ENGINEERING PIPELINE                    │
├─────────────────────────────────────────────────────────────┤
│  13 Risk Features: Device Patterns, Behavioral Activity,    │
│  Account Attributes, Transaction Patterns                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              RISK DETECTION ENGINE                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ ML Model     │  │ Rule Engine  │  │ Graph Detect │    │
│  │ (LightGBM)   │  │              │  │ (NetworkX)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                     Signal Fusion                              │
│                  (0.5 + 0.3 + 0.2)                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              RISK EVENT GENERATION                           │
├─────────────────────────────────────────────────────────────┤
│  Risk Score + Risk Level + Pipeline Traceability            │
│  + Signal Attribution + Evidence Factors                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              MONITORING & DRIFT DETECTION                     │
├─────────────────────────────────────────────────────────────┤
│  PSI Analysis → Model Drift Detection → Retraining          │
└─────────────────────────────────────────────────────────────┘
```

### Data Architecture Explanation

**Why CSV Datasets?**

Enterprise production databases cannot be accessed in a personal portfolio environment. This project uses **synthetic production-like datasets** that demonstrate real-world risk patterns while maintaining data privacy.

**Current Workflow:**
```
Dataset Upload → Feature Engineering → ML Scoring → Risk Detection → Monitoring → Investigation
```

**Future Enterprise Extension:**
- Connect to enterprise databases (PostgreSQL, MySQL, MongoDB, Snowflake, BigQuery)
- Integrate with existing data pipelines (Kafka, Kinesis, data lakes)
- Connect with existing case management systems
- Continue development of full risk case lifecycle

The platform architecture is designed for this extension path—the CSV-based workflow is a demonstration proxy for production data integration.

---

## Technology Stack

**Backend:** Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy, Alembic
**Frontend:** React, TypeScript, Tailwind CSS, Recharts
**Machine Learning:** LightGBM, scikit-learn, pandas, numpy, joblib
**Graph Analysis:** NetworkX for relationship detection
**Monitoring:** PSI for population stability monitoring
**Deployment:** Docker Compose

---

## Current Scope

### ✅ Implemented

**Data Layer**
- Dataset ingestion with CSV upload
- Data validation and quality checks
- Feature engineering pipeline (13 features)

**Detection Layer**
- ML risk scoring with LightGBM (AUC: 0.85, KS: 0.43)
- Rule-based expert system
- Graph-based network analysis
- Multi-signal fusion with weighted combination

**Risk Management**
- Risk event generation with complete traceability
- Pipeline run tracking (pipeline_run_id, model_version)
- Signal attribution and evidence factors
- Risk level override for coordinated fraud

**Monitoring**
- PSI-based model drift detection
- Feature distribution monitoring
- Baseline validation
- Performance metrics tracking

**Visualization**
- Risk command center dashboard
- Investigation queue with filtering
- Model monitoring interface
- PSI drift visualization

### 🚧 Future Enhancements

**Enterprise Data Integration**
- Database connectors for operational systems
- Data warehouse integration
- Streaming data pipeline support
- Real-time event processing

**Case Management**
- Case lifecycle workflow (creation → assignment → investigation → resolution)
- Integration with external case management systems
- Collaborative investigation tools
- Audit trail for case actions

**Advanced Features**
- Automated retraining based on PSI thresholds
- Real-time alerting and notifications
- Advanced graph analytics with temporal patterns

---

## Model Explainability & AI Enhancement

### Current ML Implementation

**Risk Scoring:**
- LightGBM gradient boosting model (AUC: 0.85, KS: 0.43)
- 13 engineered features (device patterns, behavioral activity, account attributes)
- Multi-signal fusion (ML + Rules + Graph)

**Explainability:**
- Model-based explanations from risk analysis outputs
- Signal attribution (ML, Rule, Graph contributions)
- Evidence factors for each risk event
- Investigation guidance based on risk levels

**Current Implementation Status:**
The Investigation page displays model-generated explanations:
- Risk summary with score breakdown
- Contributing factors (ML score, Rule score, Graph score)
- Recommended analyst action
- Evidence factors

These explanations are generated from **model outputs and business logic**, not LLM text generation.

### Optional AI Enhancement

The platform includes an **optional LLM integration** for natural language explanation generation:

**Configuration:**
```bash
# .env file
ENABLE_LLM_EXPLANATION=true
ANTHROPIC_API_KEY=your_key_here
```

**When Enabled:**
- LLM generates natural language case summaries
- Analyst-friendly narrative explanations
- Investigation workflow assistance

**Default Behavior (LLM Disabled):**
- Model-based explanations from risk outputs
- No API key required
- Core functionality unaffected

**Architecture:**
The `/explain` endpoint works in both modes:
- Without LLM: Returns structured model-based explanations
- With LLM: Returns natural language summaries
- Failure safety: Falls back to model-based on error

The platform operates **fully without LLM integration**. LLM is an optional enhancement for narrative explanations, not a dependency for risk scoring or investigation workflow.

---

## Production Deployment Considerations

### Demo vs Production Environment

| Aspect | Demo Environment | Production Environment |
|--------|-----------------|----------------------|
| **Data Source** | CSV upload via UI | Database/Data Warehouse integration |
| **Processing** | Batch pipeline | Streaming + Batch |
| **Case Management** | Not implemented | Full workflow or external system |
| **Authentication** | Not implemented | Enterprise SSO/OAuth |
| **Monitoring** | Manual API checks | Integrated observability |

### Enterprise Extension Path

```
Current: Dataset → Platform → Risk Event

Future:  Enterprise Data → Platform → Risk Event → Case System → Resolution
```

**Data Integration Options:**
- Database Connectors (PostgreSQL, MySQL, MongoDB)
- Data Warehouse (Snowflake, BigQuery, Redshift)
- Data Lake (S3, ADLS, HDFS)
- Streaming (Kafka, Kinesis, Pub/Sub)

**Case Management Directions:**
1. **Internal Workflow:** Build complete case lifecycle within platform
2. **External Integration:** API-based connection to existing case systems

---

## Project Structure

```
risk-platform-demo/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── models/       # Database models & schemas
│   │   ├── services/     # Business logic layer
│   │   ├── ml/           # ML models & PSI monitoring
│   │   └── migrations/   # Database migration scripts
│   └── requirements.txt
├── frontend/             # React application
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   └── services/     # API client
│   └── package.json
├── ml-models/            # ML training & artifacts
│   └── training/         # Training scripts
├── test_data/            # Validation datasets
│   ├── v2_diverse/       # Training data
│   ├── v3_subtle_drift/  # Stable monitoring demo
│   ├── v3_realistic_drift/ # Warning drift demo
│   ├── v3_drift/         # Severe drift demo
│   └── v4_demo_production/ # Production validation
├── docs/                 # Project documentation
│   ├── ml-pipeline.md
│   ├── psi-monitoring.md
│   ├── model-monitoring.md
│   ├── risk-event-lifecycle.md
│   ├── data-contract.md
│   └── validation-report.md
└── docker-compose.yml
```

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Python 3.12+ for local development
- (Optional) Node.js 20+ for frontend development

### Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

### Local Development

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Model Training

```bash
# Train ML model from CSV data
python ml-models/training/train_risk_model.py --source csv

# Train from database (after pipeline run)
python ml-models/training/train_risk_model.py --source database
```

---

## Risk Level Determination

**Two-Path CRITICAL Logic:**

**Path 1: Coordinated Fraud Override**
- When ML ≥ 80, Rule ≥ 40, Graph ≥ 50: Elevates to CRITICAL
- Handles coordinated behavior edge cases
- Does not modify weighted score, only risk level

**Path 2: High Scoring**
- When final_score ≥ 90: Automatically CRITICAL
- Natural extension of HIGH (≥ 70) risk band
- Top ~2-5% of scores achieve CRITICAL

**Risk Level Hierarchy:**
- CRITICAL: ≥ 90 (or override condition met)
- HIGH: 70 - 89
- MEDIUM: 50 - 69
- LOW: < 50

---

## Model Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| AUC | 0.85 | > 0.75 | ✅ Excellent |
| KS | 0.43 | > 0.30 | ✅ Strong |
| PSI | < 0.1 | < 0.10 | ✅ Stable |

---

## Documentation

- [ML Pipeline Documentation](docs/ml-pipeline.md)
- [PSI Monitoring Guide](docs/psi-monitoring.md)
- [Model Monitoring](docs/model-monitoring.md)
- [Risk Event Lifecycle](docs/risk-event-lifecycle.md)
- [Data Contract](docs/data-contract.md)
- [Validation Report](docs/validation-report.md)
- [Test Data Catalog](test_data/README.md)

---

## Configuration

Environment variables (see `.env.example`):

```bash
# Database
DATABASE_URL=postgresql://user:pass@database:5432/risk_platform

# Optional LLM Integration (default: disabled)
ENABLE_LLM_EXPLANATION=false
ANTHROPIC_API_KEY=

# Risk Scoring Weights
ML_WEIGHT=0.5
RULE_WEIGHT=0.3
GRAPH_WEIGHT=0.2

# Detection Thresholds
HIGH_RISK_THRESHOLD=0.7
MEDIUM_RISK_THRESHOLD=0.5
```

**Note:** The platform operates fully without LLM integration. Set `ENABLE_LLM_EXPLANATION=true` only if you want natural language explanation summaries.

---

## Development

See `CLAUDE.md` for detailed development guidance and architecture documentation.

---

## Data Disclaimer

**All datasets in this repository are synthetic.**

This project uses demonstration datasets for validation and testing purposes:

- ✅ All user accounts, devices, transactions, and activity data are synthetically generated
- ✅ No real customer data is included
- ✅ No proprietary company information is included
- ✅ No actual exchange or trading platform data is used

**Data Scenarios:**

The synthetic datasets are designed to demonstrate common risk management patterns:
- Abnormal behavioral patterns (high-frequency activity, unusual timing)
- Coordinated account activity (shared devices, network clusters)
- Risk signal distribution (low, medium, high, critical cases)
- Model drift scenarios (for PSI monitoring validation)

**Industry Inspiration:**

These patterns are inspired by common risk scenarios across:
- Consumer finance (fraud detection, account risk)
- Digital asset platforms (trading patterns, withdrawal behavior)
- E-commerce (account abuse, fraudulent transactions)

The purpose is to demonstrate technical capability in a realistic but privacy-safe manner.

---

## License

This is a demonstration portfolio project.
