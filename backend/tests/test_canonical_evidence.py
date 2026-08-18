"""
Canonical Evidence → LLM Narrative pipeline tests.

Covers the P4 canonical-evidence wiring:
- EvidenceService._derive_rule_evidence derives exactly the deterministic rules
  that RiskScoringService scores (aligned triggers + contributions, incl. the
  previously missing "First withdrawal" rule; no phantom rules).
- EvidenceService.get_canonical_evidence builds the ml/rules/graph/contextual
  structure (graph=0 -> explicit "no detected graph signal", no fake findings).
- The LLM prompt includes ML evidence, triggered Rule evidence (value/threshold/
  contribution), Graph evidence (or the explicit absence note), and contextual
  account age with its "contextual only" note.
- U00299-like case: ml=96.24, rule=80 -> prompt contains opposite-trade-ratio,
  high-withdrawal-frequency, and first-withdrawal rule evidence.
- Parser fix intact (no text block -> explicit ValueError) and timeout = 30s.
"""
import asyncio
from types import SimpleNamespace

from app.config import Settings
from app.services.evidence_service import EvidenceService
from app.services.llm_service import ClaudeProvider, LLMExplanationService
from app.services.risk_service import RiskScoringService


# --------------------------------------------------------------------------- helpers

def make_service():
    return EvidenceService.__new__(EvidenceService)  # pure-method tests, no DB


def derive(features):
    return asyncio.run(make_service()._derive_rule_evidence("U", features))


class TestRuleEvidenceDerivation:
    """Rule evidence must match RiskScoringService scoring exactly."""

    def test_u00299_features_derive_exactly_three_rules_summing_80(self):
        features = {
            "account_age_days": 112,
            "trade_frequency_24h": 0,
            "opposite_trade_ratio": 0.4524,
            "shared_device_count": 0,
            "withdrawal_frequency_24h": 14,
            "first_withdrawal_flag": True,
        }
        rules = derive(features)
        names = {r["rule_name"] for r in rules}
        assert names == {
            "High opposite trade ratio",
            "High withdrawal frequency",
            "First withdrawal to new address",
        }
        assert sum(r["contribution"] for r in rules) == 80
        by_name = {r["rule_name"]: r for r in rules}
        assert by_name["High opposite trade ratio"]["trigger"]["opposite_trade_ratio"] == 0.4524
        assert by_name["High opposite trade ratio"]["threshold"] == "opposite_trade_ratio > 0.4"
        assert by_name["High withdrawal frequency"]["trigger"]["withdrawal_frequency_24h"] == 14
        assert by_name["First withdrawal to new address"]["contribution"] == 20

    def test_alignment_with_scorer_on_random_feature_sets(self):
        """Derived contributions must equal the scorer's rule_score for any features."""
        svc = RiskScoringService.__new__(RiskScoringService)

        def feat(age, tf, opp, sd, wf, fw):
            return SimpleNamespace(
                account_age_days=age, trade_frequency_24h=tf,
                opposite_trade_ratio=opp, shared_device_count=sd,
                withdrawal_frequency_24h=wf, first_withdrawal_flag=fw,
            )

        cases = [
            (5, 60, 0.5, 5, 10, True),   # all rules fire
            (112, 0, 0.4524, 0, 14, True),  # U00299-like
            (30, 10, 0.2, 1, 2, False),  # nothing fires
            (6, 51, 0.41, 4, 6, True),   # boundaries (>, <)
            (7, 50, 0.4, 3, 5, False),   # just outside every boundary
        ]
        for age, tf, opp, sd, wf, fw in cases:
            features = {
                "account_age_days": age, "trade_frequency_24h": tf,
                "opposite_trade_ratio": opp, "shared_device_count": sd,
                "withdrawal_frequency_24h": wf, "first_withdrawal_flag": fw,
            }
            scorer_score = asyncio.run(svc._calculate_rule_score(
                feat(age, tf, opp, sd, wf, fw)))
            derived = sum(r["contribution"] for r in derive(features))
            # Rule Score = sum of contributions capped at 100 (scorer applies min(score, 100))
            assert min(derived, 100) == int(scorer_score), (
                f"evidence/scorer mismatch for {features}: {derived} vs {scorer_score}"
            )

    def test_no_phantom_rules(self):
        """The old derivation invented a 'Large linked account network' rule the
        scorer does not implement — it must not appear."""
        rules = derive({"linked_account_count": 9, "account_age_days": 100})
        assert rules == []


class TestCanonicalEvidenceBuilder:
    """get_canonical_evidence structure (DB-backed via a fake feature row)."""

    @staticmethod
    def _service_with_features(monkey_features):
        svc = EvidenceService.__new__(EvidenceService)

        async def fake_feature(user_id):
            return monkey_features

        async def fake_rules(user_id, fe):
            return await EvidenceService._derive_rule_evidence(svc, user_id, fe)

        svc._get_feature_evidence = fake_feature
        svc._derive_rule_evidence = fake_rules
        return svc

    @staticmethod
    def _event(ml=96.24, rule=80.0, graph=0.0, prob=0.96, reason="ML Pattern Detection"):
        return SimpleNamespace(
            ml_score=ml, rule_score=rule, graph_score=graph,
            risk_probability=prob, primary_reason=reason,
        )

    def run(self, svc, event, factors=None, graph=None, has_graph=False):
        return asyncio.run(svc.get_canonical_evidence(
            "U", risk_event=event, risk_factors=factors or [],
            graph_data=graph, has_graph_evidence=has_graph))

    def test_ml_and_rule_evidence_present_u00299(self):
        svc = self._service_with_features({
            "account_age_days": 112, "trade_frequency_24h": 0,
            "opposite_trade_ratio": 0.4524, "shared_device_count": 0,
            "withdrawal_frequency_24h": 14, "first_withdrawal_flag": True,
        })
        ev = self.run(svc, self._event())
        assert ev["ml"]["score"] == 96.24 and ev["ml"]["primary_driver"] == "ML Pattern Detection"
        # unified findings: rules present, no ML attribution invented
        triggered = {r["rule_name"] for r in ev["rules"]["triggered"]}
        assert {"High opposite trade ratio", "High withdrawal frequency",
                "First withdrawal to new address"} <= triggered
        assert ev["rules"]["consistent"] is True
        finding_names = {f["name"] for f in ev["findings"]}
        assert "First withdrawal to new address" in finding_names
        ml_sourced = [f["name"] for f in ev["findings"] if "ML" in f["detection_sources"]]
        assert ml_sourced == ["ML Pattern Detection Signal"], \
            "only the detector-level signal may claim ML (never feature findings)"

    def test_graph_zero_is_explicit_absence_not_finding(self):
        svc = self._service_with_features({})
        ev = self.run(svc, self._event(), has_graph=False, graph=None)
        assert ev["graph"]["has_evidence"] is False
        assert ev["graph"]["score"] == 0.0
        assert "No detected graph signal" in ev["graph"]["note"]

    def test_graph_evidence_present_when_exists(self):
        svc = self._service_with_features({})
        graph = {"nodes": [{}] * 5}  # user + 4 connected
        ev = self.run(svc, self._event(graph=57.0), graph=graph, has_graph=True)
        assert ev["graph"]["has_evidence"] is True
        assert ev["graph"]["connected_accounts"] == 4
        assert ev["graph"]["score"] == 57.0

    def test_contextual_account_age_with_rule_note(self):
        svc = self._service_with_features({"account_age_days": 112})
        ev = self.run(svc, self._event())
        assert ev["contextual"]["account_age_days"] == 112
        assert "New account with high activity" in ev["contextual"]["account_age_note"]


class TestLlmPromptIncludesEvidence:
    """The constructed prompt must carry the canonical evidence."""

    @staticmethod
    def _evidence(has_graph=False):
        return {
            "ml": {"score": 96.24, "probability": 0.96,
                   "primary_driver": "ML Pattern Detection",
                   "findings": [{"factor_name": "High Trading Frequency",
                                 "detail": "14 trades in 24h"}]},
            "rules": {"score": 80.0, "triggered": [
                {"rule_name": "High opposite trade ratio",
                 "trigger": {"opposite_trade_ratio": 0.4524},
                 "threshold": "opposite_trade_ratio > 0.4", "contribution": 35},
                {"rule_name": "High withdrawal frequency",
                 "trigger": {"withdrawal_frequency_24h": 14},
                 "threshold": "withdrawal_frequency_24h > 5", "contribution": 25},
                {"rule_name": "First withdrawal to new address",
                 "trigger": {"first_withdrawal_flag": True, "withdrawal_frequency_24h": 14},
                 "threshold": "first_withdrawal_flag = true", "contribution": 20},
            ]},
            "graph": {"score": 0.0, "has_evidence": False,
                      "note": "No detected graph signal."},
            "contextual": {"account_age_days": 112,
                           "account_age_note": "Contextual evidence only."},
        }

    def setup_method(self):
        self.svc = LLMExplanationService.__new__(LLMExplanationService)
        self.svc.provider = None

    def _risk_event(self):
        return {"risk_score": 72.12, "risk_level": "HIGH", "primary_reason": "ML Pattern Detection",
                "ml_score": 96.24, "rule_score": 80.0, "graph_score": 0.0}

    def test_prompt_contains_rule_evidence_values_and_contributions(self):
        prompt = self.svc._construct_prompt(
            "U", self._risk_event(), [], None, canonical_evidence=self._evidence())
        # Rules rendered in natural language with observed values; raw
        # thresholds/contributions are presentation-hidden (canonical keeps them)
        assert "High opposite trade ratio" in prompt
        assert "45.24%" in prompt
        assert "High withdrawal frequency" in prompt and "14 withdrawals" in prompt
        assert "First withdrawal to new address" in prompt
        assert "deterministic rules triggered" in prompt
        assert "+35" not in prompt and "+25" not in prompt and "+20" not in prompt
        assert "opposite_trade_ratio > 0.4" not in prompt

    def test_prompt_contains_ml_and_graph_and_contextual(self):
        prompt = self.svc._construct_prompt(
            "U", self._risk_event(), [], None, canonical_evidence=self._evidence())
        assert "Graph detection: score 0" in prompt
        assert "No detected graph signal" in prompt
        assert "the account is 112 days old" in prompt
        assert "contextual evidence only" in prompt
        # unified findings rendering (no ML-finding phrasing)
        assert "Key Risk Findings" in prompt
        assert "ML finding:" not in prompt

    def test_prompt_without_evidence_still_builds(self):
        prompt = self.svc._construct_prompt("U", self._risk_event(), [], None)
        assert "ML Score: 96.24" in prompt


class TestConfigAndParserRegression:
    """Timeout = 30s (config) and the no-text-block parser fix remain intact."""

    def test_timeout_default_is_30(self):
        assert Settings().EXPLAIN_LLM_TIMEOUT_SECONDS == 30

    def test_no_text_block_raises_explicit_error(self):
        provider = ClaudeProvider.__new__(ClaudeProvider)

        class _Fake:
            def create(self, **kwargs):
                m = SimpleNamespace()
                m.content = [SimpleNamespace(type="thinking", text=None)]
                return m
        provider.client = SimpleNamespace(messages=_Fake())
        try:
            asyncio.run(provider.generate_explanation(prompt="p"))
            assert False, "should raise"
        except ValueError as e:
            assert "no text content block" in str(e)
