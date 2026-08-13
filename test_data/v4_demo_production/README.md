# Demo Production Dataset v4

## Purpose

This dataset is designed for **product demonstration** of the Risk Intelligence Platform. It simulates a realistic production environment with meaningful fraud patterns and stable monitoring metrics.

**Key Design Goal**: Showcase the platform's capabilities with realistic High/Critical risk cases while maintaining healthy PSI (0.05-0.20).

---

## ⚠️ `risk_analysis_results.csv` is a NON-AUTHORITATIVE snapshot — do not use as ground truth

`risk_analysis_results.csv` is a **frozen, one-time export** (dated 2026-07-21 in the
companion `CRITICAL_OVERRIDE_VERIFICATION_SUMMARY.md`), produced by a "Critical Override
Verification Script" that is **no longer in the repository**. No current script
regenerates it.

Its `graph_score` / `final_score` (and occasionally `ml_score`) **diverge from the
authoritative values in the live database**. Why: the runtime pipeline
(`risk_service._calculate_graph_score`) recomputes `graph_score` on every run from the
live cluster state (`AccountCluster.risk_score`, `member_count`, hub role), and
`final_score = 0.5·ml + 0.3·rule + 0.2·graph` inherits that drift. The snapshot even
disagrees with its own companion summary (which reports graph 88–92 for ring members
while the CSV shows ~57–60) and with the "expected score ranges" in this README.

**The only authoritative source of risk scores is the live database table `risk_events`**
— the same values the frontend displays and `/api/risk/explain` feeds to the LLM. Use
those, not this file, for any evaluation, verification, or comparison. See also the
companion warning `risk_analysis_results.NON_AUTHORITATIVE.md`.

---

## Dataset Overview

| File | Records | Description |
|------|---------|-------------|
| `users.csv` | 2,000 | User profile data |
| `devices.csv` | 2,000 | Device and login information |
| `trades.csv` | 82,051 | Trading transactions |
| `withdrawals.csv` | 6,687 | Withdrawal transactions |
| `risk_analysis_results.csv` | 2,000 | ⚠️ **Non-authoritative** one-time score export — see warning above. Do NOT use as ground truth; use live DB `risk_events`. |

---

## Risk Distribution

| Risk Level | Count | Percentage | Score Range | Detection Rate |
|------------|-------|------------|-------------|----------------|
| **Low** | 1,200 | 60% | 10-40 | Should not trigger |
| **Medium** | 500 | 25% | 40-70 | Partial detection |
| **High** | 220 | 11% | 70-90 | Clear detection |
| **Critical** | 80 | 4% | 90-100 | Immediate action |

---

## Fraud Patterns

### Pattern 1: Account Takeover / Fraud Rings (Critical)

**Characteristics:**
- 6 fraud rings with ~10 members each
- Shared devices within ring members
- Young accounts (5-30 days old)
- High withdrawal frequency (5-10 per day)
- Multiple IPs from same subnet (proxy usage)

**Detection Signals:**
- High ML score (60-90 trades/24h)
- High Rule score (new account + high activity)
- High Graph score (cluster membership 5-12)

**Example User IDs:** U00001-U00010 (Ring 1), U00011-U00020 (Ring 2), etc.

---

### Pattern 2: Trading Manipulation (High/Critical)

**Characteristics:**
- Very high trade frequency (100-150 trades/24h)
- High opposite trade ratio (>50%)
- Concentrated on 2-3 symbols
- Alternating BUY/SELL patterns (wash trading)

**Detection Signals:**
- High ML score (frequency + opposite ratio)
- High Rule score (opposite trade ratio > 0.4)
- Low Graph score (unique device)

**Expected Count:** ~130 users

---

### Pattern 3: Withdrawal Risk (High)

**Characteristics:**
- Established accounts (60-180 days)
- High withdrawal frequency (10-18 per day)
- Large withdrawal amounts (1-8 per transaction)
- Mix of new and existing addresses

**Detection Signals:**
- Moderate ML score (normal trading)
- High Rule score (withdrawal frequency)
- Low Graph score (unique device)

**Expected Count:** ~110 users

---

## Feature Distribution

### Trading Features

| Feature | Normal Users | Risk Users | Critical |
|---------|--------------|------------|----------|
| `trade_frequency_24h` | 5-20 | 25-60 | 60-150 |
| `opposite_trade_ratio` | 0.1-0.3 | 0.3-0.4 | 0.5-0.7 |
| `trade_volume_24h` | $500-$5k | $5k-$20k | $20k-$100k |

### Withdrawal Features

| Feature | Normal Users | Risk Users |
|---------|--------------|------------|
| `withdrawal_frequency_24h` | 0-3 | 8-18 |
| `withdrawal_volume_24h` | $0-$500 | $5k-$50k |
| `withdrawal_risk_score` | 0-0.3 | 0.5-1.0 |

### Network Features

| Feature | Normal Users | Risk Users | Fraud Rings |
|---------|--------------|------------|-------------|
| `shared_device_count` | 0-1 | 1-3 | 5-12 |
| `linked_account_count` | 0-1 | 2-5 | 5-12 |
| `unique_ip_count` | 1-2 | 1-3 | 1-3 |

---

## Expected ML Metrics

### After Running Pipeline

| Metric | Expected Range | Status |
|--------|----------------|--------|
| **Overall AUC** | 0.85-0.92 | Excellent |
| **Overall KS** | 0.55-0.70 | Good separation |
| **PSI (vs v2)** | 0.05-0.20 | Stable |

### Detection Attribution

Among detected users (~800 expected):

| Detection Method | Expected % | Count |
|------------------|------------|-------|
| ML Model Only | ~35% | ~280 |
| Rule Engine Only | ~20% | ~160 |
| Graph Network Only | ~15% | ~120 |
| Multi-Signal (2+) | ~30% | ~240 |

---

## Investigation Queue

### Expected Cases

| Risk Level | Cases | Recommended Action |
|------------|-------|-------------------|
| Critical | 80 | Immediate Investigation |
| High | 220 | Manual Review |
| Medium | 500 | Monitor |

### Critical Case Examples

After uploading and running pipeline, verify critical cases show:

```sql
-- Check critical users have expected risk factors
SELECT
    u.user_id,
    re.risk_score,
    re.ml_score,
    re.rule_score,
    re.graph_score,
    ft.trade_frequency_24h,
    ft.shared_device_count,
    ft.withdrawal_frequency_24h
FROM risk_events re
JOIN users u ON re.user_id = u.user_id
JOIN feature_table ft ON re.user_id = ft.user_id
WHERE re.risk_level = 'CRITICAL'
ORDER BY re.risk_score DESC
LIMIT 10;
```

Expected results for fraud ring members:
- `ml_score`: 70-90
- `rule_score`: 35-50
- `graph_score`: 20-40
- `shared_device_count`: 5-12

---

## Network Clusters

### Fraud Ring Structure

```
RING001 (10 members)
├── Shared Device: DEV8Z1O4A35QU
├── IP Range: 163.88.122.x
└── Members: U00001-U00010

RING002 (10 members)
├── Shared Device: DEV9X2Y5B28KP
├── IP Range: 45.73.201.x
└── Members: U00011-U00020
```

### Graph Analysis Expected Results

- **Total Clusters**: 6-8 fraud rings + some small groups
- **Largest Cluster**: 12 members
- **Cluster Risk Scores**: 60-90

---

## PSI Monitoring

### Expected Stability

This dataset is designed to show **healthy production monitoring**:

| Feature | PSI Range | Status |
|---------|-----------|--------|
| `trade_frequency_24h` | 0.08-0.18 | Stable |
| `opposite_trade_ratio` | 0.05-0.15 | Stable |
| `withdrawal_frequency_24h` | 0.06-0.20 | Stable |
| `account_age_days` | 0.05-0.12 | Stable |

**Overall PSI**: 0.05-0.20 (No significant drift expected)

---

## Usage Instructions

### 1. Upload Dataset

```bash
# Via Data Pipeline page
- Upload users.csv
- Upload devices.csv
- Upload trades.csv
- Upload withdrawals.csv
```

### 2. Run Pipeline

- Click "Run Risk Analysis Pipeline"
- Wait for completion (~30-60 seconds)

### 3. Verify Results

Check **Risk Command Center** for:
- Executive Risk Summary metrics
- Risk Level Composition chart
- Risk Score Analytics
- Detection Intelligence breakdown
- Investigation Queue with meaningful cases

### 4. Verify Model Monitoring

Check **Model Monitoring** page for:
- PSI metrics in stable range (0.05-0.20)
- Feature distributions
- No critical drift alerts

---

## Comparison with Previous Datasets

| Dataset | Purpose | PSI | Risk Cases |
|---------|---------|-----|------------|
| v2_diverse | Training baseline | N/A | Balanced |
| v3_* | PSI drift testing | 0.2-0.8 | Extreme |
| **v4_demo_production** | **Product demo** | **0.05-0.20** | **Meaningful** |

---

## Technical Notes

### Random Seed
- **Seed**: 20260721
- Ensures reproducible results

### Time Range
- **Account Creation**: 2026-06-24 to 2026-07-16
- **Activity**: Concentrated in last 24 hours for realistic monitoring

### Asset Prices (2025 levels)
- BTC: ~$65,000
- ETH: ~$3,500
- SOL: ~$145
- BNB: ~$590

---

## Validation Checklist

After uploading and running pipeline:

- [ ] Risk distribution matches expected (Low 60%, Medium 25%, High 11%, Critical 4%)
- [ ] AUC > 0.85
- [ ] KS > 0.55
- [ ] Overall PSI < 0.20
- [ ] Investigation Queue contains meaningful High/Critical cases
- [ ] Detection Attribution shows diverse patterns
- [ ] Network Clusters detect fraud rings
- [ ] Model explanations show meaningful feature contributions

---

## Contact

Generated for Risk Intelligence Platform demonstration.
