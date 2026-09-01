"""
Risk Scoring Service

Orchestrates ML + Rules + Graph for combined risk scoring.
Service Layer - Independent of API, coordinates multiple scoring components.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from app.models.database import (
    RiskEvent, RiskFactor, User, FeatureTable,
    RiskLevel, CaseStatus,
)
from app.config import settings
from app.ml.model import MLInferenceService
from app.utils.pluralization import counted_noun, was_were


class RiskScoringService:
    """
    Risk Scoring Service

    Orchestrates ML + Rules + Graph for combined risk scoring.
    Input: feature_table
    Output: risk_events with ml_score, rule_score, graph_score, final_score

    Service boundary: This service coordinates scoring but delegates
    actual ML inference and rule evaluation to appropriate components.
    """

    def __init__(self, db: AsyncSession):
        """Initialize risk service with database session and ML model."""
        self.db = db
        self.ml_service = MLInferenceService()

    async def score_user(
        self,
        user_id: str,
        pipeline_run_id: Optional[str] = None,
        model_version: Optional[str] = None
    ) -> RiskEvent:
        """
        Calculate risk scores for a user.

        Args:
            user_id: User to score
            pipeline_run_id: Optional pipeline run identifier for traceability
            model_version: Optional model version used for scoring

        Returns:
            RiskEvent with all scores
        """
        # Get user features
        feature = await self.db.get(FeatureTable, user_id)
        if not feature:
            raise ValueError(f"No features found for user {user_id}")

        # Calculate component scores
        ml_probability, ml_score = await self._calculate_ml_score(feature)
        rule_score = await self._calculate_rule_score(feature)
        graph_score = await self._calculate_graph_score(user_id)

        # Combine scores (weighted)
        final_score = self._combine_scores(ml_score, rule_score, graph_score)

        # DEBUG: Log score calculation
        print(f"[RISK_DEBUG] SCORE_CALCULATION: user_id={user_id}, ml_score={ml_score:.2f}, rule_score={rule_score:.2f}, graph_score={graph_score:.2f}, final_score={final_score:.2f}")
        print(f"[RISK_DEBUG] THRESHOLDS: HIGH={settings.HIGH_RISK_THRESHOLD*100}, MEDIUM={settings.MEDIUM_RISK_THRESHOLD*100}")

        # Determine risk level (with override logic for coordinated fraud)
        risk_level = self._determine_risk_level(final_score, ml_score, rule_score, graph_score)

        # DEBUG: Log risk level determination
        print(f"[RISK_DEBUG] RISK_LEVEL_DETERMINED: user_id={user_id}, risk_level={risk_level}, final_score={final_score:.2f}")

        # Determine primary reason
        primary_reason = self._determine_primary_reason(
            ml_score, rule_score, graph_score
        )

        # Get recommended action
        recommended_action = self._get_recommended_action(risk_level)

        # Create risk event
        risk_event = RiskEvent(
            user_id=user_id,
            risk_score=Decimal(str(final_score)),
            risk_probability=Decimal(str(ml_probability)),  # Use ML probability
            risk_level=risk_level,
            primary_reason=primary_reason,
            recommended_action=recommended_action,
            detected_at=datetime.now(timezone.utc),
            event_type=self._determine_event_type(primary_reason),
            ml_score=Decimal(str(ml_score)),
            rule_score=Decimal(str(rule_score)),
            graph_score=Decimal(str(graph_score)),
            pipeline_run_id=pipeline_run_id,
            model_version=model_version,
        )

        self.db.add(risk_event)
        await self.db.flush()  # Flush to get risk_event.id before creating factors

        # DEBUG: Log RiskEvent creation after flush
        print(f"[RISK_DEBUG] RISKEVENT_CREATED: user_id={user_id}, risk_event.id={risk_event.id}, risk_level={risk_event.risk_level}, risk_score={risk_event.risk_score}")

        # Create risk factors
        await self._create_risk_factors(risk_event, feature)

        await self.db.commit()
        await self.db.refresh(risk_event)

        # Update user's current risk score
        user = await self.db.get(User, user_id)
        if user:
            user.current_risk_score = Decimal(str(final_score))
            user.risk_level = risk_level
            # DEBUG: Log User update
            print(f"[RISK_DEBUG] USER_UPDATED: user_id={user_id}, user.risk_level={user.risk_level}, user.current_risk_score={user.current_risk_score}")
            await self.db.commit()

        return risk_event

    async def score_all_users(
        self,
        pipeline_run_id: Optional[str] = None,
        model_version: Optional[str] = None
    ) -> int:
        """
        Score all users with features.

        Args:
            pipeline_run_id: Optional pipeline run identifier for traceability
            model_version: Optional model version used for scoring

        Returns:
            Number of risk events created
        """
        result = await self.db.execute(select(FeatureTable.user_id))
        user_ids = [row[0] for row in result]

        count = 0
        for user_id in user_ids:
            await self.score_user(user_id, pipeline_run_id, model_version)
            count += 1

        return count

    async def _calculate_ml_score(self, feature: FeatureTable) -> tuple[float, float]:
        """
        Calculate ML-based risk score using LightGBM model.

        Returns:
            (risk_probability, risk_score_0_100)
        """
        # Prepare feature dictionary
        features_dict = {
            'shared_device_count': feature.shared_device_count or 0,
            'linked_account_count': feature.linked_account_count or 0,
            'unique_ip_count': feature.unique_ip_count or 0,
            'trade_frequency_24h': feature.trade_frequency_24h or 0,
            'trade_frequency_7d': feature.trade_frequency_7d or 0,
            'opposite_trade_ratio': float(feature.opposite_trade_ratio) if feature.opposite_trade_ratio else 0.0,
            'avg_trade_size': float(feature.avg_trade_size) if feature.avg_trade_size else 0.0,
            'trade_volume_24h': float(feature.trade_volume_24h) if feature.trade_volume_24h else 0.0,
            'account_age_days': feature.account_age_days or 0,
            'active_days_count': feature.active_days_count or 0,
            'withdrawal_risk_score': float(feature.withdrawal_risk_score) if feature.withdrawal_risk_score else 0.0,
            'withdrawal_frequency_24h': feature.withdrawal_frequency_24h or 0,
            'withdrawal_volume_24h': float(feature.withdrawal_volume_24h) if feature.withdrawal_volume_24h else 0.0,
            'first_withdrawal_flag': 1 if feature.first_withdrawal_flag else 0,
        }

        # Get prediction from ML service
        probability, score = self.ml_service.predict_proba(features_dict)

        return probability, score

    async def _calculate_rule_score(self, feature: FeatureTable) -> float:
        """
        Calculate rule-based risk score.

        These are explicit expert rules for clear risk signals.
        """
        score = 0.0

        # Deterministic scoring rule (distinct from the contextual "Account Age" factor
        # emitted by _create_risk_factors). This is the ONLY account-age-related rule and it
        # contributes to rule_score only when BOTH conditions hold.
        # Rule: New account with high activity
        if feature.account_age_days and feature.account_age_days < 7:
            if feature.trade_frequency_24h and feature.trade_frequency_24h > 50:
                score += 40

        # Rule: High opposite trade ratio (coordinated trading indicator)
        if feature.opposite_trade_ratio and float(feature.opposite_trade_ratio) > 0.4:
            score += 35

        # Rule: Multiple shared devices
        if feature.shared_device_count and feature.shared_device_count > 3:
            score += 30

        # Rule: High withdrawal frequency
        if feature.withdrawal_frequency_24h and feature.withdrawal_frequency_24h > 5:
            score += 25

        # Rule: First withdrawal to new address + high amount
        if feature.first_withdrawal_flag and feature.withdrawal_frequency_24h:
            score += 20

        return round(min(score, 100), 2)

    async def _calculate_graph_score(self, user_id: str) -> float:
        """
        Calculate graph-based risk score.

        Based on cluster membership and position in network.
        """
        score = 0.0

        # Check if user is in any suspicious cluster
        from sqlalchemy import select
        from app.models.database import ClusterMember, AccountCluster

        result = await self.db.execute(
            select(ClusterMember, AccountCluster)
            .join(AccountCluster, ClusterMember.cluster_id == AccountCluster.cluster_id)
            .where(ClusterMember.user_id == user_id)
        )

        for member, cluster in result:
            # Base score from cluster risk
            score += float(cluster.risk_score) * 0.3

            # Additional score for cluster size
            score += min(cluster.member_count * 5, 30)

            # Hub users get higher score
            if member.role_in_cluster == "hub":
                score += 20

        return round(min(score, 100), 2)

    def _combine_scores(
        self,
        ml_score: float,
        rule_score: float,
        graph_score: float
    ) -> float:
        """Combine component scores using configured weights."""
        final_score = (
            ml_score * settings.ML_WEIGHT +
            rule_score * settings.RULE_WEIGHT +
            graph_score * settings.GRAPH_WEIGHT
        )
        return round(final_score, 2)

    def _determine_risk_level(self, final_score: float, ml_score: float = 0, rule_score: float = 0, graph_score: float = 0) -> str:
        """
        Determine risk level from final score with business override logic.

        Critical Override:
        ---------------
        Certain coordinated fraud scenarios should not rely only on weighted scoring.
        When ML anomaly detection, explicit rules, and graph network signals all agree
        on high risk, severity should escalate regardless of weighted score.

        This represents coordinated fraud ring / attack scenarios where:
        - ML: Strong behavioral anomaly detected
        - Rules: Explicit suspicious behavior patterns
        - Graph: Network connections to suspicious entities

        Override Thresholds:
        - ML score >= 80: Strong behavioral anomaly
        - Rule score >= 40: Multiple explicit rule violations
        - Graph score >= 50: Significant network risk relationships

        This rule acts as a business severity escalation for coordinated threats,
        not a replacement for model scoring.

        Normal Threshold Logic:
        ----------------------
        After override check, apply standard weighted score thresholds.
        - CRITICAL: final_score >= 90 (within HIGH level)
        - HIGH: final_score >= 70
        - MEDIUM: final_score >= 40
        - LOW: below 40

        Args:
            final_score: Combined weighted score (0-100)
            ml_score: ML component score (0-100)
            rule_score: Rule engine score (0-100)
            graph_score: Graph network score (0-100)

        Returns:
            Risk level as string (CRITICAL, HIGH, MEDIUM, LOW)
        """
        # Critical override for coordinated fraud scenarios
        # When all three detection systems agree on high risk, escalate to CRITICAL
        if (
            graph_score >= 50
            and ml_score >= 80
            and rule_score >= 40
        ):
            print(f"[RISK_DEBUG] OVERRIDE_CRITICAL: graph_score={graph_score:.2f}>=50, ml_score={ml_score:.2f}>=80, rule_score={rule_score:.2f}>=40")
            return RiskLevel.CRITICAL.value

        # Normal threshold-based classification
        # Thresholds: HIGH >= 70, MEDIUM >= 50, LOW < 50
        # CRITICAL via override requires: graph_score >= 50 AND ml_score >= 80 AND rule_score >= 40
        # CRITICAL via scoring requires: final_score >= 90
        high_threshold = settings.HIGH_RISK_THRESHOLD * 100
        medium_threshold = settings.MEDIUM_RISK_THRESHOLD * 100

        print(f"[RISK_DEBUG] THRESHOLD_CHECK: final_score={final_score:.2f}, high_threshold={high_threshold}, medium_threshold={medium_threshold}")

        if final_score >= high_threshold:
            result = RiskLevel.CRITICAL.value if final_score >= 90 else RiskLevel.HIGH.value
            print(f"[RISK_DEBUG] THRESHOLD_HIGH: final_score>={high_threshold} -> {result}")
            return result
        elif final_score >= medium_threshold:
            print(f"[RISK_DEBUG] THRESHOLD_MEDIUM: final_score>={medium_threshold} -> MEDIUM")
            return RiskLevel.MEDIUM.value
        else:
            print(f"[RISK_DEBUG] THRESHOLD_LOW: final_score<{medium_threshold} -> LOW")
            return RiskLevel.LOW.value

    def _determine_primary_reason(
        self,
        ml_score: float,
        rule_score: float,
        graph_score: float
    ) -> str:
        """Determine primary risk reason based on highest component."""
        scores = {
            "ML Pattern Detection": ml_score,
            "Explicit Risk Rules": rule_score,
            "Graph Network Analysis": graph_score,
        }

        highest = max(scores.items(), key=lambda x: x[1])
        return highest[0]

    def _get_recommended_action(self, risk_level: str) -> str:
        """Get recommended action based on risk level."""
        actions = {
            RiskLevel.CRITICAL.value: "Immediate Investigation",
            RiskLevel.HIGH.value: "Manual Review",
            RiskLevel.MEDIUM.value: "Monitor",
            RiskLevel.LOW.value: "No Action",
        }
        return actions.get(risk_level, "No Action")

    def _determine_event_type(self, primary_reason: str) -> str:
        """Determine event type from primary reason."""
        if "Graph" in primary_reason:
            return "device_sharing"
        elif "Rules" in primary_reason:
            return "suspicious_activity"
        else:
            return "pattern_anomaly"

    async def _create_risk_factors(
        self,
        risk_event: RiskEvent,
        feature: FeatureTable
    ):
        """Create detailed risk factors for the event."""
        # These are CONTEXTUAL risk factors (descriptive evidence for the analyst/LLM) drawn
        # from the feature table. A factor here does NOT by itself trigger a score. It is
        # distinct from:
        #   (A) deterministic scoring rules -> see _calculate_rule_score / _combine_scores.
        #       The only account-age rule is "New account with high activity":
        #         account_age_days < 7 AND trade_frequency_24h > 50 -> rule_score += 40
        #   (B) policy-backed guidance -> policies/*.md, surfaced via citations.
        # In particular, account_age_days is emitted for ANY age > 0, so it is labelled
        # "Account Age" (context), NOT "New Account Risk" (which would imply a threshold/rule).

        # Base factor mapping (excluding opposite_trade_ratio which is handled specially)
        #
        # withdrawal_risk_score is deliberately ABSENT. It is the fraction of
        # withdrawals sent to newly encountered addresses — the SAME underlying
        # observation as first_withdrawal_flag (both derive from
        # Withdrawal.is_new_address; flag is true iff ratio > 0, verified
        # across all 2001 feature rows). Persisting it produced a second,
        # redundant finding ("Abnormal Withdrawal Behavior") for a condition
        # already reported as the "First withdrawal to new address" rule. The
        # ratio now travels with that rule finding instead (see
        # EvidenceService._derive_rule_evidence).
        factor_mapping = {
            "shared_device_count": "Shared Device Relationships",
            "linked_account_count": "Linked Account Network",
            "trade_frequency_24h": "High Trading Frequency",
            "account_age_days": "Account Age",
        }

        # Process standard factors
        for attr, name in factor_mapping.items():
            value = getattr(feature, attr)
            if value is not None and value != 0:
                # Only create factor for significant values
                if isinstance(value, (int, float)) and value > 0:
                    factor = RiskFactor(
                        risk_event_id=risk_event.id,
                        factor_name=name,
                        factor_value=float(value) if isinstance(value, Decimal) else value,
                        factor_description=self._get_factor_description(name, value),
                    )
                    self.db.add(factor)

        # Handle opposite_trade_ratio separately to provide semantic clarity
        opposite_trade_ratio = feature.opposite_trade_ratio
        if opposite_trade_ratio is not None and opposite_trade_ratio != 0:
            value = float(opposite_trade_ratio)
            if value > 0:
                # Determine label and description based on rule threshold
                # Rule threshold: > 0.4 triggers coordinated-trading rule (see _calculate_rule_score)
                rule_threshold = 0.4
                rule_triggered = value > rule_threshold

                if rule_triggered:
                    factor_name = "Coordinated Trading Pattern"
                else:
                    factor_name = "Opposite Trade Ratio"

                factor = RiskFactor(
                    risk_event_id=risk_event.id,
                    factor_name=factor_name,
                    factor_value=value,
                    factor_description=self._get_opposite_trade_description(value, rule_triggered, rule_threshold),
                )
                self.db.add(factor)

    def _get_factor_description(self, factor_name: str, value: Any) -> str:
        """Get human-readable description for a factor.

        Count-bearing descriptions derive their noun and verb form from the
        value, so count == 1 reads grammatically ("1 shared device was used")
        — the persisted description is authoritative input to the explanation
        prompt. shared_device_count counts DEVICES (not accounts); the linked
        account count is the separate "Linked Account Network" factor.
        """
        count = int(value)
        descriptions = {
            "Shared Device Relationships": (
                f"{counted_noun(count, 'shared device', 'shared devices')} "
                f"{was_were(count)} used by this account and other users"
            ),
            "Linked Account Network": (
                f"{counted_noun(count, 'connected account', 'connected accounts')} "
                f"{was_were(count)} detected through shared devices"
            ),
            "High Trading Frequency": f"{count} trades in 24h period",
            # Contextual account-age evidence. Wording must NOT imply a policy threshold, a
            # "new account" classification, or any rule trigger. (The thresholded new-account
            # rule lives in _calculate_rule_score as "New account with high activity".)
            "Account Age": f"Account is {int(value)} days old (contextual account-age evidence; not a policy threshold)",
        }
        return descriptions.get(factor_name, f"Value: {value}")

    def _get_opposite_trade_description(self, value: float, rule_triggered: bool, rule_threshold: float) -> str:
        """
        Get human-readable description for opposite trade ratio factor.

        Semantics:
        - value > 0: Factor is created (observed signal)
        - value > 0.4: Coordinated-trading rule is triggered (score contribution)

        This method provides clear distinction between:
        1. Observed opposite-trading behavior (below threshold)
        2. Coordinated-trading rule triggered (above threshold)

        Args:
            value: The opposite_trade_ratio value
            rule_triggered: Whether the coordinated-trading rule was triggered (> 0.4)
            rule_threshold: The rule threshold (0.4)

        Returns:
            Human-readable description with clear semantic status
        """
        percentage = value * 100
        threshold_percent = rule_threshold * 100

        # Wording mirrors EvidenceService's threshold-finding descriptions so
        # the below-threshold observation vs threshold-triggered rule
        # distinction is identical everywhere it is surfaced.
        if rule_triggered:
            return (
                f"An opposite-trade ratio of {percentage:.2f}% exceeded the "
                f"{threshold_percent:.0f}% threshold, triggering the "
                f"coordinated trading rule."
            )
        else:
            return (
                f"An opposite-trade ratio of {percentage:.2f}% was observed, "
                f"which is below the {threshold_percent:.0f}% threshold for "
                f"the coordinated trading rule."
            )


class CaseManagementService:
    """Service for managing investigation cases."""

    def __init__(self, db: AsyncSession):
        """Initialize case service with database session."""
        self.db = db

    async def create_case(self, user_id: str, risk_event_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new investigation case."""
        from app.models.database import Case

        case_id = f"CASE_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{user_id}"

        case = Case(
            case_id=case_id,
            user_id=user_id,
            risk_event_id=risk_event_id,
            status=CaseStatus.NEW.value,
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(case)
        await self.db.commit()
        await self.db.refresh(case)

        return {
            "case_id": case.case_id,
            "status": case.status,
            "created_at": case.created_at,
        }

    async def update_case(
        self,
        case_id: str,
        status: Optional[str] = None,
        assigned_analyst: Optional[str] = None,
        decision: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing case."""
        from app.models.database import Case

        case = await self.db.execute(
            select(Case).where(Case.case_id == case_id)
        )
        case_obj = case.scalar_one_or_none()

        if not case_obj:
            raise ValueError(f"Case {case_id} not found")

        if status:
            case_obj.status = status
            if status == CaseStatus.CLOSED.value:
                case_obj.closed_at = datetime.now(timezone.utc)

        if assigned_analyst:
            case_obj.assigned_analyst = assigned_analyst

        if decision:
            case_obj.decision = decision

        if notes:
            case_obj.notes = notes

        case_obj.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(case_obj)

        return {
            "case_id": case_obj.case_id,
            "status": case_obj.status,
            "updated_at": case_obj.updated_at,
        }
