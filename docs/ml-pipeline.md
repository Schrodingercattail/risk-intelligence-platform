# ML Risk Scoring Pipeline

## Overview

The ML Risk Scoring Pipeline is a core component of the risk management platform, providing machine learning-based risk assessment for user accounts.

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ML SCORING PIPELINE                        │
└─────────────────────────────────────────────────────────────┘

Dataset Ingestion (CSV/Database)
    │
    ▼
Feature Engineering (13 features)
    │
    ▼
Feature Table + Labels (is_risky)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│              LIGHTGBM TRAINING                              │
├─────────────────────────────────────────────────────────────┤
│  1. train_test_split (80/20, stratified)                  │
│  2. Train LightGBM (100 rounds)                           │
│  3. Evaluate: AUC, KS                                      │
│  4. Extract feature importance                            │
│  5. Save: risk_model_latest.pkl                            │
│  6. Store: model_metadata + feature_importance tables       │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Model Artifact
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│            RISK SCORING SERVICE                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  user_id → Feature Table → ML Features                    │
│                                │                            │
│                                ▼                            │
│                    MLInferenceService                      │
│                                │                            │
│                      predict_proba()                        │
│                                │                            │
│              ┌─────────────────┴─────────────────┐        │
│              │                                   │        │
│              ▼                                   ▼        │
│        ml_probability                         ml_score  │
│              │                                   │        │
│              │              ┌─────────────────────┘        │
│              │              │                               │
│              ▼              ▼                                │
│         Combined with Rule Score + Graph Score               │
│                    (0.5 + 0.3 + 0.2)                        │
│                                │                            │
│                                ▼                            │
│                        final_score                           │
│                                │                            │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Risk Event (with risk_probability from ML)
```

## Model Components

### LightGBMTrainer Class

```python
- prepare_features(): Calculate 13 features from raw data
- train(): LightGBM training with train_test_split
- _evaluate_model(): Calculate AUC, KS, feature importance
- _save_model(): Save model artifact with metadata
```

### MLInferenceService Class

```python
- _load_model(): Load trained model artifact
- predict_proba(): Return (probability, score_0_100)
- _prepare_feature_vector(): Format features for prediction
- _fallback_prediction(): Heuristic when model unavailable
```

## Training

### Command

```bash
# Option 1: Train from CSV (generates demo data)
python ml-models/training/train_risk_model.py --source csv

# Option 2: Train from database (requires data loaded via pipeline)
python ml-models/training/train_risk_model.py --source database
```

### Training Output

```
==================================================
Model Metrics:
  ✓ AUC: 0.8542
  ✓ KS: 0.4321

Data Split:
  - Train: 1600 (80.0%)
  - Test: 400 (20.0%)
  - Positive Ratio: 30.00%

Top 10 Feature Importance
==================================================
  1. opposite_trade_ratio          :    48.23
  2. shared_device_count           :    35.18
  3. account_age_days              :    20.45
  4. trade_frequency_24h           :    15.34
  5. withdrawal_risk_score         :    10.91
  6. linked_account_count          :     8.72
  7. trade_volume_24h              :     5.56
  8. unique_ip_count               :     4.21
  9. withdrawal_frequency_24h       :     3.18
  10. active_days_count             :     2.05
```

## Model Interpretation

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **AUC = 0.85** | Excellent | Model distinguishes risky/normal users well |
| **KS = 0.43** | Strong | Good separation between score distributions |

## Risk Event Output

```json
{
  "user_id": "U00123",
  "risk_score": 76.5,
  "risk_probability": 0.88,
  "risk_level": "HIGH",
  "ml_score": 88.0,
  "rule_score": 62.0,
  "graph_score": 75.0,
  "primary_reason": "ML Pattern Detection",
  "recommended_action": "Manual Review"
}
```

## Dependencies

```bash
pip install pandas scikit-learn lightgbm
```
