# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI-Powered Market Integrity & Account Risk Monitoring Platform**

A financial trading platform risk monitoring system that demonstrates AI + Risk Control + Full-stack development capabilities.

**Business Goals:**
- Monitor user account behavior, trading activity, and risk signals
- Identify anomalous accounts, potential manipulation, and high-risk activities
- Provide risk analysis and management capabilities

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
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   │   ├── account_risk/        # Account risk monitoring
│   │   │   ├── market_integrity/   # Market integrity monitoring
│   │   │   ├── rule_engine/        # Risk rule engine
│   │   │   └── model_service/      # ML model service
│   │   ├── ml/               # ML models, training, evaluation
│   │   │   ├── features/     # Feature engineering
│   │   │   ├── models/       # Model definitions
│   │   │   └── evaluation/   # AUC, KS, PSI metrics
│   │   └── db/               # Database session
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Dashboard pages
│   │   ├── services/         # API client
│   │   └── types/            # TypeScript types
│   └── package.json
└── ml-models/
    ├── notebooks/            # Feature exploration
    ├── training/             # Model training scripts
    └── artifacts/            # Trained models
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
