# AI-Powered Market Integrity & Account Risk Monitoring Platform

A demonstration portfolio project for an AI-powered risk monitoring platform designed for cryptocurrency exchanges.

## Overview

This platform helps risk analysts identify suspicious users involved in:
- Coordinated trading
- Market manipulation
- Arbitrage abuse
- Account farming
- Linked account operations
- Abnormal withdrawal behavior

**Key Philosophy**: This is an investigation support system, not an auto-ban system. The final enforcement decision remains with human operators.

## Architecture

The system consists of three intelligence layers:

1. **ML Risk Model (LightGBM)** - Pattern recognition and historical risk learning
2. **Rule Engine** - Explicit risk signals (e.g., new account with large withdrawal)
3. **Graph Analysis (NetworkX)** - Relationship detection and cluster analysis

### Technology Stack

- **Backend**: Python, FastAPI, PostgreSQL, SQLAlchemy
- **Frontend**: React, TypeScript, Tailwind CSS, Recharts, React Flow
- **ML**: LightGBM, scikit-learn, pandas
- **Graph**: NetworkX
- **LLM**: Claude API (abstracted for provider flexibility)
- **Deployment**: Docker Compose

## Project Structure

```
risk-platform-demo/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── models/       # Database models & schemas
│   │   ├── services/     # Business logic layer
│   │   ├── ml/           # ML models & training
│   │   └── db/           # Database session
│   └── requirements.txt
├── frontend/             # React application
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   └── services/     # API client
│   └── package.json
├── ml-models/            # ML training & artifacts
├── data/                 # Sample and generated data
└── docker-compose.yml
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Python 3.12+ for local development
- (Optional) Node.js 20+ for local development

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

## Data Pipeline

The demo includes configurable data generation:

1. Upload CSV files (users, devices, trades, withdrawals)
2. Data validation and feature engineering
3. ML scoring + Rule evaluation + Graph analysis
4. Risk events stored in database
5. Visualized in dashboard

**Default demo scale**: 2,000 users, 20,000 trades, 25 suspicious clusters

## Model Metrics

The system tracks three key metrics:

- **AUC** (Area Under ROC): Overall discrimination ability (target: >0.75)
- **KS** (Kolmogorov-Smirnov): Maximum separation between distributions (target: >0.30)
- **PSI** (Population Stability Index): Model drift detection (target: <0.10)

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
HIGH_RISK_THRESHOLD=0.8
MEDIUM_RISK_THRESHOLD=0.5
```

## Development

See `CLAUDE.md` for detailed development guidance and architecture documentation.

## License

This is a demonstration portfolio project.
