# Risk Intelligence Platform

**Multi-Signal Risk Detection & Explainable Investigation Platform**

An ML-based risk detection platform with policy-backed investigation support, combining machine learning, rule engines, and graph analysis to identify suspicious behaviors and support analyst workflows across risk-sensitive industries.

---

## Project Overview

This is an **extensible risk intelligence platform** that demonstrates how modern risk systems can combine data pipelines, machine learning models, rule engines, graph-based signals, monitoring systems, and investigation workflows into a unified architecture.

The platform implements a complete risk detection pipeline from data ingestion through scoring, monitoring, and alerting. While demonstrated with trading-inspired datasets, the underlying architecture is **industry-agnostic** and transferable to multiple domains.

---

## Screenshots

### 1. Risk Overview

**Risk Overview** — Executive dashboard with detection intelligence, risk distribution, and investigation queue metrics

![Risk Overview](docs/screenshots/risk-overview.png)

### 2. Investigation Queue

**Investigation Queue** — Filterable case list with risk levels, detection methods, and recommended actions for analyst review

![Investigation Queue](docs/screenshots/investigation-queue.png)

### 3. Investigation Risk Evidence

**Risk Evidence Detail** — Transaction, network, and rule evidence with feature attribution for case analysis

![Investigation Risk Evidence](docs/screenshots/investigation-risk-evidence.png)

### 4. Policy-Backed Narrative

**Citations Display** — Policy-backed explanations with clickable citations to regulatory documents and investigation SOPs

![Policy Citations](docs/screenshots/investigation-policy-citations.png)

### 5. Evidence Gap Investigation Case

**Missing Information Panel** — Evidence completeness checking identifies missing investigation inputs (device history, account age, KYC status)

![Evidence Gap Case](docs/screenshots/investigation-evidence-gap.png)

### 6. Model Monitoring

**Model Health Dashboard** — PSI drift detection, performance metrics (AUC, KS), and feature distribution tracking

![Model Monitoring](docs/screenshots/model-monitoring.png)

### 7. Data Pipeline

**Pipeline Status** — Dataset upload, validation, feature engineering, and risk scoring workflow with stage completion tracking

![Data Pipeline](docs/screenshots/data-pipeline.png)

## Design Philosophy

This platform is an **investigation support system**, not an auto-ban system. The final enforcement decision remains with human operators. The goal is to surface risks, explain them, and enable efficient investigation.

---

## Core Capabilities

**Risk Detection**
- ML Risk Scoring — LightGBM-powered pattern recognition (AUC: 0.85, KS: 0.43)
- Rule Engine — Expert-defined risk signals for known fraud patterns
- Graph Detection — Network analysis for coordinated behavior rings
- Multi-Signal Fusion — Weighted combination with business override logic

**Investigation Support**
- Policy-Backed Explanations — Risk narratives grounded in retrieved policy citations
- Evidence Completeness Checking — Identification of missing investigation inputs
- Evidence Aggregation — Transaction, network, feature, and rule signals
- Audience-Based Formatting — Investigator (full detail) vs business (reduced sensitivity) modes
- Citation-Supported Narratives — Each key finding backed by policy document references
- Investigation Queue — Filterable workflow for analyst review

**Risk Monitoring**
- PSI Drift Detection — Population Stability Index for model drift monitoring
- Model Performance Tracking — AUC, KS, feature distribution monitoring
- Baseline Validation — Automated comparison against training distributions

**Optional AI Enhancement**
- LLM-Assisted Explanations — Natural language case summaries when enabled
- Privacy Controls — Configurable identifier redaction before external LLM calls
- Deterministic Fallback — Model-based explanations when LLM unavailable

---

## Architecture Overview

### Current Architecture

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
│              MULTI-SIGNAL RISK SCORING                       │
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
│         INVESTIGATION EXPLANATION LAYER                      │
├─────────────────────────────────────────────────────────────┤
│  • Evidence Retrieval (Transaction, Network, Rule, Feature) │
│  • Policy RAG Retrieval (Local markdown policy documents)    │
│  • Citation Generation & Validation                         │
│  • Evidence Completeness Checking                           │
│  • Audience Formatting (Investigator vs Business)            │
│  • Optional LLM Explanation Generation                       │
│  • Cache / Rate Limiting / Metrics                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              HUMAN ANALYST REVIEW                            │
├─────────────────────────────────────────────────────────────┤
│  Policy-backed narratives → Investigation decisions         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              MONITORING & DRIFT DETECTION                     │
├─────────────────────────────────────────────────────────────┤
│  PSI Analysis → Model Drift Detection → Retraining          │
└─────────────────────────────────────────────────────────────┘
```

**Key Architecture Principles:**

1. **LLM is Optional** - Risk detection operates independently of LLM services
2. **Policy-Grounded Explanations** - LLM generation (when enabled) is constrained by retrieved policy citations
3. **Deterministic Fallback** - Platform provides structured explanations when LLM unavailable
4. **Evidence-First** - All explanations backed by actual database evidence, not synthetic content

---

## Policy-Backed Investigation System

### Citation Architecture

The platform implements a sophisticated citation system that grounds risk explanations in internal policy documents rather than unsupported AI-generated conclusions.

**How It Works:**

1. **Policy RAG Retrieval** - Local retrieval from markdown policy documents (AML indicators, investigation SOP, KYC requirements)
2. **Finding Classification** - Each key finding is classified by domain (network, transaction, account, ML anomaly)
3. **Domain-Enforced Retrieval** - RAG queries scoped to relevant policy sections before retrieval
4. **Citation Registry** - Deduplication and budget control (max 5 citations per explanation)
5. **Coverage Validation** - Every finding must have at least one citation
6. **Audience Formatting** - Quote redaction for business mode, full detail for investigators

**Value Proposition:**

Risk analysts receive explanations where each key hypothesis is backed by specific policy document references, enabling:
- Regulatory compliance validation
- Audit trail for investigation decisions
- Training material for new analysts
- Consistent interpretation across teams

### Evidence Completeness Checking

The system identifies missing investigation inputs after risk detection, not just risk signals.

**Checked Evidence Types:**
- Account age and onboarding information
- Transaction history availability
- Device fingerprint and IP history
- KYC verification status

**Example Output:**
```json
{
  "missing_info": [
    "Device fingerprint and IP history",
    "Customer KYC verification status"
  ]
}
```

**Engineering Design:**

This separates detection capability from investigation readiness. A high-risk alert may be technically correct but practically unactionable without supporting evidence. The system explicitly identifies these gaps.

### Performance & Production Engineering

**Explanation Cache:**
- In-memory TTL cache (default: 600 seconds)
- Configurable max size (default: 1024 entries)
- Cache key based on user_id, audience, pipeline_run_id, policy_version

**Rate Limiting:**
- 30 requests per minute per client IP
- Sliding window implementation
- Configurable via `EXPLAIN_RATE_LIMIT_PER_MIN`

**Observability:**
- `/api/risk/metrics/explain` endpoint exposes:
  - Cache hit rate
  - Fallback rate (LLM disabled, LLM failed, LLM success)
  - Latency percentiles (p50, p95, avg)
  - Request counters

**Engineering Trade-offs:**

The platform prioritizes reliability over AI novelty. LLM integration is optional, with deterministic fallbacks ensuring continuous operation even when external services fail.

---

### Data Architecture Explanation

**Why CSV Datasets?**

Enterprise production databases cannot be accessed in a standalone open-source project environment. This project uses **synthetic production-like datasets** that demonstrate real-world risk patterns while maintaining data privacy.

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

## Design Evolution

The platform evolved from an initial dashboard wireframe exploration.

Original UI concept: https://github.com/Schrodingercattail/risk-overview-wireframe

---

## Scope

The Risk Intelligence Platform MVP implements a complete risk detection, monitoring, and investigation workflow.

### Current Implementation

**Data Ingestion & Processing**
- CSV-based dataset upload with validation
- 13-feature engineering pipeline (device patterns, behavioral activity, account attributes, transaction patterns)
- Data quality checks and pipeline traceability

**Risk Detection Engine**
- ML Risk Scoring — LightGBM gradient boosting (AUC: 0.85, KS: 0.43)
- Rule Engine — Expert-defined risk signals for known fraud patterns
- Graph Detection — Network analysis for coordinated behavior rings (NetworkX)
- Multi-Signal Fusion — Weighted combination (ML 50%, Rule 30%, Graph 20%)

**Risk Event Management**
- Risk event generation with complete audit trail
- Signal attribution (which detection methods contributed to each score)
- Evidence factors with feature-level explanations
- Risk level classification with coordinated fraud override logic
- Investigation queue with filtering by risk level

**Model Monitoring & Validation**
- PSI-based drift detection for population stability monitoring
- Feature distribution tracking vs training baseline
- Performance metrics (AUC, KS) visualization
- Model retraining workflow with baseline validation

**Visualization & Investigation**
- Risk Command Center dashboard with executive summary
- Model monitoring interface with PSI visualization
- Investigation workspace with evidence attribution
- Network relationship graph for entity analysis

### Architecture Boundaries

The MVP uses CSV-based dataset upload as a demonstration proxy for production data integration. The underlying architecture is designed to extend to enterprise data sources (databases, data warehouses, streaming pipelines).

### Explicitly Excluded

The following are **intentionally excluded** as platform infrastructure rather than core risk intelligence capabilities:

- **Authentication & Authorization** — User identity, SSO, OAuth integration
- **User Management** — Account creation, profile management, password handling
- **Role-Based Access Control (RBAC)** — Permission management, role assignment
- **Audit Logging for User Actions** — Operator activity tracking (separate from risk event audit trail)

These capabilities are typically provided by enterprise identity providers (Okta, Auth0, Azure AD) and would be integrated at the platform level in production. The MVP focuses on risk intelligence functionality independent of these infrastructure concerns.

---

## Future Extensions

The platform architecture supports several evolution paths for production deployment.

### Enterprise Data Integration

**Database & Warehouse Connectors**
- Direct integration with operational databases (PostgreSQL, MySQL, MongoDB)
- Data warehouse connectivity (Snowflake, BigQuery, Redshift)
- Data lake integration (S3, ADLS, HDFS)

**Streaming Pipeline Support**
- Batch event processing (Kafka, Kinesis, Pub/Sub) for incremental updates
- Streaming feature computation for periodic batch scoring
- Pipeline-based risk scoring for transaction-time decisions

### Case Management Workflow

**Complete Case Lifecycle**
- Structured workflow: creation → assignment → investigation → resolution
- Case status transitions with validation rules
- Collaborative investigation tools and notes
- Resolution tracking and closure workflows

**External System Integration**
- API-based connection to existing case management platforms
- Bi-directional sync for case status and outcomes
- Historical performance feedback to model training

### Operational Automation

**Automated Retraining**
- PSI-triggered retraining workflows
- A/B testing framework for model comparison
- Gradual rollout and shadow mode evaluation

**Alerting & Notifications**
- Batch alert generation for critical risk events
- Integration with notification systems (Slack, PagerDuty, email)
- Escalation workflows based on risk severity

### Advanced Model Capabilities

**Temporal Graph Analysis**
- Time-patterned relationship detection
- Evolution of network clusters over time
- Sequence-based fraud pattern recognition

**Cross-Account Trading Pattern Detection** (Future Enhancement)

Current implementation detects opposite trading behavior within single accounts.

Future enhancement would analyze coordinated trading patterns across multiple accounts:
- Opposite trade timing correlation
- Trading volume similarity analysis
- Symbol overlap detection
- Account relationship graph integration

Purpose: Detect potential coordinated trading clusters through multi-account behavioral analysis.

**Optional LLM-Assisted Investigation**
- Natural language case summaries
- Analyst workflow assistance and guidance
- Investigation prioritization recommendations

Current implementation includes an optional LLM integration endpoint that can be enabled for narrative explanation generation without affecting core risk scoring functionality.

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

---

## LLM Reliability and Safety Controls

The platform provides optional LLM-assisted investigation explanations with comprehensive reliability safeguards.

### Core Design Principle

**LLM is optional and not part of risk scoring decisions.**

Risk detection operates independently of LLM services:
- ML/rule/graph scoring remains deterministic
- LLM only used for explanation generation when enabled
- System remains fully functional through deterministic fallback when LLM unavailable

### Configuration Control

```bash
# .env file
ENABLE_LLM_EXPLANATION=false  # Default: disabled
ANTHROPIC_API_KEY=           # Required only when enabling LLM
```

### Reliability Safeguards

**Deterministic Fallback:**
- When LLM disabled: Returns structured model-based explanations
- When LLM fails: Falls back to model-based explanations
- When LLM times out: Continues with cached or model-based response
- Core risk scoring unaffected by LLM availability

**Implementation Architecture:**

1. **Risk Detection Layer** (No LLM dependency)
   - ML model generates risk scores
   - Rule engine applies expert-defined signals
   - Graph analysis detects network relationships
   - All risk signals deterministic and cached

2. **Evidence Retrieval Layer** (No LLM dependency)
   - Transaction evidence from database
   - Network evidence from cluster analysis
   - Feature evidence from feature table
   - Rule evidence derived from feature values

3. **Citation Generation Layer** (No LLM dependency)
   - Policy RAG retrieval from local markdown documents
   - Domain enforcement before retrieval
   - Citation validation and coverage checking
   - Finding-to-policy mapping

4. **Explanation Layer** (Optional LLM)
   - When enabled: LLM generates natural language summaries
   - Constrained by retrieved evidence and policy citations
   - 5-second timeout protection
   - Graceful fallback on any failure

### Privacy Controls

```bash
SHOW_USER_ID_IN_LLM_PROMPT=false  # Redact user IDs from LLM prompts
LOG_REDACT_USER_ID=true           # Redact user IDs from structured logs
```

**Sanitization Applied:**
- IP addresses → [REDACTED_IP]
- Email addresses → [REDACTED_EMAIL]
- Phone numbers → [REDACTED_PHONE]
- Long identifiers → [REDACTED_ID]
- Thresholds/percentages → [REDACTED_THRESHOLD]

### Performance Controls

```bash
EXPLAIN_CACHE_TTL_SECONDS=600      # Cache TTL (default: 10 minutes)
EXPLAIN_CACHE_MAX_SIZE=1024        # Max cache entries
EXPLAIN_RATE_LIMIT_PER_MIN=30      # Rate limit per client IP
EXPLAIN_LLM_TIMEOUT_SECONDS=5      # LLM API timeout
```

### Observability Metrics

The `/api/risk/metrics/explain` endpoint exposes in-memory counters for the
`/api/risk/explain` endpoint. Counters are per-worker and reset on process
restart; for distributed deployments use Prometheus / an APM instead.

**Cache hit/miss tracking** — recorded on every cache lookup inside
`ExplanationCache.get()`:
- `cache_hit_total` — lookup found a valid (non-expired) entry; the stored
  response is returned and the explanation is **not** regenerated.
- `cache_miss_total` — lookup missed (key absent or TTL expired).
- `cache_hit_rate` = `cache_hit_total / (cache_hit_total + cache_miss_total)`.

Because cache hits skip regeneration, they do not re-enter the LLM/fallback
tallies — each logical explanation is counted once.

**LLM success tracking:**
- `llm_total` — explanations produced by a successful LLM call
  (`explanation_source == "LLM"`).

**Fallback tracking** — a request counts as a fallback whenever the
deterministic model-based explanation is used. `fallback_total` is the sum of
two mutually exclusive paths:
- `llm_disabled_total` — LLM was disabled (or no `ANTHROPIC_API_KEY`), so the
  model-based explanation is used by default.
- `llm_failed_total` — LLM was enabled but the call failed or timed out
  (`EXPLAIN_LLM_TIMEOUT_SECONDS`), so it fell back to model-based.

A successful LLM response is **never** a fallback, so `llm_total` and
`fallback_total` are independent. Each uncached request increments exactly one
of `llm_total` / `llm_disabled_total` / `llm_failed_total` (no double counting),
and the latter two each also increment `fallback_total`.
`fallback_rate` = `fallback_total / requests_total`.

**Other counters:** `requests_total`, `success_total`, `error_total`,
`rate_limited_total`, and latency percentiles over a rolling window
(`latency_ms_p50`, `latency_ms_p95`, `latency_ms_avg`).

### Engineering Trade-offs

The platform prioritizes reliability over AI novelty:
- LLM integration is optional, not required
- Deterministic fallbacks ensure continuous operation
- External service failures don't affect risk detection
- Privacy controls limit data exposure to external AI services

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

## Evidence Gap Investigation Case

The platform includes a representative synthetic investigation scenario that demonstrates evidence completeness checking.

### U90001 Investigation Scenario

**Case Characteristics:**

U90001 is a synthetic high-risk case designed to validate evidence gap detection:

| Evidence Type | Status | Notes |
|---------------|--------|-------|
| Device Records | ❌ Missing | No device fingerprints or IP history |
| Account Age | ❌ Missing | No account_created_time available |
| KYC Verification | ❌ Missing | No KYC level recorded |
| Transaction History | ✅ Present | 60 high-frequency trade records |
| Withdrawal History | ✅ Present | 7 withdrawals to new addresses |

**Risk Profile:**
- **Trading Pattern:** High-frequency opposite trading (BUY → SELL)
- **Withdrawal Pattern:** Multiple withdrawals to new addresses in one day
- **Detection:** Elevated ML score due to trading frequency
- **Evidence Gap:** No device/IP evidence for investigation context

### Design Principle

The system separates:
- **Risk detection capability** (identifying suspicious behavior)
- **Investigation evidence completeness** (having sufficient data for investigation)

A high-risk alert may be technically correct but practically unactionable without supporting evidence. The platform explicitly identifies these gaps rather than failing analysis.

### Missing Information Display

When viewing U90001 in the Investigation page, the **Missing Information** panel displays:

```
Missing Investigation Inputs:
• Device fingerprint and IP history
• Account age and onboarding date
• Customer KYC verification status
```

### Validation Purpose

This synthetic case demonstrates:
- Evidence completeness checking identifies investigation blockers
- Risk detection operates independently of evidence availability
- Investigation workflow surfaces gaps rather than failing
- Analysts can prioritize cases with complete evidence

**Note:** This is a representative synthetic scenario, not production customer data. The case is included in validation datasets for testing evidence completeness functionality.

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
- [Cost & Latency Strategy](docs/cost-latency-strategy.md)
- [Data Contract](docs/data-contract.md)
- [Security & Privacy](docs/security_privacy.md)
- [Validation Report](docs/validation-report.md)
- [Test Data Catalog](test_data/README.md)

### Architecture Documentation

- [Citation System Design](docs/architecture/citation-system-design.md) — Citation pipeline, domain enforcement, and validation strategy
- [Citation Taxonomy](docs/architecture/citation-taxonomy.md) — Finding classification and policy mapping rules
- [LLM Optional Design](docs/architecture/llm-optional-design.md) — Optional explanation layer with fallback behavior and privacy controls

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

This is an open-source project released for educational and demonstration purposes.
