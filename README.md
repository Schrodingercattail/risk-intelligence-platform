# Risk Intelligence Platform

**Multi-Signal Risk Detection & Evidence-Grounded AI Investigation Platform**

An AI/ML risk intelligence platform combining machine learning, deterministic rule engines, graph-based detection, and RAG-grounded LLM investigation narratives to identify suspicious behaviors, ground findings in policy evidence, and support analyst-led investigations across risk-sensitive industries.

---

## Project Overview

This is an **extensible risk intelligence platform** that combines multi-signal risk detection with evidence-grounded Generative AI for investigation support. The platform integrates machine learning, rule-based signals, graph analysis, model monitoring, policy retrieval, claim-level citation validation, and persisted LLM explanations into a unified investigation workflow.

Its architecture separates risk detection from AI-generated explanation: ML, Rule, and Graph components produce structured risk evidence, while the LLM acts as an explanation layer grounded in canonical evidence and policy context. This allows investigators to use natural-language AI assistance without making the LLM the source of risk scores or the final decision-maker.

The platform implements a complete risk detection pipeline from data ingestion through scoring, monitoring, and alerting. While demonstrated with trading-inspired datasets, the underlying architecture is **industry-agnostic** and transferable to multiple risk-sensitive domains.

---

## Screenshots

The Investigation page exposes two parallel explanation capabilities —
**Evidence (Model Explainability)** for structured, deterministic risk
evidence, and **Policy-backed Narrative (Citations)** for the LLM-generated
investigation narrative. They complement each other; the LLM narrative does
not replace the Evidence tab.

### 1. Risk Overview

**Risk Overview** — Executive dashboard with detection intelligence, risk distribution, and investigation queue metrics

![Risk Overview](docs/screenshots/risk-overview.png)

### 2. Investigation Queue

**Investigation Queue** — Filterable case list with risk levels, detection methods, and recommended actions for analyst review

![Investigation Queue](docs/screenshots/investigation-queue.png)

### 3. Investigation Risk Evidence

**Risk Evidence Detail (Model Explainability)** — Structured ML, Rule, and Graph evidence with feature-level attribution and signal details for case analysis

![Investigation Risk Evidence](docs/screenshots/investigation-risk-evidence.png)

### 4. Policy-backed Narrative — Findings

**Policy-backed Narrative (Citations)** — LLM-generated investigation narrative with persistent canonical output, unified key risk findings, and explicit LLM regeneration controls

![Policy-backed Narrative Findings](docs/screenshots/investigation-policy-narrative-findings.png)

### 5. Policy-backed Narrative — Actions & Evidence

**Investigation Actions & Evidence** — SOP-aligned next actions, missing information, policy citations, and detailed ML, Rule, and Graph evidence for case investigation

![Policy-backed Narrative Actions and Evidence](docs/screenshots/investigation-policy-narrative-actions-evidence.png)

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
│  • Canonical Evidence (ML / Rule / Graph / Contextual)      │
│  • Policy RAG Retrieval (Local markdown policy documents)    │
│  • Citation Generation & Claim-Level Validation              │
│  • Evidence Completeness Checking                           │
│  • Audience Formatting (Investigator vs Business)            │
│  • Optional LLM Narrative Generation (default when enabled)  │
│  • Narrative Contract (deterministic numbering/formatting)   │
│  • Persisted Canonical Explanation + Cache Tiers             │
│  • Rate Limiting / Metrics                                   │
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
5. **Claim-Level Validation** - A citation must support the exact claim of the finding it is attached to. Findings do **not** require a citation when no directly matching policy evidence exists — **no citation is better than a wrong citation**. Contextual evidence (e.g. account age) may remain uncited; policy-backed claims and SOP recommendations receive appropriate policy grounding when available.
6. **Audience Formatting** - Quote redaction for business mode, full detail for investigators

**Value Proposition:**

Risk analysts receive explanations where each key finding is backed by specific policy document references, enabling:
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

**Explanation Persistence & Cache:**

Explanations are treated as persisted case artifacts, not transient cached
responses. Reads flow through three tiers:

```
Risk Event
   ↓
Fingerprint  (sha256 of audience | risk_event_id | pipeline_run_id |
              model_version | policy_version)
   ↓
┌─────────────────────────────┐
│ Tier 1: Memory Cache        │  performance layer; fast repeated reads;
└─────────────────────────────┘  TTL expiry does NOT trigger LLM generation
   ↓ miss
┌─────────────────────────────┐
│ Tier 2: Persisted Artifact  │  case_explanations table; stable canonical
└─────────────────────────────┘  artifact; served after a cache miss
   ↓ absent / stale
┌─────────────────────────────┐
│ Tier 3: Generate + Persist  │  LLM (or deterministic fallback) generation
└─────────────────────────────┘  → citation assembly → persist new artifact
```

- **Tier 1 — In-memory TTL cache** (default 600s, max 1024 entries): a pure
  performance layer for fast repeated reads. Cache expiry falls through to
  Tier 2 and never triggers LLM generation by itself.
- **Tier 2 — Persisted canonical explanation** (`case_explanations` table,
  one row per `user_id` + `audience`): the canonical narrative artifact for
  the current case version. Ordinary page loads and re-opens are served from
  this artifact without regenerating.
- **Tier 3 — Generate + persist**: used only when no valid persisted artifact
  exists (absent, or stale because the case version changed) or when
  regeneration is explicitly requested. The generated explanation goes
  through citation assembly/validation and is persisted as the new canonical
  artifact.

**Version fingerprint.** A stored artifact is valid only while its
`version_fingerprint` matches the current case context:

```
version_fingerprint = sha256(
    audience | risk_event_id | pipeline_run_id | model_version | policy_version
)
```

A new pipeline run, model version, or policy version changes the fingerprint,
marking the stored explanation stale. The next ordinary read regenerates.

**Ordinary read vs explicit regeneration:**

- Ordinary read (`POST /api/risk/explain`): memory cache → persisted
  artifact → **no LLM regeneration**. The narrative stays stable until an
  explicit regenerate or a case-version change.
- Explicit regeneration (`POST /api/risk/explain/regenerate`): bypasses both
  read tiers, always generates a fresh explanation (LLM, or deterministic
  fallback when unavailable), and persists it as the new canonical artifact.
  Page loads never trigger regeneration implicitly.
- `bypass_cache=true` on `/explain` skips only the Tier 1 memory cache; it
  does **not** imply regeneration — the persisted artifact can still be served.

**User-facing entry point:** Investigation users can explicitly select
**"Regenerate with LLM"** (in the Policy-backed Narrative header, next to the
source badge) to create a new narrative from the current canonical evidence
and policy context. This regenerates the explanation only; ML, Rule, and
Graph risk scores are not recalculated.

**Rate Limiting:**
- 30 requests per minute per client IP
- Sliding window implementation
- Configurable via `EXPLAIN_RATE_LIMIT_PER_MIN`

**Observability:**
- `/api/risk/metrics/explain` endpoint exposes:
  - Cache hit rate
  - Persisted-artifact reads (`persisted_total` — requests served from the persisted canonical explanation; not an LLM generation count)
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

## Canonical Evidence & Unified Findings

`EvidenceService.get_canonical_evidence()` is the **evidence source of truth**
for the explanation layer. Canonical Evidence is the source of truth for
downstream narrative, citation, and investigation flows, preventing downstream
components from independently re-deriving the meaning of component scores:

```
Canonical Evidence
├── ml          → score, probability, primary_driver
├── rules       → score, triggered deterministic rules
│                  (trigger values, thresholds, contributions,
│                   consistency check vs the rule score)
├── graph       → score; actual relationship evidence when present;
│                  an explicit "no detected graph signal" note when
│                  graph score = 0
├── contextual  → account age and other contextual information
└── findings    → unified findings (name, evidence, evidence type,
                   observed values, thresholds and contributions
                   where applicable, internal detection-source
                   provenance)
```

**Key semantics:**

- **RiskFactor rows are feature-level / contextual descriptive evidence.**
  A RiskFactor is **not** synonymous with an ML finding: "the ML model uses a
  feature" does not mean "ML independently detected that finding". Feature
  findings never claim ML attribution.
- **Detection source and finding are separate dimensions.** One finding may be
  associated with multiple internal detection sources (e.g. a shared-device
  finding supported by both graph analysis and the underlying feature), but
  the user-facing narrative does **not** expose detection-source labels.
- **Findings are unified, not bucketed.** The narrative presents a single
  "Key Risk Findings" list — not separate, mutually exclusive
  ML / Rule / Graph finding categories.
- **Rule evidence is derived, not guessed.**
  `EvidenceService._derive_rule_evidence()` mirrors the deterministic rules of
  `RiskScoringService._calculate_rule_score()` (see
  [Risk Detection & Scoring Logic](#risk-detection--scoring-logic)), so each
  triggered rule reaches the narrative with its observed values, threshold and
  contribution — the LLM never infers rules from the rule score alone.
- **Graph zero is a neutral fact.** `graph_score = 0` with no graph evidence
  means "no detected graph signal" — it is not evidence of an isolated
  account, "lone wolf" behavior, hidden infrastructure, or evasion, and it
  never receives a citation or a numbered finding.
- **Account age is contextual by itself.** The only deterministic
  account-age rule is "New account with high activity"
  (`account_age_days < 7 AND trade_frequency_24h > 50`). A 112-day-old account
  is not a new-account-rule case; account age alone does not create a
  policy-backed finding and does not automatically receive a KYC/CDD citation.

---

## Narrative Contract

The user-facing narrative has a stable, case-invariant structure. Numbering
and formatting are normalized deterministically by the backend — they are
never left to the language model:

### What this means (Policy-backed)
High-level risk interpretation.

### Key Risk Findings
Evidence-backed findings — what the system observed and why each finding was
identified. Findings without directly matching policy support may remain
uncited.

### Next Actions (SOP-aligned)
Investigation-oriented action steps.

**Contract rules:**

- Findings are numbered `1..N`; action steps are numbered separately `1..M`
  (the action numbering always restarts at 1 and never continues the findings
  count).
- Finding numbering and citation numbering are **independent** — an uncited
  finding keeps its number, and citation IDs form their own contiguous
  sequence `[1..K]`.
- Score contributions and raw implementation thresholds are retained in
  Canonical Evidence (audit/debug) but are **not** shown in the default
  narrative; thresholds are expressed in natural language with the observed
  values.
- Raw feature field names are generally not exposed; observed values are
  rendered as business language (e.g. "7 withdrawals were recorded in 24
  hours").
- Internal detection sources are never shown as
  "detected by Feature/Rule/Graph/ML" labels.
- Graph-zero is a neutral summary note, not a positive risk finding, and
  receives no citation.
- The LLM organizes the supplied canonical evidence; it does not invent
  evidence, add citation markers, or number findings/actions — the backend
  owns numbering and attaches citations afterwards.

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
- When LLM explanation is enabled and configured, the **LLM is the default
  generator** of the Policy-backed Narrative; the deterministic model-based
  explanation remains the fallback when the LLM is unavailable, times out, or
  fails. LLM integration is still optional — the platform runs fully without it.
- The Investigation UI displays the explanation source badge
  ("Source: LLM" / "Source: Model (Fallback)") so analysts know which
  generator produced the narrative.
- Generated explanations are **persisted as canonical artifacts**: ordinary
  reads (including page reloads) are served from the persisted artifact and do
  not regenerate LLM output; explicit regeneration is available via the
  **"Regenerate with LLM"** button in the Investigation UI
  (`POST /api/risk/explain/regenerate`).
- The narrative shows: a policy-backed summary, unified **Key Risk Findings**
  (each with observed evidence), and SOP-aligned next actions.

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
   - Timeout protection (default 30 seconds; reasoning-capable gateway
     responses may need the longer window — configurable via
     `EXPLAIN_LLM_TIMEOUT_SECONDS`)
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
EXPLAIN_LLM_TIMEOUT_SECONDS=30     # LLM API timeout (default: 30s — thinking-enabled
                                   # gateway responses may require the longer window)
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

**Persisted-artifact tracking:**
- `persisted_total` — reads served from the persisted canonical explanation
  (a memory-cache miss that hit the store). Deliberately not an LLM/fallback
  counter: a persisted read is not a generation, so generation counters are
  never double-counted.

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

## Risk Detection & Scoring Logic

Source of truth: `backend/app/services/risk_service.py` (`RiskScoringService`), config in `backend/app/config.py`. Three distinct concepts — keep them separate:

1. **Detection threshold** — when a detection method is considered to have contributed a *meaningful signal* (used for detection attribution, NOT for scoring): ML ≥ 10, Rule ≥ 15, Graph ≥ 10 (`DETECTION_ML/RULE/GRAPH_THRESHOLD`).
2. **Signal score** — each method's own 0–100 system score (below).
3. **Final risk score / level** — the weighted fusion and level thresholds (next section).

### A. ML Detection (LightGBM)

- **Score range:** 0–100 system score (`ml_score`), derived from the model's risk probability; `risk_probability` is stored separately.
- **Semantics:** `ml_score` is a **system signal score, not a calibrated probability of fraud** — do not read it as "96% chance of fraud". `risk_probability` is the raw model output.
- **How it's produced:** LightGBM inference over 13 engineered features in `feature_table` (`RiskScoringService._calculate_ml_score` → `MLInferenceService.predict_proba`; features listed in `backend/app/ml/model.py`).
- **Explainable evidence:** the pipeline persists `RiskFactor` rows (e.g. "High Trading Frequency", "Shared Device Relationships") and `FeatureTable` values. `RiskFactor` rows represent **feature-level / contextual descriptive evidence** associated with a risk event — they are not ML findings by themselves. Canonical Evidence (below) aggregates ML, Rule, Graph and contextual evidence into the unified structure consumed by the narrative/citation flows (`EvidenceService.get_canonical_evidence`).
- ML detection attribution threshold (ML ≥ 10) ≠ the score itself.

### B. Rule Engine (deterministic)

Each rule contributes a fixed amount when its trigger condition holds; **Rule Score = sum of triggered contributions, capped at 100** (`_calculate_rule_score`). Evidence derivation aligned 1:1 in `EvidenceService._derive_rule_evidence` — the triggered rules (value / threshold / contribution) are provided to the LLM as structured evidence.

| Rule name | Trigger condition | Contribution | Evidence fields |
|---|---|---|---|
| New account with high activity | `account_age_days < 7` AND `trade_frequency_24h > 50` | +40 | `account_age_days`, `trade_frequency_24h` |
| High opposite trade ratio | `opposite_trade_ratio > 0.4` | +35 | `opposite_trade_ratio` |
| Multiple shared devices | `shared_device_count > 3` | +30 | `shared_device_count` |
| High withdrawal frequency | `withdrawal_frequency_24h > 5` | +25 | `withdrawal_frequency_24h` |
| First withdrawal | `first_withdrawal_flag = true` AND `withdrawal_frequency_24h` present | +20 | `first_withdrawal_flag`, `withdrawal_frequency_24h` |

**Important:** "Account Age" alone is *contextual evidence*, never a rule. The only account-age rule is "New account with high activity" above (both conditions required).

### C. Graph Detection (network)

- **How it's computed** (`_calculate_graph_score`): for each cluster the user belongs to (from `account_clusters` / `cluster_members`): `cluster.risk_score × 0.3 + min(member_count × 5, 30) + 20 if hub`. Score capped at 100.
- **Graph evidence exists** when the user has actual cluster/network relationships (connected accounts via shared devices/IPs). Then the connected-account count and cluster context are provided as structured graph evidence.
- **Graph score = 0 means "No detected graph signal"** — nothing more. It is *not* evidence of an isolated account, "lone wolf" actor, hidden infrastructure, or evasion/OpSec behavior, and the explanation layer must not narrate it as such.

### Final score fusion and risk levels

- `final_score = 0.5×ml_score + 0.3×rule_score + 0.2×graph_score` (`ML/RULE/GRAPH_WEIGHT`, capped per-method at 100 before fusion).
- Risk levels: see next section.

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
