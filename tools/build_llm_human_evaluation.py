#!/usr/bin/env python3
"""
Build the P1 human-evaluation sheet for the 20 LLM investigation explanations.

Joins, by user_id:
  - eval/explain_eval_cases.csv                  (case set + pipeline_run_id)
  - live DB: risk_events / users / risk_factors  (AUTHORITATIVE ground truth)
  - eval/llm_raw_explanations/<user_id>.json     (the LLM output to evaluate)

Output: eval/llm_human_evaluation.csv  (one row per case; verbatim LLM text;
rating columns left blank for human input).

Ground-truth sourcing (authoritative — same values the runtime pipeline persists
and /api/risk/explain feeds to the LLM):
  Scores / level / primary_reason / recommended_action / detected_at -> risk_events
    (fusion risk_score = 0.5*ml + 0.3*rule + 0.2*graph, persisted at pipeline time)
  Account context (country / kyc_level / vip_level / account_created_time) -> users
  Evidence (risk factors) -> risk_factors on the latest risk_event

Do NOT use test_data/v4_demo_production/risk_analysis_results.csv as ground truth: it is
a frozen one-time 2026-07-21 export (its generator script is no longer in the repo) whose
graph_score/final_score diverge from the DB — the runtime recomputes graph_score each
pipeline run, so the snapshot drifts. This previously made accurate LLM output look wrong.
See test_data/v4_demo_production/risk_analysis_results.NON_AUTHORITATIVE.md.

Important — account age & connected-account count are sourced from the
risk_factors (e.g. "New Account Risk: 6 days old", "Linked Account Network:
18 connected accounts detected"), because those are the exact values passed to
the LLM. Computing them from detected_at - account_created_time yields a
DIFFERENT number and would falsely make the LLM look wrong. Likewise the
connected count comes from the "Linked Account Network" factor, not
feature_table.cluster_size (which is not populated for these cases).

gt_*_high (which detection signals actually fired) are recomputed from the DB
scores vs settings.DETECTION_*_THRESHOLD (ml>=10, rule>=15, graph>=10).

Citation handling (per rubric, Dimension 4 "if present"):
  - num_citations / has_citations are always preserved.
  - The 7 zero-citation cases get citation_applicability="N/A_no_policy_finding"
    and citation_quality_1_5="N/A" (NOT auto-failed). An evaluator may override
    to 1 only if they judge relevant policy existed and was omitted.

Hallucination / unsupported-claim coverage:
  Already covered by the rubric's Accuracy & Groundedness (Dim 1) + failure codes
  A1/A2/A4/A5. No separate hallucination column is added.

This script only READS (cases CSV, DB, LLM JSON) and WRITES the output CSV. It
does not modify application/backend/frontend code, does not regenerate any LLM
explanation, and does not touch eval/explain_eval_results.csv.

Usage (run from repo root with the backend venv active; DB must be reachable):
    python tools/build_llm_human_evaluation.py
"""
import argparse
import asyncio
import csv
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

# Columns written to the sheet, in order.
COLUMNS = [
    # --- A. Case metadata (filled) ---
    "user_id",
    "risk_level",            # runtime classification (risk_events.risk_level)
    "detected_at",           # risk_events.detected_at (authoritative)
    "pipeline_run_id",       # cases CSV
    "audience",              # how the LLM output was generated
    "explanation_source",    # from LLM JSON
    "llm_error",             # from LLM JSON (blank if None)
    # --- B. Structured ground truth (filled, authoritative -> DB) ---
    "gt_risk_score",         # risk_events.risk_score (final fused)
    "gt_ml_score",
    "gt_rule_score",
    "gt_graph_score",
    "gt_primary_reason",     # risk_events.primary_reason
    "gt_recommended_action", # risk_events.recommended_action (system baseline)
    "gt_risk_factors",       # authoritative evidence: RiskFactor "name :: desc" per line
    "gt_account_age_days",   # parsed from "New Account Risk" factor (as the LLM saw it)
    "gt_connected_accounts", # parsed from "Linked Account Network" factor
    "gt_ml_high",            # recomputed: ml_score >= DETECTION_ML_THRESHOLD
    "gt_rule_high",          # recomputed: rule_score >= DETECTION_RULE_THRESHOLD
    "gt_graph_high",         # recomputed: graph_score >= DETECTION_GRAPH_THRESHOLD
    "gt_country",
    "gt_kyc_level",
    "gt_vip_level",
    # --- C. LLM output (verbatim; not hand-copied or altered) ---
    "llm_summary",
    "llm_key_findings",      # newline-joined, verbatim
    "llm_recommended_action",
    "num_citations",
    "has_citations",
    "llm_citations",         # "[id] doc :: section :: quote" per line, verbatim
    "citation_applicability",
    # --- D. Human rating columns (input) ---
    "structure_validity_pass_fail",  # input  (rubric E0)
    "accuracy_1_5",                  # input  (rubric Dim 1; covers hallucination)
    "readability_1_5",               # input  (rubric Dim 2)
    "actionability_1_5",             # input  (rubric Dim 3)
    "citation_quality_1_5",          # input  (N/A pre-set for zero-citation cases)
    "sensitivity_pass_fail",         # input  (rubric E1)
    "failure_codes",                 # input  (from explain_failure_taxonomy.md)
    "notes",                         # input
    "evaluator_id",                  # input
]


def _round2(value):
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def _high(score, threshold):
    try:
        return "true" if float(score) >= threshold else "false"
    except (TypeError, ValueError):
        return ""


def _format_factors(factors):
    """Authoritative evidence list: 'factor_name :: factor_description' per line."""
    return "\n".join(
        f"{f.factor_name} :: {f.factor_description}"
        for f in factors
        if f.factor_name or f.factor_description
    )


def _parse_account_age(factors):
    """Account age as the LLM saw it, from the 'New Account Risk' factor text."""
    for f in factors:
        if (f.factor_name or "").lower().startswith("new account"):
            m = re.search(r"(\d+)\s*days?\s*old", f.factor_description or "", re.I)
            if m:
                return m.group(1)
    # Fallback: any 'N days old' phrase in any factor.
    for f in factors:
        m = re.search(r"(\d+)\s*days?\s*old", f.factor_description or "", re.I)
        if m:
            return m.group(1)
    return ""


def _parse_connected_accounts(factors):
    """Connected-account count from the 'Linked Account Network' factor text."""
    for f in factors:
        if "connected" in (f.factor_name or "").lower() or "linked" in (f.factor_name or "").lower():
            m = re.search(r"(\d+)\s*connected\s*accounts?", f.factor_description or "", re.I)
            if m:
                return m.group(1)
    for f in factors:
        m = re.search(r"(\d+)\s*connected\s*accounts?", f.factor_description or "", re.I)
        if m:
            return m.group(1)
    return ""


def _format_citations(citations):
    """Verbatim, readable layout of citation objects (quotes unaltered)."""
    if not citations:
        return ""
    lines = []
    for c in citations:
        cid = c.get("id", "")
        doc = c.get("doc", "")
        section = c.get("section", "")
        quote = c.get("quote", "")
        lines.append(f"[{cid}] {doc} :: {section} :: {quote}")
    return "\n".join(lines)


def _fetch_ground_truth(user_ids):
    """
    Read-only DB query. Returns {user_id: (risk_event, user, [risk_factors])}
    using the app's async session + ORM models. Also returns resolved settings.
    """
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from sqlalchemy import select, desc
    from app.db.session import async_session_maker
    from app.models.database import RiskEvent, User, RiskFactor
    from app.config import settings

    out = {}

    async def _load():
        async with async_session_maker() as s:
            for uid in user_ids:
                re_ = (await s.execute(
                    select(RiskEvent)
                    .where(RiskEvent.user_id == uid)
                    .order_by(desc(RiskEvent.detected_at))
                    .limit(1)
                )).scalar_one_or_none()
                u = (await s.execute(
                    select(User).where(User.user_id == uid)
                )).scalar_one_or_none()
                factors = []
                if re_ is not None:
                    factors = list((await s.execute(
                        select(RiskFactor).where(RiskFactor.risk_event_id == re_.id)
                    )).scalars().all())
                out[uid] = (re_, u, factors)

    asyncio.run(_load())
    return out, settings


def build(cases_path, llm_dir, out_path):
    cases = list(csv.DictReader(open(cases_path, newline="")))
    if not cases:
        sys.exit(f"No cases in {cases_path}")

    user_ids = [c["user_id"] for c in cases]
    gt, settings = _fetch_ground_truth(user_ids)

    missing_re = [u for u in user_ids if gt[u][0] is None]
    if missing_re:
        sys.exit(f"No risk_events row for: {missing_re}")

    llm_dir = Path(llm_dir)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for case in cases:
        uid = case["user_id"]
        re_, u, factors = gt[uid]

        llm_file = llm_dir / f"{uid}.json"
        if not llm_file.exists():
            sys.exit(f"Missing LLM JSON: {llm_file}")
        llm = json.loads(llm_file.read_text())

        citations = llm.get("citations") or []
        num_cit = len(citations)

        row = {
            "user_id": uid,
            "risk_level": re_.risk_level or "",
            "detected_at": re_.detected_at.isoformat() if re_.detected_at else "",
            "pipeline_run_id": case.get("pipeline_run_id", ""),
            "audience": "investigator",
            "explanation_source": llm.get("explanation_source", ""),
            "llm_error": "" if llm.get("llm_error") is None else str(llm.get("llm_error")),
            "gt_risk_score": _round2(re_.risk_score),
            "gt_ml_score": _round2(re_.ml_score),
            "gt_rule_score": _round2(re_.rule_score),
            "gt_graph_score": _round2(re_.graph_score),
            "gt_primary_reason": re_.primary_reason or "",
            "gt_recommended_action": re_.recommended_action or "",
            "gt_risk_factors": _format_factors(factors),
            "gt_account_age_days": _parse_account_age(factors),
            "gt_connected_accounts": _parse_connected_accounts(factors),
            "gt_ml_high": _high(re_.ml_score, settings.DETECTION_ML_THRESHOLD),
            "gt_rule_high": _high(re_.rule_score, settings.DETECTION_RULE_THRESHOLD),
            "gt_graph_high": _high(re_.graph_score, settings.DETECTION_GRAPH_THRESHOLD),
            "gt_country": (u.country if u else "") or "",
            "gt_kyc_level": (u.kyc_level if u else "") or "",
            "gt_vip_level": (u.vip_level if u else "") or "",
            "llm_summary": llm.get("summary", ""),
            "llm_key_findings": "\n".join(llm.get("key_findings") or []),
            "llm_recommended_action": llm.get("recommended_action", ""),
            "num_citations": str(num_cit),
            "has_citations": "true" if num_cit > 0 else "false",
            "llm_citations": _format_citations(citations),
            "citation_applicability": "APPLICABLE" if num_cit > 0 else "N/A_no_policy_finding",
            # Human-input columns (blank unless pre-set below)
            "structure_validity_pass_fail": "",
            "accuracy_1_5": "",
            "readability_1_5": "",
            "actionability_1_5": "",
            "citation_quality_1_5": "N/A" if num_cit == 0 else "",
            "sensitivity_pass_fail": "",
            "failure_codes": "",
            "notes": "",
            "evaluator_id": "",
        }
        rows.append({k: row.get(k, "") for k in COLUMNS})

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def main():
    p = argparse.ArgumentParser(description="Build eval/llm_human_evaluation.csv (ground truth from DB)")
    p.add_argument("--cases", default=str(REPO_ROOT / "eval/explain_eval_cases.csv"))
    p.add_argument("--llm-dir", default=str(REPO_ROOT / "eval/llm_raw_explanations"))
    p.add_argument("--out", default=str(REPO_ROOT / "eval/llm_human_evaluation.csv"))
    args = p.parse_args()

    rows = build(args.cases, args.llm_dir, args.out)

    case_ids = [r["user_id"] for r in csv.DictReader(open(args.cases, newline=""))]
    out_ids = [r["user_id"] for r in rows]
    print(f"Wrote {args.out}")
    print(f"rows (excl header): {len(rows)}  | columns: {len(COLUMNS)}")
    print(f"user_ids match cases CSV: {out_ids == case_ids}")
    print(f"no missing/duplicate user_ids: {len(out_ids) == len(set(out_ids)) == len(case_ids)}")
    zero_cite = [r["user_id"] for r in rows if r["num_citations"] == "0"]
    print(f"zero-citation cases ({len(zero_cite)}): {zero_cite}")


if __name__ == "__main__":
    main()
