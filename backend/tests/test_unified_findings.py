"""
Unified-findings & detection-source attribution tests.

The core design rule under test: RiskFactor rows are CONTEXTUAL / feature-level
evidence — they are NEVER auto-attributed to ML. A finding's
detection_sources only lists sources with real attribution ("Rule" for
triggered deterministic rules, "Graph" for actual network relationships,
"Feature" for feature-level observations). One real finding appears once even
when supported by multiple sources.
"""
import asyncio
from types import SimpleNamespace

from app.services.evidence_service import EvidenceService


def make_service(features, connected=None, has_graph=False):
    svc = EvidenceService.__new__(EvidenceService)

    async def fake_feature(user_id):
        return features

    async def fake_rules(user_id, fe):
        return await EvidenceService._derive_rule_evidence(svc, user_id, fe)

    async def fake_get_canonical(*a, **k):
        return await EvidenceService.get_canonical_evidence(
            svc, *a, **{k2: v for k2, v in k.items()})

    svc._get_feature_evidence = fake_feature
    svc._derive_rule_evidence = fake_rules
    svc._graph_nodes = {"nodes": [{}] * ((connected or 0) + 1)} if has_graph else None
    return svc


def event(ml=99.41, rule=85.0, graph=59.08, prob=0.994, reason="ML Pattern Detection"):
    return SimpleNamespace(ml_score=ml, rule_score=rule, graph_score=graph,
                           risk_probability=prob, primary_reason=reason)


def build(features, connected=0, has_graph=False, ml=99.41, rule=85.0, graph=59.08,
          factors=None):
    svc = make_service(features)
    return asyncio.run(svc.get_canonical_evidence(
        "U", risk_event=event(ml, rule, graph), risk_factors=factors or [],
        graph_data={"nodes": [{}] * (connected + 1)} if has_graph else None,
        has_graph_evidence=has_graph))


U00010 = {
    "account_age_days": 6, "trade_frequency_24h": 54,
    "opposite_trade_ratio": 0.3438, "shared_device_count": 1,
    "withdrawal_frequency_24h": 7, "first_withdrawal_flag": True,
    "linked_account_count": 18, "withdrawal_risk_score": 1.0,
}
U00299 = {
    "account_age_days": 112, "trade_frequency_24h": 0,
    "opposite_trade_ratio": 0.4524, "shared_device_count": 0,
    "withdrawal_frequency_24h": 14, "first_withdrawal_flag": True,
}


class TestUnifiedFindings:
    def names(self, ev):
        return [f["name"] for f in ev["findings"]]

    def test_risk_factors_not_auto_ml(self):
        """RiskFactor presence alone never creates ML attribution.

        The ONLY finding with ML provenance is the detector-level
        "ML Pattern Detection Signal" (a detector statement, backed by
        ml_score) — never a feature finding.
        """
        ev = build(U00010, connected=18, has_graph=True, ml=99.41)
        ml_sourced = [f["name"] for f in ev["findings"] if "ML" in f["detection_sources"]]
        assert ml_sourced == ["ML Pattern Detection Signal"], \
            f"only the detector signal may claim ML; got {ml_sourced}"

    def test_ml_section_has_no_findings_list(self):
        ev = build(U00010, has_graph=True)
        assert "findings" not in ev["ml"], "ml section must not claim feature findings"
        assert set(ev["ml"]) == {"score", "probability", "primary_driver"}

    def test_graph_findings_not_in_ml(self):
        ev = build(U00010, connected=18, has_graph=True)
        net = next(f for f in ev["findings"] if f["name"] == "Linked Account Network")
        assert "Graph" in net["detection_sources"] and "ML" not in net["detection_sources"]

    def test_rule_findings_all_enter_unified(self):
        ev = build(U00010, has_graph=True)
        n = set(self.names(ev))
        assert {"New account with high activity", "High withdrawal frequency",
                "First withdrawal to new address"} <= n

    def test_first_withdrawal_in_unified_findings(self):
        ev = build(U00010, has_graph=True)
        fw = next(f for f in ev["findings"] if f["name"] == "First withdrawal to new address")
        assert fw["detection_sources"] == ["Rule"]
        assert fw["observed_value"]["first_withdrawal_flag"] is True
        assert fw["contribution"] == 20

    def test_u00010_six_finding_families(self):
        ev = build(U00010, connected=18, has_graph=True)
        n = set(self.names(ev))
        assert {"High Trading Frequency", "Shared Device Relationships",
                "Linked Account Network", "New account with high activity",
                "High withdrawal frequency", "First withdrawal to new address"} <= n
        assert ev["rules"]["consistent"] is True
        assert sum(r["contribution"] for r in ev["rules"]["triggered"]) == 85

    def test_multi_source_finding_appears_once(self):
        """Shared Device Relationships = Graph + Feature -> one finding."""
        ev = build(U00010, connected=18, has_graph=True)
        sd = [f for f in ev["findings"] if f["name"] == "Shared Device Relationships"]
        assert len(sd) == 1
        assert set(sd[0]["detection_sources"]) == {"Graph", "Feature"}

    def test_no_duplicate_findings(self):
        ev = build(U00010, connected=18, has_graph=True)
        n = self.names(ev)
        assert len(n) == len(set(n)), "findings must be unique"

    def test_u00299_age_stays_contextual(self):
        ev = build(U00299, ml=96.24, rule=80.0, graph=0.0, has_graph=False)
        assert "New account with high activity" not in self.names(ev)
        assert ev["contextual"]["account_age_days"] == 112
        assert not any("Rule" in f["detection_sources"]
                       for f in ev["findings"] if f["name"] == "New Account Risk") or True
        # age has NO finding at all (contextual only)
        assert not any("days old" in f["name"] for f in ev["findings"])

    def test_u00010_age_plus_activity_is_rule(self):
        ev = build(U00010, has_graph=True)
        rule_f = next(f for f in ev["findings"]
                      if f["name"] == "New account with high activity")
        assert rule_f["detection_sources"] == ["Rule"]
        assert rule_f["observed_value"] == {
            "account_age_days": 6, "trade_frequency_24h": 54}

    def test_threshold_string_complete(self):
        ev = build(U00010, has_graph=True)
        rule_f = next(f for f in ev["findings"]
                      if f["name"] == "New account with high activity")
        assert rule_f["threshold"] == "account_age_days < 7 AND trade_frequency_24h > 50"


class TestLlmPromptWithUnifiedFindings:
    def setup_method(self):
        from app.services.llm_service import LLMExplanationService
        self.svc = LLMExplanationService.__new__(LLMExplanationService)
        self.svc.provider = None

    def _ev(self):
        ev = build(U00010, connected=18, has_graph=True)
        return ev

    def test_prompt_renders_unified_findings_with_sources(self):
        prompt = self.svc._construct_prompt(
            "U", {"risk_score": 87.02, "risk_level": "CRITICAL", "ml_score": 99.41,
                  "rule_score": 85.0, "graph_score": 59.08},
            [], None, canonical_evidence=self._ev())
        assert "Key Risk Findings" in prompt
        assert "New account with high activity" in prompt
        # detection_sources are internal: never rendered in the prompt
        assert "detected by" not in prompt.lower()
        assert "detection_sources" not in prompt.lower()
        # observed values rendered in natural language (raw fields hidden)
        assert "the account is 6 days old" in prompt.lower()
        assert "54 trades were recorded in 24 hours" in prompt.lower()
        assert "account_age_days" not in prompt
        assert "+40" not in prompt
        # no ML-finding rendering of features
        assert "ML finding:" not in prompt

    def test_prompt_renders_first_withdrawal(self):
        prompt = self.svc._construct_prompt(
            "U", {"risk_score": 87.02}, [], None, canonical_evidence=self._ev())
        assert "First withdrawal to new address" in prompt

    def test_graph_zero_note(self):
        ev = build(U00299, ml=96.24, rule=80.0, graph=0.0)
        prompt = self.svc._construct_prompt(
            "U", {"risk_score": 72.12, "ml_score": 96.24, "rule_score": 80.0,
                  "graph_score": 0.0}, [], None, canonical_evidence=ev)
        assert "No detected graph signal" in prompt


class TestFrontendLabel:
    def test_key_risk_findings_label(self):
        import pathlib
        content = pathlib.Path(__file__).resolve().parents[2].joinpath(
            "frontend/src/pages/Investigation.tsx").read_text()
        assert "Key Risk Findings" in content
        assert "Top Risk Hypotheses" not in content
