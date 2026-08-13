# ⚠️ `risk_analysis_results.csv` is NON-AUTHORITATIVE

**Do not use this file as ground truth for risk scores.** It is kept only as a historical
record of a one-off verification run.

## What this file is

A **frozen, one-time export** dated 2026-07-21 (see `CRITICAL_OVERRIDE_VERIFICATION_SUMMARY.md`),
produced by a "Critical Override Verification Script" that is **no longer in the repository**.
No current script regenerates or refreshes it.

## Why it is wrong / stale

- `graph_score` is recomputed on every pipeline run from the **live cluster state**
  (`AccountCluster.risk_score`, `member_count`, hub role) in
  `risk_service._calculate_graph_score`, so it drifts away from this snapshot.
- `final_score = 0.5·ml + 0.3·rule + 0.2·graph` inherits that drift.
- The file even disagrees with its own companion summary (graph 88–92 there vs ~57–60
  here) and with the v4 `README.md` expected score ranges.

## Use this instead

The **live database table `risk_events`** is the only authoritative source of risk scores
— the same values the frontend displays and `/api/risk/explain` feeds to the LLM. For the
evaluation set, `tools/build_llm_human_evaluation.py` pulls ground truth directly from the
DB (`risk_events` / `users` / `risk_factors`).

See also: `README.md` → section *⚠️ `risk_analysis_results.csv` is a NON-AUTHORITATIVE snapshot*.
