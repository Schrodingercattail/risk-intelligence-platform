# Screenshot Demo Dataset

**Version:** 1.0
**Created:** 2026-08-05
**Purpose:** README screenshots and frontend demonstrations

---

## Dataset Overview

This dataset combines the production demo data (v4_demo_production) with a special investigation case (U90001) to create a comprehensive demonstration dataset suitable for:

- README screenshots
- Investigation page demonstrations
- Pipeline dashboard demonstrations
- Risk queue demonstrations
- Model monitoring demonstrations

---

## Dataset Composition

### Source Datasets

1. **v4_demo_production** (2000 users)
   - Normal users with complete evidence
   - Diverse risk levels (LOW, MEDIUM, HIGH, CRITICAL)
   - Device fingerprints and IP history
   - Trading and withdrawal patterns

2. **u90001_evidence_gap_case** (1 user)
   - Special investigation case U90001
   - High-risk user with missing evidence
   - No device records
   - No account age or KYC information

### Final Dataset

| File | Records | Description |
|------|---------|-------------|
| users.csv | 2001 | 2000 normal users + U90001 |
| devices.csv | 2000 | Device records for normal users only (U90001 has none) |
| trades.csv | 82111 | Trading records for all users |
| withdrawals.csv | 6694 | Withdrawal records for all users |

---

## U90001 Investigation Case

### Case Characteristics

U90001 is designed as a clear suspicious case with **missing investigation evidence**:

**User Profile:**
- **Country:** US
- **KYC Level:** Missing
- **Account Created:** Missing
- **VIP Level:** Missing

**Trading Behavior:**
- **60 trade records** with high-frequency pattern
- Opposite trading behavior (BUY followed by SELL)
- Multiple symbols (BTC, ETH)
- Concentrated timing pattern

**Withdrawal Behavior:**
- **7 withdrawal records**
- All to new addresses (is_new_address = True)
- Multiple withdrawals in short time period
- BTC asset only

**Evidence Gap:**
- **NO device records** (intentionally missing)
- NO IP history
- NO account age information
- NO KYC verification status

### Expected Investigation Display

When viewing U90001 in the Investigation page, the **Missing Information** panel should display:

```
Missing Information:
• Device fingerprint and IP history
• Account age and onboarding date
• Customer KYC verification status
```

This demonstrates the platform's evidence completeness checking capability.

---

## Risk Level Distribution

The dataset maintains diverse risk levels for realistic screenshots:

- **LOW:** Normal users with typical behavior patterns
- **MEDIUM:** Users with moderate risk indicators
- **HIGH:** Users with significant risk signals
- **CRITICAL:** U90001 (high-frequency trading + evidence gaps)

---

## Evidence Completeness Examples

### Complete Evidence (Normal Users)

Most users in the dataset have:
- Device fingerprint and IP history
- Account age from account_created_time
- KYC level information
- Transaction history
- Withdrawal patterns

### Missing Evidence (U90001)

U90001 demonstrates the platform's ability to detect investigation readiness gaps:
- No device/IP evidence
- No account age
- No KYC verification
- High-risk behavior requires investigation despite missing evidence

---

## Pipeline Compatibility

This dataset is designed to successfully run through the complete pipeline:

### Upload Validation

✅ All four required CSV files present
✅ Valid CSV format
✅ Correct column headers
✅ Foreign key integrity maintained

### Pipeline Stages

✅ **Data Validation:** Passes validation checks
✅ **Feature Engineering:** 13 features computed for all users
✅ **Rule Scoring:** Rule-based signals generated
✅ **ML Scoring:** LightGBM model produces risk scores
✅ **Graph Analysis:** Network clusters detected (U90001 will have graph_score = 0)

### Expected Behavior

**U90001 Risk Profile:**
- **ML Score:** Elevated due to high trading frequency
- **Rule Score:** Elevated due to withdrawal patterns
- **Graph Score:** 0 (no device/network evidence)
- **Final Risk Level:** HIGH or CRITICAL (depending on weighted combination)

**Graph Analysis:**
- Completes successfully (not PENDING)
- Detects clusters among normal users
- U90001 has no cluster membership (no devices to share)

---

## Model Monitoring Suitability

The dataset preserves sufficient user diversity for meaningful model monitoring:

- **User Count:** 2001 users (enough for statistical analysis)
- **Feature Distribution:** Maintains v4 diversity
- **Risk Distribution:** All risk levels represented
- **PSI Drift:** Baseline comparison remains meaningful

---

## File Structure

```
test_data/screenshot_demo_dataset/
├── README.md
├── users.csv
├── devices.csv
├── trades.csv
└── withdrawals.csv
```

---

## Usage Instructions

### For README Screenshots

1. Start the platform: `docker-compose up`
2. Upload all four CSV files via Data Pipeline page
3. Run the pipeline: `POST /api/pipeline/run`
4. Navigate to pages for screenshots:
   - Risk Command Center
   - Investigation Queue
   - Investigation Case Detail (select U90001)
   - Model Monitoring

### For Investigation Demo

1. Complete pipeline upload and run
2. Navigate to Investigation page
3. Find U90001 in the investigation queue
4. Click to view case detail
5. Observe missing information panel
6. Review risk evidence and signals

### For Evidence Completeness Demo

1. View U90001 case detail
2. Check "Missing Information" section
3. Compare with normal user cases
4. Observe evidence completeness differences

---

## Validation Results

### Foreign Key Integrity

- ✅ All trades.user_id exist in users.csv
- ✅ All withdrawals.user_id exist in users.csv
- ✅ All devices.user_id exist in users.csv
- ✅ No orphan records

### Pipeline Compatibility

- ✅ Upload validation passes
- ✅ Feature engineering completes
- ✅ Rule scoring completes
- ✅ ML scoring completes
- ✅ Graph analysis completes

### Evidence Completeness

- ✅ U90001 missing: Device/IP history
- ✅ U90001 missing: Account age
- ✅ U90001 missing: KYC verification
- ✅ Normal users: Complete evidence

---

## Design Decisions

### Preserved U90001 Characteristics

The dataset maintains U90001 as a clear suspicious case:

1. **No Device Records**
   - devices.csv contains only v4 device records
   - U90001 intentionally has no devices
   - Preserves evidence gap for demonstration

2. **High-Frequency Trading**
   - 60 trade records concentrated in one day
   - Opposite trading pattern (BUY → SELL)
   - Multiple symbols (BTC, ETH)

3. **Multiple Withdrawals**
   - 7 withdrawal records to new addresses
   - All withdrawals on same day
   - Demonstrates withdrawal pattern risk

### Data Integrity

The dataset ensures:
- No orphan records (all foreign keys valid)
- Consistent timestamps within reasonable ranges
- Proper CSV formatting
- Pipeline compatibility

### Screenshot Suitability

The dataset provides:
- Diverse risk levels for realistic dashboard
- Clear investigation case (U90001)
- Meaningful model monitoring metrics
- Complete evidence for most users
- Intentional evidence gaps for demonstration

---

## Comparison with Source Datasets

### v4_demo_production

| Aspect | v4 | screenshot_demo |
|--------|-----|-----------------|
| Users | 2000 | 2001 (+U90001) |
| Devices | 2000 | 2000 (no U90001 devices) |
| Trades | 82051 | 82111 (+60 U90001 trades) |
| Withdrawals | 6688 | 6694 (+7 U90001 withdrawals) |

### u90001_evidence_gap_case

The U90001 case is preserved with all key characteristics:
- Missing evidence (no devices, no account age, no KYC)
- High-frequency trading pattern
- Multiple withdrawals to new addresses
- Suspicious behavior indicators

---

## Future Extensions

This dataset can be extended with:
- Additional investigation cases with different evidence gaps
- Edge cases for testing validation logic
- Performance testing scenarios
- Model drift demonstration cases

---

## License

This dataset is part of the Risk Intelligence Platform and follows the same license terms.

---

## Contact

For questions or issues with this dataset, please refer to the main project repository.
