# Risk Platform Demo - Project Handoff

## Current Status

Project: risk-platform-demo

Stage:
Runtime verification / demo validation phase

Not in architecture design phase.

---

# Completed

## Environment

✅ macOS Apple Silicon environment

✅ Python virtual environment:

/Users/vv/risk-platform-demo/.venv

Python:
3.12

---

## Backend

Framework:
FastAPI

Status:
Implemented and running successfully.

Verified:

GET /health

Response:

{
 "status":"healthy",
 "app":"Risk Platform API",
 "version":"0.1.0"
}


Swagger:

Available at:

http://127.0.0.1:8000/api/docs


---

## Database

PostgreSQL 16 installed via Homebrew.

Database:

risk_platform

User:

"user"

Tables created:

- users
- devices
- trades
- withdrawals
- risk_events
- risk_factors
- cases
- feature_table
- feature_importance
- model_metadata
- account_clusters
- cluster_members


---

## Demo Data

Generator fixed.

Command:

python -m app.utils.data_generation


Generated:

users.csv
devices.csv
trades.csv
withdrawals.csv
risk_labels.csv


Final data:

Users:
2000

Risk users:
600

Normal users:
1400


---

## Machine Learning

Model:

LightGBM


Training command:

python ml-models/training/train_risk_model.py --source csv


Result:

AUC:
0.9968

KS:
0.9381


Model artifact:

ml-models/artifacts/risk_model_latest.pkl


Top features:

1. withdrawal_frequency_24h
2. account_age_days
3. trade_frequency_24h
4. withdrawal_risk_score
5. trade_volume_24h


---

## PSI Monitoring

Completed.

Frontend:

frontend/src/pages/ModelMonitoring.tsx


Implemented:

- Overall PSI monitoring
- Feature-level PSI
- PSI interpretation guide
- Business-friendly explanations
- Separation between PSI and feature importance


---

## Recent Code Fixes

SQLAlchemy 2.x compatibility fixed:

- raw SQL wrapped with text()
- numpy float converted to Python float


Model loading verification logs added:

backend/app/ml/model.py


---

# Current Known Issues

## 1. Backend startup

Must start from:

backend directory


Command:

cd backend

source ../.venv/bin/activate

uvicorn app.main:app --reload


---

## 2. Frontend not verified yet

Need:

npm install

npm run dev


---

## 3. API integration testing remaining

Need verify:

- frontend calls backend APIs
- model monitoring page
- PSI display
- risk overview page


---

# Important Instructions For Next Claude

Do NOT redesign architecture.

Do NOT recreate environment.

Current project is already implemented.

Continue from runtime verification stage.

First:

1. Read this file
2. Check backend running
3. Start frontend
4. Test full demo flow

