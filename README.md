# Risk Management Platform Prototype

An enterprise-grade risk management platform prototype demonstrating ML-powered fraud detection, rule-based risk assessment, and graph-based network analysis for cryptocurrency exchanges.

## Project Overview

This is an **extensible risk management platform prototype** designed to showcase enterprise-level fraud detection capabilities. The platform implements a complete risk detection pipeline from data ingestion through scoring, monitoring, and alerting.

### Core Capabilities

- **ML Risk Scoring** - LightGBM-powered pattern recognition with AUC > 0.85
- **Rule Engine** - Expert-defined risk signals for known fraud patterns
- **Graph Detection** - Network analysis for coordinated fraud rings
- **Risk Event Lifecycle** - Complete audit trail with pipeline traceability
- **PSI Monitoring** - Model drift detection with Population Stability Index
- **Multi-Signal Fusion** - Weighted combination with business override logic

### Design Philosophy

This platform is an **investigation support system**, not an auto-ban system. The final enforcement decision remains with human operators.

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
│  13 Risk Features: Device Patterns, Trading Behavior,       │
│  Account Attributes, Withdrawal Activity                     │
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

## Technology Stack

- **Backend**: Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy
- **Frontend**: React, TypeScript, Tailwind CSS, Recharts
- **ML**: LightGBM, scikit-learn, pandas
- **Graph**: NetworkX for relationship analysis
- **Monitoring**: PSI for model drift detection
- **Deployment**: Docker Compose

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
- Explainable AI enhancements

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

**Data Integration Options**
- Database Connectors (PostgreSQL, MySQL, MongoDB)
- Data Warehouse (Snowflake, BigQuery, Redshift)
- Data Lake (S3, ADLS, HDFS)
- Streaming (Kafka, Kinesis, Pub/Sub)

**Case Management Directions**
1. **Internal Workflow**: Build complete case lifecycle within platform
2. **External Integration**: API-based connection to existing case systems

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

## Model Training

```bash
# Train ML model from CSV data
python ml-models/training/train_risk_model.py --source csv

# Train from database (after pipeline run)
python ml-models/training/train_risk_model.py --source database
```

## Risk Level Override

The platform implements a **business severity layer** for coordinated fraud detection.

**Override Condition** (when ALL three are true):
- ML score ≥ 80
- Rule score ≥ 40  
- Graph score ≥ 50

**Result**: Risk level elevated to CRITICAL, regardless of weighted score.

This handles edge cases where weighted combination may underrepresent coordinated manipulation threat levels.

## Model Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| AUC | 0.85 | > 0.75 | ✅ Excellent |
| KS | 0.43 | > 0.30 | ✅ Strong |
| PSI | < 0.1 | < 0.10 | ✅ Stable |

## Documentation

- [ML Pipeline Documentation](docs/ml-pipeline.md)
- [PSI Monitoring Guide](docs/psi-monitoring.md)
- [Model Monitoring](docs/model-monitoring.md)
- [Risk Event Lifecycle](docs/risk-event-lifecycle.md)
- [Data Contract](docs/data-contract.md)
- [Validation Report](docs/validation-report.md)
- [Test Data Catalog](test_data/README.md)

## Configuration

Environment variables (see `.env.example`):

```bash
# Database
DATABASE_URL=postgresql://user:pass@database:5432/risk_platform

# LLM API (for explanation generation)
ANTHROPIC_API_KEY=your_key_here

# Risk Scoring Weights
ML_WEIGHT=0.5
RULE_WEIGHT=0.3
GRAPH_WEIGHT=0.2

# Detection Thresholds
HIGH_RISK_THRESHOLD=0.7
MEDIUM_RISK_THRESHOLD=0.5
```

## Development

See `CLAUDE.md` for detailed development guidance and architecture documentation.

## License

This is a demonstration portfolio project.
