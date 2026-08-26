"""
Coordinated Trading Pattern: wording calibration + citation accuracy.

The opposite-trade ratio is a single aggregate statistic — it cannot show that
the account "consistently offset another party's positions", and the policy
corpus has NO section supporting opposite-trade/coordinated-trading semantics.
Therefore:
- wording is threshold-explicit: below 40% = observed metric (NEVER phrased as
  the rule firing); above 40% = the rule triggered
- the finding stays UNCITED (the High-Velocity Transfers section supports
  velocity/counts, not offsetting behavior) unless a genuinely matching
  policy section exists.
"""
import re

from app.services.citation_retrieval_service import (
    ClaimRefiner,
    create_citation_retrieval_service,
)
from app.services.llm_service import LLMExplanationService


FINDING = "Coordinated Trading Pattern — An opposite-trade ratio of 34.38% was observed"


class TestCoordinatedTradingCitation:
    """No citation is better than a wrong citation."""

    def test_claim_refiner_rejects_velocity_section(self):
        # The High-Velocity Transfers section does not support the claim
        assert not ClaimRefiner.claim_supported(
            FINDING,
            "AML / 2. Transaction Velocity & Burst Patterns / 2.1 High-Velocity Transfers",
            "A sudden spike in the number of outgoing or incoming transfers within a "
            "short time window may indicate account takeover, mule activity, fraud "
            "automation. Typical evidence includes counts, short inter-transaction "
            "intervals, deviation from baselines.")
        # Structured transfers (amounts/recipients/timing) do not either
        assert not ClaimRefiner.claim_supported(
            FINDING, "AML / 2.2 Structured or Repetitive Transfers",
            "Repeated transfers with similar amounts, recipients, or timing patterns")

    def test_claim_refiner_accepts_genuine_match_if_corpus_grows(self):
        assert ClaimRefiner.claim_supported(
            FINDING, "AML / Trading Conduct / Offset patterns",
            "Pairs of accounts executing offsetting opposite trades may indicate "
            "coordinated trading.")

    def test_finding_is_uncited_with_current_corpus(self):
        r = create_citation_retrieval_service().retrieve_citations(
            key_findings=[FINDING], rule_score=85.0)
        assert r.finding_to_citations.get(FINDING) == [], \
            "coordinated-trading finding must be uncited (no matching policy)"
        assert not r.citations, "no citation entry may be generated for it"

    def test_high_withdrawal_frequency_citation_unchanged(self):
        r = create_citation_retrieval_service().retrieve_citations(
            key_findings=["High withdrawal frequency — 7 withdrawals in 24h"],
            rule_score=85.0)
        ids = r.finding_to_citations.get(
            "High withdrawal frequency — 7 withdrawals in 24h", [])
        assert ids
        for cit in r.citations:
            if cit.id in ids:
                assert "AML" in cit.doc and "velocity" in cit.section.lower()

    def test_high_trading_frequency_citation_unchanged(self):
        r = create_citation_retrieval_service().retrieve_citations(
            key_findings=["High Trading Frequency — 54 trades in 24h"], rule_score=85.0)
        ids = r.finding_to_citations.get(
            "High Trading Frequency — 54 trades in 24h", [])
        assert ids
        for cit in r.citations:
            if cit.id in ids:
                assert "AML" in cit.doc and "velocity" in cit.section.lower()

    def test_mixed_findings_ids_contiguous_and_no_dangling(self):
        findings = [
            "Coordinated Trading Pattern — An opposite-trade ratio of 34.38% was observed",
            "High withdrawal frequency — 7 withdrawals in 24h",
            "High Trading Frequency — 54 trades in 24h",
        ]
        r = create_citation_retrieval_service().retrieve_citations(
            key_findings=findings, rule_score=85.0)
        cited = sorted({i for v in r.finding_to_citations.values() for i in v})
        assert cited == list(range(1, len(cited) + 1))
        assert all(c.id in cited for c in r.citations)
        # coordinated trading contributes no marks
        assert not r.finding_to_citations.get(findings[0])


class TestWordingCalibration:
    """Prompt instructs threshold-explicit interpretation of the ratio."""

    def test_prompt_contains_calibrated_opposite_trade_guidance(self):
        svc = LLMExplanationService.__new__(LLMExplanationService)
        svc.provider = None
        prompt = svc._construct_prompt(
            "U", {"risk_score": 87.02, "ml_score": 99.41}, [], None,
            canonical_evidence={
                "ml": {"score": 99.41, "probability": None,
                       "primary_driver": "ML Pattern Detection"},
                "rules": {"score": 85.0, "triggered": []},
                "graph": {"has_evidence": False, "score": 0, "note": "none"},
                "contextual": {},
                "findings": [{"name": "Coordinated Trading Pattern",
                              "evidence": "x", "detection_sources": ["Feature"],
                              "evidence_type": "feature",
                              "observed_value": {"opposite_trade_ratio": 0.3438}}],
            })
        # whitespace-normalized: instruction text wraps across source lines
        import re
        low = re.sub(r"\s+", " ", prompt.lower())
        # threshold semantics are part of the business contract
        assert "below the 40% threshold for the coordinated trading rule" in low
        assert "exceeded the 40% threshold, triggering the coordinated trading rule" in low
        assert "does not show that the account offset another" in low
        # natural-language observed value rendered threshold-aware
        assert "opposite-trade ratio of 34.38% was observed, which is below" in low
        # wording that implies the rule fired below threshold is explicitly banned
        assert "never write \"potentially coordinated trading behavior\"" in low
        assert "any wording implying the" in low

    def test_target_wording_matches_spec(self):
        # the canonical target sentences are exactly what the instruction models
        svc = LLMExplanationService.__new__(LLMExplanationService)
        svc.provider = None
        assert svc._humanize_observed("x", {"opposite_trade_ratio": 0.3438}) == \
            ("an opposite-trade ratio of 34.38% was observed, which is below "
             "the 40% threshold for the coordinated trading rule")
        assert svc._humanize_observed("x", {"opposite_trade_ratio": 0.52}) == \
            ("an opposite-trade ratio of 52.00% exceeded the 40% threshold, "
             "triggering the coordinated trading rule")
        # boundary: exactly 0.4 does NOT trigger the rule (strict >)
        assert "below the 40% threshold" in \
            svc._humanize_observed("x", {"opposite_trade_ratio": 0.4})
