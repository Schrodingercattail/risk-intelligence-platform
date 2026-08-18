"""
Narrative presentation-layer tests.

Canonical Evidence remains complete (thresholds, contributions, raw values,
detection_sources); the DEFAULT user-facing narrative is investigation-oriented:
- no score contributions, no raw threshold expressions / snake_case fields
- no "withdrawal risk score = N"
- natural-language rendering of observed values
- ML signal visible + labeled as system signal
- no detection-source wording
- Key Risk Findings and Next Actions have independent numbering scopes
"""
import asyncio
from types import SimpleNamespace

from app.services.evidence_service import EvidenceService
from app.services.llm_service import LLMExplanationService


U00010_FEATURES = {
    "account_age_days": 6, "trade_frequency_24h": 54,
    "opposite_trade_ratio": 0.3438, "shared_device_count": 1,
    "withdrawal_frequency_24h": 7, "first_withdrawal_flag": True,
    "linked_account_count": 18, "withdrawal_risk_score": 1.0,
}


def build_evidence(ml=99.41, rule=85.0, graph=59.08, has_graph=True, connected=18,
                   features=None):
    svc = EvidenceService.__new__(EvidenceService)
    feats = dict(features if features is not None else U00010_FEATURES)

    async def fe(u):
        return feats

    async def rules(u, f):
        return await EvidenceService._derive_rule_evidence(svc, u, f)

    svc._get_feature_evidence = fe
    svc._derive_rule_evidence = rules
    return asyncio.run(svc.get_canonical_evidence(
        "U", risk_event=SimpleNamespace(
            ml_score=ml, rule_score=rule, graph_score=graph,
            risk_probability=0.99, primary_reason="ML Pattern Detection"),
        risk_factors=[],
        graph_data={"nodes": [{}] * (connected + 1)} if has_graph else None,
        has_graph_evidence=has_graph))


def make_prompt_svc():
    svc = LLMExplanationService.__new__(LLMExplanationService)
    svc.provider = None
    return svc


def risk_event_dict():
    return {"risk_score": 87.02, "risk_level": "CRITICAL", "ml_score": 99.41,
            "rule_score": 85.0, "graph_score": 59.08}


class TestCanonicalEvidenceStillComplete:
    """Presentation hides details; canonical evidence keeps everything."""

    def test_canonical_keeps_threshold_contribution_raw(self):
        ev = build_evidence()
        rule_f = next(f for f in ev["findings"]
                      if f["name"] == "New account with high activity")
        assert rule_f["threshold"] == "account_age_days < 7 AND trade_frequency_24h > 50"
        assert rule_f["contribution"] == 40
        assert rule_f["observed_value"] == {"account_age_days": 6,
                                            "trade_frequency_24h": 54}
        assert "Rule" in rule_f["detection_sources"]
        # withdrawal risk score feature retained in canonical (via factor findings)
        awb = next(f for f in ev["findings"] if f["name"] == "Abnormal Withdrawal Behavior")
        assert awb["observed_value"]["withdrawal_risk_score"] == 1.0


class TestPromptPresentationLayer:
    """The prompt renders investigation language, not scoring internals."""

    def setup_method(self):
        self.svc = make_prompt_svc()
        self.ev = build_evidence()
        self.prompt = self.svc._construct_prompt(
            "U", risk_event_dict(), [], None, canonical_evidence=self.ev)
        self.low = self.prompt.lower()

    def test_no_contribution_rendering(self):
        # no numeric contribution points anywhere in the prompt data
        assert "contributes +" not in self.low
        assert "+40" not in self.prompt and "+25" not in self.prompt and "+20" not in self.prompt
        assert "contribution:" not in self.low
        # the only allowed occurrence of the word is the prohibition instruction
        import re
        occurrences = [m.start() for m in re.finditer("contribution", self.low)]
        for pos in occurrences:
            context = self.low[max(0, pos - 60):pos + 20]
            assert "never" in context, f"non-instruction contribution mention: {context!r}"

    def test_no_raw_threshold_expressions(self):
        assert "account_age_days <" not in self.low
        assert "trade_frequency_24h >" not in self.low
        assert "withdrawal_frequency_24h >" not in self.low
        # natural language with real observed values instead
        assert "6 days old" in self.low
        assert "54 trades were recorded in 24 hours" in self.low
        assert "7 withdrawals were recorded in 24 hours" in self.low
        assert "34.38%" in self.prompt

    def test_no_raw_field_names(self):
        for field in ("account_age_days", "trade_frequency_24h",
                      "withdrawal_frequency_24h", "first_withdrawal_flag",
                      "opposite_trade_ratio", "shared_device_count",
                      "withdrawal_risk_score"):
            assert field not in self.prompt, f"raw field leaked: {field}"

    def test_withdrawal_risk_score_not_in_prompt_findings(self):
        assert "abnormal withdrawal behavior" not in self.low, \
            "sub-score finding omitted from narrative (kept in canonical)"

    def test_ml_signal_visible_and_labeled(self):
        assert "99.41" in self.prompt
        assert "ml pattern detection" in self.low
        assert "not a calibrated probability" in self.low

    def test_no_detection_source_wording(self):
        assert "detected by" not in self.low
        assert "detection_sources" not in self.low

    def test_numbering_scope_instruction(self):
        # backend owns numbering: model uses "- " lines only; backend numbers
        assert 'starting with "- "' in self.low
        assert "never number findings or actions yourself" in self.low
        assert "cover all supplied canonical findings" in self.low

    def test_humanize_observed(self):
        assert self.svc._humanize_observed("x", {
            "account_age_days": 6, "trade_frequency_24h": 54,
            "first_withdrawal_flag": True, "opposite_trade_ratio": 0.3438,
        }) == ("the account is 6 days old; 54 trades were recorded in 24 hours; "
               "a first withdrawal to a new address was detected; "
               "an opposite-trade ratio of 34.38% was observed")


class TestParserNumberingScopes:
    def setup_method(self):
        self.svc = make_prompt_svc()

    def test_actions_restart_at_1_after_findings_1_to_9(self):
        text = (
            "## Summary\ns\n## Key Findings\n"
            + "\n".join(f"{i}. finding {i}" for i in range(1, 10))
            + "\n## Recommended Action\nEscalate:\n"
            + "\n".join(f"{i}. step {i}" for i in range(1, 6))
        )
        p = self.svc._parse_explanation(text, {"primary_reason": "x"})
        assert len(p["key_findings"]) == 9
        first_action = p["recommended_action"].split("\n")[1]  # after theme line
        assert first_action.startswith("1."), "actions must restart at 1"

    def test_sections_stay_separate(self):
        text = ("## Summary\ns\n## Key Findings\n1. finding one\n"
                "## Recommended Action\n1. act one\n2. act two")
        p = self.svc._parse_explanation(text, {"primary_reason": "x"})
        assert p["key_findings"] == ["1. finding one"]
        assert "1. act one" in p["recommended_action"]
        assert "act two" not in " ".join(p["key_findings"])
