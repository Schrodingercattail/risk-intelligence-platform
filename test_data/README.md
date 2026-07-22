# Test Data Catalog

## Overview

This directory contains datasets used for model training, validation, and demonstration of the Risk Management Platform.

## Dataset Descriptions

### v2_diverse - Training Dataset

**Purpose**: ML model training and PSI baseline generation

**Usage**:
- Train LightGBM risk scoring model
- Generate feature distribution baseline for PSI monitoring
- Validate feature engineering pipeline

**Characteristics**:
- Diverse fraud patterns for comprehensive model training
- Balanced risk distribution (30% risky, 70% normal)
- ~2,000 users with full feature coverage

**Contains**: users.csv, devices.csv, trades.csv, withdrawals.csv

**⚠️ DO NOT DELETE** - Required for model retraining and baseline regeneration

---

### v3_subtle_drift - Stable Monitoring Demo

**Purpose**: Demonstrate stable monitoring scenario

**Expected PSI**: < 0.1 (Stable)

**Usage**:
- Show monitoring system correctly identifies stable data
- Validate no false positive drift alerts
- Demonstrate "all clear" monitoring state

**Characteristics**:
- Minor population variations from baseline
- Within acceptable drift tolerance
- Suitable for showing stable production state

**Contains**: users.csv, devices.csv, trades.csv, withdrawals.csv

**⚠️ DO NOT DELETE** - Required for stable monitoring demonstration

---

### v3_realistic_drift - Warning Drift Demo

**Purpose**: Demonstrate warning-level drift detection

**Expected PSI**: 0.1 - 0.25 (Warning)

**Usage**:
- Show monitoring detects moderate population shift
- Validate warning alert system
- Demonstrate "attention needed" monitoring state

**Characteristics**:
- Noticeable but not critical feature distribution changes
- Some features show elevated PSI scores
- Suitable for showing operational response to drift

**Contains**: users.csv, devices.csv, trades.csv, withdrawals.csv

**⚠️ DO NOT DELETE** - Required for warning drift demonstration

---

### v3_controlled_drift - Controlled Drift Demo

**Purpose**: Demonstrate controlled drift detection with precise feature distribution changes

**Expected PSI**: 0.10 - 0.25 (Warning to Drift range)

**Usage**:
- Show monitoring detects controlled feature shifts
- Validate PSI sensitivity to specific feature changes
- Demonstrate intermediate drift state between subtle and realistic

**Characteristics**:
- Controlled feature distribution modifications
- Specific features targeted for drift injection
- Suitable for controlled PSI testing and validation

**Contains**: users.csv, devices.csv, trades.csv, withdrawals.csv

**⚠️ DO NOT DELETE** - Required for controlled drift demonstration

---

### v3_drift - Severe Drift Demo

**Purpose**: Demonstrate severe drift detection

**Expected PSI**: > 0.25 (Drift)

**Usage**:
- Show monitoring detects significant population change
- Validate severe drift alert system
- Demonstrate "retrain required" monitoring state

**Characteristics**:
- Major feature distribution shifts from baseline
- Multiple features exceed drift threshold
- Suitable for justifying model retraining

**Contains**: users.csv, devices.csv, trades.csv, withdrawals.csv

**⚠️ DO NOT DELETE** - Required for severe drift demonstration

---

### v4_demo_production - Production Validation Dataset

**Purpose**: Final production-like validation and end-to-end demonstration

**Usage**:
- Complete pipeline validation
- Signal attribution demonstration
- Risk event lifecycle testing
- Multi-signal fusion verification
- Production demo showcase

**Characteristics**:
- Production-like data quality and volume
- Realistic fraud pattern distribution
- Comprehensive signal coverage
- Full feature completeness

**Contains**: users.csv, devices.csv, trades.csv, withdrawals.csv

**⚠️ DO NOT DELETE** - Required for final validation and production demos

---

## Data Structure

All datasets follow the same schema:

- **users.csv**: User account information (user_id, country, kyc_level, account_created_time, vip_level)
- **devices.csv**: Device and login information (user_id, device_id, ip_address, location, browser_fingerprint, timestamps)
- **trades.csv**: Trading activity (user_id, trade_id, symbol, side, price, quantity, timestamp)
- **withdrawals.csv**: Withdrawal requests (user_id, withdraw_id, asset, amount, address, is_new_address, timestamp)

## Usage Notes

### For Model Training

```bash
# Train with v2_diverse dataset
python ml-models/training/train_risk_model.py --source csv --data-path test_data/v2_diverse
```

### For PSI Monitoring Demo

1. Train baseline with v2_diverse
2. Load v3_subtle_drift → shows Stable status
3. Load v3_realistic_drift → shows Warning status
4. Load v3_drift → shows Drift status

### For Production Demo

Use v4_demo_production dataset to showcase:
- Complete risk detection workflow
- Multi-signal attribution
- Risk event traceability
- Investigation queue functionality

## Data Retention

⚠️ **All datasets in this directory are project assets and must be preserved.**

Do not add this directory to .gitignore.
