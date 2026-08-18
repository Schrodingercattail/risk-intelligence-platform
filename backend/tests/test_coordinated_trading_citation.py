"""
Coordinated Trading Pattern: wording calibration + citation accuracy.

The opposite-trade ratio is a single aggregate statistic — it cannot show that
the account "consistently offset another party's positions", and the policy
corpus has NO section supporting opposite-trade/coordinated-trading semantics.
Therefore:
- wording must be calibrated (observed fact + "may warrant further review" +
  "potentially coordinated trading behavior")
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
    """Prompt instructs calibrated interpretation of the ratio."""

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
        low = prompt.lower()
        assert "may warrant further review" in low
        assert "potentially coordinated trading behavior" in low
        assert "does not show that the account offset another" in low
        # natural-language observed value rendered
        assert "opposite-trade ratio of 34.38%" in low
        # over-claiming words are prohibited in the instruction
        assert "nor confirm coordination" in low

    def test_target_wording_matches_spec(self):
        # the canonical target sentence is exactly what the instruction models
        svc = LLMExplanationService.__new__(LLMExplanationService)
        svc.provider = None
        assert svc._humanize_observed("x", {"opposite_trade_ratio": 0.3438}) == \
            "an opposite-trade ratio of 34.38% was observed"
