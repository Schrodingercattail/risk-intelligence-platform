# Explanation Evaluation Summary Template

This template provides a structure for aggregating and analyzing evaluation results. Copy this file and customize with your actual evaluation data.

---

## Evaluation Metadata

| Field | Value |
|-------|-------|
| **Evaluation Date** | YYYY-MM-DD |
| **Evaluator(s)** | Names |
| **Total Cases Evaluated** | N |
| **Risk Level Distribution** | CRITICAL: N, HIGH: N, MEDIUM: N |
| **Explanation Mode** | LLM / MODEL_FALLBACK / Mixed |
| **Pipeline Run ID** | run_YYYYMMDD |

---

## Overall Quality Summary

### Quality Distribution

| Quality Level | Count | Percentage |
|---------------|-------|------------|
| Excellent (4-5 avg, PASS) | N | NN% |
| Good (≥3.5 avg, PASS) | N | NN% |
| Fair (≥2.5 avg, PASS) | N | NN% |
| Poor (<2.5 avg OR FAIL) | N | NN% |

### Pass/Fail Summary

| Dimension | Pass | Fail | Pass Rate |
|-----------|------|------|-----------|
| Sensitivity & Privacy | N | N | NN% |

---

## Dimension Scoring Summary

### How to Compute Averages

For each dimension (Accuracy, Readability, Actionability, Citation Quality):

```
Average = (Sum of all scores for that dimension) / (Number of evaluated cases)
```

### Dimension Results

| Dimension | Average | Std Dev | Min | Max |
|-----------|---------|--------|-----|-----|
| Accuracy & Groundedness | X.X | X.X | 1 | 5 |
| Readability | X.X | X.X | 1 | 5 |
| Actionability | X.X | X.X | 1 | 5 |
| Citation Quality | X.X | X.X | 1 | 5 |

### Dimension Breakdown by Risk Level

| Dimension | CRITICAL Avg | HIGH Avg | MEDIUM Avg |
|-----------|-------------|----------|------------|
| Accuracy | X.X | X.X | X.X |
| Readability | X.X | X.X | X.X |
| Actionability | X.X | X.X | X.X |
| Citation Quality | X.X | X.X | X.X |

---

## Failure Code Analysis

### Top Failure Codes

| Failure Code | Count | Percentage | Description |
|--------------|-------|------------|-------------|
| A2 | N | NN% | Score Mismatch |
| D1 | N | NN% | Irrelevant Citation |
| E1 | N | NN% | Sensitive Leakage |
| C1 | N | NN% | Vague Action |

**Total failures recorded:** N (some cases may have multiple failure codes)

### Failure Code Distribution by Category

| Category | Total Failures | Most Common Code |
|----------|-----------------|-------------------|
| A (Accuracy) | N | A2 |
| B (Readability) | N | B2 |
| C (Actionability) | N | C1 |
| D (Citations) | N | D1 |
| E (Privacy) | N | E1 |

### Failure Patterns

**Systemic Issues Detected:**
- Pattern 1: Description of pattern observed
- Pattern 2: Description of pattern observed

**Example Analysis:**
- High A2 (Score Mismatch) → Template or data sync issues
- High E1 (Sensitive Leakage) → Redaction configuration problems

---

## Quality Trends by Risk Level

### CRITICAL Cases (N total)

| Metric | Value |
|--------|-------|
| Average Overall Score | X.X / 5.0 |
| Pass Rate | NN% |
| Most Common Failure | Code: XX (N occurrences) |

**Key Findings:**
- Bullet point on CRITICAL case quality

### HIGH Cases (N total)

| Metric | Value |
|--------|-------|
| Average Overall Score | X.X / 5.0 |
| Pass Rate | NN% |
| Most Common Failure | Code: XX (N occurrences) |

**Key Findings:**
- Bullet point on HIGH case quality

### MEDIUM Cases (N total)

| Metric | Value |
|--------|-------|
| Average Overall Score | X.X / 5.0 |
| Pass Rate | NN% |
| Most Common Failure | Code: XX (N occurrences) |

**Key Findings:**
- Bullet point on MEDIUM case quality

---

## Comparison: LLM vs Model-Based

### Mode Performance (if mixed evaluation)

| Explanation Mode | Count | Avg Score | Most Common Failure |
|------------------|-------|-----------|---------------------|
| LLM | N | X.X | Code: XX |
| MODEL_FALLBACK | N | X.X | Code: XX |

**Key Findings:**
- Bullet point on mode differences

---

## Action Plan

### Priority Issues (Critical/High Severity)

| Issue | Failure Code | Affected Cases | Action | Owner | Target Date |
|-------|--------------|----------------|--------|-------|-------------|
| Issue description | XX | N | Action plan | Name | YYYY-MM-DD |

### Improvement Recommendations

**Short-term (1-2 weeks):**
1. Recommendation for quick wins
2. Recommendation for quick wins

**Medium-term (1-2 months):**
1. Recommendation for structural improvements
2. Recommendation for structural improvements

**Long-term (3+ months):**
1. Recommendation for systemic changes
2. Recommendation for systemic changes

---

## Appendix: Evaluation Notes

### Case-by-Case Highlights

**Positive Examples:**
- user_XXX: Description of what worked well
- user_XXX: Description of what worked well

**Problematic Examples:**
- user_XXX: Description of issue (Code: XX)
- user_XXX: Description of issue (Code: XX)

### Evaluator Feedback

**General Observations:**
- Free text notes on overall evaluation experience
- Suggestions for improving evaluation process

**Rubric Feedback:**
- Any clarifications needed in rubric definitions
- Suggestions for new failure codes

---

## Related Documents

- [Evaluation Rubric](explain_eval_rubric.md) — Detailed scoring criteria
- [Failure Taxonomy](explain_failure_taxonomy.md) — Complete failure code definitions
- [Export Script](../../tools/export_explain_eval_set.py) — How to generate case sets
