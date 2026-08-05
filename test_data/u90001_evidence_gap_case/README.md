# U90001 Evidence Gap Test Case

## Purpose

This dataset tests the "Missing Info to Confirm" module in the Risk Investigation workflow.

It creates a realistic investigation case (U90001) that:
- Generates MEDIUM/HIGH risk through the normal pipeline
- Has intentional evidence gaps
- Appears in Investigation Queue
- Triggers Missing Info to Confirm display

## Files

- `users.csv` - U90001 with NULL account_created_time and kyc_level
- `devices.csv` - Header only (no device records for U90001)
- `trades.csv` - 60 trades (30 BUY, 30 SELL) within 24h
- `withdrawals.csv` - 7 withdrawals with is_new_address=true within 24h

## Expected Results

### Risk Profile
- Risk Level: MEDIUM or higher
- Risk Drivers: High Trading Frequency, Opposite Trading Pattern, Withdrawal Risk

### Missing Info to Confirm
```
[
  "Account age and onboarding date",      // NULL account_created_time
  "Device fingerprint and IP history",    // No device records
  "Customer KYC verification status"      // NULL kyc_level
]
```

NOT included (because data exists):
- "Transaction history"  // trades.csv has 60 records

## Usage

1. Upload via CSV upload workflow (`POST /api/pipeline/upload`)
2. Run pipeline
3. Verify U90001 appears in Investigation Queue
4. Check Missing Info to Confirm section displays expected gaps
