# LLM Explanation Quality — P1 Manual Evaluation Summary

> Scope: human evaluation of the 20 LLM-generated investigation explanations in
> `eval/llm_raw_explanations/`. This report aggregates the human ratings in
> `eval/llm_human_evaluation.csv`. **This version reflects the P1 cleanup pass**: human scores
> normalized to the integer rubric scale and failure codes re-audited against the taxonomy
> (see §3b). It does **not** modify the rubric, the taxonomy, the human notes, or the fallback
> artifacts. Every number is reproducible from the CSV using the rules in §3.

---

## 1. Evaluation setup

- **What was evaluated:** the `summary`, `key_findings`, `recommended_action`, and
  `citations` from the LLM explanation path (`/api/risk/explain`, `explanation_source = "LLM"`,
  `audience = investigator`) for 20 investigation cases.
- **Source files (used, not modified):**
  - Ratings: `eval/llm_human_evaluation.csv` (rating columns; LLM-output columns verbatim from
    JSON; ground-truth columns from the live DB).
  - Rubric: `eval/explain_eval_rubric.md` — four 1–5 dimensions (Accuracy & Groundedness,
    Readability, Actionability, Citation Quality) + Pass/Fail (Response Structure Validity,
    Sensitivity & Privacy).
  - Failure taxonomy: `eval/explain_failure_taxonomy.md` (A1–A6, B1–B6, C1–C6, D1–D6, E1–E5).
- **Baseline for comparison:** the earlier model-based (fallback) human evaluation in
  `eval/explain_eval_results.csv` / `eval/explain_eval_summary.md` (v1.1.0), same 20 `user_id`s.

---

## 2. Dataset composition

20 cases, keyed by `user_id`, identical to `eval/explain_eval_cases.csv` (no missing/duplicate
ids). Composition by authoritative DB `risk_events.risk_level`:

| Risk level | Cases | user_ids |
|---|---|---|
| CRITICAL | 6 | U00010, U00011, U00015, U00020, U00033, U00047 |
| HIGH | 11 | U00201, U00210, U00217, U00232, U00233, U00236, U00237, U00264, U00274, U00292, U00299 |
| MEDIUM | 3 | U00221, U00223, U00247 |

**Citations:** 13 cases carry policy citations (6 CRITICAL × 3, 7 HIGH/MEDIUM × 2); **7 cases
have zero citations** (U00210, U00223, U00236, U00237, U00247, U00274, U00299) →
`citation_quality_1_5 = N/A` for those. Citation-count distribution: `3 → 6, 2 → 7, 0 → 7`.

---

## 3. Scoring methodology (rules used — no silent normalization)

- **Pass rates** (Response Structure Validity, Sensitivity) = `count(pass) / 20`.
- **Dimension averages (Accuracy, Readability, Actionability)** = mean of as-entered values
  over all 20 cases.
- **Citation Quality average** = mean over the **13 non-N/A cases only** (7 zero-citation =
  N/A, excluded).
- **Failure-code frequency** = number of cases whose `failure_codes` contains the code
  (pattern `[A-E][1-6]`), each code counted once per case; `percentage = cases / 20`.

### 3b. Normalization performed (P1 cleanup)

The cleanup modified only the rating/code cells in `eval/llm_human_evaluation.csv`. The
`notes` column and all LLM-output / ground-truth columns were left verbatim. Documentation:

**(i) Scores rounded to the integer 1–5 rubric scale** (4 non-integer values):

| Case | Column | Was | Now | Basis (from the evaluator's own note) |
|---|---|---|---|---|
| U00011 | accuracy | 4.5 | **4** | "Minor overstatement … factually aligned" → a defect exists → rubric 4 (Good, minor discrepancies) |
| U00015 | accuracy | 4.5 | **4** | "Minor overstatement … no factual hallucination" → defect exists → 4 |
| U00233 | actionability | 4.5 | **4** | "action somewhat aggressive for HIGH risk" → defect exists → 4 |
| U00015 | citation | 4.7 | **5** | standard rounding (no citation defect noted) → 5 |

Rule stated: **round to the nearest integer; half-points (4.5) round down to 4 where the note
identifies a minor defect** (rubric "4 = Good / minor discrepancies" rather than "5 =
Excellent"); **4.7 rounds up to 5**.

**(ii) Failure codes cleaned to valid taxonomy codes only.**
- Reduced free-text `failure_codes` entries to clean `code[;code]` lists (the per-case
  rationale already lives in the `notes` column, which is unchanged).
- Removed the non-standard annotation `A4_minor_overstatement` (U00011, U00015).

**(iii) A4 vs A5 re-audit** (per taxonomy: **A4 = false attribution of a detection method that
was not used**; **A5 = fabricated/invented risk factors not in the ground truth**).
"Generic over-interpretation" is **not** A4 unless a specific detection method is falsely
attributed. Result of the re-audit:
- The **11 cases previously labeled A4** ("unsupported behavioral claim / fraud typology",
  e.g. *sleeper account, bot, money laundering, fraud ring*) are **fabricated factors →
  reclassified to A5**. None falsely attributed a detection method (ML/Rule/Graph were used;
  the `graph_score = 0 → "lone wolf / isolated actor"` pattern interprets an *absence* and is
  over-interpretation/fabrication, not a false claim that Graph *detected* something).
- **A4: 11 → 0. A5: 15 → 18.**
- **U00011 and U00015 retain no failure code**: their notes state "no factual hallucination" /
  "factually aligned" — i.e. neither A5 (fabrication) nor A4 (false attribution) applies; the
  minor overstatement is captured by their accuracy score (4).

**(iv) Other tidying (same value, normalized form):** `U00237` citation `N/A，3 → N/A`
(zero-citation case); `U00223` sensitivity `PASS → pass` (casing).

### 3c. Post-normalization verification

- Exactly **20 rows**, **20 unique `user_id`s**, **0 duplicates**.
- All Accuracy / Readability / Actionability cells conform to **integer 1–5**.
- `citation_quality_1_5` is integer 1–5 or `N/A`; **N/A appears only** for the 7 zero-citation
  cases.
- **No invalid or malformed failure codes** (all in A1–A6/B1–B6/C1–C6/D1–D6/E1–E5; well-formed
  `code[;code]`).
- `notes` column preserved (multi-line content, full-width punctuation, and quotation marks
  intact).

---

## 4. Results

### 4.1 Aggregate metrics (after normalization)

| Metric | Value | n |
|---|---|---|
| Response Structure Validity — pass rate | **100%** | 20/20 |
| Accuracy & Groundedness — average | **3.50 / 5** | 20 |
| Readability — average | **5.00 / 5** | 20 |
| Actionability — average | **4.45 / 5** | 20 |
| Citation Quality — average (excl. N/A) | **4.08 / 5** | 13 (7 N/A) |
| Sensitivity & Privacy — pass rate | **100%** | 20/20 |

### 4.2 Score distributions (after normalization)

| Dimension | Distribution (score → count) | Median |
|---|---|---|
| Accuracy | 3 → 10, 4 → 10 | 3.5 |
| Readability | 5 → 20 | 5.0 |
| Actionability | 4 → 11, 5 → 9 | 4.0 |
| Citation (numeric, n=13) | 3 → 3, 4 → 6, 5 → 4 | 4.0 |

**Reading:** Readability is uniformly perfect; Actionability is high; Accuracy is the weakest
dimension (median 3.5; half the cases scored 3). Citation quality is good *where citations
exist*, but 7/20 cases (35%) have no citation to score.

---

## 5. Failure-code analysis (after normalization)

### 5.1 Frequencies

| Code | Name | Cases | % of 20 |
|---|---|---|---|
| **A5** | Factor Fabrication / incorrect inference | **18** | **90%** |
| **D1** | Irrelevant Citation | 5 | 25% |
| A4 | False Attribution | **0** | 0% |
| A1 / A2 / A3 / A6 | hallucination / score mismatch / level mismatch / contradiction | 0 | 0% |
| B* / C* / E* | readability / actionability / privacy | 0 | 0% |

2 cases (U00011, U00015) carry **no failure code** (see §3b).

### 5.2 Specifically requested codes

| Code | Result |
|---|---|
| A5 Factor Fabrication | **18 cases (90%)** — the dominant issue |
| A4 False Attribution | **0 cases** (the 11 pre-cleanup A4 labels were reclassified to A5 — §3b) |
| A2 Score Mismatch | **0 cases** — numeric scores match ground truth |
| A3 Level Mismatch | **0 cases** — risk levels are correct |
| D1 Irrelevant Citation | **5 cases (25%)** — the KYC/CDD citation attached to account-age/fraud claims it does not support |
| D2 Missing Citation | **0 cases** (not coded by evaluators; qualitative caveat below) |
| C3 Inappropriate Action | **0 cases** — no C-codes at all |
| E-series (privacy/sensitivity) | **0 cases** — all 20 sensitivity = pass |

### 5.3 Failure categories (separated)

- **Factual / grounding — A5 (90%):** the dominant category. These are **not** numeric errors
  (A2/A3 = 0); scores and levels are accurate. The failure is *fabrication*: accurate signals
  are converted into unsupported fraud narratives. (A4 = 0 after re-audit.)
- **Citation — D1 (25%):** the attached policy (KYC/CDD "enhanced review") does not support the
  account-age/fraud claims. Separately, 7 cases have no citation (N/A).
- **Actionability:** strong (avg 4.45); **no C-codes**.
- **Readability:** perfect (5.00); **no B-codes**.
- **Privacy / sensitivity:** clean (100% pass); **no E-codes**.

> Qualitative caveat (not coded): several zero-citation cases (e.g. U00237) have notes stating
> "No citations provided despite policy/action claims," which resembles D2 (Missing Citation).
> Evaluators marked these `citation_quality = N/A` rather than assigning D2, so D2 = 0 in the
> coded data; this is an observation, not a re-code.

---

## 6. Representative failure patterns

All quotes/claims are traceable to the `notes` column of `eval/llm_human_evaluation.csv`. All
examples below are coded **A5** (factor fabrication / unsupported inference) unless noted.

**Pattern A — account_age reinterpreted as a policy "New Account Risk" threshold (systemic).**
- **U00274:** "incorrectly interprets a **171-day** account as satisfying a 'new account risk'
  threshold, while the implemented rule requires age <7 days with high activity."
- **U00210:** "treats **139 days** as a high-risk/new-account observation window, **invents a
  sub-150-day threshold** and sleeper-account classification."
- **U00247:** "**fabricates a policy threshold** for 'new account' risk ('typically <90-120
  days')."
- **U00217 / U00264 / U00299 / U00292 / U00221 / U00233 / U00223:** same on 120-/174-/112-/
  164-/86-/105-day accounts.

**Pattern B — sleeper-account / fraud narratives built from accurate signals (A5).**
- CRITICAL cases (U00010, U00033, U00047, U00020): unsupported typologies — "botnet, money
  laundering, sleeper cell", "Sybil attack, bonus abuse, wash trading", "synthetic identity".
- **U00236:** "unsupported fraud hypotheses (lone wolf, unseen infrastructure, 3–6 month
  attack window)."

**Pattern C — `graph_score = 0` over-interpreted as "isolated / evasive actor" (A5).**
- U00210 ("infers sophisticated OpSec from Graph Score 0.0"), U00221 ("isolated actor"),
  U00247 ("independent/unknown-network"), U00264 ("isolated IP/device usage or evasion
  techniques"). (Per §3b, this is fabrication/over-interpretation = A5, **not** A4.)

**Pattern D — ML score described as fraud probability / certainty (A5).**
- U00232 / U00236 / U00237 / U00292: "ML score described as fraud probability / certainty of
  malicious intent."

**Pattern E — citation does not support the claim (D1).**
- U00233 / U00217 / U00264 / U00292 / U00221: "Citation [1] supports enhanced review but does
  not support the claimed account-age risk window or fraud behavior assumptions."

---

## 7. Systemic LLM behavior pattern (not isolated errors)

**Yes — the evaluation indicates a systemic pattern, not isolated mistakes.** After the A4→A5
re-audit, **A5 appears in 90% of cases** (18/20) and clusters on one mechanism:

1. The system emits a risk factor literally named **"New Account Risk"** for **any**
   `account_age_days > 0` (no "newness" threshold; see
   `backend/app/services/risk_service.py::_create_risk_factors`). The LLM receives that label
   for accounts that are 86–174 days old.
2. The LLM **over-interprets that label as a policy-defined "new account" threshold**,
   **fabricates the threshold** ("<90–120 days", "sub-150-day"), and builds a
   **sleeper-account / fraud narrative** on top of it.
3. Related over-inference recurs: `graph_score = 0` → "lone wolf / isolated / OpSec evasion";
   high `ml_score` → "fraud probability / certainty of malicious intent".

This is a **grounding / fabrication problem (A5)**, fluent but unsupported — **not** a numeric
accuracy problem (A2 = A3 = 0, A4 = 0). Root causes are shared between (a) the **system side**
— a misleadingly-named factor and the absence of policy text defining an account-age threshold
— and (b) the **LLM side** — converting evidence into confirmed fraud conclusions. Because it
is systemic and signal-driven, it should be addressed at the prompt / factor-naming / policy
layer, not case-by-case.

---

## 8. Comparison with fallback baseline (small paired human evaluation)

Same 20 `user_id`s, both rated by humans on the same rubric. **n = 20 (citation: n = 13 where
the LLM case is numeric).** This is a **descriptive paired comparison only — with n = 20 no
claim of statistical superiority is made.**

| Dimension | LLM avg | Fallback avg | Mean Δ (LLM − FB) | LLM higher / equal / lower |
|---|---|---|---|---|
| Accuracy & Groundedness | 3.50 | 4.00 | **−0.50** | 0 / 10 / 10 |
| Readability | 5.00 | 4.00 | **+1.00** | 20 / 0 / 0 |
| Actionability | 4.45 | 3.30 | **+1.15** | 19 / 1 / 0 |
| Citation Quality | 4.08 (n=13) | 2.15 (n=13) | **+1.92** | 12 / 1 / 0 |

(Fallback overall citation average over its 20 cases = 2.10, per `eval/explain_eval_summary.md`.)

**Different failure profiles (frequencies):**

| Code | LLM | Fallback |
|---|---|---|
| A4 False Attribution | 0 | 0 |
| A5 Factor Fabrication | 18 (90%) | 0 |
| D1 Irrelevant Citation | 5 (25%) | 19 (95%) |
| D6 Excessive Citations | 0 | 14 (70%) |
| B2 Redundancy | 0 | 5 (25%) |
| B3 Jargon | 0 | 5 (25%) |

**Interpretation (descriptive, not inferential):**
- The **LLM** is markedly more readable and actionable, and its citations score higher *where
  present*. Its weakness is **accuracy/grounding**: it fabricates factors (A5 90%), so it
  scores below the fallback on Accuracy in 10/20 cases.
- The **fallback** is factually conservative (no A-codes; higher Accuracy) but less
  readable/actionable, with poor citations (D1 95%, D6 70%).
- The two systems fail differently: **LLM = fluent but fabricates (A5)**; **fallback =
  accurate but plain, with weak citations**. With n = 20 these are observations, not a ranking.

---

## 9. Limitations

- **Sample size:** n = 20 cases, single rating per case (`evaluator_id` blank — rater count
  not recorded). No inter-rater reliability; no statistical significance.
- **Normalization was applied (see §3b):** 4 non-integer scores rounded to integers and 11 A4
  codes reclassified to A5, per documented rules tied to the evaluators' own notes. This
  resolved the rubric-scale deviations present in the raw ratings.
- **Citation average covers only 13/20 cases** (7 zero-citation = N/A), so it is not directly
  comparable to an all-cases average.
- **File encoding:** `eval/llm_human_evaluation.csv` is GBK-encoded (originally UTF-8; re-saved
  by an editor in a Chinese locale). Content is intact; noted for tooling.
- **Ground truth** is the live DB (`risk_events` / `users` / `risk_factors`); the
  `test_data/v4_demo_production/risk_analysis_results.csv` snapshot is **not** authoritative
  (see `risk_analysis_results.NON_AUTHORITATIVE.md`).
- **"New Account Risk" is a code-generated factor for any `account_age_days > 0`** with no
  policy threshold (see `eval/README.md` → *Risk-factor Ground-truth Notes*); this is part of
  the systemic pattern in §7, not an LLM-only issue.

---

## 10. Recommended next improvements

1. **Fix the systemic fabrication (highest leverage).** Constrain the prompt so the LLM may
   not (a) treat "New Account Risk" as a policy threshold, (b) invent thresholds, or (c)
   convert signals into confirmed fraud conclusions. Require hypotheses to be labeled as
   inferences. Directly targets A5 (90%).
2. **Rename / re-scope the "New Account Risk" factor** (system side) so the label is not
   emitted for mature accounts, or gate it behind a real threshold (the existing rule
   `account_age_days < 7 AND trade_frequency_24h > 50`).
3. **Add policy text** defining any intended account-age/onboarding thresholds (to
   `policies/*.md`) so the claim is either policy-backed or explicitly an inference — this
   also gives the citation pipeline something to cite (addresses D1 and the 7 no-citation
   cases).
4. **Citation grounding check:** attach a citation only when the policy snippet actually
   supports the specific claim (reduces D1).
5. **Evaluation process:** record `evaluator_id`, use ≥2 raters per case for inter-rater
   reliability, and enforce the integer 1–5 scale at entry (this cleanup would then be
   unnecessary).
6. **Re-run on a larger sample** (50+) before drawing any comparative conclusion between the
   LLM and fallback paths.

---

### Traceability

All aggregates are reproducible from `eval/llm_human_evaluation.csv` with the rules in §3 and
the normalization in §3b; failure-code counts use the `[A-E][1-6]` match on the `failure_codes`
column; the paired comparison joins on `user_id` against `eval/explain_eval_results.csv`.
Representative quotes in §6 are copied from the `notes` column.
