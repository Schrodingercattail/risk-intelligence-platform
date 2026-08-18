"""
Focused tests for the P2 grounding/calibration changes.

Covers:
- The LLM default system prompt contains the grounding contract (evidence boundary,
  account-age semantics, score semantics, graph-score semantics, fraud-typology calibration,
  investigation boundary). Intentionally asserts on key phrases, not on full natural-language
  output (avoid brittle tests).
- The account-age risk factor is labelled and described as CONTEXTUAL evidence, not as a
  thresholded policy rule ("New Account Risk").
- The deterministic "New account with high activity" scoring rule threshold and contribution
  are unchanged (account_age_days < 7 AND trade_frequency_24h > 50 -> +40).

These tests do NOT call the LLM and do NOT assert on generated explanation text.
"""
import asyncio
from types import SimpleNamespace

from app.services.llm_service import ClaudeProvider
from app.services.risk_service import RiskScoringService


# --------------------------------------------------------------------------------------
# TASK 2 — grounding contract present in the system prompt
# --------------------------------------------------------------------------------------

class TestSystemPromptGroundingContract:
    """The default system prompt must carry the P2 grounding constraints."""

    def setup_method(self):
        # _default_system_prompt lives on ClaudeProvider (used as the system role when no
        # explicit system_prompt is passed). Bypass __init__ to avoid needing an API key.
        self.service = ClaudeProvider.__new__(ClaudeProvider)
        self.prompt = self.service._default_system_prompt()

    def test_prompt_has_grounding_contract_section(self):
        assert "GROUNDING CONTRACT" in self.prompt

    def test_evidence_boundary_rule(self):
        # Rule 1: only state factors present in evidence; no invented factors/typologies.
        assert "Evidence boundary" in self.prompt
        assert "Do not invent" in self.prompt

    def test_account_age_rule(self):
        # Rule 2: account age is contextual; no invented thresholds/narratives; references the
        # one real rule by name so the LLM can distinguish context from trigger.
        assert "CONTEXTUAL EVIDENCE" in self.prompt
        assert "New account with high activity" in self.prompt
        assert "sleeper account" in self.prompt
        assert "threshold" in self.prompt.lower()

    def test_risk_score_semantics_rule(self):
        # Rule 3: scores are signals, not probabilities/certainties.
        assert "SYSTEM SCORES" in self.prompt
        assert "probability of fraud" in self.prompt
        assert "certainty of malicious intent" in self.prompt

    def test_graph_score_semantics_rule(self):
        # Rule 4: Graph Score = 0 means no signal; no lone-wolf/OpSec inferences.
        flat = " ".join(self.prompt.split())  # normalize line wraps
        assert "Graph Score = 0" in flat
        assert "lone wolf" in flat
        assert "OpSec" in flat

    def test_fraud_typology_calibration_rule(self):
        # Rule 5: no unsupported typologies; use calibrated/hedged language.
        assert "money laundering" in self.prompt
        assert "calibrated language" in self.prompt
        assert "may suggest" in self.prompt

    def test_investigation_boundary_rule(self):
        # Rule 6: investigation support, not enforcement; no unverified hypothesis as fact.
        assert "INVESTIGATION SUPPORT" in self.prompt
        assert "review/validation" in self.prompt


# --------------------------------------------------------------------------------------
# ClaudeProvider response parsing (Anthropic-compatible gateway blocks)
# --------------------------------------------------------------------------------------

class TestClaudeContentBlockExtraction:
    """generate_explanation must return the type='text' block, not content[0]."""

    def setup_method(self):
        # Bypass __init__ (needs an API key); only patch the client afterwards.
        self.provider = ClaudeProvider.__new__(ClaudeProvider)

    @staticmethod
    def _run(provider, content):
        class _FakeMessages:
            def create(self, **kwargs):
                class _Msg:
                    pass
                m = _Msg()
                m.content = content
                return m
        class _FakeClient:
            messages = _FakeMessages()
        provider.client = _FakeClient()
        return asyncio.run(provider.generate_explanation(prompt="p"))

    def test_thinking_block_then_text_block(self):
        """Gateway-style response: thinking block (text=None) first, text after."""
        thinking = SimpleNamespace(type="thinking", text=None, thinking="reasoning...")
        text = SimpleNamespace(type="text", text="LLM test OK")
        result = self._run(self.provider, [thinking, text])
        assert result == "LLM test OK"

    def test_single_text_block_still_works(self):
        text = SimpleNamespace(type="text", text="Normal single-block response")
        assert self._run(self.provider, [text]) == "Normal single-block response"

    def test_text_block_not_first_and_not_last(self):
        blocks = [
            SimpleNamespace(type="thinking", text=None),
            SimpleNamespace(type="text", text="the answer"),
            SimpleNamespace(type="tool_use", text=None),
        ]
        assert self._run(self.provider, blocks) == "the answer"

    def test_no_text_block_raises_explicit_error(self):
        """No text block -> clear ValueError naming the block types, not None."""
        blocks = [SimpleNamespace(type="thinking", text=None)]
        try:
            self._run(self.provider, blocks)
            assert False, "should have raised"
        except ValueError as e:
            assert "no text content block" in str(e)
            assert "thinking" in str(e)


# --------------------------------------------------------------------------------------
# TASK 1 — account-age factor is contextual, not a policy threshold
# --------------------------------------------------------------------------------------

class TestAccountAgeFactorSemantics:
    """The account-age factor must read as contextual evidence, not a thresholded rule."""

    def setup_method(self):
        # Bypass __init__ (avoids DB session + ML model load); the methods under test are pure.
        self.service = RiskScoringService.__new__(RiskScoringService)

    def test_account_age_factor_description_is_contextual(self):
        desc = self.service._get_factor_description("Account Age", 6)
        assert "6 days" in desc                       # accurate value is reported
        assert "new account indicator" not in desc    # old misleading phrase is gone
        assert "not a policy threshold" in desc       # explicitly states it is not a rule

    def test_legacy_new_account_risk_label_no_longer_defined(self):
        # The old factor label must no longer resolve to a tailored description; it falls back
        # to the generic formatter, proving it is not an emitted factor anymore.
        legacy = self.service._get_factor_description("New Account Risk", 6)
        assert legacy == "Value: 6"


# --------------------------------------------------------------------------------------
# TASK 1 (regression) — the deterministic new-account rule is unchanged
# --------------------------------------------------------------------------------------

class TestNewAccountRuleUnchanged:
    """The real scoring rule 'New account with high activity' keeps its threshold and weight."""

    def setup_method(self):
        self.service = RiskScoringService.__new__(RiskScoringService)

    @staticmethod
    def _feature(**over):
        base = dict(
            account_age_days=0,
            trade_frequency_24h=0,
            opposite_trade_ratio=0,
            shared_device_count=0,
            withdrawal_frequency_24h=0,
            first_withdrawal_flag=False,
        )
        base.update(over)
        return SimpleNamespace(**base)

    def test_rule_fires_when_young_and_high_activity(self):
        # account_age_days < 7 AND trade_frequency_24h > 50 -> +40 (and nothing else fires)
        score = asyncio.run(self.service._calculate_rule_score(
            self._feature(account_age_days=5, trade_frequency_24h=60)
        ))
        assert score == 40

    def test_rule_does_not_fire_when_account_too_old(self):
        score = asyncio.run(self.service._calculate_rule_score(
            self._feature(account_age_days=30, trade_frequency_24h=60)
        ))
        assert score == 0

    def test_rule_does_not_fire_when_young_but_low_activity(self):
        score = asyncio.run(self.service._calculate_rule_score(
            self._feature(account_age_days=5, trade_frequency_24h=10)
        ))
        assert score == 0
