# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Risk Intelligence Platform**

A machine learning-driven risk detection, monitoring, and investigation system.

### Project Context

This project is inspired by risk management scenarios from consumer finance and digital asset platforms, but the architecture is designed to be industry-agnostic and transferable across risk-sensitive industries.

The platform demonstrates:
- ML-based risk detection with feature engineering
- Multi-signal fusion (ML + Rules + Graph)
- Model monitoring and drift detection (PSI)
- Investigation workflow support
- Full-stack implementation (FastAPI + React)

### Business Focus

A machine learning-driven risk detection, monitoring, and investigation system. The platform demonstrates how to combine data pipelines, ML models, rule engines, graph signals, and investigation workflows into a unified architecture.

**Business Goals:**
- Identify abnormal user behavior patterns across risk-sensitive domains
- Combine multiple risk signals (ML + Rules + Graph) into coherent decisions
- Support investigation workflows with signal attribution and evidence
- Monitor model performance and detect data drift
- Provide explainable risk decisions for operators

**Industry Context:**
Inspired by risk management scenarios from consumer finance and digital asset platforms, but designed to be industry-agnostic and transferable across fintech, fraud prevention, e-commerce, and marketplace integrity domains.

## Technology Stack

### Backend
- **Python 3.12+**
- **FastAPI** - Web framework
- **PostgreSQL** - Database
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations

### Machine Learning
- **scikit-learn** - Feature engineering & modeling
- **LightGBM** - Gradient boosting models
- **pandas/numpy** - Data processing
- **joblib** - Model persistence

### Frontend
- **React + TypeScript**
- **Dashboard UI** - Risk visualization
- **Chart libraries** - Analytics display

## Core Modules

```
risk-platform-demo/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI endpoints
│   │   ├── core/             # Configuration, security, dependencies
│   │   ├── models/           # SQLAlchemy database models & Pydantic schemas
│   │   ├── services/         # Business logic layer
│   │   │   ├── feature_engineering.py      # Feature engineering pipeline
│   │   │   ├── risk_service.py             # Risk scoring & event generation
│   │   │   ├── graph_service.py            # Network analysis & clusters
│   │   │   ├── pipeline_service.py         # Pipeline orchestration
│   │   │   ├── psi_service.py              # PSI drift monitoring
│   │   │   ├── model_monitoring_service.py # Model performance tracking
│   │   │   ├── evidence_service.py         # Risk evidence attribution
│   │   │   └── llm_service.py              # Optional LLM-assisted explanation layer (extension capability)
│   │   ├── ml/               # ML models, PSI calculation
│   │   │   ├── model.py      # LightGBM model interface
│   │   │   └── psi.py        # PSI calculation utilities
│   │   └── db/               # Database session management
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Dashboard pages (Command Center, Investigation, etc.)
│   │   ├── services/         # API client
│   │   └── types/            # TypeScript types
│   └── package.json
├── ml-models/
│   ├── training/             # Model training scripts
│   └── artifacts/            # Trained models & baselines
└── test_data/                # Validation datasets
```

## Development Commands

```bash
# Backend
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Tests
pytest backend/tests/
pytest backend/tests/tests/test_account_risk.py -v

# ML Model Training
python ml-models/training/train_risk_model.py

# Frontend
cd frontend
npm install
npm run dev
```

## Service Architecture

### Core Risk Intelligence Services (Always Active)

The platform's core risk detection pipeline:

- **feature_engineering.py** — Feature engineering pipeline (13 risk features)
- **risk_service.py** — Risk scoring, event generation, signal fusion
- **graph_service.py** — Network analysis, cluster detection
- **pipeline_service.py** — Pipeline orchestration and workflow
- **psi_service.py** — PSI drift detection and monitoring
- **model_monitoring_service.py** — Model performance tracking
- **evidence_service.py** — Risk evidence attribution for explainability

### Optional Extension Services

**llm_service.py** — LLM-assisted explanation layer (extension capability)

This service is designed as an **optional enhancement** for natural language explanation generation. The platform operates fully without it.

**Configuration Control:**
- `ENABLE_LLM_EXPLANATION=false` (default): Model-based explanations only
- `ENABLE_LLM_EXPLANATION=true` + `ANTHROPIC_API_KEY`: LLM generates natural language summaries

**Behavior:**
- When ENABLE_LLM_EXPLANATION=true and API key is set: LLM generates natural language case summaries
- When disabled or no API key: Returns structured explanations from model outputs
- On LLM API failure: Automatically falls back to model-based explanations
- The `/explain` endpoint works in both modes without breaking investigation workflow

**Implementation:**
- The `/api/risk/explain` endpoint checks `settings.ENABLE_LLM_EXPLANATION`
- If enabled, calls LLM service for narrative summaries
- If disabled, calls `_generate_model_based_explanation()` for structured output
- Risk scoring and event generation are unaffected by LLM configuration
- The `/explain` endpoint works in both modes (LLM or structured fallback)

**Current Implementation:** The Investigation UI displays explanations generated from risk analysis outputs (ML scores, rule hits, graph signals) — this is **model explainability**, not LLM-generated text.

**Future Enhancement:** LLM integration could provide:
- Natural language case summaries
- Analyst workflow assistance
- Investigation guidance generation

---

## Architecture Principles

1. **Clear Separation of Concerns**
   - API layer handles HTTP only
   - Services contain business logic
   - ML models are isolated and versioned

2. **Model Evaluation Standards**
   - AUC - Overall discrimination performance
   - KS - Maximum separation between distributions
   - PSI - Population stability monitoring
   - Feature importance for explainability

3. **Rule Engine Design**
   - Configurable risk strategies
   - Rule matching and hit logging
   - Risk level hierarchy

4. **API Design**
   - RESTful endpoints
   - Request/response validation with Pydantic
   - OpenAPI documentation auto-generated

---

**When updating this file**: Add new patterns, commands, and architectural decisions as they emerge during development.
