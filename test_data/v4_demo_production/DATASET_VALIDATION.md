# Demo Production Dataset v4 - Validation Summary

## Dataset Information

- **Purpose**: Product demonstration for Risk Intelligence Platform
- **Generation Date**: 2026-07-21 21:17:50
- **Random Seed**: 20260721

## Dataset Size

| File | Records |
|------|--------|
| users.csv | 2,000 |
| devices.csv | 2,000 |
| trades.csv | 82,051 |
| withdrawals.csv | 6,687 |

## Expected Risk Distribution

| Risk Level | Count | Percentage | Score Range |
|------------|-------|------------|-------------|
| Low | 1,200 | 60% | 10-40 |
| Medium | 500 | 25% | 40-70 |
| High | 220 | 11% | 70-90 |
| Critical | 80 | 4% | 90-100 |

## Fraud Patterns Generated

### 1. Account Takeover / Fraud Rings (Critical)
- **6 fraud rings** with ~12 members each
- Shared devices within rings
- Young accounts (5-30 days)
- High withdrawal frequency
- Multiple IPs per ring

### 2. Trading Manipulation (High/Critical)
- High trade frequency (80-120 trades/24h)
- High opposite trade ratio (>50%)
- Concentrated on 3 symbols
- Alternating BUY/SELL patterns

### 3. Withdrawal Risk (High)
- High withdrawal frequency (10-18/24h)
- Large withdrawal amounts
- Mix of new addresses

## Expected ML Metrics

- **Overall AUC**: 0.85-0.92
- **Overall KS**: 0.55-0.70
- **PSI vs v2 baseline**: 0.05-0.20 (stable)

## Feature Distribution Notes

Features are distributed close to v2 training baseline:
- `trade_frequency_24h`: Bimodal (normal users 5-20, manipulation 40-120)
- `opposite_trade_ratio`: Normal users 0.1-0.3, manipulation 0.5-0.7
- `withdrawal_frequency_24h`: Normal users 0-3, risk users 8-18
- `shared_device_count`: Fraud rings 3-12, others 0-1
- `account_age_days`: Wide distribution (5-365 days)

## Investigation Queue Validation

After uploading and running pipeline, verify:

```sql
-- Check risk level distribution
SELECT risk_level, COUNT(*) as count
FROM risk_events
GROUP BY risk_level
ORDER BY 
  CASE risk_level
    WHEN 'CRITICAL' THEN 1
    WHEN 'HIGH' THEN 2
    WHEN 'MEDIUM' THEN 3
    WHEN 'LOW' THEN 4
  END;
```

## Critical User Examples

Expected critical users should have:
- ML score >= 80 (high frequency trading)
- Rule score >= 40 (new account + suspicious patterns)
- Graph score >= 20 (fraud ring membership)
- Final score >= 90

