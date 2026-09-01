"""
Claim-level citation grounding + user-facing attribution removal tests.

Design rule under test: Risk Finding ≠ Detection Source ≠ Policy Citation.
- detection_sources stay INTERNAL (canonical evidence) but must never appear
  in user-facing narrative or prompt-rendered findings
- a citation must support the finding's specific CLAIM; when the policy corpus
  has no matching support the finding remains uncited (no marker, no entry,
  and the finding is NOT deleted)
"""
import asyncio
from types import SimpleNamespace

from app.services.citation_retrieval_service import (
    ClaimRefiner,
    CitationRetrievalService,
    create_citation_retrieval_service,
)
from app.services.evidence_service import EvidenceService
from app.services.llm_service import LLMExplanationService


U00010_FEATURES = {
    "account_age_days": 6, "trade_frequency_24h": 54,
    "opposite_trade_ratio": 0.3438, "shared_device_count": 1,
    "withdrawal_frequency_24h": 7, "first_withdrawal_flag": True,
    "linked_account_count": 18, "withdrawal_risk_score": 1.0,
}

U00010_FINDINGS = [
    "1. New account with high activity",
    "2. High withdrawal frequency — 7 withdrawals in 24h",
    "3. First withdrawal to new address",
    "4. Shared Device Relationships",
    "5. Linked Account Network — 18 connected accounts",
    "6. Coordinated Trading Pattern",
    "7. High Trading Frequency — 54 trades in 24h",
]


class TestNoUserFacingDetectionSources:
    """detection_sources are internal only."""

    def _evidence(self):
        svc = EvidenceService.__new__(EvidenceService)
        async def fe(u): return dict(U00010_FEATURES)
        async def rules(u, f):
            return await EvidenceService._derive_rule_evidence(svc, u, f)
        svc._get_feature_evidence = fe
        svc._derive_rule_evidence = rules
        return asyncio.run(svc.get_canonical_evidence(
            "U", risk_event=SimpleNamespace(ml_score=99.41, rule_score=85.0,
                                            graph_score=59.08, risk_probability=0.99,
                                            primary_reason="ML Pattern Detection"),
            risk_factors=[], graph_data={"nodes": [{}]*19}, has_graph_evidence=True))

    def test_prompt_never_renders_detection_sources(self):
        ev = self._evidence()
        # internal provenance retained
        assert any("Rule" in f["detection_sources"] for f in ev["findings"])
        svc = LLMExplanationService.__new__(LLMExplanationService)
        svc.provider = None
        prompt = svc._construct_prompt(
            "U", {"risk_score": 87.02, "ml_score": 99.41, "rule_score": 85.0,
                  "graph_score": 59.08}, [], None, canonical_evidence=ev)
        low = prompt.lower()
        assert "detected by" not in low, "findings rendering must not leak provenance"
        assert "detection_sources" not in low
        # ML signal is still expressed, at detector level
        assert "99.41" in prompt and "ml pattern detection" in low
        assert "not a calibrated probability" in low
        # instruction to the LLM not to output provenance or invent markers
        assert "never mention how a finding was produced" in low
        assert "detection-source label" in low
        # uncited findings must not be dropped / no invented policy backing
        assert "do not delete or omit a finding" in low
        assert "policy requires" in low or "policy grounding" in low

    def test_ml_section_expresses_detector_signal(self):
        ev = self._evidence()
        assert ev["ml"]["score"] == 99.41
        assert ev["ml"]["primary_driver"] == "ML Pattern Detection"
        # the detector-level signal finding exists (with ML provenance), but
        # FEATURE findings never claim ML
        detector = [f for f in ev["findings"]
                    if f["name"] == "ML Pattern Detection Signal"]
        assert detector and detector[0]["detection_sources"] == ["ML"]
        feature_findings = [f for f in ev["findings"]
                            if f["evidence_type"] == "feature"]
        assert feature_findings
        assert not any("ML" in f["detection_sources"] for f in feature_findings)


class TestClaimLevelCitations:
    """A citation must support the finding's specific claim."""

    def setup_method(self):
        self.service: CitationRetrievalService = create_citation_retrieval_service()

    def test_high_withdrawal_frequency_gets_velocity_citation(self):
        r = self.service.retrieve_citations(
            key_findings=["High withdrawal frequency — 7 withdrawals in 24h"],
            rule_score=85.0)
        ids = r.finding_to_citations.get("High withdrawal frequency — 7 withdrawals in 24h", [])
        docs = [c for c in r.citations if c.id in ids]
        assert docs and all("AML" in c.doc for c in docs)
        assert all("velocity" in c.section.lower() for c in docs)

    def test_first_withdrawal_gets_no_velocity_citation(self):
        r = self.service.retrieve_citations(
            key_findings=["First withdrawal to new address"], rule_score=85.0)
        assert not r.finding_to_citations.get("First withdrawal to new address"), \
            "no policy supports the first-withdrawal/new-address claim -> uncited"

    def test_first_withdrawal_finding_not_deleted(self):
        # uncited findings remain in the mapping with an empty list (kept by caller)
        r = self.service.retrieve_citations(
            key_findings=["First withdrawal to new address"], rule_score=85.0)
        assert "First withdrawal to new address" in r.finding_to_citations

    def test_claim_refiner_direct_semantics(self):
        assert not ClaimRefiner.claim_supported(
            "First withdrawal to new address",
            "AML / 2. Transaction Velocity / 2.1 High-Velocity Transfers",
            "A sudden spike in the number of transfers in a short window...")
        assert ClaimRefiner.claim_supported(
            "High withdrawal frequency",
            "AML / 2. Transaction Velocity / 2.1 High-Velocity Transfers",
            "A sudden spike in the number of transfers in a short window...")
        assert ClaimRefiner.claim_supported(
            "First withdrawal to new address",
            "AML / Withdrawals / New payee first withdrawal", "first withdrawal to a new payee")

    def test_graph_findings_never_kyc(self):
        r = self.service.retrieve_citations(
            key_findings=["Shared Device Relationships", "Linked Account Network"],
            graph_score=59.08, has_graph_evidence=True)
        for f, ids in r.finding_to_citations.items():
            for cit in r.citations:
                if cit.id in ids:
                    assert "kyc" not in cit.doc.lower()
                    assert "network" in cit.section.lower() or "relationship" in cit.section.lower()

    def test_trading_finding_gets_transaction_citation(self):
        r = self.service.retrieve_citations(
            key_findings=["High Trading Frequency — 54 trades in 24h"], rule_score=85.0)
        ids = r.finding_to_citations.get("High Trading Frequency — 54 trades in 24h", [])
        assert ids
        for cit in r.citations:
            if cit.id in ids:
                assert "AML" in cit.doc

    def test_contextual_age_no_kyc(self):
        r = self.service.retrieve_citations(
            key_findings=["The account is 112 days old.", "Account Age Context"])
        assert not r.finding_to_citations.get("The account is 112 days old.")
        assert not r.finding_to_citations.get("Account Age Context")

    def test_u00010_full_citation_matrix(self):
        r = self.service.retrieve_citations(
            key_findings=U00010_FINDINGS, ml_score=99.41, rule_score=85.0,
            graph_score=59.08, has_graph_evidence=True)
        cited = {f: ids for f, ids in r.finding_to_citations.items() if ids}
        uncited = {f: ids for f, ids in r.finding_to_citations.items() if not ids}
        # first withdrawal, coordinated trading AND the new-account rule are
        # intentionally uncited: no policy section supports those specific
        # claims (3.2 covers transfer volume after onboarding, not the
        # <7d AND >50-trades conjunction)
        assert {"3. First withdrawal to new address",
                "6. Coordinated Trading Pattern",
                "1. New account with high activity"} <= set(uncited)
        assert set(cited) == set(U00010_FINDINGS) - {
            "3. First withdrawal to new address", "6. Coordinated Trading Pattern",
            "1. New account with high activity"}
        # IDs contiguous from 1, no dangling
        ids = sorted({i for v in cited.values() for i in v})
        assert ids == list(range(1, len(ids) + 1))
        assert all(c.id in ids for c in r.citations)

    def test_no_two_different_claims_share_a_velocity_citation(self):
        r = self.service.retrieve_citations(
            key_findings=["High withdrawal frequency — 7 withdrawals in 24h",
                          "First withdrawal to new address"], rule_score=85.0)
        freq = set(r.finding_to_citations.get("High withdrawal frequency — 7 withdrawals in 24h", []))
        fw = set(r.finding_to_citations.get("First withdrawal to new address", []))
        assert freq and not fw
        assert not (freq & fw), "velocity citation must not back the first-withdrawal claim"


class TestUncitedFindingRendering:
    """Assembly: uncited findings get no marker; marker↔citation bijection holds."""

    def test_renumber_ignores_unmarked_and_keeps_contiguous(self):
        from app.api.routes.risk import _renumber_used_citations
        candidates = [
            {"id": 1, "doc": "AML.md", "section": "3.2 Large Transfers"},
            {"id": 2, "doc": "AML.md", "section": "2.1 High-Velocity"},
            {"id": 3, "doc": "AML.md", "section": "5.1 Network"},
        ]
        marked = [
            "1. New account with high activity [1]",
            "2. High withdrawal frequency — 7 withdrawals in 24h [2]",
            "3. First withdrawal to new address",  # uncited: no marker
            "4. Shared Device Relationships [3]",
        ]
        old_to_new, next_id = _renumber_used_citations(marked, candidates)
        assert old_to_new == {1: 1, 2: 2, 3: 3}
        assert next_id == 4
        # first-withdrawal stays unmarked and is not deleted
        assert marked[2] == "3. First withdrawal to new address"
