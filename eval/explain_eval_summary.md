# Explanation Evaluation Summary — v1.1.0

Evaluation report for the Risk Intelligence Platform's explainability system. This document aggregates manual evaluation results for the `/api/risk/explain` endpoint.

---

## Evaluation Metadata

| Field | Value |
|-------|-------|
| **Evaluation Date** | 2026-08-03 |
| **Evaluator(s)** | Manual evaluation |
| **Total Cases Evaluated** | 20 |
| **Risk Level Distribution** | CRITICAL: 6, HIGH: 11, MEDIUM: 3 |
| **Explanation Mode** | MODEL_FALLBACK |
| **Pipeline Run ID** | run_20260722_093824_114fa3d9 |

---

## Overall Quality Summary

### Executive Summary

The explainability system demonstrates strong performance on factual grounding, schema compliance, and privacy protection. All 20 cases passed sensitivity & privacy checks and response structure validation. However, citation quality emerges as the primary limitation — 95% of cases contained citation quality issues, primarily D1 irrelevant citations and D6 excessive citations, indicating systemic issues in policy citation relevance, specificity, and ranking, indicating systemic issues in policy citation relevance and specificity.

### Quality Distribution

| Quality Level | Count | Percentage |
|---------------|-------|------------|
| Excellent (4-5 avg, PASS) | 1 | 5% |
| Good (≥3.5 avg, PASS) | 19 | 95% |
| Fair (≥2.5 avg, PASS) | 0 | 0% |
| Poor (<2.5 avg OR FAIL) | 0 | 0% |

### Pass/Fail Summary

| Dimension | Pass | Fail | Pass Rate |
|-----------|------|------|-----------|
| Sensitivity & Privacy | 20 | 0 | 100% |
| Response Structure Validity | 20 | 0 | 100% |

---

## Dimension Scoring Summary

### Dimension Results

| Dimension | Average | Std Dev | Min | Max |
|-----------|---------|--------|-----|-----|
| Accuracy & Groundedness | 4.0 | 0.0 | 4 | 4 |
| Readability | 4.0 | 0.0 | 4 | 4 |
| Actionability | 3.3 | 0.46 | 3 | 4 |
| Citation Quality | 2.1 | 0.44 | 2 | 4 |

**Key Observations:**
- **Accuracy & Groundedness**: Perfect consistency across all cases. All claims are grounded in risk event data; scores match exactly; findings align with actual factors.
- **Readability**: All explanations are clear, professional, and logically structured. No jargon overload or ambiguity.
- **Actionability**: Slightly lower average due to generic recommended actions. Most cases receive "Manual Review" without specific investigative guidance.
- **Citation Quality**: Major weakness. Citations often irrelevant to actual risk evidence (e.g., network policies cited without graph signals).

### Dimension Breakdown by Risk Level

| Dimension | HIGH Avg |
|-----------|----------|
| Accuracy & Groundedness | 4.0 |
| Readability | 4.0 |
| Actionability | 3.3 |
| Citation Quality | 2.1 |

*All evaluated cases were HIGH risk level.*

---

## Failure Code Analysis

### Top Failure Codes

| Failure Code | Count | Percentage | Description |
|--------------|-------|------------|-------------|
| D1 | 19 | 95% | Irrelevant Citation |
| D6 | 14 | 70% | Excessive Citations |
| B2 | 5 | 25% | Excessive Redundancy |
| B3 | 5 | 25% | Jargon Overload |

**Total failures recorded:** 43 (some cases have multiple failure codes)

### Failure Code Distribution by Category

| Category | Total Failures | Most Common Code |
|----------|-----------------|-------------------|
| A (Accuracy) | 0 | — |
| B (Readability) | 10 | B2, B3 |
| C (Actionability) | 0 | — |
| D (Citations) | 33 | D1 |
| E (Privacy) | 0 | — |

### Failure Pattern Analysis

**Pattern 1: Evidence-Citation Alignment Gap**

The current retrieval mechanism selects policies based primarily on semantic similarity to the full explanation context. It does not sufficiently validate whether the cited policy is supported by actual risk evidence present in the case.

*Example:*
- Finding states "shared device/IP links" but device/IP evidence may be absent
- Network/risky cluster citations appear without corresponding graph signals
- High trading frequency citations should reference behavior/velocity policies, not network/device policies

**Root Cause:** RAG retrieval operates on query similarity without evidence-aware filtering.

**Pattern 2: Excessive Citations**

Multiple citations are attached to simple findings, creating citation bloat that dilutes relevance and overwhelms investigators.

*Example:*
- A single key finding may reference 5+ citations
- Many citations are tangentially related rather than directly supportive
- Retrieval optimization favors recall over precision

**Impact:** Investigators must parse excessive citations to identify truly relevant policy references, reducing investigation efficiency.

**Pattern 3: Generic Investigation Policy Citations**

KYC/CDD policies are frequently cited but often do not directly explain *why* the account received a specific risk score. These policies are more relevant to investigation workflow procedures than to risk attribution.

*Example:*
- KYC requirements cited for ML/rule score explanations
- General investigation SOPs cited without connecting to specific risk signals
- CDD tiers referenced without clear link to case evidence

**Impact:** Citations feel procedural rather than explanatory, reducing their value for risk investigators seeking to understand score rationale.

---

## Quality Trends by Risk Level

### Summary by Risk Level

| Risk Level | Cases | Avg Score | Pass Rate | Most Common Failure |
|------------|-------|-----------|-----------|---------------------|
| CRITICAL | 6 | 3.35 / 5.0 | 100% | D1 (Irrelevant Citation) |
| HIGH | 11 | 3.35 / 5.0 | 100% | D1 (Irrelevant Citation) |
| MEDIUM | 3 | 3.35 / 5.0 | 100% | D1 (Irrelevant Citation) |

**Key Findings:**
- Citation grounding was the primary issue across all risk levels — policies cited often lacked supporting evidence in the case
- Strong factual accuracy and readability maintained consistently regardless of risk severity
- No privacy or structure violations detected in any risk level

**Note:** No significant quality difference was observed across risk levels in this evaluation sample. The small sample size (3 MEDIUM, 6 CRITICAL) limits statistical conclusions about risk-level performance variation.

---

## Comparison: LLM vs Model-Based

### Mode Performance

| Explanation Mode | Count | Avg Score | Most Common Failure |
|------------------|-------|-----------|---------------------|
| LLM | 0 | — | — |
| MODEL_FALLBACK | 20 | 3.35 | D1 (Irrelevant Citation) |

**Key Findings:**
- All evaluated cases used MODEL_FALLBACK mode
- Performance is consistent across the evaluated dataset
- No LLM-specific issues were observed in this evaluation

---

## Action Plan

### Priority Issues (Critical/High Severity)

| Issue | Failure Code | Affected Cases | Action | Owner | Target Date |
|-------|--------------|----------------|--------|-------|-------------|
| Evidence-citation misalignment | D1 | 19 (95%) | Implement evidence-aware citation validation | Backend Team | 2026-08-17 |
| Excessive citations | D6 | 14 (70%) | Add citation relevance ranking and deduplication | Backend Team | 2026-08-31 |

### Improvement Recommendations

**Short-term (1-2 weeks):**
1. **Add evidence-aware citation validation** — Filter citations based on presence of supporting evidence signals (e.g., only cite network policies if graph signals exist)
2. **Implement finding-level citation mapping** — Map specific findings to relevant policy sections rather than using blanket similarity matching
3. **Add citation count limits** — Cap citations per finding (e.g., max 2-3) to reduce bloat

**Medium-term (1-2 months):**
1. **Develop citation relevance ranking** — Implement scoring based on:
   - Evidence match score (does cited policy align with actual evidence?)
   - Policy relevance score (is policy directly applicable to risk type?)
   - Specificity score (avoid generic investigation policies for specific risks)
2. **Build automated citation evaluation** — Create regression tests for citation quality
3. **Add human feedback loop** — Allow investigators to flag irrelevant citations

**Long-term (3+ months):**
1. **Automated evaluation regression pipeline** — Continuous quality monitoring on new explanations
2. **Investigator feedback integration** — Collect and incorporate human feedback for explainability improvement
3. **Multi-stage retrieval refinement** — Implement retrieval + reranking pipeline for better citation precision

---

## Appendix: Evaluation Notes

### Case-by-Case Highlights

**Positive Examples:**
- Group 1 (1 case): Citations were well-related to network/device risk points; clear alignment between findings and cited policies

**Problematic Examples:**
- Group 2 (5 cases): Citation mapping not specific — device/IP policy cited for shared device findings; high trading frequency should cite behavior/velocity policy; KYC citations more appropriate for missing information investigation than risk score explanation
- Group 3 (14 cases): Citations generally policy-related but not always grounded in case evidence — network/risky cluster citations appear without graph signals; KYC citations generic and do not directly support ML/rule scores

### Evaluator Feedback

**General Observations:**
- The evaluation process was straightforward; rubric criteria were clear
- All cases passed privacy and structure validation, indicating good schema compliance
- Citation quality assessment required careful review of finding-to-citation alignment
- Actionability scoring benefited from understanding investigation workflow context

**Rubric Feedback:**
- No clarifications needed in current rubric definitions
- Failure codes adequately cover observed issues
- Consider adding specific failure code for "generic investigation citation" in future rubric versions

---

## Related Documents

- [Evaluation Rubric](explain_eval_rubric.md) — Detailed scoring criteria
- [Failure Taxonomy](explain_failure_taxonomy.md) — Complete failure code definitions
- [Export Script](../../tools/export_explain_eval_set.py) — How to generate case sets
