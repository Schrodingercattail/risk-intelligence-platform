"""
Authoritative finding semantics regression tests.

Two source-of-truth defects these guard against (both observed on the real
U00010 explanation):

1. SEMANTIC DUPLICATION — "First withdrawal to new address" (rule) and
   "Abnormal Withdrawal Behavior" (feature) described the SAME underlying
   condition. Both features derive from Withdrawal.is_new_address:

       first_withdrawal_flag = any(is_new_address)          # a bool
       withdrawal_risk_score = count(is_new_address)/total  # the ratio

   so flag is true iff ratio > 0 (verified across all 2001 feature_table
   rows: 671 rows have both, 0 rows disagree). Emitting both produced two
   numbered findings for one condition. The fix removes the feature finding
   and carries the ratio on the surviving rule finding, so no observed
   information is lost.

2. COUNT BLIND WORDING — relationship evidence hardcoded a plural (or the
   "(s)" cop-out) instead of deriving noun/verb form from the authoritative
   count, and mislabelled shared_device_count (a DEVICE count) as an account
   count. For U00010 the narrative said "1 linked accounts through shared
   devices" while 18 accounts actually share that device.

Distinct findings that must STAY distinct are asserted too: high withdrawal
FREQUENCY (a velocity claim) is genuinely different from a first withdrawal
to a NEW ADDRESS (a destination-history claim), and the shared-DEVICE count
is genuinely different from the linked-ACCOUNT count.
"""
import asyncio
from types import SimpleNamespace

from app.services.evidence_service import EvidenceService
from app.services.llm_service import LLMExplanationService
from app.services.risk_service import RiskScoringService
from app.utils.pluralization import counted_noun, was_were

# Real U00010 feature values (feature_table row + derived rule evidence).
U00010_FEATURES = {
    "account_age_days": 6, "trade_frequency_24h": 54,
    "opposite_trade_ratio": 0.3438, "shared_device_count": 1,
    "withdrawal_frequency_24h": 7, "first_withdrawal_flag": True,
    "linked_account_count": 18, "withdrawal_risk_score": 1.0,
}


def build_evidence(features=None, connected=18, has_graph=True,
                   risk_factors=()):
    """Build canonical evidence from feature values (no DB)."""
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
            ml_score=99.41, rule_score=85.0, graph_score=59.08,
            risk_probability=0.99, primary_reason="ML Pattern Detection"),
        risk_factors=list(risk_factors),
        graph_data={"nodes": [{}] * (connected + 1)} if has_graph else None,
        has_graph_evidence=has_graph))


def finding_names(ev):
    return [f["name"] for f in ev["findings"]]


# --------------------------------------------------------------------------------------
# 1. The authoritative finding set has the intended semantic identity
# --------------------------------------------------------------------------------------

class TestFindingSemanticIdentity:
    """One conceptual finding appears exactly once in canonical evidence."""

    def test_u00010_finding_set(self):
        names = finding_names(build_evidence())
        assert names == [
            "ML Pattern Detection Signal",
            "New account with high activity",
            "High withdrawal frequency",
            "First withdrawal to new address",
            "Shared Device Relationships",
            "Linked Account Network",
            "High Trading Frequency",
            "Opposite Trade Ratio",
        ]

    def test_findings_unique(self):
        names = finding_names(build_evidence())
        assert len(names) == len(set(names)), "duplicate finding names emitted"

    def test_first_withdrawal_carries_the_ratio(self):
        """The surviving finding states the full new-address exposure.

        withdrawal_risk_score no longer forms its own finding, so its value
        must travel on the first-withdrawal rule finding (observed_value) and
        its business rendering must appear in the evidence text.
        """
        ev = build_evidence()
        fw = next(f for f in ev["findings"]
                  if f["name"] == "First withdrawal to new address")
        assert fw["observed_value"]["withdrawal_risk_score"] == 1.0
        assert fw["observed_value"]["first_withdrawal_flag"] is True
        assert fw["observed_value"]["withdrawal_frequency_24h"] == 7
        assert "100.00% of withdrawals were sent to newly encountered addresses" \
            in fw["evidence"]
        assert fw["contribution"] == 20, "rule contribution must not change"

    def test_partial_new_address_ratio_also_merges(self):
        """A partial ratio (U00201: 3/13 new) still yields exactly one finding."""
        feats = dict(U00010_FEATURES, withdrawal_risk_score=0.2308,
                     withdrawal_frequency_24h=13)
        names = finding_names(build_evidence(features=feats))
        assert "First withdrawal to new address" in names
        assert "Abnormal Withdrawal Behavior" not in names
        fw = next(f for f in build_evidence(features=feats)["findings"]
                  if f["name"] == "First withdrawal to new address")
        assert fw["observed_value"]["withdrawal_risk_score"] == 0.2308
        assert "23.08%" in fw["evidence"]

    def test_zero_new_address_ratio_emits_neither(self):
        """No new-address withdrawals -> no finding at all for the condition."""
        feats = dict(U00010_FEATURES, withdrawal_risk_score=0.0,
                     first_withdrawal_flag=False)
        names = finding_names(build_evidence(features=feats))
        assert "First withdrawal to new address" not in names
        assert "Abnormal Withdrawal Behavior" not in names


# --------------------------------------------------------------------------------------
# 2. Redundant findings are not emitted when they represent the same condition
# --------------------------------------------------------------------------------------

class TestNoRedundantFindings:
    def test_abnormal_withdrawal_behavior_not_emitted_for_u00010(self):
        names = finding_names(build_evidence())
        assert "Abnormal Withdrawal Behavior" not in names, \
            "withdrawal_risk_score and first_withdrawal_flag are the same " \
            "observation; only 'First withdrawal to new address' may represent it"

    def test_feature_map_no_longer_maps_withdrawal_risk_score(self):
        assert "withdrawal_risk_score" not in EvidenceService._FEATURE_FINDING_NAMES

    def test_scorer_no_longer_persists_abnormal_withdrawal_factor(self):
        """The persistence-side factor mapping must drop the redundant entry."""
        svc = RiskScoringService.__new__(RiskScoringService)
        # factor_mapping is built inside _create_risk_factors; assert via the
        # source of truth the method uses: _get_factor_description falls
        # through to the generic formatter for the removed label.
        assert svc._get_factor_description("Abnormal Withdrawal Behavior", 1.0) \
            == "Value: 1.0"

    def test_no_factor_description_defined_for_the_merged_finding(self):
        """The old label must fall through to the generic formatter."""
        assert RiskScoringService.__new__(
            RiskScoringService)._get_factor_description(
            "Abnormal Withdrawal Behavior", 1.0) == "Value: 1.0"

    def test_prompt_does_not_supply_the_redundant_finding(self):
        svc = LLMExplanationService.__new__(LLMExplanationService)
        svc.provider = None
        prompt = svc._construct_prompt(
            "U", {"risk_score": 87.02, "risk_level": "CRITICAL",
                  "ml_score": 99.41, "rule_score": 85.0, "graph_score": 59.08},
            [], None, canonical_evidence=build_evidence())
        assert "abnormal withdrawal behavior" not in prompt.lower()
        # the surviving finding's business rendering IS supplied
        assert "newly encountered addresses" in prompt.lower()


# --------------------------------------------------------------------------------------
# 3. Genuinely distinct findings remain distinct
# --------------------------------------------------------------------------------------

class TestDistinctFindingsStayDistinct:
    def test_withdrawal_frequency_distinct_from_new_address(self):
        """Velocity claim vs destination-history claim are different findings."""
        ev = build_evidence()
        names = finding_names(ev)
        assert "High withdrawal frequency" in names
        assert "First withdrawal to new address" in names
        freq = next(f for f in ev["findings"]
                    if f["name"] == "High withdrawal frequency")
        newaddr = next(f for f in ev["findings"]
                       if f["name"] == "First withdrawal to new address")
        # different rules, different triggers, different contributions
        assert freq["contribution"] == 25 and newaddr["contribution"] == 20
        assert freq["observed_value"]["withdrawal_frequency_24h"] == 7
        assert freq["observed_value"].get("first_withdrawal_flag") is None

    def test_shared_devices_distinct_from_linked_accounts(self):
        """Device count and linked-account count are different findings."""
        ev = build_evidence()
        names = finding_names(ev)
        assert "Shared Device Relationships" in names
        assert "Linked Account Network" in names
        sd = next(f for f in ev["findings"]
                  if f["name"] == "Shared Device Relationships")
        lan = next(f for f in ev["findings"]
                   if f["name"] == "Linked Account Network")
        assert sd["observed_value"] == {"shared_device_count": 1}
        assert lan["observed_value"] == {"connected_accounts": 18}
        assert sd["supporting_feature"] != lan["supporting_feature"]

    def test_below_threshold_observation_distinct_from_rule(self):
        """Opposite Trade Ratio (below threshold) != Coordinated Trading Pattern."""
        names = finding_names(build_evidence())
        assert "Opposite Trade Ratio" in names
        assert "Coordinated Trading Pattern" not in names
        above = finding_names(build_evidence(
            features=dict(U00010_FEATURES, opposite_trade_ratio=0.55)))
        assert "Coordinated Trading Pattern" in above
        assert "Opposite Trade Ratio" not in above

    def test_rule_evidence_alignment_with_scorer_unchanged(self):
        """Merging findings must not change rule scoring semantics."""
        svc = RiskScoringService.__new__(RiskScoringService)
        features = {
            "account_age_days": 6, "trade_frequency_24h": 54,
            "opposite_trade_ratio": 0.3438, "shared_device_count": 1,
            "withdrawal_frequency_24h": 7, "first_withdrawal_flag": True,
        }
        esvc = EvidenceService.__new__(EvidenceService)
        derived = sum(r["contribution"]
                      for r in asyncio.run(
                          EvidenceService._derive_rule_evidence(esvc, "U", features)))
        scorer = asyncio.run(svc._calculate_rule_score(SimpleNamespace(
            account_age_days=6, trade_frequency_24h=54,
            opposite_trade_ratio=0.3438, shared_device_count=1,
            withdrawal_frequency_24h=7, first_withdrawal_flag=True)))
        assert min(derived, 100) == int(scorer) == 85


# --------------------------------------------------------------------------------------
# 4. Linked-account wording: count == 1
# --------------------------------------------------------------------------------------

class TestLinkedAccountWordingSingular:
    def test_shared_device_evidence_singular(self):
        """shared_device_count=1 must read as one DEVICE, grammatically."""
        ev = build_evidence()  # U00010: shared_device_count = 1
        sd = next(f for f in ev["findings"]
                  if f["name"] == "Shared Device Relationships")
        assert sd["evidence"] == \
            "1 shared device was used by this account and other users"

    def test_linked_account_evidence_singular(self):
        ev = build_evidence(connected=1)
        lan = next(f for f in ev["findings"]
                   if f["name"] == "Linked Account Network")
        assert lan["evidence"] == \
            "1 connected account was detected through shared devices"

    def test_factor_description_singular(self):
        desc = RiskScoringService.__new__(
            RiskScoringService)._get_factor_description(
            "Shared Device Relationships", 1)
        assert desc == "1 shared device was used by this account and other users"

    def test_prompt_humanized_singular(self):
        svc = LLMExplanationService.__new__(LLMExplanationService)
        out = svc._humanize_observed("Shared Device Relationships",
                                     {"shared_device_count": 1})
        assert out == "1 shared device was used by this account and other users"

    def test_no_parenthetical_plural_cop_out(self):
        ev = build_evidence()
        for f in ev["findings"]:
            assert "(s)" not in f["evidence"], \
                f"ungrammatical '(s)' wording in {f['name']}: {f['evidence']!r}"

    def test_fallback_evidence_singular(self):
        """No persisted RiskFactor row -> fallback still grammatical."""
        out = EvidenceService._render_fallback_evidence("shared_device_count", 1)
        assert out == "1 shared device was used by this account and other users"
        out = EvidenceService._render_fallback_evidence("linked_account_count", 1)
        assert out == "1 connected account was detected through shared devices"


# --------------------------------------------------------------------------------------
# 5. Linked-account wording: count > 1
# --------------------------------------------------------------------------------------

class TestLinkedAccountWordingPlural:
    def test_shared_device_evidence_plural(self):
        ev = build_evidence(features=dict(U00010_FEATURES, shared_device_count=4))
        sd = next(f for f in ev["findings"]
                  if f["name"] == "Shared Device Relationships")
        assert sd["evidence"] == \
            "4 shared devices were used by this account and other users"

    def test_linked_account_evidence_plural(self):
        ev = build_evidence(connected=18)  # U00010: linked_account_count = 18
        lan = next(f for f in ev["findings"]
                   if f["name"] == "Linked Account Network")
        assert lan["evidence"] == \
            "18 connected accounts were detected through shared devices"

    def test_factor_description_plural(self):
        desc = RiskScoringService.__new__(
            RiskScoringService)._get_factor_description(
            "Linked Account Network", 18)
        assert desc == "18 connected accounts were detected through shared devices"

    def test_prompt_humanized_plural(self):
        svc = LLMExplanationService.__new__(LLMExplanationService)
        out = svc._humanize_observed("Linked Account Network",
                                     {"connected_accounts": 18})
        assert out == "18 connected accounts were detected through shared devices"

    def test_fallback_evidence_plural(self):
        assert EvidenceService._render_fallback_evidence(
            "shared_device_count", 4) == \
            "4 shared devices were used by this account and other users"
        assert EvidenceService._render_fallback_evidence(
            "linked_account_count", 18) == \
            "18 connected accounts were detected through shared devices"

    def test_wording_tracks_arbitrary_counts(self):
        """Not hard-coded: the count in the sentence equals the observed value."""
        for count in (1, 2, 3, 7, 17, 18, 99):
            ev = build_evidence(connected=count)
            lan = next(f for f in ev["findings"]
                       if f["name"] == "Linked Account Network")
            assert str(count) in lan["evidence"]
            assert counted_noun(count, "connected account",
                                "connected accounts") in lan["evidence"]
            assert was_were(count) in lan["evidence"]
