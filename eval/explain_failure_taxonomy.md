# Explanation Failure Taxonomy

This document defines failure codes for categorizing explanation quality issues. Use these codes when recording failures during evaluation.

---

## Failure Code Structure

Each failure code has a **category letter** and **numeric identifier**:

- **A**: Accuracy & Groundedness failures
- **B**: Readability failures
- **C**: Actionability failures
- **D**: Citation Quality failures
- **E**: Sensitivity & Privacy failures

---

## Category A: Accuracy & Groundedness Failures

| Code | Name | Definition | Example |
|------|------|------------|---------|
| **A1** | Hallucination | Completely fabricated content not supported by any data | Claims account has "5 chargebacks" when no chargeback data exists |
| **A2** | Score Mismatch | Reported scores don't match actual risk event data | Summary says "risk score 85" but actual is 72 |
| **A3** | Level Mismatch | Stated risk level doesn't match actual | Says "HIGH risk" but actual is "MEDIUM" |
| **A4** | False Attribution | Claims detection method that wasn't used | Says "Graph Network detected this" but graph_score=0 |
| **A5** | Factor Fabrication | Inventors risk factors not in data | Lists "unusual withdrawal pattern" when no withdrawal data |
| **A6** | Contradiction | Explanation contradicts itself | Says "ML score 85" then later "ML score 15" |

---

## Category B: Readability Failures

| Code | Name | Definition | Example |
|------|------|------------|---------|
| **B1** | Unreadable Text | Text is grammatically incoherent or nonsensical | "Risk the account score due to ML high rule graph" |
| **B2** | Excessive Redundancy | Repetitive content without added value | Repeats "ML Signal Score: 85" in 5 different places |
| **B3** | Jargon Overload | Excessive technical terms without explanation | "Feature importance weights indicate high Gini impurity" |
| **B4** | Poor Structure | Disorganized content; difficult to follow | Key findings buried in paragraph; no clear sections |
| **B5** | Vague Phrasing | Language so generic it conveys nothing | "The account shows some activity that might be concerning" |
| **B6** | Contradictory Statements | Explanation contradicts itself | "Action required: None" but also "immediate review needed" |

---

## Category C: Actionability Failures

| Code | Name | Definition | Example |
|------|------|------------|---------|
| **C1** | Vague Action | Recommended action is not specific | "Review the case" (no guidance on what to review) |
| **C2** | No Action | No recommended action provided | `recommended_action` field is empty or "N/A" |
| **C3** | Inappropriate Action | Action doesn't match risk level | CRITICAL case with "continue monitoring" |
| **C4** | Contradictory Action | Action conflicts with findings | Says "freeze account" but evidence shows low risk |
| **C5** | Impossible Action | Action is not operationally feasible | "Contact user via unlisted phone number" |
| **C6** | Missing Priority | No indication of urgency for high-severity cases | CRITICAL case with no urgency indication |

---

## Category D: Citation Quality Failures

| Code | Name | Definition | Example |
|------|------|------------|---------|
| **D1** | Irrelevant Citation | Cited policy has no connection to case | Cites "crypto AML policy" for account age violation |
| **D2** | Missing Citation | Finding mentions policy but no citation included | References "policy states X" but no `[n]` mark |
| **D3** | Fabricated Citation | Citation to non-existent policy | Cites "Policy Section 9.3" when doc doesn't exist |
| **D4** | Mismatched Citation | Citation mark doesn't match citation list | Text has `[1][2]` but only 1 citation in list |
| **D5** | Inaccurate Quote | Cited quote doesn't match policy text | Quote shows "require freeze" but policy says "may review" |
| **D6** | Excessive Citations | Too many citations dilute relevance | 10+ citations for simple velocity case |

---

## Category E: Sensitivity & Privacy Failures

| Code | Name | Definition | Example |
|------|------|------------|---------|
| **E1** | Sensitive Leakage | PII or sensitive data exposed in explanation | "User connected from IP 192.168.1.1" |
| **E2** | User ID Exposure | Full user ID exposed when redaction expected | "User user_12345678 shows..." (when redaction enabled) |
| **E3** | Internal ID Exposure | Database IDs or internal identifiers exposed | "account_id: 45923 triggered alert" |
| **E4** | Financial Detail Leakage | Specific transaction amounts exposed | "Transferred exactly $8,234.56 to wallet X" |
| **E5** | Location Granularity | Overly specific location information | "User logged in from Building 4, Floor 3" |

---

## How to Use Failure Codes

### Recording Failures

When evaluating explanations, record failure codes in `explain_eval_results.csv`:

```csv
failure_codes
A2;D1
C1
E1
B2;B4
```

### Multiple Failure Codes

An explanation can have multiple failure codes (semicolon-separated):

- **Primary failure:** The most severe issue affecting quality
- **Secondary failures:** Additional issues that compound the problem

### Failure Severity

| Severity | Codes | Impact |
|----------|-------|--------|
| **Critical** | E1-E5, A1 | Security/data breach risk; immediate attention |
| **High** | A2-A4, C2-C3 | Misleading investigators; workflow impact |
| **Medium** | D1-D3, C1, B1 | Usability issues; reduced efficiency |
| **Low** | B2-B6, D4-D6, A5-A6 | Minor quality issues |

### Failure Patterns for Investigation

Common patterns that indicate systemic issues:

| Pattern | Likely Root Cause |
|---------|-------------------|
| Many A2/A3 | Template or data sync issues |
| Many E1/E2 | Redaction configuration problems |
| Many D2/D4 | Citation parsing bugs |
| Many C1/C3 | Action recommendation logic gaps |
| Many B2/B4 | LLM or template wording issues |

---

## Related Documents

- [Evaluation Rubric](explain_eval_rubric.md) — Scoring dimensions and criteria
- [Evaluation Summary Template](explain_eval_summary.md) — How to aggregate and analyze results
