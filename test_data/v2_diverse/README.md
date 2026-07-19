# Diverse Detection Attribution Dataset (v2_diverse)

## Overview

This dataset is designed for regression testing of the risk platform's detection attribution system. It produces diverse detection coverage patterns by creating different types of risk users that trigger specific combinations of detection methods.

**Location:** `test_data/v2_diverse/`

**Generated Date:** 2026-07-19

## Dataset Statistics

- **Total Users:** 2,000
- **Devices:** 2,000
- **Trades:** 38,482
- **Withdrawals:** 6,475

## Detection Attribution Thresholds (from config)

- **LightGBM:** `ml_score >= 10.0`
- **Rule Engine:** `rule_score >= 15.0`
- **Graph Network:** `graph_score >= 10.0`

## User Type Distribution

| User Type | Count | Percentage |
|-----------|-------|------------|
| Normal | 1,200 | 60% |
| ML-only Risk | 200 | 10% |
| Rule-only Risk | 200 | 10% |
| Graph-only Risk | 200 | 10% |
| Multi-signal Risk | 200 | 10% |

## Data Generation Strategy

### 1. Normal Users (60% - 1,200 users)

**Characteristics:**
- Established accounts (60-365 days old)
- Normal KYC levels (higher proportion of INTERMEDIATE/FULL)
- Low to moderate trading activity (2-10 trades)
- Low withdrawal frequency (0-3 withdrawals)
- Unique devices and IPs (no sharing)

**Expected Detection:**
- ML Score: < 10 (normal behavioral patterns)
- Rule Score: < 15 (no rule violations)
- Graph Score: 0 (no cluster membership)
- **Detection Methods:** None

---

### 2. ML-only Risk Users (10% - 200 users)

**Strategy:** Trigger ML pattern detection without rule violations or graph relationships.

**Characteristics:**
- New accounts (3-10 days old)
- **Very high trade frequency** (60-100 trades in recent days)
- Low opposite trade ratio (< 0.4) to avoid coordinated trading rule
- Unique devices (no sharing) to avoid graph detection
- Low withdrawal frequency (0-2) to avoid rule triggers
- High concentration of recent activity (within last 2 days)

**Expected Detection:**
- ML Score: >= 10 (high frequency trading pattern detected)
- Rule Score: < 15 (minimal rule triggers)
- Graph Score: 0 (no cluster membership)
- **Detection Methods:** LightGBM only

**Key Features Driving ML Score:**
- `trade_frequency_24h`: 60-100 (very high)
- `trade_frequency_7d`: 60-100
- `account_age_days`: 3-10 (new account)
- `active_days_count`: 2-3

---

### 3. Rule-only Risk Users (10% - 200 users)

**Strategy:** Trigger explicit rule violations without ML patterns or graph relationships.

**Characteristics:**
- **Very new accounts** (1-5 days old)
- Normal trade frequency (5-15 trades) to avoid ML detection
- **High withdrawal frequency** (8-15 withdrawals) to trigger withdrawal rules
- **First withdrawal to new address** (rule trigger)
- Large withdrawal amounts (2-10 units)
- Unique devices (no sharing) to avoid graph detection

**Expected Detection:**
- ML Score: < 10 (normal behavioral patterns)
- Rule Score: >= 15 (multiple rule violations)
- Graph Score: 0 (no cluster membership)
- **Detection Methods:** Rule Engine only

**Rules Triggered:**
- New account with high activity: +40 points
- High withdrawal frequency: +25 points
- First withdrawal to new address: +20 points

---

### 4. Graph-only Risk Users (10% - 200 users)

**Strategy:** Create network relationships without ML patterns or rule violations.

**Characteristics:**
- Normal account age (30-180 days)
- **Shared devices** with 5 users per cluster
- Shared IPs within clusters
- Low trade frequency (3-12 trades) to avoid ML detection
- Low withdrawal frequency (0-4 withdrawals) to avoid rule triggers
- All withdrawals to existing addresses (no new address flag)

**Expected Detection:**
- ML Score: < 10 (normal behavioral patterns)
- Rule Score: < 15 (minimal rule triggers)
- Graph Score: >= 10 (cluster membership)
- **Detection Methods:** Graph Network only

**Graph Detection Logic:**
- Cluster members trigger graph score via cluster membership
- `cluster.risk_score * 0.3` + `member_count * 5` + hub bonus
- 5-member clusters generate sufficient graph score

---

### 5. Multi-signal Risk Users (10% - 200 users)

**Strategy:** Create users that trigger all detection methods.

**Characteristics:**
- Newer accounts (5-20 days old)
- **High trade frequency** (40-80 trades) → ML trigger
- **High withdrawal frequency** (6-12 withdrawals) → Rule trigger
- **Shared devices** for subset → Graph trigger
- New address flags present

**Expected Detection:**
- ML Score: >= 10 (high frequency trading)
- Rule Score: >= 15 (withdrawal rules)
- Graph Score: >= 10 (cluster membership for subset)
- **Detection Methods:** LightGBM + Rule Engine (+ Graph Network if in cluster)

---

## Expected Detection Attribution Distribution

Based on the user type distribution and detection logic, the expected Detection Coverage for high-risk cases (HIGH + CRITICAL levels) should be approximately:

| Detection Method | Expected Coverage | Rationale |
|------------------|-------------------|-----------|
| LightGBM Model | ~66% | ML-only (200) + Multi-signal (200) = 400 out of 600 high-risk users |
| Rule Engine | ~66% | Rule-only (200) + Multi-signal (200) = 400 out of 600 high-risk users |
| Graph Network | ~33% | Graph-only (200) + Multi-signal subset (~100 with shared devices) = ~300 out of 600 |

**Note:** These percentages do NOT need to sum to 100%. A single user can be detected by multiple methods (especially multi-signal users).

## Expected Risk Level Distribution

| Risk Level | Expected Count | Percentage |
|------------|----------------|------------|
| LOW | ~1,400 | ~70% |
| MEDIUM | ~400 | ~20% |
| HIGH | ~180 | ~9% |
| CRITICAL | ~20 | ~1% |

## CSV File Structure

### users.csv
```csv
user_id,country,kyc_level,account_created_time,vip_level
U00001,US,NONE,2025-12-19 16:49:36,NORMAL
```

### devices.csv
```csv
user_id,device_id,ip_address,location,browser_fingerprint,first_seen,last_seen
U00001,DEVABCD123456,192.168.1.100,US,FPABCD1234567890,2025-12-19 10:00:00,2026-07-15 14:30:00
```

### trades.csv
```csv
trade_id,user_id,symbol,side,price,quantity,timestamp
T000001,U00001,BTC,BUY,45123.45,1.5,2026-07-18 10:30:00
```

### withdrawals.csv
```csv
withdraw_id,user_id,asset,amount,address,is_new_address,timestamp
W000001,U00001,BTC,1.5,0xabc123...,true,2026-07-18 11:00:00
```

## How to Use This Dataset

### Option 1: Manual Upload via UI
1. Navigate to Data Pipeline page
2. Select the 4 CSV files from `test_data/v2_diverse/`
3. Click "Upload Datasets"
4. Wait for pipeline processing
5. Check Detection Coverage chart on Risk Overview page

### Option 2: API Upload
```bash
# Using curl
curl -X POST "http://localhost:8000/api/pipeline/upload" \
  -F "users=@test_data/v2_diverse/users.csv" \
  -F "devices=@test_data/v2_diverse/devices.csv" \
  -F "trades=@test_data/v2_diverse/trades.csv" \
  -F "withdrawals=@test_data/v2_diverse/withdrawals.csv"

# Then run pipeline
curl -X POST "http://localhost:8000/api/pipeline/run" \
  -H "Content-Type: application/json" \
  -d '{"run_full_pipeline": true, "generate_risk_events": true}'
```

### Option 3: Python Script
```python
import requests

API_URL = "http://localhost:8000"

# Upload files
files = {
    'users': open('test_data/v2_diverse/users.csv', 'rb'),
    'devices': open('test_data/v2_diverse/devices.csv', 'rb'),
    'trades': open('test_data/v2_diverse/trades.csv', 'rb'),
    'withdrawals': open('test_data/v2_diverse/withdrawals.csv', 'rb'),
}
response = requests.post(f"{API_URL}/api/pipeline/upload", files=files)
print(response.json())

# Run pipeline
response = requests.post(f"{API_URL}/api/pipeline/run", json={
    "run_full_pipeline": True,
    "generate_risk_events": True
})
print(response.json())
```

## Validation Checklist

After uploading and processing this dataset, verify:

- [ ] Risk Overview shows ~2,000 analyzed users
- [ ] Risk Level Composition shows distribution close to expected
- [ ] Detection Coverage chart shows diverse attribution (not 100% across all methods)
- [ ] LightGBM Model detection rate ~66%
- [ ] Rule Engine detection rate ~66%
- [ ] Graph Network detection rate ~33%
- [ ] Investigation Queue contains mixed detection method cases
- [ ] Each detection method badge shows different combinations

## Important Notes

1. **No Code Changes Required**
   - This dataset works with existing detection logic
   - No thresholds, weights, or scoring logic modified
   - Only data generation patterns create diversity

2. **Realistic Patterns**
   - Each user type represents realistic fraud/risk patterns
   - ML-only users represent behavioral anomalies without obvious violations
   - Rule-only users represent clear violations without ML flagging
   - Graph-only users represent network-based risk
   - Multi-signal users represent complex, multi-faceted risk

3. **Detection Attribution Independence**
   - Methods are independent; a user can trigger multiple
   - Percentages reflect actual detection capability overlap
   - Chart should show meaningful diversity

## Generated By

`test_data/generate_diverse_dataset.py`

**Random Seed:** 20260719 (for reproducibility)

**Regeneration:**
```bash
python test_data/generate_diverse_dataset.py
```
