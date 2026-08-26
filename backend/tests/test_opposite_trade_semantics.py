"""
Opposite Trade Ratio Semantic Clarity Tests.

These tests verify the semantic distinction between:
1. Observed opposite-trading behavior (0 < opposite_trade_ratio <= 0.4)
2. Coordinated-trading rule triggered (opposite_trade_ratio > 0.4)

The key behavioral expectations:
- Factor is created for ANY non-zero opposite_trade_ratio
- Factor name depends on threshold: "Opposite Trade Ratio" vs "Coordinated Trading Pattern"
- Rule contribution (+35) ONLY when value > 0.4
- Factor description clearly indicates rule status

U00010 (opposite_trade_ratio = 0.3438) should:
- Create factor "Opposite Trade Ratio"
- NOT trigger coordinated-trading rule
- NOT receive +35 score contribution
"""
import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

from app.services.risk_service import RiskScoringService
from app.models.database import RiskEvent, FeatureTable


def make_mock_feature(opposite_trade_ratio):
    """Create a mock FeatureTable with specific opposite_trade_ratio."""
    feature = Mock(spec=FeatureTable)
    feature.opposite_trade_ratio = Decimal(str(opposite_trade_ratio))
    feature.account_age_days = 100
    feature.shared_device_count = 0
    feature.linked_account_count = 0
    feature.trade_frequency_24h = 10
    feature.trade_frequency_7d = 20
    feature.avg_trade_size = Decimal("1000.0")
    feature.trade_volume_24h = Decimal("10000.0")
    feature.active_days_count = 50
    feature.withdrawal_risk_score = Decimal("0.1")
    feature.withdrawal_frequency_24h = 0
    feature.withdrawal_volume_24h = Decimal("0.0")
    feature.first_withdrawal_flag = False
    return feature


class TestOppositeTradeSemantics:
    """Test semantic clarity of opposite_trade_ratio handling."""

    def test_ratio_001_creates_observation_not_rule(self):
        """0.01: Creates factor, no rule trigger, no +35 score."""
        ratio = 0.01
        feature = make_mock_feature(ratio)

        # Rule scoring: should NOT trigger
        score = asyncio.run(RiskScoringService.__new__(RiskScoringService)._calculate_rule_score(feature))
        assert score == 0.0, f"Ratio {ratio}: Expected 0 rule_score, got {score}"

    def test_ratio_3438_creates_observation_not_rule(self):
        """0.3438: U00010 case - creates factor, no rule trigger, no +35 score."""
        ratio = 0.3438
        feature = make_mock_feature(ratio)

        # Rule scoring: should NOT trigger
        score = asyncio.run(RiskScoringService.__new__(RiskScoringService)._calculate_rule_score(feature))
        assert score == 0.0, f"Ratio {ratio}: Expected 0 rule_score, got {score}"

    def test_ratio_40_no_rule_trigger(self):
        """0.40: Exactly at threshold - no rule trigger, no +35 score."""
        ratio = 0.40
        feature = make_mock_feature(ratio)

        # Rule scoring: should NOT trigger (must be > 0.4)
        score = asyncio.run(RiskScoringService.__new__(RiskScoringService)._calculate_rule_score(feature))
        assert score == 0.0, f"Ratio {ratio}: Expected 0 rule_score, got {score}"

    def test_ratio_41_triggers_rule(self):
        """0.41: Rule triggered, +35 score contribution."""
        ratio = 0.41
        feature = make_mock_feature(ratio)

        # Rule scoring: should trigger
        score = asyncio.run(RiskScoringService.__new__(RiskScoringService)._calculate_rule_score(feature))
        assert score == 35.0, f"Ratio {ratio}: Expected 35 rule_score, got {score}"

    def test_ratio_60_triggers_rule(self):
        """0.60: Rule triggered, +35 score contribution."""
        ratio = 0.60
        feature = make_mock_feature(ratio)

        # Rule scoring: should trigger
        score = asyncio.run(RiskScoringService.__new__(RiskScoringService)._calculate_rule_score(feature))
        assert score == 35.0, f"Ratio {ratio}: Expected 35 rule_score, got {score}"


class TestFactorNameSemantics:
    """Test that factor names distinguish observation from rule trigger."""

    def test_below_threshold_uses_neutral_name(self):
        """Ratios below threshold should get 'Opposite Trade Ratio' name."""
        svc = RiskScoringService.__new__(RiskScoringService)

        # Mock the DB operations
        mock_db = Mock()
        mock_risk_event = Mock(spec=RiskEvent)
        mock_risk_event.id = 1

        # Set db attribute on service
        svc.db = mock_db

        test_ratios = [0.01, 0.20, 0.3438, 0.40]

        for ratio in test_ratios:
            feature = make_mock_feature(ratio)

            # Capture created factors
            created_factors = []
            def capture_add(factor):
                created_factors.append(factor)

            mock_db.add = capture_add

            # Run factor creation
            asyncio.run(svc._create_risk_factors(mock_risk_event, feature))

            # Find opposite trade factor
            opp_factor = next((f for f in created_factors if "opposite" in f.factor_name.lower() or "trade" in f.factor_name.lower()), None)

            assert opp_factor is not None, f"Ratio {ratio}: Expected factor to be created"
            assert opp_factor.factor_name == "Opposite Trade Ratio", (
                f"Ratio {ratio}: Expected 'Opposite Trade Ratio', got '{opp_factor.factor_name}'"
            )

    def test_above_threshold_uses_rule_triggered_name(self):
        """Ratios above threshold should get 'Coordinated Trading Pattern' name."""
        svc = RiskScoringService.__new__(RiskScoringService)

        # Mock the DB operations
        mock_db = Mock()
        mock_risk_event = Mock(spec=RiskEvent)
        mock_risk_event.id = 1

        # Set db attribute on service
        svc.db = mock_db

        test_ratios = [0.41, 0.50, 0.60]

        for ratio in test_ratios:
            feature = make_mock_feature(ratio)

            # Capture created factors
            created_factors = []
            def capture_add(factor):
                created_factors.append(factor)

            mock_db.add = capture_add

            # Run factor creation
            asyncio.run(svc._create_risk_factors(mock_risk_event, feature))

            # Find opposite trade factor
            opp_factor = next((f for f in created_factors if "opposite" in f.factor_name.lower() or "trade" in f.factor_name.lower() or "coordinated" in f.factor_name.lower()), None)

            assert opp_factor is not None, f"Ratio {ratio}: Expected factor to be created"
            assert opp_factor.factor_name == "Coordinated Trading Pattern", (
                f"Ratio {ratio}: Expected 'Coordinated Trading Pattern', got '{opp_factor.factor_name}'"
            )


class TestFactorDescriptionSemantics:
    """Test that factor descriptions clearly indicate rule status."""

    def test_below_threshold_description_shows_not_triggered(self):
        """Below threshold: description should indicate rule not triggered."""
        svc = RiskScoringService.__new__(RiskScoringService)

        # Mock the DB operations
        mock_db = Mock()
        mock_risk_event = Mock(spec=RiskEvent)
        mock_risk_event.id = 1

        # Set db attribute on service
        svc.db = mock_db

        ratio = 0.3438
        feature = make_mock_feature(ratio)

        # Capture created factors
        created_factors = []
        def capture_add(factor):
            created_factors.append(factor)

        mock_db.add = capture_add

        # Run factor creation
        asyncio.run(svc._create_risk_factors(mock_risk_event, feature))

        # Find opposite trade factor
        opp_factor = next((f for f in created_factors if "Opposite Trade Ratio" in f.factor_name), None)

        assert opp_factor is not None, "Expected factor to be created"
        assert "below the 40% threshold for the coordinated trading rule" in opp_factor.factor_description, (
            f"Description must use the below-threshold business wording: {opp_factor.factor_description}"
        )
        assert "34.38%" in opp_factor.factor_description, (
            f"Description should show observed value: {opp_factor.factor_description}"
        )
        # narrative-contract guard: no raw threshold syntax in user-facing text
        assert ">" not in opp_factor.factor_description, (
            f"Description must not contain raw comparison syntax: {opp_factor.factor_description}"
        )

    def test_above_threshold_description_shows_triggered(self):
        """Above threshold: description should indicate rule triggered."""
        svc = RiskScoringService.__new__(RiskScoringService)

        # Mock the DB operations
        mock_db = Mock()
        mock_risk_event = Mock(spec=RiskEvent)
        mock_risk_event.id = 1

        # Set db attribute on service
        svc.db = mock_db

        ratio = 0.50
        feature = make_mock_feature(ratio)

        # Capture created factors
        created_factors = []
        def capture_add(factor):
            created_factors.append(factor)

        mock_db.add = capture_add

        # Run factor creation
        asyncio.run(svc._create_risk_factors(mock_risk_event, feature))

        # Find opposite trade factor
        opp_factor = next((f for f in created_factors if "Coordinated" in f.factor_name), None)

        assert opp_factor is not None, "Expected factor to be created"
        assert "exceeded the 40% threshold, triggering the coordinated trading rule" in opp_factor.factor_description, (
            f"Description must use the threshold-triggered business wording: {opp_factor.factor_description}"
        )
        assert "50.00%" in opp_factor.factor_description, (
            f"Description should show observed value: {opp_factor.factor_description}"
        )
        assert ">" not in opp_factor.factor_description, (
            f"Description must not contain raw comparison syntax: {opp_factor.factor_description}"
        )


class TestU00010Behavior:
    """Test specific U00010 behavior (opposite_trade_ratio = 0.3438)."""

    def test_u00010_semantics(self):
        """U00010: 34.38% should be observation, not triggered rule."""
        ratio = 0.3438
        feature = make_mock_feature(ratio)

        # Rule scoring: should NOT trigger
        score = asyncio.run(RiskScoringService.__new__(RiskScoringService)._calculate_rule_score(feature))
        assert score == 0.0, f"U00010: Expected 0 rule_score, got {score}"

        # Factor creation should use neutral name
        svc = RiskScoringService.__new__(RiskScoringService)
        mock_db = Mock()
        mock_risk_event = Mock(spec=RiskEvent)
        mock_risk_event.id = 1

        # Set db attribute on service
        svc.db = mock_db

        created_factors = []
        def capture_add(factor):
            created_factors.append(factor)
        mock_db.add = capture_add

        asyncio.run(svc._create_risk_factors(mock_risk_event, feature))

        opp_factor = next((f for f in created_factors if "Opposite Trade Ratio" in f.factor_name), None)
        assert opp_factor is not None, "U00010: Expected 'Opposite Trade Ratio' factor"
        assert opp_factor.factor_name == "Opposite Trade Ratio", (
            f"U00010: Expected 'Opposite Trade Ratio', got '{opp_factor.factor_name}'"
        )
        assert "below the 40% threshold for the coordinated trading rule" in opp_factor.factor_description, (
            f"U00010: Description must use the below-threshold business wording: {opp_factor.factor_description}"
        )


class TestThresholdBoundary:
    """Test exact threshold behavior (0.4)."""

    def test_exactly_at_threshold_no_trigger(self):
        """0.40: Exactly at threshold should NOT trigger (must be > 0.4)."""
        ratio = 0.40
        feature = make_mock_feature(ratio)

        # Rule scoring: should NOT trigger
        score = asyncio.run(RiskScoringService.__new__(RiskScoringService)._calculate_rule_score(feature))
        assert score == 0.0, f"Ratio 0.40: Expected 0 rule_score, got {score}"

    def test_just_above_threshold_triggers(self):
        """0.41: Just above threshold should trigger."""
        ratio = 0.41
        feature = make_mock_feature(ratio)

        # Rule scoring: should trigger
        score = asyncio.run(RiskScoringService.__new__(RiskScoringService)._calculate_rule_score(feature))
        assert score == 35.0, f"Ratio 0.41: Expected 35 rule_score, got {score}"
